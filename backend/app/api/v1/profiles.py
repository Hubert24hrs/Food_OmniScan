"""Eater profiles (self + family): allergens, diets, avoid lists, goals."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import DB, CurrentUser
from app.data.allergens import ALLERGENS
from app.models import (
    AllergenProfile,
    DietaryPreference,
    FamilyProfile,
    IngredientAvoidanceRule,
    User,
)
from app.services import entitlements as ent
from app.services.allergens import EU_14, US_MAJOR
from app.services.compatibility import DIETS
from app.services.text import normalize_term

router = APIRouter(prefix="/profiles", tags=["profiles"])


def profile_out(fp: FamilyProfile, active_id: str | None = None) -> dict:
    return {
        "id": fp.id,
        "name": fp.name,
        "relationship": fp.relationship_label,
        "is_primary": fp.is_primary,
        "birth_year": fp.birth_year,
        "avatar_color": fp.avatar_color,
        "goals": fp.goals or {},
        "is_active": fp.id == active_id,
        "allergens": [
            {"code": a.allergen_code, "severity": a.severity, "avoid_traces": a.avoid_traces} for a in fp.allergens
        ],
        "diets": sorted(d.code for d in fp.dietary_preferences),
        "avoid": sorted(r.term for r in fp.avoid_rules),
    }


def get_owned(db, user: User, profile_id: str) -> FamilyProfile:
    fp = db.get(FamilyProfile, profile_id)
    if not fp or fp.owner_user_id != user.id:
        raise HTTPException(404, "Profile not found")
    return fp


def resolve_profiles(db, user: User | None, profile_ids: list[str] | None) -> list[FamilyProfile]:
    if user is None:
        return []
    if profile_ids:
        return [get_owned(db, user, pid) for pid in profile_ids]
    active = user.settings.active_family_profile_id if user.settings else None
    if active:
        fp = db.get(FamilyProfile, active)
        if fp and fp.owner_user_id == user.id:
            return [fp]
    return [p for p in user.family_profiles if p.is_primary][:1]


@router.get("/options")
def options():
    return {
        "allergens": [
            {"code": c, "name": a["name"], "us_major": c in US_MAJOR, "eu_14": c in EU_14} for c, a in ALLERGENS.items()
        ],
        "us_major_allergens": US_MAJOR,
        "eu_allergens": EU_14,
        "diets": [{"code": k, "name": v} for k, v in DIETS.items()],
        "severities": ["intolerance", "mild", "severe", "anaphylaxis"],
    }


@router.get("")
def list_profiles(user: CurrentUser):
    active = user.settings.active_family_profile_id if user.settings else None
    if not active and user.family_profiles:
        active = next((p.id for p in user.family_profiles if p.is_primary), None)
    return [profile_out(p, active) for p in user.family_profiles]


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    relationship: str | None = Field(default=None, max_length=40)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    avatar_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    goals: dict | None = None


@router.post("", status_code=201)
def create_profile(body: ProfileIn, user: CurrentUser, db: DB):
    ent.count_cap(db, user, "family_profiles", len(user.family_profiles))
    fp = FamilyProfile(
        owner_user_id=user.id,
        name=body.name,
        relationship_label=body.relationship,
        birth_year=body.birth_year,
        avatar_color=body.avatar_color,
        goals=body.goals or {},
    )
    db.add(fp)
    db.commit()
    db.refresh(fp)
    return profile_out(fp)


@router.patch("/{profile_id}")
def update_profile(profile_id: str, body: ProfileIn, user: CurrentUser, db: DB):
    fp = get_owned(db, user, profile_id)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(fp, "relationship_label" if k == "relationship" else k, v)
    db.commit()
    return profile_out(fp)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str, user: CurrentUser, db: DB):
    fp = get_owned(db, user, profile_id)
    if fp.is_primary:
        raise HTTPException(400, "The primary profile can't be deleted.")
    if user.settings and user.settings.active_family_profile_id == fp.id:
        user.settings.active_family_profile_id = None
    db.delete(fp)
    db.commit()


@router.post("/{profile_id}/activate")
def activate(profile_id: str, user: CurrentUser, db: DB):
    fp = get_owned(db, user, profile_id)
    user.settings.active_family_profile_id = fp.id
    db.commit()
    return profile_out(fp, fp.id)


def _require_health_consent(user: User) -> None:
    if user.consent_health_data_at is None:
        raise HTTPException(
            403,
            {"code": "consent_required", "message": "Allow Food omniScan to store allergy and diet information first."},
        )


class AllergenIn(BaseModel):
    code: str
    severity: str = Field(default="severe", pattern="^(intolerance|mild|severe|anaphylaxis)$")
    avoid_traces: bool = True


@router.put("/{profile_id}/allergens")
def set_allergens(profile_id: str, body: list[AllergenIn], user: CurrentUser, db: DB):
    _require_health_consent(user)
    fp = get_owned(db, user, profile_id)
    bad = [a.code for a in body if a.code not in ALLERGENS]
    if bad:
        raise HTTPException(422, f"Unknown allergen codes: {bad}")
    fp.allergens.clear()
    db.flush()
    for a in {a.code: a for a in body}.values():
        fp.allergens.append(
            AllergenProfile(profile_id=fp.id, allergen_code=a.code, severity=a.severity, avoid_traces=a.avoid_traces)
        )
    db.commit()
    return profile_out(fp)


@router.put("/{profile_id}/diets")
def set_diets(profile_id: str, body: list[str], user: CurrentUser, db: DB):
    _require_health_consent(user)
    fp = get_owned(db, user, profile_id)
    bad = [d for d in body if d not in DIETS]
    if bad:
        raise HTTPException(422, f"Unknown diets: {bad}")
    fp.dietary_preferences.clear()
    db.flush()
    for d in sorted(set(body)):
        fp.dietary_preferences.append(DietaryPreference(profile_id=fp.id, code=d))
    db.commit()
    return profile_out(fp)


@router.put("/{profile_id}/avoid")
def set_avoid(profile_id: str, body: list[str], user: CurrentUser, db: DB):
    _require_health_consent(user)
    fp = get_owned(db, user, profile_id)
    terms = sorted({normalize_term(t)[:120] for t in body if normalize_term(t)})
    if len(terms) > 100:
        raise HTTPException(422, "At most 100 avoid terms.")
    fp.avoid_rules.clear()
    db.flush()
    for t in terms:
        fp.avoid_rules.append(IngredientAvoidanceRule(profile_id=fp.id, term=t))
    db.commit()
    return profile_out(fp)


@router.get("/{profile_id}")
def get_profile(profile_id: str, user: CurrentUser, db: DB):
    return profile_out(get_owned(db, user, profile_id))
