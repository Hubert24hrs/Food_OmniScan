"""Payment provider adapters: Stripe (web, primary/US), RevenueCat (iOS/Android), Paystack (Africa web).

Every webhook is signature-verified and recorded in `payment_events` for idempotency.
Entitlements are derived only from verified server-side events, never from the client.
"""

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import PaymentEvent, Subscription, User


class WebhookError(Exception):
    pass


def tier_from_code(code: str | None) -> str | None:
    c = (code or "").lower()
    for tier in ("family", "premium", "plus"):
        if tier in c:
            return tier
    return None


def record_event(db: Session, provider: str, event_id: str, event_type: str, payload: dict) -> bool:
    """Returns False if this event was already processed (idempotency)."""
    if db.scalar(select(PaymentEvent).where(PaymentEvent.provider == provider, PaymentEvent.event_id == event_id)):
        return False
    db.add(PaymentEvent(provider=provider, event_id=event_id, event_type=event_type, payload=payload))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return False
    return True


def upsert_subscription(
    db: Session,
    user_id: str,
    *,
    tier: str,
    status: str,
    provider: str,
    ref: str | None,
    period_end: datetime | None,
    interval: str = "month",
) -> Subscription:
    sub = None
    if ref:
        sub = db.scalar(select(Subscription).where(Subscription.provider == provider, Subscription.provider_ref == ref))
    if sub is None:
        sub = Subscription(user_id=user_id, provider=provider, provider_ref=ref, tier=tier, status=status)
        db.add(sub)
    sub.tier, sub.status, sub.current_period_end, sub.interval = tier, status, period_end, interval
    db.flush()
    return sub


# ---------------------------------------------------------------------------- Stripe


def stripe_verify(payload: bytes, sig_header: str | None, secret: str, tolerance: int = 300) -> dict:
    if not sig_header:
        raise WebhookError("Missing Stripe-Signature")
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    ts = parts.get("t")
    sigs = [v for k, v in (p.split("=", 1) for p in sig_header.split(",") if "=" in p) if k == "v1"]
    if not ts or not sigs:
        raise WebhookError("Malformed Stripe-Signature")
    if abs(time.time() - int(ts)) > tolerance:
        raise WebhookError("Stripe signature timestamp outside tolerance")
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in sigs):
        raise WebhookError("Invalid Stripe signature")
    return json.loads(payload)


def stripe_checkout(user: User, tier: str, interval: str) -> str:
    s = get_settings()
    if not s.stripe_secret_key:
        raise WebhookError("Stripe is not configured")
    price = s.stripe_price_map.get(f"{tier}_{interval}")
    if not price:
        raise WebhookError(f"No Stripe price configured for {tier}_{interval}")
    data = {
        "mode": "subscription",
        "line_items[0][price]": price,
        "line_items[0][quantity]": "1",
        "success_url": f"{s.public_app_url}/subscription?status=success",
        "cancel_url": f"{s.public_app_url}/subscription?status=cancelled",
        "client_reference_id": user.id,
        "customer_email": user.email,
        "subscription_data[metadata][user_id]": user.id,
        "subscription_data[metadata][tier]": tier,
        "metadata[user_id]": user.id,
        "metadata[tier]": tier,
    }
    r = httpx.post("https://api.stripe.com/v1/checkout/sessions", data=data, auth=(s.stripe_secret_key, ""), timeout=20)
    if r.status_code != 200:
        raise WebhookError(f"Stripe error {r.status_code}: {r.text[:200]}")
    return r.json()["url"]


def stripe_handle(db: Session, event: dict) -> str:
    if not record_event(db, "stripe", event["id"], event["type"], event):
        return "duplicate"
    obj = event["data"]["object"]
    et = event["type"]
    if et in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        meta = obj.get("metadata") or {}
        user_id = meta.get("user_id")
        tier = meta.get("tier") or tier_from_code(
            (obj.get("items", {}).get("data") or [{}])[0].get("price", {}).get("lookup_key")
        )
        if user_id and tier and db.get(User, user_id):
            status = {
                "active": "active",
                "trialing": "active",
                "past_due": "past_due",
                "canceled": "cancelled",
                "unpaid": "past_due",
                "incomplete_expired": "expired",
            }.get(obj.get("status"), "expired")
            if et == "customer.subscription.deleted":
                status = "cancelled"
            end = obj.get("current_period_end") or (
                (obj.get("items", {}).get("data") or [{}])[0].get("current_period_end")
            )
            interval = ((obj.get("items", {}).get("data") or [{}])[0].get("price", {}).get("recurring") or {}).get(
                "interval", "month"
            )
            upsert_subscription(
                db,
                user_id,
                tier=tier,
                status=status,
                provider="stripe",
                ref=obj.get("id"),
                period_end=datetime.fromtimestamp(end, UTC) if end else None,
                interval=interval,
            )
    db.commit()
    return "processed"


