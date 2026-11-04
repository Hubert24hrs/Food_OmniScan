"""Recipes, AI recipe generation, meal plans and recipe-to-shopping-list conversion."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.api.v1.products import region_of
from app.api.v1.profiles import profile_out, resolve_profiles
from app.api.v1.shopping import add_lines, list_out, target_list
from app.core.deps import DB, CurrentUser, OptionalUser
from app.data.content_seed import SUBSTITUTIONS
from app.models import MealPlan, Recipe
from app.services import entitlements as ent
from app.services import product_service as ps
from app.services.ai import features as ai
from app.services.ai.provider import AIError, AINotConfigured, get_provider

router = APIRouter(tags=["recipes"])


def recipe_summary(r: Recipe) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "cuisine": r.cuisine,
        "region": r.region,
        "servings": r.servings,
        "time_minutes": r.time_minutes,
        "tags": r.tags or [],
        "diet_tags": r.diet_tags or [],
        "ai_generated": r.source == "ai",
        "mine": r.created_by is not None,
    }


def recipe_out(r: Recipe) -> dict:
    return {
        **recipe_summary(r),
        "ingredients": r.ingredients,
        "steps": r.steps,
        "preparation_notes": r.preparation_notes,
        "nutrition_per_serving": r.nutrition,
        "nutrition_is_estimate": r.nutrition_is_estimate,
        "verified": r.verified,
    }


def _visible(db, user, recipe_id: str) -> Recipe:
    r = db.get(Recipe, recipe_id)
    if not r or not (r.is_public or (user and r.created_by == user.id)):
        raise HTTPException(404, "Recipe not found")
    return r


def _ingredient_text(r: Recipe) -> str:
    return ", ".join(i["name"] for i in r.ingredients if i.get("name"))


def substitutions_for(r: Recipe, profile) -> list[dict]:
    """Culinary swaps for ingredients that clash with the profile's allergens, diets or low-sodium goal."""
    if profile is None:
        return []
    keys = [a.allergen_code for a in profile.allergens] + [d.code for d in profile.dietary_preferences]
    names = [i["name"].lower() for i in r.ingredients if i.get("name")]
    out = []
    for key in keys:
        for sub in SUBSTITUTIONS.get(key, []):
            hits = sorted({n for n in names for f in sub["for"] if f in n})
            if hits:
                out.append({"because": key, "replace": hits, "with": sub["use"]})
    return out


def compatibility(db, user, r: Recipe, profile_ids: list[str] | None) -> dict | None:
    profiles = resolve_profiles(db, user, profile_ids)
    if not profiles:
        return None
    res = ps.analyze_text(
        _ingredient_text(r),
        None,
        cfg=ps.active_methodology(db),
        profiles=[ps._profile_spec(p) for p in profiles],
        region=region_of(user),
    )
    return {
        "profiles": res["compatibility"],
        "allergens": [a for a in res["allergens"] if a["status"] in ("contains", "may_contain")],
        "substitutions": substitutions_for(r, profiles[0]),
        "note": "Checked from the recipe's ingredient names. Always check the labels of what you buy.",
    }


@router.get("/recipes")
def list_recipes(
    db: DB,
    user: OptionalUser,
    q: str | None = Query(default=None, max_length=80),
    cuisine: str | None = None,
    region: str | None = Query(default=None, max_length=8),
    diet: str | None = None,
    tag: str | None = None,
    mine: bool = False,
    limit: int = Query(30, ge=1, le=60),
):
    cond = Recipe.is_public.is_(True)
    if user:
        cond = or_(cond, Recipe.created_by == user.id)
    stmt = select(Recipe).where(cond)
    if mine and user:
        stmt = select(Recipe).where(Recipe.created_by == user.id)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(Recipe.title).like(like), func.lower(Recipe.description).like(like)))
    if cuisine:
        stmt = stmt.where(func.lower(Recipe.cuisine) == cuisine.lower())
    if region:
        stmt = stmt.where(Recipe.region == region.upper())
    rows = db.scalars(stmt.order_by(Recipe.title).limit(200)).all()
    if diet:
        rows = [r for r in rows if diet in (r.diet_tags or [])]
    if tag:
        rows = [r for r in rows if tag in (r.tags or [])]
    return [recipe_summary(r) for r in rows[:limit]]


@router.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: str, db: DB, user: OptionalUser, profile_ids: list[str] | None = Query(default=None)):
    r = _visible(db, user, recipe_id)
    return {**recipe_out(r), "compatibility": compatibility(db, user, r, profile_ids)}


class IngredientIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: float | None = Field(default=None, ge=0, le=100000)
    unit: str | None = Field(default=None, max_length=20)
    note: str | None = Field(default=None, max_length=120)


class RecipeIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    cuisine: str | None = Field(default=None, max_length=60)
    region: str | None = Field(default=None, max_length=8)
    servings: int = Field(4, ge=1, le=50)
    time_minutes: int | None = Field(default=None, ge=1, le=1440)
    ingredients: list[IngredientIn] = Field(min_length=1, max_length=60)
    steps: list[str] = Field(default_factory=list, max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=12)
    diet_tags: list[str] = Field(default_factory=list, max_length=12)


@router.post("/recipes", status_code=201)
def create_recipe(body: RecipeIn, db: DB, user: CurrentUser):
    r = Recipe(
        **body.model_dump(exclude={"ingredients"}),
        ingredients=[i.model_dump() for i in body.ingredients],
        created_by=user.id,
        is_public=False,
        source="user",
    )
    db.add(r)
    db.commit()
    return recipe_out(r)


@router.delete("/recipes/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: str, db: DB, user: CurrentUser):
    r = db.get(Recipe, recipe_id)
    if not r or r.created_by != user.id:
        raise HTTPException(404, "Recipe not found")
    db.delete(r)
    db.commit()


def _provider():
    try:
        return get_provider()
    except AINotConfigured as e:
        raise HTTPException(503, {"code": "ai_not_configured", "message": f"AI isn't available: {e}"})


def _run_ai(db, user, feature: str, call):
    provider = _provider()
    try:
        res = call(provider)
        data = res.json()
    except (AIError, ValueError) as e:
        ent.record_usage(db, user, feature, provider.name, getattr(provider, "model", None), ok=False)
        raise HTTPException(
            502, {"code": "ai_failed", "message": "The AI couldn't do that right now.", "detail": str(e)[:200]}
        )
    ent.record_usage(
        db, user, feature, res.provider, res.model, input_tokens=res.input_tokens, output_tokens=res.output_tokens
    )
    return data


def _constraints(db, user, profile_id: str | None, **extra) -> tuple[str, list]:
    profiles = resolve_profiles(db, user, [profile_id] if profile_id else None)
    region = extra.pop("region", None) or (user.country or "US")
    return ai.constraints_text(profile_out(profiles[0]) if profiles else None, {"region": region, **extra}), profiles


def _clean_ingredients(items) -> list[dict]:
    out = []
    for i in items or []:
        if isinstance(i, dict) and i.get("name"):
            q = i.get("quantity")
            out.append(
                {
                    "name": str(i["name"])[:120],
                    "quantity": q if isinstance(q, int | float) else None,
                    "unit": (str(i["unit"])[:20] if i.get("unit") else None),
                    "note": (str(i["note"])[:120] if i.get("note") else None),
                }
            )
    return out[:60]


class GenerateRecipeIn(BaseModel):
    request: str = Field(min_length=3, max_length=1000)  # e.g. "dinner with beans and plantain, 30 minutes"
    profile_id: str | None = None
    region: str | None = Field(default=None, max_length=8)
    servings: int = Field(4, ge=1, le=20)
    ingredients_on_hand: list[str] = Field(default_factory=list, max_length=30)


@router.post("/recipes/generate", status_code=201)
def generate_recipe(body: GenerateRecipeIn, db: DB, user: CurrentUser):
    ent.require_quota(db, user, "ai_recipes")
    constraints, profiles = _constraints(
        db,
        user,
        body.profile_id,
        region=body.region,
        servings=body.servings,
        ingredients_on_hand=body.ingredients_on_hand,
    )
    data = _run_ai(db, user, "ai_recipes", lambda p: ai.generate_recipe(p, body.request, constraints))
    ingredients = _clean_ingredients(data.get("ingredients"))
    if not data.get("title") or not ingredients:
        raise HTTPException(502, {"code": "ai_failed", "message": "The AI returned an incomplete recipe. Try again."})
    nut = data.get("nutrition_per_serving_estimate")
    r = Recipe(
        title=str(data["title"])[:200],
        description=(str(data.get("description") or "")[:1000] or None),
        cuisine=(str(data.get("cuisine") or "")[:60] or None),
        region=(body.region or user.country or None),
        servings=int(data.get("servings") or body.servings),
        time_minutes=data.get("time_minutes") if isinstance(data.get("time_minutes"), int) else None,
        ingredients=ingredients,
        steps=[str(s)[:600] for s in (data.get("steps") or [])][:40],
        tags=[str(t)[:30] for t in (data.get("tags") or [])][:12],
        diet_tags=[str(t)[:30] for t in (data.get("diet_tags") or [])][:12],
        preparation_notes=(str(data.get("preparation_notes") or "")[:1000] or None),
        nutrition=nut if isinstance(nut, dict) else None,
        nutrition_is_estimate=True,
        source="ai",
        created_by=user.id,
        is_public=False,
    )
    db.add(r)
    db.commit()
    out = recipe_out(r)
    out["compatibility"] = compatibility(db, user, r, [profiles[0].id] if profiles else None)
    out["notice"] = "AI-generated recipe. Nutrition values are rough estimates. Check labels for allergens."
    return out


@router.post("/recipes/{recipe_id}/nutrition-estimate")
def estimate_nutrition(recipe_id: str, db: DB, user: CurrentUser):
    r = _visible(db, user, recipe_id)
    ent.require_quota(db, user, "ai_recipes")
    data = _run_ai(
        db,
        user,
        "ai_recipes",
        lambda p: ai.estimate_recipe_nutrition(
            p, {"title": r.title, "servings": r.servings, "ingredients": r.ingredients, "steps": r.steps}
        ),
    )
    keys = ("energy_kcal", "protein", "carbohydrates", "fat", "fiber", "sugars", "sodium_mg")
    est = {k: data.get(k) for k in keys if isinstance(data.get(k), int | float)}
    if not est:
        raise HTTPException(502, {"code": "ai_failed", "message": "Couldn't estimate this recipe. Try again."})
    r.nutrition, r.nutrition_is_estimate = est, True
    db.commit()
    return {"nutrition_per_serving": est, "assumptions": data.get("assumptions"), "is_estimate": True}


def _scaled(r: Recipe, servings: int | None) -> list[dict]:
    factor = (servings / r.servings) if servings and r.servings else 1
    lines = []
    for i in r.ingredients:
        q = i.get("quantity")
        qty = None
        if isinstance(q, int | float):
            qty = f"{round(q * factor, 2):g} {i.get('unit') or ''}".strip()
        lines.append({"text": i["name"], "quantity": qty})
    return lines


class ToListIn(BaseModel):
    list_id: str | None = None
    servings: int | None = Field(default=None, ge=1, le=50)


@router.post("/recipes/{recipe_id}/shopping-list")
def recipe_to_list(recipe_id: str, body: ToListIn, db: DB, user: CurrentUser):
    r = _visible(db, user, recipe_id)
    sl = target_list(db, user, body.list_id, f"For {r.title}")
    added = add_lines(db, sl, user, _scaled(r, body.servings))
    db.commit()
    return {"added": added, "list": list_out(sl)}


# ------------------------------------------------------------------ meal plans


def plan_out(db, mp: MealPlan) -> dict:
    return {
        "id": mp.id,
        "name": mp.name,
        "start_date": mp.start_date.isoformat() if mp.start_date else None,
        "profile_id": mp.profile_id,
        "days": mp.days,
        "updated_at": mp.updated_at.isoformat(),
    }


def _plan(db, user, plan_id: str) -> MealPlan:
    mp = db.get(MealPlan, plan_id)
    if not mp or mp.user_id != user.id:
        raise HTTPException(404, "Meal plan not found")
    return mp


class PlanMealIn(BaseModel):
    meal_type: str = Field(pattern="^(breakfast|lunch|dinner|snack)$")
    title: str = Field(min_length=1, max_length=200)
    recipe_id: str | None = None
    description: str | None = Field(default=None, max_length=500)
    estimated_kcal: float | None = Field(default=None, ge=0, le=5000)


class PlanDayIn(BaseModel):
    day: int = Field(ge=1, le=7)
    meals: list[PlanMealIn] = Field(default_factory=list, max_length=8)


class PlanIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    start_date: date | None = None
    profile_id: str | None = None
    days: list[PlanDayIn] = Field(default_factory=list, max_length=7)


@router.get("/meal-plans")
def list_plans(db: DB, user: CurrentUser):
    rows = db.scalars(select(MealPlan).where(MealPlan.user_id == user.id).order_by(MealPlan.updated_at.desc())).all()
    return [plan_out(db, mp) for mp in rows]


@router.get("/meal-plans/{plan_id}")
def get_plan(plan_id: str, db: DB, user: CurrentUser):
    return plan_out(db, _plan(db, user, plan_id))


def _count_plans(db, user) -> int:
    return len(db.scalars(select(MealPlan.id).where(MealPlan.user_id == user.id)).all())


@router.post("/meal-plans", status_code=201)
def create_plan(body: PlanIn, db: DB, user: CurrentUser):
    ent.count_cap(db, user, "meal_plans", _count_plans(db, user))
    mp = MealPlan(
        user_id=user.id,
        profile_id=body.profile_id,
        name=body.name,
        start_date=body.start_date,
        days=[d.model_dump() for d in body.days],
    )
    db.add(mp)
    db.commit()
    return plan_out(db, mp)


@router.put("/meal-plans/{plan_id}")
def update_plan(plan_id: str, body: PlanIn, db: DB, user: CurrentUser):
    mp = _plan(db, user, plan_id)
    mp.name, mp.start_date, mp.profile_id = body.name, body.start_date, body.profile_id
    mp.days = [d.model_dump() for d in body.days]
    db.commit()
    return plan_out(db, mp)


@router.delete("/meal-plans/{plan_id}", status_code=204)
def delete_plan(plan_id: str, db: DB, user: CurrentUser):
    db.delete(_plan(db, user, plan_id))
    db.commit()


class GeneratePlanIn(BaseModel):
    days: int = Field(7, ge=1, le=7)
    profile_id: str | None = None
    region: str | None = Field(default=None, max_length=8)
    kcal_target: int | None = Field(default=None, ge=1000, le=5000)
    weekly_budget: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")
    preferences: str | None = Field(default=None, max_length=500)


@router.post("/meal-plans/generate", status_code=201)
def generate_plan(body: GeneratePlanIn, db: DB, user: CurrentUser):
    ent.require_quota(db, user, "ai_meal_plans")
    ent.count_cap(db, user, "meal_plans", _count_plans(db, user))
    constraints, profiles = _constraints(
        db,
        user,
        body.profile_id,
        region=body.region,
        kcal_target=body.kcal_target,
        weekly_budget=body.weekly_budget,
        currency=body.currency or user.currency,
        preferences=body.preferences,
    )
    data = _run_ai(db, user, "ai_meal_plans", lambda p: ai.generate_meal_plan(p, body.days, constraints))
    titles = {r.title.lower(): r.id for r in db.scalars(select(Recipe).where(Recipe.is_public.is_(True))).all()}
    days = []
    for d in (data.get("days") or [])[: body.days]:
        meals = []
        for m in (d.get("meals") or [])[:8]:
            if m.get("meal_type") not in ("breakfast", "lunch", "dinner", "snack") or not m.get("title"):
                continue
            title = str(m["title"])[:200]
            kcal = m.get("estimated_kcal")
            meals.append(
                {
                    "meal_type": m["meal_type"],
                    "title": title,
                    "description": (str(m.get("description") or "")[:500] or None),
                    "estimated_kcal": kcal if isinstance(kcal, int | float) else None,
                    "recipe_id": titles.get(title.lower()),
                }
            )
        days.append({"day": len(days) + 1, "meals": meals})
    if not days:
        raise HTTPException(502, {"code": "ai_failed", "message": "The AI returned an empty plan. Try again."})
    mp = MealPlan(
        user_id=user.id,
        profile_id=profiles[0].id if profiles else None,
        name=str(data.get("name") or "My meal plan")[:120],
        start_date=date.today(),
        days=days,
    )
    db.add(mp)
    db.commit()
    return {
        **plan_out(db, mp),
        "notes": data.get("notes"),
        "notice": "AI-generated plan. Calories are rough estimates. Check labels for allergens.",
    }


@router.post("/meal-plans/{plan_id}/shopping-list")
def plan_to_list(plan_id: str, body: ToListIn, db: DB, user: CurrentUser):
    """Shopping list from every recipe linked in the plan; meals without a recipe are listed by name."""
    mp = _plan(db, user, plan_id)
    lines: list[dict] = []
    unlinked = []
    for d in mp.days:
        for m in d.get("meals", []):
            r = db.get(Recipe, m["recipe_id"]) if m.get("recipe_id") else None
            if r and (r.is_public or r.created_by == user.id):
                lines += _scaled(r, body.servings)
            else:
                unlinked.append(m["title"])
    sl = target_list(db, user, body.list_id, f"For {mp.name}")
    added = add_lines(db, sl, user, lines)
    db.commit()
    return {"added": added, "meals_without_recipe": sorted(set(unlinked)), "list": list_out(sl)}
