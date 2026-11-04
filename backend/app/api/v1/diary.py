"""Food diary: log products (exact label data) or manual/AI-estimated meals."""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.profiles import get_owned, resolve_profiles
from app.core.deps import DB, CurrentUser
from app.models import BodyMetric, FoodDiary, MealEntry, Product, WaterLog
from app.services import entitlements as ent
from app.services import product_service as ps
from app.services import tracking
from app.services.nutrition import scale_micros

router = APIRouter(prefix="/diary", tags=["diary"])
NUTR = ("energy_kcal", "protein", "carbohydrates", "fat", "fiber", "sugars", "sodium")


def entry_out(e: MealEntry, micros: bool = False) -> dict:
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
        **({"micros": e.micros or {}} if micros else {}),
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
    show_micros = ent.has_feature(db, user, "micronutrients")
    waters = db.scalars(select(WaterLog).where(WaterLog.profile_id == pid, WaterLog.day == day)).all()
    return {
        "day": day.isoformat(),
        "profile_id": pid,
        "entries": [entry_out(e, show_micros) for e in entries],
        "totals": _totals(entries),
        "goals": fp.goals or {},
        "targets": tracking.targets_for(fp.goals),
        "water": {"total_ml": sum(w.ml for w in waters), "logs": [{"id": w.id, "ml": w.ml} for w in waters]},
        "micros": tracking.micro_totals(entries) if show_micros else None,
        "micros_locked": not show_micros,
    }


class EntryIn(BaseModel):
    day: date | None = None
    profile_id: str | None = None
    meal_type: str = Field(pattern="^(breakfast|lunch|dinner|snack)$")
    product_id: str | None = None
    quantity_g: float | None = Field(default=None, gt=0, le=5000)
    servings: float | None = Field(default=None, gt=0, le=50)
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
    e = _build_entry(body, db, user)
    db.add(e)
    db.commit()
    return entry_out(e, ent.has_feature(db, user, "micronutrients"))


class BulkIn(BaseModel):
    entries: list[EntryIn] = Field(min_length=1, max_length=12)


@router.post("/entries/bulk", status_code=201)
def add_entries(body: BulkIn, db: DB, user: CurrentUser):
    """Log several items at once, e.g. the foods recognised in a meal photo (marked as estimates)."""
    rows = [_build_entry(b, db, user) for b in body.entries]
    db.add_all(rows)
    db.commit()
    return [entry_out(e) for e in rows]


def _build_entry(body: EntryIn, db, user) -> MealEntry:
    pid = _profile_id(db, user, body.profile_id)
    d = _diary(db, user, pid, body.day or date.today(), create=True)
    if body.product_id:
        p = db.get(Product, body.product_id)
        if not p:
            raise HTTPException(404, "Product not found")
        n = ps.nutrition_input(p)
        serving = n.serving_size_g if n and n.serving_size_g else None
        if body.quantity_g:
            qty = body.quantity_g
        elif body.servings and serving:
            qty = round(body.servings * serving, 1)
        else:
            qty = serving
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
            micros=scale_micros(n.extra.get("micros"), f) if n else None,
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
    return e


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


# ------------------------------------------------------------------ targets, water, weight


class GoalsIn(BaseModel):
    profile_id: str | None = None
    goals: dict[str, float] = Field(max_length=20)


@router.put("/goals")
def set_goals(body: GoalsIn, db: DB, user: CurrentUser):
    fp = get_owned(db, user, _profile_id(db, user, body.profile_id))
    unknown = set(body.goals) - set(tracking.TARGET_KEYS)
    if unknown:
        raise HTTPException(422, f"Unknown targets: {', '.join(sorted(unknown))}")
    if any(v < 0 or v > 100000 for v in body.goals.values()):
        raise HTTPException(422, "Targets must be between 0 and 100000")
    fp.goals = {**(fp.goals or {}), **body.goals}
    db.commit()
    return {"goals": fp.goals, "targets": tracking.targets_for(fp.goals)}


