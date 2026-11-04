from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models._common import IdMixin, TimestampMixin

EVIDENCE_TYPES = ("product_measurement", "regulatory", "published_research", "estimate", "unverified")
EVIDENCE_QUALITY = ("high", "moderate", "low", "very_low")


class ScientificSource(IdMixin, TimestampMixin, Base):
    __tablename__ = "scientific_sources"

    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)  # stable reference key
    title: Mapped[str] = mapped_column(String(500))
    authors: Mapped[str | None] = mapped_column(String(500))
    publisher: Mapped[str | None] = mapped_column(String(200))
    year: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(String(500))
    doi: Mapped[str | None] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(
        String(30)
    )  # regulation | guideline | peer_reviewed | agency_opinion | lab_report
    evidence_quality: Mapped[str] = mapped_column(String(10), default="moderate")
    summary: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[str | None] = mapped_column(String(36))


class ProductEvidence(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_evidence"

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("scientific_sources.id", ondelete="SET NULL"))
    claim: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(30))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class LaboratoryReport(IdMixin, TimestampMixin, Base):
    """A product-specific measurement. Only these may drive product contaminant findings."""

    __tablename__ = "laboratory_reports"

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    lab_name: Mapped[str] = mapped_column(String(200))
    method: Mapped[str | None] = mapped_column(String(200))  # e.g. ICP-MS
    batch: Mapped[str | None] = mapped_column(String(80))
    tested_on: Mapped[date | None] = mapped_column(Date)
    analyte: Mapped[str] = mapped_column(
        String(60), index=True
    )  # lead, cadmium, arsenic, mercury, glyphosate, microplastics...
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    threshold: Mapped[float | None] = mapped_column(Float)
    threshold_jurisdiction: Mapped[str | None] = mapped_column(String(60))
    threshold_reference: Mapped[str | None] = mapped_column(String(300))
    exceeds_threshold: Mapped[bool | None] = mapped_column(Boolean)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("scientific_sources.id", ondelete="SET NULL"))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[str | None] = mapped_column(String(36))


class ProductRecall(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_recalls"

    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), index=True)
    barcode: Mapped[str | None] = mapped_column(String(14), index=True)
    title: Mapped[str] = mapped_column(String(300))
    reason: Mapped[str] = mapped_column(Text)
    hazard: Mapped[str | None] = mapped_column(String(60))  # undeclared_allergen | microbial | foreign_body | chemical
    jurisdiction: Mapped[str] = mapped_column(String(10))  # US | UK | EU | NG ...
    authority: Mapped[str] = mapped_column(String(80))  # FDA | FSA | NAFDAC ...
    recall_date: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="active")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