# ---------------------------------------------------------------------------- RevenueCat


def revenuecat_handle(db: Session, auth_header: str | None, body: dict) -> str:
    s = get_settings()
    if (
        not s.revenuecat_webhook_auth
        or not auth_header
        or not hmac.compare_digest(auth_header.removeprefix("Bearer ").strip(), s.revenuecat_webhook_auth)
    ):
        raise WebhookError("Invalid RevenueCat authorization")
    ev = body.get("event") or {}
    if not ev.get("id"):
        raise WebhookError("Missing event id")
    if not record_event(db, "revenuecat", ev["id"], ev.get("type", "unknown"), body):
        return "duplicate"
    user_id = ev.get("app_user_id")
    tier = tier_from_code(ev.get("product_id")) or tier_from_code(",".join(ev.get("entitlement_ids") or []))
    if user_id and tier and db.get(User, user_id):
        t = ev.get("type")
        status = (
            "active"
            if t in ("INITIAL_PURCHASE", "RENEWAL", "PRODUCT_CHANGE", "UNCANCELLATION", "NON_RENEWING_PURCHASE")
            else "expired"
            if t == "EXPIRATION"
            else "active"
            if t == "CANCELLATION"
            else "past_due"
            if t == "BILLING_ISSUE"
            else None
        )
        # CANCELLATION keeps access until expiration_at_ms; EXPIRATION ends it.
        if status:
            exp = ev.get("expiration_at_ms")
            upsert_subscription(
                db,
                user_id,
                tier=tier,
                status=status,
                provider="revenuecat",
                ref=ev.get("original_transaction_id") or ev.get("transaction_id"),
                period_end=datetime.fromtimestamp(exp / 1000, UTC) if exp else None,
                interval="year" if "annual" in (ev.get("product_id") or "").lower() else "month",
            )
    db.commit()
    return "processed"


# ---------------------------------------------------------------------------- Paystack


def paystack_verify(payload: bytes, signature: str | None) -> dict:
    s = get_settings()
    if not s.paystack_secret_key:
        raise WebhookError("Paystack is not configured")
    expected = hmac.new(s.paystack_secret_key.encode(), payload, hashlib.sha512).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature):
        raise WebhookError("Invalid Paystack signature")
    return json.loads(payload)


def paystack_handle(db: Session, body: dict) -> str:
    data = body.get("data") or {}
    event_id = str(data.get("id") or data.get("reference") or data.get("subscription_code") or "")
    if not event_id:
        raise WebhookError("Missing event id")
    if not record_event(db, "paystack", f"{body.get('event')}:{event_id}", body.get("event", "unknown"), body):
        return "duplicate"
    meta = data.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            meta = {}
    user_id = meta.get("user_id")
    tier = meta.get("tier") or tier_from_code(
        (data.get("plan") or {}).get("name") if isinstance(data.get("plan"), dict) else None
    )
    if user_id and tier and db.get(User, user_id):
        ev = body.get("event")
        if ev in ("charge.success", "subscription.create"):
            nxt = data.get("next_payment_date")
            upsert_subscription(
                db,
                user_id,
                tier=tier,
                status="active",
                provider="paystack",
                ref=data.get("subscription_code") or data.get("reference"),
                period_end=datetime.fromisoformat(nxt.replace("Z", "+00:00")) if nxt else None,
            )
        elif ev in ("subscription.disable", "subscription.not_renew"):
            upsert_subscription(
                db,
                user_id,
                tier=tier,
                status="cancelled",
                provider="paystack",
                ref=data.get("subscription_code"),
                period_end=None,
            )
    db.commit()
    return "processed"
