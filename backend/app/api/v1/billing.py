from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.deps import DB, CurrentUser
from app.services import entitlements as ent
from app.services.payments import billing

router = APIRouter(prefix="/billing", tags=["billing"])

PLAN_COPY = {
    "free": [
        "Unlimited barcode scans",
        "Health score with full explanation",
        "Allergen and diet alerts",
        "1 profile",
        f"{ent.DEFAULT_MATRIX['ai_assistant']['free']} AI questions/month",
    ],
    "plus": [
        "Everything in Free",
        "2 profiles",
        "Unlimited comparisons",
        "200 healthier-alternative searches/month",
        f"{ent.DEFAULT_MATRIX['ai_assistant']['plus']} AI questions/month",
    ],
    "premium": [
        "Everything in Plus",
        "Unlimited alternatives",
        "AI nutrition assistant (500/month)",
        "AI photo label and meal recognition (300/month)",
        "3 profiles",
    ],
    "family": ["Everything in Premium", "Up to 8 family profiles", "Shared shopping lists", "Higher AI limits"],
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
