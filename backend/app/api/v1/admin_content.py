"""Admin: analytics, product and ingredient creation, lab report and recall review,
content (articles, recipes), price moderation and scheduled jobs. All mutations are audit-logged."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.deps import DB, Admin, Moderator, request_ip
from app.models import (
    AIUsageRecord,
    Article,
    FoodScan,
    Ingredient,
    IngredientSynonym,
    LaboratoryReport,
    MealEntry,
    PantryItem,
    PriceObservation,
    Product,
    ProductBarcode,
    ProductRecall,
    Recipe,
    User,
)
from app.services import alerts
from app.services import product_service as ps
from app.services.audit import audit, snapshot
from app.services.barcode import InvalidBarcode, parse_barcode
from app.services.knowledge import invalidate_kb
from app.services.nutrition import NutritionInput
from app.services.providers.base import ProviderProduct
from app.services.text import normalize_term

router = APIRouter(prefix="/admin", tags=["admin"])


def _now():
    return datetime.now(UTC)


# ------------------------------------------------------------------ analytics


@router.get("/analytics")
def analytics(db: DB, _: Moderator, days: int = Query(30, ge=1, le=365)):
    since = _now() - timedelta(days=days)
    day = func.date(FoodScan.created_at)
    scans_by_day = db.execute(
        select(day, func.count()).where(FoodScan.created_at >= since).group_by(day).order_by(day)
    ).all()
    top = db.execute(
        select(Product.id, Product.name, Product.brand_text, func.count(FoodScan.id).label("n"))
        .join(FoodScan, FoodScan.product_id == Product.id)
        .where(FoodScan.created_at >= since)
        .group_by(Product.id, Product.name, Product.brand_text)
        .order_by(func.count(FoodScan.id).desc())
        .limit(15)
    ).all()
    not_found = db.execute(
        select(FoodScan.barcode, func.count())
        .where(FoodScan.created_at >= since, FoodScan.status == "not_found")
        .group_by(FoodScan.barcode)
        .order_by(func.count().desc())
        .limit(15)
    ).all()
    signups = db.execute(
        select(func.date(User.created_at), func.count())
        .where(User.created_at >= since)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    ).all()
    features = db.execute(
        select(AIUsageRecord.feature, func.count(), func.coalesce(func.sum(AIUsageRecord.est_cost_usd), 0))
        .where(AIUsageRecord.created_at >= since)
        .group_by(AIUsageRecord.feature)
    ).all()
    return {
        "days": days,
        "scans_by_day": [{"day": str(d), "scans": n} for d, n in scans_by_day],
        "active_scanners": db.scalar(
            select(func.count(func.distinct(FoodScan.user_id))).where(FoodScan.created_at >= since)
        ),
        "signups_by_day": [{"day": str(d), "users": n} for d, n in signups],
        "top_products": [{"id": i, "name": n, "brand": b, "scans": c} for i, n, b, c in top],
        "top_missing_barcodes": [{"barcode": b, "scans": c} for b, c in not_found],
        "feature_usage": [{"feature": f, "uses": n, "est_cost_usd": round(c, 4)} for f, n, c in features],
        "diary_entries": db.scalar(select(func.count()).select_from(MealEntry).where(MealEntry.created_at >= since)),
        "pantry_items": db.scalar(select(func.count()).select_from(PantryItem)),
        "recipes_user_or_ai": db.scalar(select(func.count()).select_from(Recipe).where(Recipe.created_by.is_not(None))),
    }


# ------------------------------------------------------------------ products & ingredients


class ProductCreate(BaseModel):
    barcode: str
    name: str = Field(min_length=1, max_length=300)
    brand: str | None = Field(default=None, max_length=300)
    category: str | None = Field(default=None, max_length=160)
    quantity: str | None = Field(default=None, max_length=80)
    serving_size: str | None = Field(default=None, max_length=80)
    ingredients_text: str | None = Field(default=None, max_length=8000)
    nutrition: dict[str, float] | None = None  # per 100 g / 100 ml, NutritionInput field names
    is_beverage: bool = False
    countries: list[str] = Field(default_factory=list, max_length=20)
    nafdac_number: str | None = Field(default=None, max_length=40)
    reason: str | None = Field(default=None, max_length=500)


@router.post("/products", status_code=201)
def create_product(body: ProductCreate, db: DB, mod: Moderator, request: Request):
    try:
        bc = parse_barcode(body.barcode)
    except InvalidBarcode as e:
        raise HTTPException(422, {"code": "invalid_barcode", "message": str(e)})
    if db.scalar(select(ProductBarcode).where(ProductBarcode.gtin14 == bc.gtin14)):
        raise HTTPException(409, "A product with this barcode already exists; edit it instead")
    n = None
    if body.nutrition:
        n = NutritionInput(
            **{k: v for k, v in body.nutrition.items() if k in NutritionInput.__dataclass_fields__},
            is_beverage=body.is_beverage,
        )
    pp = ProviderProduct(
        source="admin",
        source_id=f"admin:{bc.raw}",
        barcode=bc.raw,
        name=body.name,
        brand=body.brand,
        category_label=body.category,
        quantity=body.quantity,
        serving_size=body.serving_size,
        ingredients_text=body.ingredients_text,
        ingredients_lang="en",
        nutrition=n if n and n.core_present() else None,
        countries_tags=[f"en:{c.lower()}" for c in body.countries],
        is_beverage=body.is_beverage,
        license="Entered by Food omniScan staff",
        attribution="Food omniScan editorial team",
    )
    p = ps.upsert_product(db, pp, bc, {"all": "admin"})
    p.source, p.verified_at, p.verified_by = "admin", _now(), mod.id
    p.nafdac_number = body.nafdac_number
    audit(
        db,
        mod,
        "product.create",
        "product",
        p.id,
        after=snapshot(p, ["name", "brand_text", "source"]),
        ip=request_ip(request),
        note=body.reason,
    )
    db.commit()
    return {"id": p.id}


class IngredientCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]{2,120}$")
    name: str = Field(max_length=200)
    us_name: str | None = Field(default=None, max_length=200)
    category: str = Field(max_length=60)
    function: str = Field(max_length=300)
    plain_language: str | None = Field(default=None, max_length=4000)
    concern_level: str = Field("neutral", pattern="^(beneficial|neutral|caution|concern|unknown)$")
    concern_summary: str | None = Field(default=None, max_length=4000)
    e_number: str | None = Field(default=None, max_length=10)
    allergen_code: str | None = Field(default=None, max_length=40)
    synonyms: list[str] = Field(default_factory=list, max_length=40)
    source_keys: list[str] = Field(default_factory=list, max_length=20)


@router.post("/ingredients", status_code=201)
def create_ingredient(body: IngredientCreate, db: DB, admin: Admin, request: Request):
    if db.scalar(select(Ingredient).where(Ingredient.slug == body.slug)):
        raise HTTPException(409, "Ingredient slug exists")
    ing = Ingredient(
        **body.model_dump(exclude={"synonyms"}),
        is_additive=bool(body.e_number),
        verification_status="pending",
        flags=[],
        regulatory_notes=[],
    )
    db.add(ing)
    db.flush()
    for t in {normalize_term(x) for x in [body.name, *body.synonyms]}:
        if t and not db.scalar(
            select(IngredientSynonym).where(IngredientSynonym.term == t, IngredientSynonym.language == "en")
        ):
            db.add(IngredientSynonym(ingredient_id=ing.id, term=t, language="en"))
    audit(db, admin, "ingredient.create", "ingredient", ing.slug, after=body.model_dump(), ip=request_ip(request))
    db.commit()
    invalidate_kb()
    return {"slug": ing.slug}


# ------------------------------------------------------------------ lab reports & recalls


@router.get("/lab-reports")
def lab_reports(db: DB, _: Moderator, verified: bool | None = None):
    stmt = select(LaboratoryReport).order_by(LaboratoryReport.created_at.desc()).limit(200)
    if verified is not None:
        stmt = stmt.where(LaboratoryReport.verified.is_(verified))
    return [
        {
            "id": r.id,
            "product_id": r.product_id,
            "lab_name": r.lab_name,
            "analyte": r.analyte,
            "value": r.value,
            "unit": r.unit,
            "batch": r.batch,
            "tested_on": r.tested_on.isoformat() if r.tested_on else None,
            "exceeds_threshold": r.exceeds_threshold,
            "verified": r.verified,
        }
        for r in db.scalars(stmt).all()
    ]


@router.post("/lab-reports/{report_id}/verify")
def verify_lab(report_id: str, db: DB, admin: Admin, request: Request):
    r = db.get(LaboratoryReport, report_id)
    if not r:
        raise HTTPException(404, "Lab report not found")
    r.verified = True
    audit(db, admin, "lab_report.verify", "lab_report", r.id, ip=request_ip(request))
    db.commit()
    return {"id": r.id, "verified": True}


@router.get("/recalls")
def recalls(db: DB, _: Moderator):
    rows = db.scalars(select(ProductRecall).order_by(ProductRecall.created_at.desc()).limit(200)).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "authority": r.authority,
            "jurisdiction": r.jurisdiction,
            "product_id": r.product_id,
            "barcode": r.barcode,
            "status": r.status,
            "verified": r.verified,
            "notified_at": r.notified_at.isoformat() if r.notified_at else None,
        }
        for r in rows
    ]


# ------------------------------------------------------------------ articles


class ArticleIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]{3,120}$")
    title: str = Field(max_length=200)
    summary: str = Field(max_length=500)
    body: str = Field(max_length=20000)
    topic: str = Field(pattern="^(nutrition|processing|ingredients|safety|african|announcement)$")
    region: str | None = Field(default=None, max_length=8)
    source_keys: list[str] = Field(default_factory=list, max_length=20)
    status: str = Field("draft", pattern="^(draft|published)$")


def _article_admin(a: Article) -> dict:
    return {
        "slug": a.slug,
        "title": a.title,
        "summary": a.summary,
        "body": a.body,
        "topic": a.topic,
        "region": a.region,
        "source_keys": a.source_keys,
        "status": a.status,
        "published_at": a.published_at.isoformat() if a.published_at else None,
    }


@router.get("/articles")
def admin_articles(db: DB, _: Moderator):
    return [_article_admin(a) for a in db.scalars(select(Article).order_by(Article.updated_at.desc())).all()]


@router.put("/articles/{slug}")
def upsert_article(slug: str, body: ArticleIn, db: DB, mod: Moderator, request: Request):
    if body.slug != slug:
        raise HTTPException(422, "Slug in the URL and body must match")
    a = db.scalar(select(Article).where(Article.slug == slug))
    before = _article_admin(a) if a else None
    if a is None:
        a = Article(slug=slug, author_id=mod.id, **body.model_dump(exclude={"slug"}))
        db.add(a)
    else:
        for k, v in body.model_dump(exclude={"slug"}).items():
            setattr(a, k, v)
    if a.status == "published" and a.published_at is None:
        a.published_at = _now()
    audit(db, mod, "article.upsert", "article", slug, before=before, after=body.model_dump(), ip=request_ip(request))
    db.commit()
    return _article_admin(a)


@router.delete("/articles/{slug}", status_code=204)
def delete_article(slug: str, db: DB, admin: Admin, request: Request):
    a = db.scalar(select(Article).where(Article.slug == slug))
    if not a:
        raise HTTPException(404, "Article not found")
    audit(db, admin, "article.delete", "article", slug, before=_article_admin(a), ip=request_ip(request))
    db.delete(a)
    db.commit()


# ------------------------------------------------------------------ recipes & prices moderation


@router.get("/recipes")
def admin_recipes(db: DB, _: Moderator, verified: bool | None = None):
    stmt = select(Recipe).where(Recipe.is_public.is_(True))
    if verified is not None:
        stmt = stmt.where(Recipe.verified.is_(verified))
    return [
        {"id": r.id, "title": r.title, "region": r.region, "verified": r.verified, "has_nutrition": bool(r.nutrition)}
        for r in db.scalars(stmt.order_by(Recipe.title)).all()
    ]


class RecipePatch(BaseModel):
    verified: bool | None = None
    is_public: bool | None = None


@router.patch("/recipes/{recipe_id}")
def patch_recipe(recipe_id: str, body: RecipePatch, db: DB, mod: Moderator, request: Request):
    r = db.get(Recipe, recipe_id)
    if not r:
        raise HTTPException(404, "Recipe not found")
    before = snapshot(r, ["verified", "is_public"])
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    audit(
        db,
        mod,
        "recipe.update",
        "recipe",
        r.id,
        before=before,
        after=snapshot(r, ["verified", "is_public"]),
        ip=request_ip(request),
    )
    db.commit()
    return {"id": r.id, "verified": r.verified, "is_public": r.is_public}


@router.delete("/prices/{price_id}", status_code=204)
def delete_price(price_id: str, db: DB, mod: Moderator, request: Request):
    p = db.get(PriceObservation, price_id)
    if not p:
        raise HTTPException(404, "Price report not found")
    audit(
        db,
        mod,
        "price.delete",
        "price",
        p.id,
        before=snapshot(p, ["product_id", "price", "currency", "store"]),
        ip=request_ip(request),
    )
    db.delete(p)
    db.commit()


# ------------------------------------------------------------------ jobs


@router.post("/jobs/daily")
def run_daily_jobs(db: DB, admin: Admin, request: Request):
    """Expiry reminders every day; weekly reports and tips on Mondays. Normally run by a scheduler."""
    out = alerts.run_daily(db)
    audit(db, admin, "jobs.daily", "jobs", None, after=out, ip=request_ip(request))
    db.commit()
    return out