class WaterIn(BaseModel):
    ml: int = Field(gt=0, le=5000)
    day: date | None = None
    profile_id: str | None = None


@router.post("/water", status_code=201)
def add_water(body: WaterIn, db: DB, user: CurrentUser):
    pid = _profile_id(db, user, body.profile_id)
    day = body.day or date.today()
    db.add(WaterLog(user_id=user.id, profile_id=pid, day=day, ml=body.ml))
    db.commit()
    return {"day": day.isoformat(), "total_ml": tracking.water_total(db, pid, day)}


@router.delete("/water/{log_id}", status_code=204)
def delete_water(log_id: str, db: DB, user: CurrentUser):
    w = db.get(WaterLog, log_id)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "Not found")
    db.delete(w)
    db.commit()


class WeightIn(BaseModel):
    weight_kg: float = Field(gt=10, lt=400)
    day: date | None = None
    profile_id: str | None = None


@router.put("/weight")
def log_weight(body: WeightIn, db: DB, user: CurrentUser):
    pid = _profile_id(db, user, body.profile_id)
    day = body.day or date.today()
    row = db.scalar(select(BodyMetric).where(BodyMetric.profile_id == pid, BodyMetric.day == day))
    if row is None:
        row = BodyMetric(user_id=user.id, profile_id=pid, day=day, weight_kg=body.weight_kg)
        db.add(row)
    else:
        row.weight_kg = body.weight_kg
    db.commit()
    return {"day": day.isoformat(), "weight_kg": row.weight_kg}


@router.get("/weight")
def weight_history(db: DB, user: CurrentUser, profile_id: str | None = None, days: int = Query(90, ge=7, le=730)):
    pid = _profile_id(db, user, profile_id)
    fp = get_owned(db, user, pid)
    rows = db.scalars(
        select(BodyMetric)
        .where(BodyMetric.profile_id == pid, BodyMetric.day >= date.today() - timedelta(days=days))
        .order_by(BodyMetric.day)
    ).all()
    return {
        "goal_kg": (fp.goals or {}).get("weight_goal_kg"),
        "entries": [{"day": r.day.isoformat(), "weight_kg": r.weight_kg} for r in rows],
    }


# ------------------------------------------------------------------ reports & insights (paid)


def _period(period: str, end: date | None) -> tuple[date, date]:
    end = end or date.today()
    return end - timedelta(days=6 if period == "week" else 29), end


@router.get("/report")
def report(
    db: DB,
    user: CurrentUser,
    period: str = Query("week", pattern="^(week|month)$"),
    end: date | None = None,
    profile_id: str | None = None,
):
    ent.require_feature(db, user, "nutrition_reports")
    pid = _profile_id(db, user, profile_id)
    start, end = _period(period, end)
    out = tracking.period_report(db, pid, start, end, get_owned(db, user, pid).goals)
    if not ent.has_feature(db, user, "micronutrients"):
        out["micros"] = None
    return {"period": period, **out}


@router.get("/insights")
def food_insights(db: DB, user: CurrentUser, days: int = Query(30, ge=7, le=90), profile_id: str | None = None):
    ent.require_feature(db, user, "health_insights")
    pid = _profile_id(db, user, profile_id)
    end = date.today()
    start = end - timedelta(days=days - 1)
    rep = tracking.period_report(db, pid, start, end, get_owned(db, user, pid).goals)
    product_ids = db.scalars(
        select(MealEntry.product_id)
        .join(FoodDiary, FoodDiary.id == MealEntry.diary_id)
        .where(FoodDiary.profile_id == pid, FoodDiary.day >= start)
    ).all()
    return {
        "days": days,
        "days_logged": rep["days_logged"],
        "insights": tracking.insights(rep),
        "product_score_mix": tracking.scored_product_mix(db, [p for p in product_ids if p]),
        "top_foods": rep["top_foods"],
        "disclaimer": "Patterns in what you logged, compared with your own targets. Not medical advice.",
    }
