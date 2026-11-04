from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.deps import DB, CurrentUser
from app.services import entitlements as ent
from app.services.payments import billing

router = APIRouter(prefix="/billing", tags=["billing"])

PLAN_COPY = {
    "free": [
        "Unlimited barcode, label and nutrition scans",
        "Health score with full explanation",
        "Allergen alerts, diet checks and recalls (always free)",
        "Food diary, water tracking and nutrition targets",
        "Recipes, ingredient encyclopedia and food-safety research",
        "1 profile, 2 shopping lists",
        f"{ent.DEFAULT_MATRIX['ai_assistant']['free']} AI questions and "
        f"{ent.DEFAULT_MATRIX['ai_vision']['free']} AI photo reads a month",
    ],
    "plus": [
        "Everything in Free",
        "Vitamin and mineral tracking, weekly and monthly reports",
        "Watchlist ingredient alerts",
        "Pantry with expiry reminders",
        "Grocery budget, shopping history and price comparison",
        "Meal planner (4 plans), full category rankings, personalised picks",
        "Assistant in Pidgin, Yoruba, Igbo, Hausa, French and Spanish",
        f"{ent.DEFAULT_MATRIX['ai_assistant']['plus']} AI questions, "
        f"{ent.DEFAULT_MATRIX['ai_vision']['plus']} AI photo reads, "
        f"{ent.DEFAULT_MATRIX['ai_recipes']['plus']} AI recipes a month",
        "2 profiles, unlimited comparisons",
    ],
    "premium": [
        "Everything in Plus",
        "AI meal plans, including Nigerian and African dishes",
        "Personal food-pattern insights",
        "Unlimited meal plans, alternatives and shopping lists",
        f"{ent.DEFAULT_MATRIX['ai_assistant']['premium']} AI questions, "
        f"{ent.DEFAULT_MATRIX['ai_vision']['premium']} AI photo reads (meals, labels, products) a month",
        "3 profiles",
    ],
    "family": [
        "Everything in Premium",
        "Household sharing: pantry, shopping lists and budget",
        "Up to 8 family profiles",
        "Higher AI limits",
    ],
}


@router.get("/plans")
def plans():
    return [
        {
            "tier": t,
            "monthly_usd": ent.PRICES_USD[t],
            "annual_usd": ent.ANNUAL_PRICES_USD.get(t),
            "features": PLAN_COPY[t],
            "limits": {f: ent.DEFAULT_MATRIX[f][t] for f in ent.DEFAULT_MATRIX},
            "feature_labels": ent.FEATURE_LABELS,
        }
        for t in ent.TIERS
    ]


@router.get("/me")
def my_billing(db: DB, user: CurrentUser):
    return ent.usage_overview(db, user)


class CheckoutIn(BaseModel):
    tier: str = Field(pattern="^(plus|premium|family)$")
    interval: str = Field("month", pattern="^(month|year)$")


@router.post("/checkout")
def checkout(body: CheckoutIn, user: CurrentUser):
    try:
        return {"provider": "stripe", "url": billing.stripe_checkout(user, body.tier, body.interval)}
    except billing.WebhookError as e:
        raise HTTPException(503, {"code": "billing_not_configured", "message": str(e)})


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: DB, stripe_signature: str | None = Header(default=None)):
    secret = get_settings().stripe_webhook_secret
    if not secret:
        raise HTTPException(503, "Stripe webhook not configured")
    payload = await request.body()
    try:
        event = billing.stripe_verify(payload, stripe_signature, secret)
    except billing.WebhookError as e:
        raise HTTPException(400, str(e))
    return {"result": billing.stripe_handle(db, event)}


@router.post("/webhooks/revenuecat")
async def revenuecat_webhook(request: Request, db: DB, authorization: str | None = Header(default=None)):
    try:
        return {"result": billing.revenuecat_handle(db, authorization, await request.json())}
    except billing.WebhookError as e:
        raise HTTPException(401, str(e))


@router.post("/webhooks/paystack")
async def paystack_webhook(request: Request, db: DB, x_paystack_signature: str | None = Header(default=None)):
    payload = await request.body()
    try:
        body = billing.paystack_verify(payload, x_paystack_signature)
        return {"result": billing.paystack_handle(db, body)}
    except billing.WebhookError as e:
        raise HTTPException(401, str(e))
