"""Account, privacy (consent, export, deletion) and usage."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models import (
    CommunitySubmission,
    FamilyProfile,
    FavouriteProduct,
    FoodDiary,
    FoodScan,
    Notification,
    ScanHistory,
    ShoppingList,
    Subscription,
    UserReview,
)
from app.services import entitlements as ent

router = APIRouter(prefix="/me", tags=["account"])


def user_out(db, user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "country": user.country,
        "locale": user.locale,
        "currency": user.currency,
        "region": "US"
        if (user.country or "US") == "US"
        else "EU"
        if user.country not in ("NG", "GH", "KE", "ZA")
        else "INTL",
        "consent_health_data": user.consent_health_data_at is not None,
        "consent_ai_history": user.consent_ai_history,
        "marketing_opt_in": user.marketing_opt_in,
        "active_profile_id": user.settings.active_family_profile_id if user.settings else None,
        "units": user.settings.units if user.settings else "us",
        "tier": ent.active_tier(db, user),
        "created_at": user.created_at.isoformat(),
    }


@router.get("")
def get_me(user: CurrentUser, db: DB):
    return user_out(db, user)


class MePatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    locale: str | None = Field(default=None, max_length=10)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    units: str | None = Field(default=None, pattern="^(us|metric)$")
    consent_health_data: bool | None = None
    consent_ai_history: bool | None = None
    marketing_opt_in: bool | None = None


@router.patch("")
def patch_me(body: MePatch, user: CurrentUser, db: DB):
    data = body.model_dump(exclude_unset=True)
    for k in ("display_name", "locale", "consent_ai_history", "marketing_opt_in"):
        if k in data:
            setattr(user, k, data[k])
    if "country" in data and data["country"]:
        user.country = data["country"].upper()
    if "currency" in data and data["currency"]:
        user.currency = data["currency"].upper()
    if "units" in data and user.settings:
        user.settings.units = data["units"]
    if "consent_health_data" in data:
        if data["consent_health_data"]:
            user.consent_health_data_at = user.consent_health_data_at or datetime.now(UTC)
        else:
            # Withdrawing consent removes stored health data (allergies, diets, avoid lists).
            user.consent_health_data_at = None
            for fp in user.family_profiles:
                fp.allergens.clear()
                fp.dietary_preferences.clear()
                fp.avoid_rules.clear()
    db.commit()
    return user_out(db, user)


@router.get("/usage")
def usage(user: CurrentUser, db: DB):
    return ent.usage_overview(db, user)


def _rows(db, model, **filters):
    out = []
    for r in db.scalars(select(model).filter_by(**filters)).all():
        out.append(
            {
                c.name: (v.isoformat() if hasattr(v, "isoformat") else v)
                for c in r.__table__.columns
                if c.name != "password_hash"
                for v in [getattr(r, c.name)]
            }
        )
    return out


@router.get("/export")
def export_data(user: CurrentUser, db: DB):
    """GDPR/CCPA-style data export (machine-readable JSON)."""
    profiles = []
    for fp in user.family_profiles:
        profiles.append(
            {
                "id": fp.id,
                "name": fp.name,
                "relationship": fp.relationship_label,
                "goals": fp.goals,
                "allergens": [
                    {"code": a.allergen_code, "severity": a.severity, "avoid_traces": a.avoid_traces}
                    for a in fp.allergens
                ],
                "diets": [d.code for d in fp.dietary_preferences],
                "avoid": [r.term for r in fp.avoid_rules],
            }
        )
    diaries = []
    for d in db.scalars(select(FoodDiary).where(FoodDiary.user_id == user.id)).all():
        diaries.append(
            {
                "day": d.day.isoformat(),
                "profile_id": d.profile_id,
                "entries": [
                    {
                        c.name: getattr(e, c.name)
                        if not hasattr(getattr(e, c.name), "isoformat")
                        else getattr(e, c.name).isoformat()
                        for c in e.__table__.columns
                    }
                    for e in d.entries
                ],
            }
        )
    lists = []
    for sl in db.scalars(select(ShoppingList).where(ShoppingList.owner_user_id == user.id)).all():
        lists.append(
            {
                "name": sl.name,
                "items": [{"text": i.text, "quantity": i.quantity, "checked": i.checked} for i in sl.items],
            }
        )
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "account": user_out(db, user),
        "profiles": profiles,
        "scan_history": _rows(db, ScanHistory, user_id=user.id),
        "scans": _rows(db, FoodScan, user_id=user.id),
        "favourites": _rows(db, FavouriteProduct, user_id=user.id),
        "reviews": _rows(db, UserReview, user_id=user.id),
        "submissions": _rows(db, CommunitySubmission, user_id=user.id),
        "subscriptions": _rows(db, Subscription, user_id=user.id),
        "notifications": _rows(db, Notification, user_id=user.id),
        "food_diary": diaries,
        "shopping_lists": lists,
    }


class DeleteIn(BaseModel):
    confirm: str


@router.delete("", status_code=204)
def delete_account(body: DeleteIn, user: CurrentUser, db: DB):
    """Permanent account deletion. Community submissions that were approved stay as anonymous product data."""
    if body.confirm != "DELETE":
        raise HTTPException(422, "Type DELETE to confirm account deletion.")
    for s in db.scalars(select(CommunitySubmission).where(CommunitySubmission.user_id == user.id)).all():
        db.delete(s)
    db.query(FamilyProfile).filter(FamilyProfile.owner_user_id == user.id).delete()
    db.delete(user)
    db.commit()
