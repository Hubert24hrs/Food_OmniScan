from datetime import datetime

from sqlalchemy import (
    Boolean,
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
from app.models._common import IdMixin, JSONType, TimestampMixin


class Manufacturer(IdMixin, TimestampMixin, Base):
    __tablename__ = "manufacturers"

    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    country: Mapped[str | None] = mapped_column(String(2))
    website: Mapped[str | None] = mapped_column(String(300))
    parent_company: Mapped[str | None] = mapped_column(String(200))
    transparency_notes: Mapped[str | None] = mapped_column(Text)


class FoodBrand(IdMixin, TimestampMixin, Base):
    __tablename__ = "food_brands"

    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    manufacturer_id: Mapped[str | None] = mapped_column(ForeignKey("manufacturers.id", ondelete="SET NULL"))
    country: Mapped[str | None] = mapped_column(String(2))


class FoodCategory(IdMixin, Base):
    __tablename__ = "food_categories"

    code: Mapped[str] = mapped_column(String(160), unique=True, index=True)  # e.g. OFF tag "en:breakfast-cereals"
    name: Mapped[str] = mapped_column(String(160))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("food_categories.id", ondelete="SET NULL"))
    is_beverage: Mapped[bool] = mapped_column(Boolean, default=False)


class Product(IdMixin, TimestampMixin, Base):
    __tablename__ = "products"

    name: Mapped[str | None] = mapped_column(String(300), index=True)
    generic_name: Mapped[str | None] = mapped_column(String(300))
    brand_id: Mapped[str | None] = mapped_column(ForeignKey("food_brands.id", ondelete="SET NULL"), index=True)
    brand_text: Mapped[str | None] = mapped_column(String(300))
    category_id: Mapped[str | None] = mapped_column(ForeignKey("food_categories.id", ondelete="SET NULL"), index=True)
    categories_tags: Mapped[list] = mapped_column(JSONType, default=list)
    quantity: Mapped[str | None] = mapped_column(String(80))
    serving_size: Mapped[str | None] = mapped_column(String(80))
    countries_tags: Mapped[list] = mapped_column(JSONType, default=list)
    labels_tags: Mapped[list] = mapped_column(JSONType, default=list)  # en:organic, en:halal...
    packaging_text: Mapped[str | None] = mapped_column(Text)
    packaging_tags: Mapped[list] = mapped_column(JSONType, default=list)
    ingredients_text: Mapped[str | None] = mapped_column(Text)
    ingredients_lang: Mapped[str | None] = mapped_column(String(8))
    allergens_tags: Mapped[list] = mapped_column(JSONType, default=list)
    traces_tags: Mapped[list] = mapped_column(JSONType, default=list)
    additives_tags: Mapped[list] = mapped_column(JSONType, default=list)
    ingredients_analysis_tags: Mapped[list] = mapped_column(JSONType, default=list)
    nova_group: Mapped[int | None] = mapped_column(Integer)
    nova_source: Mapped[str | None] = mapped_column(String(20))  # off | estimated | admin
    nutriscore_grade: Mapped[str | None] = mapped_column(String(2))
    image_url: Mapped[str | None] = mapped_column(String(500))
    nafdac_number: Mapped[str | None] = mapped_column(String(40), index=True)
    is_beverage: Mapped[bool] = mapped_column(Boolean, default=False)
    # Provenance
    source: Mapped[str] = mapped_column(String(20), index=True)  # off | usda | community | admin
    source_id: Mapped[str | None] = mapped_column(String(80))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_license: Mapped[str | None] = mapped_column(String(120))
    raw_data: Mapped[dict | None] = mapped_column(JSONType)  # untouched provider payload subset
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active | hidden
    completeness: Mapped[float] = mapped_column(Float, default=0.0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[str | None] = mapped_column(String(36))
    search_text: Mapped[str | None] = mapped_column(Text)  # denormalised name/brand/category for search

    barcodes: Mapped[list["ProductBarcode"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    images: Mapped[list["ProductImage"]] = relationship(cascade="all, delete-orphan")
    nutrition: Mapped[list["NutritionFacts"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    ingredients: Mapped[list["ProductIngredient"]] = relationship(
        cascade="all, delete-orphan", order_by="ProductIngredient.position"
    )
    brand: Mapped[FoodBrand | None] = relationship()
    category: Mapped[FoodCategory | None] = relationship()

    def nutrition_per_100(self) -> "NutritionFacts | None":
        for n in self.nutrition:
            if n.basis in ("100g", "100ml"):
                return n
        return None


class ProductBarcode(IdMixin, Base):
    __tablename__ = "product_barcodes"

    # Normalised GTIN-14 is the duplicate-prevention key: UPC-A 0123... and EAN-13 00123... collide.
    gtin14: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    barcode: Mapped[str] = mapped_column(String(14), index=True)  # as printed
    format: Mapped[str] = mapped_column(String(10))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)

    product: Mapped[Product] = relationship(back_populates="barcodes")


class ProductImage(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_images"

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # front | ingredients | nutrition | packaging | other
    url: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(20))
    uploaded_by: Mapped[str | None] = mapped_column(String(36))


class ProductIngredient(IdMixin, Base):
    __tablename__ = "product_ingredients"

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    raw_text: Mapped[str] = mapped_column(String(300))
    ingredient_slug: Mapped[str | None] = mapped_column(String(120), index=True)
    percent: Mapped[float | None] = mapped_column(Float)
    match_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    analysis_version: Mapped[str | None] = mapped_column(String(20))


class NutritionFacts(IdMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_facts"
    __table_args__ = (UniqueConstraint("product_id", "basis"),)

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    basis: Mapped[str] = mapped_column(String(10))  # 100g | 100ml | serving
    serving_size_g: Mapped[float | None] = mapped_column(Float)
    energy_kcal: Mapped[float | None] = mapped_column(Float)
    energy_kj: Mapped[float | None] = mapped_column(Float)
    fat: Mapped[float | None] = mapped_column(Float)
    saturated_fat: Mapped[float | None] = mapped_column(Float)
    trans_fat: Mapped[float | None] = mapped_column(Float)
    carbohydrates: Mapped[float | None] = mapped_column(Float)
    sugars: Mapped[float | None] = mapped_column(Float)
    added_sugars: Mapped[float | None] = mapped_column(Float)
    fiber: Mapped[float | None] = mapped_column(Float)
    protein: Mapped[float | None] = mapped_column(Float)
    salt: Mapped[float | None] = mapped_column(Float)
    sodium: Mapped[float | None] = mapped_column(Float)  # grams
    cholesterol_mg: Mapped[float | None] = mapped_column(Float)
    fruits_veg_nuts_pct: Mapped[float | None] = mapped_column(Float)
    extra: Mapped[dict] = mapped_column(JSONType, default=dict)  # vitamins/minerals as reported
    source: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    product: Mapped[Product] = relationship(back_populates="nutrition")
