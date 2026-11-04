"""Server-verified subscription entitlements and AI credit accounting.

Allergen warnings, scores and score explanations are never paywalled.
"""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AIUsageRecord, Subscription, SubscriptionEntitlement, User

TIERS = ("free", "plus", "premium", "family")
PRICES_USD = {"free": 0, "plus": 3.99, "premium": 7.99, "family": 11.99}
ANNUAL_PRICES_USD = {"plus": 39.99, "premium": 79.99, "family": 119.99}  # ~2 months free

# feature -> {tier: monthly limit}; None = unlimited, 0 = not included
DEFAULT_MATRIX: dict[str, dict[str, int | None]] = {
    "ai_assistant": {"free": 5, "plus": 60, "premium": 500, "family": 1000},
    "ai_vision": {"free": 3, "plus": 30, "premium": 300, "family": 600},
    "alternatives": {"free": 15, "plus": 200, "premium": None, "family": None},
    "comparisons": {"free": 10, "plus": None, "premium": None, "family": None},
    "family_profiles": {"free": 1, "plus": 2, "premium": 3, "family": 8},  # a cap, not monthly
    "shopping_lists": {"free": 2, "plus": 10, "premium": None, "family": None},
}
CREDIT_COST = {"ai_assistant": 1, "ai_vision": 1}


def active_tier(db: Session, user: User) -> str:
    now = datetime.now(UTC)
    subs = db.scalars(
        select(Subscription).where(Subscription.user_id == user.id, Subscription.status == "active")
    ).all()
    best = "free"
    for s in subs:
        end = s.current_period_end
        if end is not None and (end if end.tzinfo else end.replace(tzinfo=UTC)) < now:
            continue
        if TIERS.index(s.tier) > TIERS.index(best):
            best = s.tier
    return best


def limit_for(db: Session, tier: str, feature: str) -> int | None:
    row = db.scalar(
        select(SubscriptionEntitlement).where(
            SubscriptionEntitlement.tier == tier, SubscriptionEntitlement.feature == feature
        )
    )
    if row is not None:
        return row.monthly_limit
    return DEFAULT_MATRIX.get(feature, {}).get(tier, 0)


def _month_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def used_this_month(db: Session, user: User, feature: str) -> int:
    return (
        db.scalar(
            select(func.coalesce(func.sum(AIUsageRecord.credits), 0)).where(
                AIUsageRecord.user_id == user.id,
                AIUsageRecord.feature == feature,
                AIUsageRecord.status == "ok",
                AIUsageRecord.created_at >= _month_start(),
            )
        )
        or 0
    )


def require_quota(db: Session, user: User, feature: str) -> None:
    tier = active_tier(db, user)
    lim = limit_for(db, tier, feature)
    if lim is None:
        return
    used = used_this_month(db, user, feature)
    if used + CREDIT_COST.get(feature, 1) > lim:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            {
                "code": "quota_exceeded",
                "feature": feature,
                "tier": tier,
                "limit": lim,
                "used": used,
                "message": f"You've used all {lim} {feature.replace('_', ' ')} credits this month on the {tier} plan.",
            },
        )


def record_usage(
    db: Session,
    user: User | None,
    feature: str,
    provider: str,
    model: str | None,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    ok: bool = True,
) -> AIUsageRecord:
    # Rough list-price estimate for monitoring only (USD per 1M tokens), configurable later.
    cost = (input_tokens * 0.30 + output_tokens * 2.50) / 1_000_000
    rec = AIUsageRecord(
        user_id=user.id if user else None,
        feature=feature,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        credits=CREDIT_COST.get(feature, 1) if ok else 0,
        est_cost_usd=round(cost, 6),
        status="ok" if ok else "error",
    )
    db.add(rec)
    db.commit()
    return rec


def count_cap(db: Session, user: User, feature: str, current: int) -> None:
    """Enforce non-monthly caps such as number of family profiles."""
    tier = active_tier(db, user)
    lim = limit_for(db, tier, feature)
    if lim is not None and current >= lim:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            {
                "code": "plan_limit",
                "feature": feature,
                "tier": tier,
                "limit": lim,
                "message": f"Your {tier} plan allows {lim} {feature.replace('_', ' ')}. Upgrade for more.",
            },
        )


def usage_overview(db: Session, user: User) -> dict:
    tier = active_tier(db, user)
    out = {}
    for feature in DEFAULT_MATRIX:
        lim = limit_for(db, tier, feature)
        out[feature] = {"limit": lim, "used": used_this_month(db, user, feature) if feature in CREDIT_COST else None}
    return {"tier": tier, "features": out}
