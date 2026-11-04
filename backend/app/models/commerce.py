from datetime import datetime

from sqlalchemy import (
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


class Subscription(IdMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tier: Mapped[str] = mapped_column(String(20))  # free | plus | premium | family
    status: Mapped[str] = mapped_column(String(20), index=True)  # active | cancelled | expired | past_due
    interval: Mapped[str] = mapped_column(String(10), default="month")  # month | year
    provider: Mapped[str] = mapped_column(String(20))  # paystack | revenuecat | manual
    provider_ref: Mapped[str | None] = mapped_column(String(120), index=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SubscriptionEntitlement(IdMixin, Base):
    """Plan matrix: what each tier unlocks. Editable by admins, enforced server-side."""

    __tablename__ = "subscription_entitlements"
    __table_args__ = (UniqueConstraint("tier", "feature"),)

    tier: Mapped[str] = mapped_column(String(20), index=True)
    feature: Mapped[str] = mapped_column(String(40))
    monthly_limit: Mapped[int | None] = mapped_column(Integer)  # None = unlimited, 0 = not included


class AIUsageRecord(IdMixin, Base):
    __tablename__ = "ai_usage_records"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    feature: Mapped[str] = mapped_column(String(40), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str | None] = mapped_column(String(60))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    credits: Mapped[int] = mapped_column(Integer, default=1)
    est_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok | error | refunded
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PaymentEvent(IdMixin, Base):
    """Webhook idempotency ledger."""

    __tablename__ = "payment_events"
    __table_args__ = (UniqueConstraint("provider", "event_id"),)

    provider: Mapped[str] = mapped_column(String(20))
    event_id: Mapped[str] = mapped_column(String(160))
    event_type: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSONType)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(IdMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # recall | submission | system | announcement
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONType, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AdminAuditLog(IdMixin, Base):
    __tablename__ = "admin_audit_logs"

    actor_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    before: Mapped[dict | None] = mapped_column(JSONType)
    after: Mapped[dict | None] = mapped_column(JSONType)
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    note: Mapped[str | None] = mapped_column(Text)
