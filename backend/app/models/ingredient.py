from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models._common import IdMixin, JSONType, TimestampMixin

CONCERN_LEVELS = ("beneficial", "neutral", "caution", "concern", "unknown")


class Ingredient(IdMixin, TimestampMixin, Base):
    __tablename__ = "ingredients"

    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    us_name: Mapped[str | None] = mapped_column(String(200))  # US label name, e.g. "Red 40" (US is the default locale)
    category: Mapped[str] = mapped_column(String(60), index=True)  # e.g. colour, sweetener, oil, grain
    function: Mapped[str | None] = mapped_column(String(300))  # why manufacturers use it
    plain_language: Mapped[str | None] = mapped_column(Text)
    concern_level: Mapped[str] = mapped_column(String(20), default="neutral", index=True)
    concern_summary: Mapped[str | None] = mapped_column(Text)
    e_number: Mapped[str | None] = mapped_column(String(10), index=True)
    is_additive: Mapped[bool] = mapped_column(Boolean, default=False)
    vegan: Mapped[str] = mapped_column(String(8), default="yes")  # yes | no | maybe
    vegetarian: Mapped[str] = mapped_column(String(8), default="yes")
    halal_concern: Mapped[str] = mapped_column(String(8), default="no")  # no | yes | maybe
    allergen_code: Mapped[str | None] = mapped_column(String(40))
    flags: Mapped[list] = mapped_column(JSONType, default=list)  # seed_oil, artificial_sweetener, upf_marker...
    fodmap: Mapped[str | None] = mapped_column(String(8))  # high | low | None (unknown)
    regulatory_notes: Mapped[list] = mapped_column(JSONType, default=list)  # [{jurisdiction, note, source_key}]
    source_keys: Mapped[list] = mapped_column(JSONType, default=list)  # scientific_sources.key
    verification_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | verified
    verified_by: Mapped[str | None] = mapped_column(String(36))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    synonyms: Mapped[list["IngredientSynonym"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )
    additive: Mapped["FoodAdditive | None"] = relationship(back_populates="ingredient", uselist=False)


class IngredientSynonym(IdMixin, Base):
    __tablename__ = "ingredient_synonyms"
    __table_args__ = (UniqueConstraint("term", "language"),)

    ingredient_id: Mapped[str] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"), index=True)
    term: Mapped[str] = mapped_column(String(160), index=True)  # normalised (lowercase, no accents)
    language: Mapped[str] = mapped_column(String(8), default="en")
    region: Mapped[str | None] = mapped_column(String(8))  # e.g. NG for "groundnut"

    ingredient: Mapped[Ingredient] = relationship(back_populates="synonyms")


class FoodAdditive(IdMixin, Base):
    __tablename__ = "food_additives"

    e_number: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    ingredient_id: Mapped[str] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"), unique=True)
    additive_class: Mapped[str] = mapped_column(String(60))
    adi_mg_per_kg_bw: Mapped[float | None] = mapped_column(Float)
    adi_source_key: Mapped[str | None] = mapped_column(String(80))
    eu_status: Mapped[str | None] = mapped_column(String(40))  # authorised | not_authorised | restricted
    us_status: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)

    ingredient: Mapped[Ingredient] = relationship(back_populates="additive")
