"""Grounded AI nutrition assistant (retrieval over our structured product + knowledge data)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.products import region_of
from app.api.v1.profiles import profile_out, resolve_profiles
from app.core.deps import DB, CurrentUser
from app.models import Product, ScientificSource
from app.services import entitlements as ent
from app.services import product_service as ps
from app.services.ai import features as ai
from app.services.ai.provider import AIError, AINotConfigured, get_provider
from app.services.knowledge import get_kb

router = APIRouter(prefix="/assistant", tags=["assistant"])


class Msg(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=4000)


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    product_ids: list[str] = Field(default_factory=list, max_length=4)
    ingredient_slugs: list[str] = Field(default_factory=list, max_length=10)
    history: list[Msg] = Field(default_factory=list, max_length=16)
    profile_id: str | None = None


def _product_context(db, p: Product, profiles, region) -> dict:
    a = ps.analyze_product(db, p, profiles, region)
    sc = a["score"]
    return {
        "name": p.name,
        "brand": p.brand_text,
        "barcode": p.barcodes[0].barcode if p.barcodes else None,
        "data_source": p.source,
        "attribution": (p.raw_data or {}).get("attribution"),
        "ingredients_text": p.ingredients_text,
        "nutrition_per_100": ps.nutrition_input(p).to_dict() if ps.nutrition_input(p) else None,
        "score": {
            "overall": sc["overall"],
            "grade": sc["grade"],
            "confidence": sc["confidence"],
            "methodology_version": sc["methodology_version"],
            "components": {
                k: {"score": v["score"], "adjustments": v["adjustments"], "notes": v["notes"]}
                for k, v in sc["components"].items()
            },
            "caps": sc["caps_applied"],
            "front_of_pack": sc["front_of_pack"],
        },
        "ingredients": [{"text": i["text"], **(i["ingredient"] or {})} for i in a["ingredients"]],
        "allergens": [
            {"name": x["name"], "status": x["status"]} for x in a["allergens"] if x["status"] != "not_detected"
        ],
        "compatibility": a["compatibility"],
        "recalls": a["recalls"],
        "contaminant_testing": a["contaminant_testing"],
    }


@router.post("/ask")
def ask(body: AskIn, db: DB, user: CurrentUser):
    ent.require_quota(db, user, "ai_assistant")
    try:
        provider = get_provider()
    except AINotConfigured as e:
        raise HTTPException(503, {"code": "ai_not_configured", "message": f"The AI assistant isn't available: {e}"})
    region = region_of(user)
    profiles = resolve_profiles(db, user, [body.profile_id] if body.profile_id else None)
    products = []
    for pid in body.product_ids:
        p = db.get(Product, pid)
        if p:
            products.append(_product_context(db, p, profiles, region))
    kb = get_kb(db)
    ingredients = []
    for slug in body.ingredient_slugs:
        e = kb.by_slug.get(slug)
        if e:
            ingredients.append(
                {
                    "slug": e.slug,
                    "name": e.display_name(region),
                    "function": e.function,
                    "concern_level": e.concern_level,
                    "summary": e.concern_summary,
                    "plain_language": e.plain_language,
                    "regulatory_notes": e.regulatory_notes,
                    "sources": e.source_keys,
                }
            )
    keys = set()
    for p in products:
        for c in p["score"]["components"].values():
            for adj in c["adjustments"]:
                keys.update(adj.get("source_keys", []))
    for i in ingredients:
        keys.update(i["sources"])
    sources = [
        {
            "key": s.key,
            "title": s.title,
            "publisher": s.publisher,
            "year": s.year,
            "url": s.url,
            "evidence_quality": s.evidence_quality,
            "summary": s.summary,
        }
        for s in db.scalars(select(ScientificSource).where(ScientificSource.key.in_(keys or {"-"}))).all()
    ]
    ctx = ai.build_context(
        products + [{"ingredient_knowledge": ingredients}] if ingredients else products,
        sources,
        profile_out(profiles[0]) if profiles else None,
    )
    try:
        res = ai.ask(provider, body.question, ctx, [h.model_dump() for h in body.history])
    except AIError as e:
        ent.record_usage(db, user, "ai_assistant", provider.name, getattr(provider, "model", None), ok=False)
        raise HTTPException(
            502, {"code": "ai_failed", "message": "The assistant couldn't answer right now.", "detail": str(e)[:200]}
        )
    ent.record_usage(
        db,
        user,
        "ai_assistant",
        res.provider,
        res.model,
        input_tokens=res.input_tokens,
        output_tokens=res.output_tokens,
    )
    return {
        "answer": res.text,
        "grounded_on": {"products": [p["name"] for p in products], "ingredients": [i["name"] for i in ingredients]},
        "sources": sources,
        "ai_generated": True,
        "disclaimer": ai.MEDICAL_DISCLAIMER,
        "history_stored": False,
    }
