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

# feature -> {tier: monthly limit}; None = unlimited, 0 = not included.
# Safety information (allergens, scores and their explanations, recalls, lab results, contaminant research)
# is never in this matrix: it is free for everyone.
_PLUS = {"free": 0, "plus": None, "premium": None, "family": None}
_PREMIUM = {"free": 0, "plus": 0, "premium": None, "family": None}
_FAMILY = {"free": 0, "plus": 0, "premium": 0, "family": None}
DEFAULT_MATRIX: dict[str, dict[str, int | None]] = {
    # metered (monthly)
    "ai_assistant": {"free": 5, "plus": 60, "premium": 500, "family": 1000},
    "ai_vision": {"free": 3, "plus": 30, "premium": 300, "family": 600},
    "ai_recipes": {"free": 0, "plus": 10, "premium": 60, "family": 120},
    "ai_meal_plans": {"free": 0, "plus": 0, "premium": 20, "family": 40},
    "alternatives": {"free": 15, "plus": 200, "premium": None, "family": None},
    "comparisons": {"free": 10, "plus": None, "premium": None, "family": None},
    # caps (not monthly)
    "family_profiles": {"free": 1, "plus": 2, "premium": 3, "family": 8},
    "shopping_lists": {"free": 2, "plus": 10, "premium": None, "family": None},
    "meal_plans": {"free": 0, "plus": 4, "premium": None, "family": None},
    # access (on/off by plan)
    "micronutrients": _PLUS,
    "nutrition_reports": _PLUS,
    "ingredient_alerts": _PLUS,
    "pantry": _PLUS,
    "budget": _PLUS,
    "price_comparison": _PLUS,
    "full_rankings": _PLUS,
    "recommendations": _PLUS,
    "assistant_languages": _PLUS,
    "health_insights": _PREMIUM,
    "household": _FAMILY,
}
METERED = ("ai_assistant", "ai_vision", "ai_recipes", "ai_meal_plans", "alternatives", "comparisons")
CAPS = ("family_profiles", "shopping_lists", "meal_plans")
CREDIT_COST = {"ai_assistant": 1, "ai_vision": 1, "ai_recipes": 1, "ai_meal_plans": 1}

# Shown on the plans page and in upgrade prompts.
FEATURE_LABELS = {
    "ai_assistant": "AI nutrition assistant questions",
    "ai_vision": "AI photo reading (labels, meals, products)",
    "ai_recipes": "AI recipe generation and recipe nutrition estimates",
    "ai_meal_plans": "AI meal plans",
    "alternatives": "Healthier-alternative searches",
    "comparisons": "Product comparisons",
    "family_profiles": "Family profiles",
    "shopping_lists": "Shopping lists",
    "meal_plans": "Saved meal plans",
    "micronutrients": "Vitamin and mineral tracking",
    "nutrition_reports": "Weekly and monthly nutrition reports",
    "ingredient_alerts": "Watchlist ingredient alerts",
    "pantry": "Pantry and expiry reminders",
    "budget": "Grocery budget and shopping history",
    "price_comparison": "Price comparison and where to buy",
    "full_rankings": "Full category rankings",
    "recommendations": "Personalised product recommendations",
    "assistant_languages": "Assistant in Pidgin, Yoruba, Igbo, Hausa, French, Spanish",
    "health_insights": "Personal food-pattern insights",
    "household": "Household sharing (pantry, lists, budget)",
}


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


def min_tier(db: Session, feature: str) -> str | None:
    """Cheapest plan that includes a feature (respects admin overrides)."""
    for t in TIERS:
        if limit_for(db, t, feature) != 0:
            return t
    return None


def _upgrade(db: Session, tier: str, feature: str) -> HTTPException:
    need = min_tier(db, feature)
    label = FEATURE_LABELS.get(feature, feature.replace("_", " "))
    return HTTPException(
        status.HTTP_402_PAYMENT_REQUIRED,
        {
            "code": "upgrade_required",
            "feature": feature,
            "tier": tier,
            "required_tier": need,
            "message": f"{label} is included with {need.title() if need else 'a paid plan'}. "
            f"You're on the {tier.title()} plan.",
        },
    )


def has_feature(db: Session, user: User | None, feature: str) -> bool:
    if user is None:
        return False
    return limit_for(db, active_tier(db, user), feature) != 0


def require_feature(db: Session, user: User, feature: str) -> None:
    """On/off plan features (pantry, reports, household...)."""
    tier = active_tier(db, user)
    if limit_for(db, tier, feature) == 0:
        raise _upgrade(db, tier, feature)


def require_quota(db: Session, user: User, feature: str) -> None:
    tier = active_tier(db, user)
    lim = limit_for(db, tier, feature)
    if lim is None:
        return
    if lim == 0:
        raise _upgrade(db, tier, feature)
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
    if lim == 0:
        raise _upgrade(db, tier, feature)
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
        kind = "metered" if feature in METERED else "cap" if feature in CAPS else "access"
        out[feature] = {
            "kind": kind,
            "label": FEATURE_LABELS.get(feature, feature),
            "limit": lim,
            "included": lim != 0,
            "used": used_this_month(db, user, feature) if kind == "metered" else None,
        }
    return {"tier": tier, "features": out}
