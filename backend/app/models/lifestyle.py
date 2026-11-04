"""Tracking, pantry, household, budget, prices, sharing and editorial content."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models._common import IdMixin, JSONType, TimestampMixin, utcnow


class WaterLog(IdMixin, Base):
    __tablename__ = "water_logs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("family_profiles.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    ml: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BodyMetric(IdMixin, Base):
    """Weight check-ins for weight goals. Stored per profile, never shared."""

    __tablename__ = "body_metrics"
    __table_args__ = (UniqueConstraint("profile_id", "day"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("family_profiles.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[float] = mapped_column(Float)


class Household(IdMixin, TimestampMixin, Base):
    __tablename__ = "households"

    name: Mapped[str] = mapped_column(String(80))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    members: Mapped[list["HouseholdMember"]] = relationship(cascade="all, delete-orphan")


class HouseholdMember(IdMixin, Base):
    __tablename__ = "household_members"
    __table_args__ = (UniqueConstraint("household_id", "invited_email"),)

    household_id: Mapped[str] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    invited_email: Mapped[str] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(10), default="member")  # owner | member
    status: Mapped[str] = mapped_column(String(10), default="invited")  # invited | active
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PantryItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "pantry_items"

    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id", ondelete="SET NULL"), index=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[str | None] = mapped_column(String(40))
    location: Mapped[str] = mapped_column(String(20), default="cupboard")  # fridge | freezer | cupboard
    expires_on: Mapped[date | None] = mapped_column(Date, index=True)
    opened_on: Mapped[date | None] = mapped_column(Date)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Budget(IdMixin, TimestampMixin, Base):
    """Monthly grocery budget for a person, or for a household when household_id is set."""

    __tablename__ = "budgets"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), unique=True)
    monthly_amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")


class Purchase(IdMixin, Base):
    """Shopping history and budget tracking."""

    __tablename__ = "purchases"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id", ondelete="SET NULL"), index=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[str | None] = mapped_column(String(40))
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    store: Mapped[str | None] = mapped_column(String(120))
    purchased_on: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PriceObservation(IdMixin, Base):
    """A price someone saw on a shelf. Crowd-reported, never presented as a retailer feed."""

    __tablename__ = "price_observations"

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    store: Mapped[str] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(2), index=True)
    observed_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SharedReport(IdMixin, Base):
    """Public link to a product report. Never includes the sharer's profiles."""

    __tablename__ = "shared_reports"

    token: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Article(IdMixin, TimestampMixin, Base):
    """Educational content managed in the admin dashboard."""

    __tablename__ = "articles"

    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String(30), index=True)  # nutrition|processing|ingredients|safety|african
    region: Mapped[str | None] = mapped_column(String(8))
    source_keys: Mapped[list] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(10), default="draft", index=True)  # draft | published
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_id: Mapped[str | None] = mapped_column(String(36))
