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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models._common import IdMixin, JSONType, TimestampMixin, utcnow


class ScoringMethodology(IdMixin, TimestampMixin, Base):
    """A versioned, immutable-once-published scoring configuration.

    Administrators publish a new version instead of editing an old one, so every
    stored ProductScore can be traced back to the exact rules that produced it.
    """

    __tablename__ = "scoring_methodologies"

    version: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    config: Mapped[dict] = mapped_column(JSONType)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(36))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScoringRule(IdMixin, Base):
    """Flattened, browsable view of a methodology's rules (generated on publish)."""

    __tablename__ = "scoring_rules"

    methodology_id: Mapped[str] = mapped_column(ForeignKey("scoring_methodologies.id", ondelete="CASCADE"), index=True)
    component: Mapped[str] = mapped_column(String(40))
    code: Mapped[str] = mapped_column(String(80))
    params: Mapped[dict] = mapped_column(JSONType, default=dict)
    description: Mapped[str | None] = mapped_column(Text)


class ProductScore(IdMixin, Base):
    __tablename__ = "product_scores"
    __table_args__ = (UniqueConstraint("product_id", "methodology_version", "inputs_hash"),)

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    methodology_version: Mapped[str] = mapped_column(String(20), index=True)
    inputs_hash: Mapped[str] = mapped_column(String(64))
    overall: Mapped[int | None] = mapped_column(Integer)
    grade: Mapped[str] = mapped_column(String(20))  # excellent | good | fair | poor | insufficient_data
    confidence: Mapped[str] = mapped_column(String(10))  # high | medium | low
    coverage: Mapped[float] = mapped_column(Float)
    result: Mapped[dict] = mapped_column(JSONType)  # components, deductions, flags
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProductWarning(IdMixin, Base):
    __tablename__ = "product_warnings"

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(10))  # info | caution | concern | critical
    title: Mapped[str] = mapped_column(String(200))
    explanation: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(30))
    source_keys: Mapped[list] = mapped_column(JSONType, default=list)
    methodology_version: Mapped[str] = mapped_column(String(20))
