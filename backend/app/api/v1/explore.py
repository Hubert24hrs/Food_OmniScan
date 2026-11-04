"""Discovery: category rankings, recommendations, shareable reports, prices, product history,
education, local food glossary, food-safety topics."""

import re
import secrets
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.v1.products import product_out, region_of
from app.api.v1.profiles import resolve_profiles
from app.core.deps import DB, CurrentUser, OptionalUser
from app.data.content_seed import LOCAL_FOODS, LOCAL_INGREDIENT_NAMES, RISK_EXPLAINER, SAFETY_TOPICS
from app.models import (
    AdminAuditLog,
    Article,
    FoodBrand,
    FoodCategory,
    LaboratoryReport,
    Manufacturer,
    PriceObservation,
    Product,
    Recipe,
    ScanHistory,
    ScientificSource,
    SharedReport,
)
from app.services import entitlements as ent
from app.services import product_service as ps
from app.services.alternatives import country_tag

router = APIRouter(tags=["explore"])

FREE_RANKING_ROWS = 5
_COMPONENT_LABELS = {
    "nutrition": "nutrition",
    "ingredients": "ingredients and additives",
    "processing": "processing",
    "dietary_suitability": "dietary suitability",
    "product_concerns": "product-specific concerns",
}


def _criteria(cfg: dict) -> str:
    """Describe the ranking criteria from the active methodology's own weights."""
    parts = [f"{_COMPONENT_LABELS.get(k, k)} {v}%" for k, v in cfg["weights"].items()]
    return f"Overall health score ({', '.join(parts)}). Products with insufficient data are not ranked."


# ------------------------------------------------------------------ categories & rankings


@router.get("/categories")
def categories(db: DB, limit: int = Query(60, ge=1, le=200)):
    rows = db.execute(
        select(FoodCategory.code, FoodCategory.name, func.count(Product.id))
        .join(Product, Product.category_id == FoodCategory.id)
        .where(Product.status == "active")
        .group_by(FoodCategory.code, FoodCategory.name)
        .order_by(func.count(Product.id).desc())
        .limit(limit)
    ).all()
    return [{"code": c, "name": n, "products": k} for c, n, k in rows]


def _ranked(db, category: str, country: str | None) -> list[dict]:
    cat = db.scalar(select(FoodCategory).where(FoodCategory.code == category))
    if not cat:
        raise HTTPException(404, "Category not found")
    products = db.scalars(select(Product).where(Product.category_id == cat.id, Product.status == "active")).all()
    if country:
        tag = country_tag(country)
        products = [p for p in products if tag in (p.countries_tags or [])]
    out = []
    for p in products:
        summary = ps.product_summary(db, p)  # stored score for the active methodology, computed if missing
        if summary["score"] is not None:  # insufficient data: not ranked
            out.append(summary)
    out.sort(key=lambda r: (-r["score"], r["name"] or ""))
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out


@router.get("/rankings")
def rankings(
    db: DB,
    user: OptionalUser,
    category: str = Query(min_length=2, max_length=160),
    country: str | None = Query(default=None, pattern="^[A-Za-z]{2}$"),
):
    """Products in a category ranked by the current methodology's overall score (highest first).

    Products without enough data to score are left out rather than ranked low.
    """
    rows = _ranked(db, category, country)
    full = ent.has_feature(db, user, "full_rankings")
    return {
        "category": category,
        "methodology_version": ps.active_methodology(db)["version"],
        "criteria": _criteria(ps.active_methodology(db)),
        "total": len(rows),
        "results": rows if full else rows[:FREE_RANKING_ROWS],
        "locked": not full and len(rows) > FREE_RANKING_ROWS,
        "best_in_category": rows[0] if rows else None,
    }


@router.get("/recommendations")
def recommendations(db: DB, user: CurrentUser, limit: int = Query(12, ge=1, le=30)):
    """Better-scoring products in the categories you scan most, that pass your profile's checks."""
    ent.require_feature(db, user, "recommendations")
    profiles = resolve_profiles(db, user, None)
    history = db.scalars(
        select(ScanHistory).where(ScanHistory.user_id == user.id).order_by(ScanHistory.last_scanned_at.desc()).limit(50)
    ).all()
    cats: dict[str, int] = {}
    seen = set()
    for h in history:
        p = db.get(Product, h.product_id)
        seen.add(h.product_id)
        if p and p.category_id:
            cats[p.category_id] = cats.get(p.category_id, 0) + h.scan_count
    out = []
    for cat_id, _ in sorted(cats.items(), key=lambda kv: -kv[1])[:4]:
        cat = db.get(FoodCategory, cat_id)
        for r in _ranked(db, cat.code, None)[:15]:
            if r["id"] in seen:
                continue
            p = db.get(Product, r["id"])
            verdicts = [c["verdict"] for c in ps.analyze_product(db, p, profiles, region_of(user))["compatibility"]]
            if "red" in verdicts:
                continue
            out.append({**r, "category_name": cat.name, "reason": f"Scores {r['score']} in {cat.name}"})
            if len(out) >= limit:
                return {"results": out}
    return {"results": out, "note": None if out else "Scan a few products so we can learn what you buy."}


