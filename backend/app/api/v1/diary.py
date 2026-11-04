"""Food diary: log products (exact label data) or manual/AI-estimated meals."""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.profiles import get_owned, resolve_profiles
from app.core.deps import DB, CurrentUser
from app.models import FoodDiary, MealEntry, Product
from app.services import product_service as ps

router = APIRouter(prefix="/diary", tags=["diary"])
NUTR = ("energy_kcal", "protein", "carbohydrates", "fat", "fiber", "sugars", "sodium")


def entry_out(e: MealEntry) -> dict:
    return {
        "id": e.id,
        "meal_type": e.meal_type,
        "description": e.description,
        "product_id": e.product_id,
        "quantity_g": e.quantity_g,
        "source": e.source,
        "is_estimate": e.is_estimate,
        **{k: getattr(e, k) for k in NUTR if k != "sodium"},
        "sodium_mg": round(e.sodium * 1000) if e.sodium is not None else None,
    }


def _diary(db, user, profile_id: str, day: date, create: bool = False) -> FoodDiary | None:
    d = db.scalar(select(FoodDiary).where(FoodDiary.profile_id == profile_id, FoodDiary.day == day))
    if d is None and create:
        d = FoodDiary(user_id=user.id, profile_id=profile_id, day=day)
        db.add(d)
        db.flush()
    return d


def _totals(entries) -> dict:
    tot = {k: 0.0 for k in NUTR}
    for e in entries:
        for k in NUTR:
            v = getattr(e, k)
            if v is not None:
                tot[k] += v
    tot = {k: round(v, 1) for k, v in tot.items()}
    tot["sodium_mg"] = round(tot.pop("sodium") * 1000)
    tot["includes_estimates"] = any(e.is_estimate for e in entries)
    return tot


def _profile_id(db, user, profile_id: str | None) -> str:
    if profile_id:
        return get_owned(db, user, profile_id).id
    profiles = resolve_profiles(db, user, None)
    if not profiles:
        raise HTTPException(400, "No profile")
    return profiles[0].id


@router.get("")
def get_day(db: DB, user: CurrentUser, day: date | None = None, profile_id: str | None = None):
    pid = _profile_id(db, user, profile_id)
    day = day or date.today()
    d = _diary(db, user, pid, day)
    entries = d.entries if d else []
    fp = get_owned(db, user, pid)
    return {
        "day": day.isoformat(),
        "profile_id": pid,
        "entries": [entry_out(e) for e in entries],
        "totals": _totals(entries),
        "goals": fp.goals or {},
    }


class EntryIn(BaseModel):
    day: date | None = None
    profile_id: str | None = None
    meal_type: str = Field(pattern="^(breakfast|lunch|dinner|snack)$")
    product_id: str | None = None
    quantity_g: float | None = Field(default=None, gt=0, le=5000)
    description: str | None = Field(default=None, max_length=200)
    energy_kcal: float | None = Field(default=None, ge=0, le=10000)
    protein: float | None = Field(default=None, ge=0, le=1000)
    carbohydrates: float | None = Field(default=None, ge=0, le=1000)
    fat: float | None = Field(default=None, ge=0, le=1000)
    fiber: float | None = Field(default=None, ge=0, le=500)
    sugars: float | None = Field(default=None, ge=0, le=1000)
    sodium_mg: float | None = Field(default=None, ge=0, le=50000)
    is_estimate: bool = False


@router.post("/entries", status_code=201)
def add_entry(body: EntryIn, db: DB, user: CurrentUser):
    pid = _profile_id(db, user, body.profile_id)
    d = _diary(db, user, pid, body.day or date.today(), create=True)
    if body.product_id:
        p = db.get(Product, body.product_id)
        if not p:
            raise HTTPException(404, "Product not found")
        n = ps.nutrition_input(p)
        qty = body.quantity_g or (n.serving_size_g if n and n.serving_size_g else None)
        if qty is None:
            raise HTTPException(422, "quantity_g is required (no serving size on record)")
        f = qty / 100
        vals = {k: (getattr(n, k) * f if n and getattr(n, k) is not None else None) for k in NUTR} if n else {}
        e = MealEntry(
            diary_id=d.id,
            meal_type=body.meal_type,
            product_id=p.id,
            quantity_g=qty,
            description=body.description or " ".join(filter(None, [p.brand_text, p.name])) or "Product",
            source="product",
            is_estimate=False,
            **{k: (round(v, 3) if v is not None else None) for k, v in vals.items()},
        )
    else:
        if not body.description:
            raise HTTPException(422, "description is required for manual entries")
        e = MealEntry(
            diary_id=d.id,
            meal_type=body.meal_type,
            description=body.description,
            quantity_g=body.quantity_g,
            energy_kcal=body.energy_kcal,
            protein=body.protein,
            carbohydrates=body.carbohydrates,
            fat=body.fat,
            fiber=body.fiber,
            sugars=body.sugars,
            sodium=body.sodium_mg / 1000 if body.sodium_mg is not None else None,
            source="ai_estimate" if body.is_estimate else "manual",
            is_estimate=body.is_estimate,
        )
    db.add(e)
    db.commit()
    return entry_out(e)


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: str, db: DB, user: CurrentUser):
    e = db.get(MealEntry, entry_id)
    if not e:
        raise HTTPException(404, "Not found")
    d = db.get(FoodDiary, e.diary_id)
    if not d or d.user_id != user.id:
        raise HTTPException(404, "Not found")
    db.delete(e)
    db.commit()


@router.get("/summary")
def summary(db: DB, user: CurrentUser, days: int = Query(7, ge=1, le=92), profile_id: str | None = None):
    pid = _profile_id(db, user, profile_id)
    start = date.today() - timedelta(days=days - 1)
    rows = db.scalars(select(FoodDiary).where(FoodDiary.profile_id == pid, FoodDiary.day >= start)).all()
    by_day = {d.day: d for d in rows}
    series = []
    for i in range(days):
        day = start + timedelta(days=i)
        d = by_day.get(day)
        series.append({"day": day.isoformat(), **_totals(d.entries if d else [])})
    logged = [s for s in series if s["energy_kcal"] > 0]
    avg = (
        {
            k: round(sum(s[k] for s in logged) / len(logged), 1)
            for k in ("energy_kcal", "protein", "carbohydrates", "fat", "fiber", "sugars", "sodium_mg")
        }
        if logged
        else None
    )
    return {"profile_id": pid, "days": days, "series": series, "average_logged_day": avg, "days_logged": len(logged)}
