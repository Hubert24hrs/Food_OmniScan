from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models._common import IdMixin, JSONType, TimestampMixin, utcnow

ROLES = ("user", "contributor", "moderator", "admin")


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(200))
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="user", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    country: Mapped[str | None] = mapped_column(String(2))  # ISO 3166-1 alpha-2
    locale: Mapped[str] = mapped_column(String(10), default="en")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Consent and privacy. Dietary/allergy data is treated as sensitive health data.
    consent_terms_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_health_data_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_ai_history: Mapped[bool] = mapped_column(Boolean, default=False)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)

    settings: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    family_profiles: Mapped[list["FamilyProfile"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", order_by="FamilyProfile.created_at"
    )


class UserProfile(IdMixin, TimestampMixin, Base):
    """Per-account settings (table name follows the spec: user_profiles)."""

    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    active_family_profile_id: Mapped[str | None] = mapped_column(String(36))
    units: Mapped[str] = mapped_column(String(10), default="metric")
    theme: Mapped[str] = mapped_column(String(10), default="system")
    notification_prefs: Mapped[dict] = mapped_column(JSONType, default=dict)

    user: Mapped[User] = relationship(back_populates="settings")


class FamilyProfile(IdMixin, TimestampMixin, Base):
    """An eater: the account holder ("Me") or a household member."""

    __tablename__ = "family_profiles"

    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    relationship_label: Mapped[str | None] = mapped_column(String(40))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    birth_year: Mapped[int | None] = mapped_column(Integer)
    avatar_color: Mapped[str | None] = mapped_column(String(9))
    goals: Mapped[dict] = mapped_column(JSONType, default=dict)  # e.g. {"kcal": 2000, "protein_g": 90}

    owner: Mapped[User] = relationship(back_populates="family_profiles")
    dietary_preferences: Mapped[list["DietaryPreference"]] = relationship(cascade="all, delete-orphan")
    allergens: Mapped[list["AllergenProfile"]] = relationship(cascade="all, delete-orphan")
    avoid_rules: Mapped[list["IngredientAvoidanceRule"]] = relationship(cascade="all, delete-orphan")


class DietaryPreference(IdMixin, Base):
    __tablename__ = "dietary_preferences"
    __table_args__ = (UniqueConstraint("profile_id", "code"),)

    profile_id: Mapped[str] = mapped_column(ForeignKey("family_profiles.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(40))  # vegan, keto, halal, low_sodium...
    strict: Mapped[bool] = mapped_column(Boolean, default=True)


class AllergenProfile(IdMixin, Base):
    __tablename__ = "allergen_profiles"
    __table_args__ = (UniqueConstraint("profile_id", "allergen_code"),)

    profile_id: Mapped[str] = mapped_column(ForeignKey("family_profiles.id", ondelete="CASCADE"), index=True)
    allergen_code: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20), default="severe")  # intolerance|mild|severe|anaphylaxis
    avoid_traces: Mapped[bool] = mapped_column(Boolean, default=True)


class IngredientAvoidanceRule(IdMixin, Base):
    __tablename__ = "ingredient_avoidance_rules"
    __table_args__ = (UniqueConstraint("profile_id", "term"),)

    profile_id: Mapped[str] = mapped_column(ForeignKey("family_profiles.id", ondelete="CASCADE"), index=True)
    term: Mapped[str] = mapped_column(String(120))  # normalised term or ingredient slug
    ingredient_slug: Mapped[str | None] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(String(200))


class AdminUser(IdMixin, Base):
    """Grant record for elevated roles (who granted what, when)."""

    __tablename__ = "admin_users"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    role: Mapped[str] = mapped_column(String(20))
    granted_by: Mapped[str | None] = mapped_column(String(36))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