# ------------------------------------------------------------------ shareable product reports


@router.post("/products/{product_id}/share", status_code=201)
def share_product(product_id: str, db: DB, user: OptionalUser):
    p = db.get(Product, product_id)
    if not p or p.status != "active":
        raise HTTPException(404, "Product not found")
    row = SharedReport(token=secrets.token_urlsafe(12), product_id=p.id, created_by=user.id if user else None)
    db.add(row)
    db.commit()
    return {"token": row.token, "path": f"/r/{row.token}"}


@router.get("/shared/{token}")
def shared_report(token: str, db: DB):
    row = db.scalar(select(SharedReport).where(SharedReport.token == token))
    p = db.get(Product, row.product_id) if row else None
    if not p or p.status != "active":
        raise HTTPException(404, "Report not found")
    # No profiles: a shared report never exposes the sharer's personal compatibility data.
    return {"product": product_out(db, p), "analysis": ps.analyze_product(db, p, [], "US"), "shared": True}


# ------------------------------------------------------------------ brand, history, lab results


@router.get("/products/{product_id}/details")
def product_details(product_id: str, db: DB):
    """Brand and manufacturer, NAFDAC registration, verified lab results and the change history."""
    p = db.get(Product, product_id)
    if not p or p.status != "active":
        raise HTTPException(404, "Product not found")
    brand = db.get(FoodBrand, p.brand_id) if p.brand_id else None
    maker = db.get(Manufacturer, brand.manufacturer_id) if brand and brand.manufacturer_id else None
    labs = db.scalars(
        select(LaboratoryReport).where(LaboratoryReport.product_id == p.id, LaboratoryReport.verified.is_(True))
    ).all()
    history = db.scalars(
        select(AdminAuditLog)
        .where(AdminAuditLog.entity == "product", AdminAuditLog.entity_id == p.id)
        .order_by(AdminAuditLog.created_at.desc())
        .limit(30)
    ).all()
    changes = []
    for h in history:
        diff = sorted(k for k in (h.after or {}) if (h.before or {}).get(k) != (h.after or {}).get(k))
        changes.append({"at": h.created_at.isoformat(), "action": h.action, "fields": diff, "note": h.note})
    return {
        "brand": brand.name if brand else p.brand_text,
        "manufacturer": None
        if not maker
        else {
            "name": maker.name,
            "parent_company": maker.parent_company,
            "country": maker.country,
            "website": maker.website,
        },
        "nafdac": nafdac_info(p.nafdac_number),
        "lab_results": [
            {
                "lab": r.lab_name,
                "method": r.method,
                "batch": r.batch,
                "tested_on": r.tested_on.isoformat() if r.tested_on else None,
                "analyte": r.analyte,
                "value": r.value,
                "unit": r.unit,
                "threshold": r.threshold,
                "threshold_jurisdiction": r.threshold_jurisdiction,
                "exceeds_threshold": r.exceeds_threshold,
                "note": "Verified test of this product. Results apply to the batch tested.",
            }
            for r in labs
        ],
        "history": changes,
        "last_synced_at": p.last_synced_at.isoformat() if p.last_synced_at else None,
        "source": p.source,
    }


_NAFDAC = re.compile(r"^(A[0-9]|[0-9]{2})-?[0-9]{3,5}[A-Z]?$", re.I)


def nafdac_info(number: str | None) -> dict | None:
    if not number:
        return None
    n = number.strip().upper().replace(" ", "")
    return {
        "number": n,
        "format_ok": bool(_NAFDAC.match(n)),
        "check_url": "https://greenbook.nafdac.gov.ng/",
        "note": "Check this number in the NAFDAC Greenbook. Registration isn't a health rating.",
    }


# ------------------------------------------------------------------ prices (crowd-reported)


