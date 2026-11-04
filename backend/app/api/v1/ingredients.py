"""Ingredient encyclopedia and research sources (public)."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.deps import DB
from app.models import Ingredient, ProductRecall, ScientificSource
from app.services.knowledge import get_kb

router = APIRouter(tags=["ingredients"])


def source_out(s: ScientificSource) -> dict:
    return {
        "key": s.key,
        "title": s.title,
        "authors": s.authors,
        "publisher": s.publisher,
        "year": s.year,
        "url": s.url,
        "doi": s.doi,
        "source_type": s.source_type,
        "evidence_quality": s.evidence_quality,
        "summary": s.summary,
        "verified": s.verified,
    }


def ingredient_out(i: Ingredient, region: str = "US", sources: list | None = None) -> dict:
    return {
        "slug": i.slug,
        "name": i.us_name if region == "US" and i.us_name else i.name,
        "international_name": i.name,
        "category": i.category,
        "function": i.function,
        "plain_language": i.plain_language,
        "concern_level": i.concern_level,
        "concern_summary": i.concern_summary,
        "e_number": i.e_number,
        "vegan": i.vegan,
        "vegetarian": i.vegetarian,
        "halal_concern": i.halal_concern,
        "allergen": i.allergen_code,
        "fodmap": i.fodmap,
        "flags": i.flags,
        "regulatory_notes": i.regulatory_notes,
        "synonyms": sorted({s.term for s in i.synonyms})[:40],
        "verification_status": i.verification_status,
        "verified_at": i.verified_at.isoformat() if i.verified_at else None,
        "sources": sources if sources is not None else i.source_keys,
    }


@router.get("/ingredients")
def list_ingredients(
    db: DB,
    q: str | None = Query(None, max_length=80),
    category: str | None = None,
    concern: str | None = Query(None, pattern="^(beneficial|neutral|caution|concern|unknown)$"),
    flag: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    region: str = "US",
):
    if q:
        slugs = [e.slug for e in get_kb(db).search(q, limit=limit)]
        rows = {i.slug: i for i in db.scalars(select(Ingredient).where(Ingredient.slug.in_(slugs))).all()}
        items = [rows[s] for s in slugs if s in rows]
    else:
        stmt = select(Ingredient)
        if category:
            stmt = stmt.where(Ingredient.category == category)
        if concern:
            stmt = stmt.where(Ingredient.concern_level == concern)
        items = list(db.scalars(stmt.order_by(Ingredient.name).offset(offset).limit(limit if not flag else 1000)).all())
    if flag:
        items = [i for i in items if flag in (i.flags or [])][:limit]
    cats = sorted({c for (c,) in db.execute(select(Ingredient.category).distinct()).all()})
    return {
        "items": [
            {
                "slug": i.slug,
                "name": i.us_name if region == "US" and i.us_name else i.name,
                "category": i.category,
                "concern_level": i.concern_level,
                "e_number": i.e_number,
                "function": i.function,
            }
            for i in items
        ],
        "categories": cats,
    }


@router.get("/ingredients/{slug}")
def get_ingredient(slug: str, db: DB, region: str = "US"):
    i = db.scalar(select(Ingredient).where(Ingredient.slug == slug))
    if not i:
        raise HTTPException(404, "Ingredient not found")
    srcs = db.scalars(select(ScientificSource).where(ScientificSource.key.in_(i.source_keys or ["-"]))).all()
    return ingredient_out(i, region, [source_out(s) for s in srcs])


@router.get("/sources")
def list_sources(db: DB, source_type: str | None = None):
    stmt = select(ScientificSource)
    if source_type:
        stmt = stmt.where(ScientificSource.source_type == source_type)
    return [source_out(s) for s in db.scalars(stmt.order_by(ScientificSource.year.desc())).all()]


@router.get("/recalls")
def recalls(db: DB, jurisdiction: str | None = None, limit: int = Query(50, le=200)):
    stmt = select(ProductRecall).where(ProductRecall.verified.is_(True))
    if jurisdiction:
        stmt = stmt.where(ProductRecall.jurisdiction == jurisdiction.upper())
    rows = db.scalars(stmt.order_by(ProductRecall.recall_date.desc()).limit(limit)).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "reason": r.reason,
            "hazard": r.hazard,
            "jurisdiction": r.jurisdiction,
            "authority": r.authority,
            "recall_date": r.recall_date.isoformat() if r.recall_date else None,
            "url": r.url,
            "status": r.status,
            "product_id": r.product_id,
            "barcode": r.barcode,
        }
        for r in rows
    ]
