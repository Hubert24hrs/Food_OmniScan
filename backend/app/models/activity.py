from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models._common import IdMixin, JSONType, TimestampMixin, utcnow


class FoodScan(IdMixin, Base):
    """Raw scan event log (every attempt, including failures, for OCR/scan quality monitoring)."""

    __tablename__ = "food_scans"
    __table_args__ = (UniqueConstraint("user_id", "client_id"),)

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str | None] = mapped_column(String(36))
    scan_type: Mapped[str] = mapped_column(
        String(20)
    )  # barcode | ingredients_ocr | nutrition_ocr | front_photo | search
    barcode: Mapped[str | None] = mapped_column(String(14), index=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(20))  # found | not_found | invalid | error
    confidence: Mapped[float | None] = mapped_column(Float)
    ocr_text: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    client_id: Mapped[str | None] = mapped_column(String(64))  # idempotency key for offline-queued scans
    client_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ScanHistory(IdMixin, Base):
    """User-facing history: one row per (user, product), bumped on re-scan."""

    __tablename__ = "scan_history"
    __table_args__ = (UniqueConstraint("user_id", "product_id"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    profile_id: Mapped[str | None] = mapped_column(String(36))
    first_scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    scan_count: Mapped[int] = mapped_column(Integer, default=1)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)


class ProductAlternative(IdMixin, Base):
    __tablename__ = "product_alternatives"
    __table_args__ = (UniqueConstraint("product_id", "alternative_product_id", "methodology_version"),)

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    alternative_product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    methodology_version: Mapped[str] = mapped_column(String(20))
    score_delta: Mapped[int] = mapped_column(Integer)
    reasons: Mapped[dict] = mapped_column(JSONType, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProductComparison(IdMixin, Base):
    __tablename__ = "product_comparisons"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_ids: Mapped[list] = mapped_column(JSONType)
    objective: Mapped[str] = mapped_column(String(30))
    result: Mapped[dict] = mapped_column(JSONType)
    share_token: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FavouriteProduct(IdMixin, Base):
    __tablename__ = "favourite_products"
    __table_args__ = (UniqueConstraint("user_id", "product_id", "list_type"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    list_type: Mapped[str] = mapped_column(String(20), default="favourite")  # favourite | trusted | incompatible
    profile_id: Mapped[str | None] = mapped_column(String(36))
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserReview(IdMixin, TimestampMixin, Base):
    __tablename__ = "user_reviews"
    __table_args__ = (UniqueConstraint("user_id", "product_id"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(120))
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="published")  # published | hidden


class CommunitySubmission(IdMixin, TimestampMixin, Base):
    __tablename__ = "community_submissions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="new_product")  # new_product | correction | report
    barcode: Mapped[str | None] = mapped_column(String(14), index=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    payload: Mapped[dict] = mapped_column(JSONType)
    images: Mapped[list] = mapped_column(JSONType, default=list)
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(36))
    review_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ShoppingList(IdMixin, TimestampMixin, Base):
    __tablename__ = "shopping_lists"

    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    shared_with_family: Mapped[bool] = mapped_column(Boolean, default=False)

    items: Mapped[list["ShoppingListItem"]] = relationship(
        cascade="all, delete-orphan", order_by="ShoppingListItem.created_at"
    )


class ShoppingListItem(IdMixin, Base):
    __tablename__ = "shopping_list_items"

    list_id: Mapped[str] = mapped_column(ForeignKey("shopping_lists.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[str | None] = mapped_column(String(40))
    checked: Mapped[bool] = mapped_column(Boolean, default=False)
    added_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FoodDiary(IdMixin, Base):
    __tablename__ = "food_diaries"
    __table_args__ = (UniqueConstraint("profile_id", "day"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("family_profiles.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date, index=True)

    entries: Mapped[list["MealEntry"]] = relationship(cascade="all, delete-orphan", order_by="MealEntry.created_at")


class MealEntry(IdMixin, Base):
    __tablename__ = "meal_entries"

    diary_id: Mapped[str] = mapped_column(ForeignKey("food_diaries.id", ondelete="CASCADE"), index=True)
    meal_type: Mapped[str] = mapped_column(String(20))  # breakfast | lunch | dinner | snack
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    description: Mapped[str] = mapped_column(String(200))
    quantity_g: Mapped[float | None] = mapped_column(Float)
    energy_kcal: Mapped[float | None] = mapped_column(Float)
    protein: Mapped[float | None] = mapped_column(Float)
    carbohydrates: Mapped[float | None] = mapped_column(Float)
    fat: Mapped[float | None] = mapped_column(Float)
    fiber: Mapped[float | None] = mapped_column(Float)
    sugars: Mapped[float | None] = mapped_column(Float)
    sodium: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(20))  # product | manual | ai_estimate
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MealPlan(IdMixin, TimestampMixin, Base):
    __tablename__ = "meal_plans"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str | None] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date | None] = mapped_column(Date)
    days: Mapped[list] = mapped_column(JSONType, default=list)  # [{day, meals:[{meal_type, recipe_id|text}]}]


class Recipe(IdMixin, TimestampMixin, Base):
    __tablename__ = "recipes"

    title: Mapped[str] = mapped_column(String(200), index=True)
    cuisine: Mapped[str | None] = mapped_column(String(60))
    region: Mapped[str | None] = mapped_column(String(8))
    ingredients: Mapped[list] = mapped_column(JSONType, default=list)
    steps: Mapped[list] = mapped_column(JSONType, default=list)
    nutrition: Mapped[dict | None] = mapped_column(JSONType)
    nutrition_is_estimate: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str | None] = mapped_column(String(300))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(String(36))