class PriceIn(BaseModel):
    price: float = Field(gt=0, le=10_000_000)
    currency: str = Field(pattern="^[A-Z]{3}$")
    store: str = Field(min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    country: str = Field(pattern="^[A-Z]{2}$")
    observed_on: date | None = None


@router.post("/products/{product_id}/prices", status_code=201)
def report_price(product_id: str, body: PriceIn, db: DB, user: CurrentUser):
    if not db.get(Product, product_id):
        raise HTTPException(404, "Product not found")
    observed = body.observed_on or date.today()
    if observed > date.today():
        raise HTTPException(422, "Date can't be in the future")
    db.add(
        PriceObservation(
            product_id=product_id, user_id=user.id, **body.model_dump(exclude={"observed_on"}), observed_on=observed
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/products/{product_id}/prices")
def product_prices(product_id: str, db: DB, user: OptionalUser, country: str | None = None):
    """Recent shelf prices reported by users, grouped by store. Not a live retailer feed."""
    since = date.today() - timedelta(days=120)
    stmt = select(PriceObservation).where(
        PriceObservation.product_id == product_id, PriceObservation.observed_on >= since
    )
    if country:
        stmt = stmt.where(PriceObservation.country == country.upper())
    rows = db.scalars(stmt.order_by(PriceObservation.observed_on.desc())).all()
    stores = sorted({(r.store, r.city, r.country) for r in rows})
    base = {
        "reports": len(rows),
        "where_to_buy": [{"store": s, "city": c, "country": k} for s, c, k in stores],
        "note": "Prices are reported by Food omniScan users and may be out of date.",
    }
    if not ent.has_feature(db, user, "price_comparison"):
        return {**base, "locked": True, "by_store": None}
    latest: dict[tuple, PriceObservation] = {}
    for r in rows:
        latest.setdefault((r.store, r.city, r.currency), r)
    by_store = sorted(
        (
            {"store": s, "city": c, "currency": cur, "price": r.price, "observed_on": r.observed_on.isoformat()}
            for (s, c, cur), r in latest.items()
        ),
        key=lambda x: (x["currency"], x["price"]),
    )
    return {**base, "locked": False, "by_store": by_store, "cheapest": by_store[0] if by_store else None}


@router.post("/prices/compare")
def compare_prices(db: DB, user: CurrentUser, product_ids: list[str], country: str | None = None):
    """Cheapest recent reported price for each product (same currency), e.g. for alternatives."""
    ent.require_feature(db, user, "price_comparison")
    out = []
    for pid in product_ids[:10]:
        stmt = select(PriceObservation).where(PriceObservation.product_id == pid)
        if country:
            stmt = stmt.where(PriceObservation.country == country.upper())
        r = db.scalars(stmt.order_by(PriceObservation.price)).first()
        out.append(
            {
                "product_id": pid,
                "cheapest": None
                if not r
                else {
                    "price": r.price,
                    "currency": r.currency,
                    "store": r.store,
                    "observed_on": r.observed_on.isoformat(),
                },
            }
        )
    return out


# ------------------------------------------------------------------ education & local foods & safety


def article_out(a: Article, full: bool = False) -> dict:
    out = {
        "slug": a.slug,
        "title": a.title,
        "summary": a.summary,
        "topic": a.topic,
        "region": a.region,
        "published_at": a.published_at.isoformat() if a.published_at else None,
    }
    if full:
        out["body"] = a.body
        out["source_keys"] = a.source_keys
    return out


@router.get("/articles")
def articles(db: DB, topic: str | None = None):
    stmt = select(Article).where(Article.status == "published")
    if topic:
        stmt = stmt.where(Article.topic == topic)
    return [article_out(a) for a in db.scalars(stmt.order_by(Article.published_at.desc())).all()]


def _sources(db, keys: list[str]) -> list[dict]:
    rows = db.scalars(select(ScientificSource).where(ScientificSource.key.in_(keys or ["-"]))).all()
    return [
        {"key": s.key, "title": s.title, "publisher": s.publisher, "year": s.year, "url": s.url, "verified": s.verified}
        for s in rows
    ]


@router.get("/articles/{slug}")
def article(slug: str, db: DB):
    a = db.scalar(select(Article).where(Article.slug == slug, Article.status == "published"))
    if not a:
        raise HTTPException(404, "Article not found")
    return {**article_out(a, full=True), "sources": _sources(db, a.source_keys)}


@router.get("/local-foods")
def local_foods(db: DB, q: str | None = Query(default=None, max_length=60), kind: str | None = None):
    rows = LOCAL_FOODS
    if q:
        t = q.lower()
        rows = [f for f in rows if t in f["name"].lower() or any(t in v.lower() for v in f["names"].values())]
    if kind:
        rows = [f for f in rows if f["kind"] == kind]
    recipes = {r.title: r.id for r in db.scalars(select(Recipe).where(Recipe.is_public.is_(True))).all()}
    return {
        "foods": [{**f, "recipe_id": recipes.get(f.get("recipe_title"))} for f in rows],
        "ingredient_names": LOCAL_INGREDIENT_NAMES,
        "names_reviewed": False,
        "note": "Local names are as commonly used and are pending editorial review. Nutrient values for these "
        "dishes vary a lot with recipe and portion; use a photo estimate or the FAO West Africa food "
        "composition table.",
    }


@router.get("/safety/topics")
def safety_topics(db: DB):
    return {
        "risk_explainer": RISK_EXPLAINER,
        "topics": [{**t, "sources": _sources(db, t["source_keys"])} for t in SAFETY_TOPICS],
    }
