"""Analyse label text (from on-device OCR) and photos (cloud vision, quota-limited)."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.api.v1.products import region_of
from app.api.v1.profiles import resolve_profiles
from app.core.config import get_settings
from app.core.deps import DB, CurrentUser, OptionalUser
from app.services import entitlements as ent
from app.services import product_service as ps
from app.services.ai import features as ai
from app.services.ai.provider import AIError, AINotConfigured, get_provider
from app.services.compatibility import ProfileSpec
from app.services.nutrition import (
    NUTRIENT_FIELDS,
    NutritionInput,
    label_to_per100,
    parse_nutrition_label,
)
from app.services.uploads import validate_image

router = APIRouter(prefix="/analysis", tags=["analysis"])


class NutritionPer100(BaseModel):
    energy_kcal: float | None = Field(default=None, ge=0, le=1000)
    fat: float | None = Field(default=None, ge=0, le=100)
    saturated_fat: float | None = Field(default=None, ge=0, le=100)
    trans_fat: float | None = Field(default=None, ge=0, le=100)
    cholesterol_mg: float | None = Field(default=None, ge=0, le=5000)
    carbohydrates: float | None = Field(default=None, ge=0, le=100)
    sugars: float | None = Field(default=None, ge=0, le=100)
    added_sugars: float | None = Field(default=None, ge=0, le=100)
    fiber: float | None = Field(default=None, ge=0, le=100)
    protein: float | None = Field(default=None, ge=0, le=100)
    salt: float | None = Field(default=None, ge=0, le=100)
    sodium: float | None = Field(default=None, ge=0, le=40)
    serving_size_g: float | None = Field(default=None, gt=0, le=2000)


class TextAnalysisIn(BaseModel):
    ingredients_text: str | None = Field(default=None, max_length=10000)
    nutrition_text: str | None = Field(default=None, max_length=10000)
    nutrition: NutritionPer100 | None = None
    is_beverage: bool = False
    profile_ids: list[str] | None = None


@router.post("/text")
def analyze_text(body: TextAnalysisIn, db: DB, user: OptionalUser):
    """Score corrected OCR text before (or without) submitting a product. Nothing is saved."""
    if not body.ingredients_text and not body.nutrition_text and not body.nutrition:
        raise HTTPException(422, "Provide ingredients_text, nutrition_text or nutrition")
    parsed_label = None
    n: NutritionInput | None = None
    if body.nutrition:
        n = NutritionInput(**body.nutrition.model_dump(), is_beverage=body.is_beverage)
        if not n.core_present():
            n = None
    elif body.nutrition_text:
        parsed_label = parse_nutrition_label(body.nutrition_text)
        n = label_to_per100(parsed_label, body.is_beverage)
    profiles = resolve_profiles(db, user, body.profile_ids)
    specs = [
        ProfileSpec(
            id=p.id,
            name=p.name,
            allergens=[
                {"code": a.allergen_code, "severity": a.severity, "avoid_traces": a.avoid_traces} for a in p.allergens
            ],
            diets=[d.code for d in p.dietary_preferences],
            avoid_terms=[r.term for r in p.avoid_rules],
        )
        for p in profiles
    ]
    res = ps.analyze_text(
        body.ingredients_text,
        n,
        is_beverage=body.is_beverage,
        cfg=ps.active_methodology(db),
        profiles=specs,
        region=region_of(user),
    )
    res["nutrition_label"] = parsed_label
    res["nutrition_per_100"] = {k: getattr(n, k) for k in NUTRIENT_FIELDS} if n else None
    res["note"] = "Analysis of text you provided. Review OCR results for errors before saving."
    return res


class LabelTextIn(BaseModel):
    text: str = Field(min_length=10, max_length=10000)
    is_beverage: bool = False


@router.post("/nutrition-label")
def nutrition_label(body: LabelTextIn):
    parsed = parse_nutrition_label(body.text)
    n = label_to_per100(parsed, body.is_beverage)
    return {
        "parsed": parsed,
        "per_100": {k: getattr(n, k) for k in NUTRIENT_FIELDS} if n else None,
        "needs_serving_size": parsed["basis"] == "serving" and not parsed["serving_size_g"],
    }


@router.post("/image")
async def analyze_image(
    db: DB,
    user: CurrentUser,
    task: str = Form(..., pattern="^(ingredients|nutrition|front|meal)$"),
    image: UploadFile = File(...),
):
    """Cloud vision extraction (Gemini). Results are suggestions the user must review."""
    data = await image.read()
    mime = validate_image(data, get_settings().max_upload_mb)
    ent.require_quota(db, user, "ai_vision")
    try:
        provider = get_provider()
    except AINotConfigured as e:
        raise HTTPException(
            503,
            {
                "code": "ai_not_configured",
                "message": str(e),
                "fallback": "Use on-device OCR (the app's default) and send the text to /analysis/text.",
            },
        )
    try:
        result = ai.vision(provider, task, mime, data)
        extracted = result.json()
    except (AIError, ValueError) as e:
        ent.record_usage(db, user, "ai_vision", provider.name, getattr(provider, "model", None), ok=False)
        raise HTTPException(
            502, {"code": "ai_failed", "message": "Image analysis failed. Try a clearer photo.", "detail": str(e)[:200]}
        )
    ent.record_usage(
        db,
        user,
        "ai_vision",
        result.provider,
        result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
    out = {
        "task": task,
        "extracted": extracted,
        "ai_generated": True,
        "notice": "Extracted by AI. Check it against the package before saving.",
    }
    if task == "ingredients" and extracted.get("ingredients_text"):
        txt = out["ingredients_text"] = ai.ingredients_with_statements(extracted)
        out["analysis"] = ps.analyze_text(txt, None, cfg=ps.active_methodology(db), region=region_of(user))
    if task == "nutrition" and extracted.get("panel_text"):
        out["nutrition_label"] = parse_nutrition_label(extracted["panel_text"])
    if task == "meal":
        out["notice"] = (
            "Calories and nutrients are AI estimates from a photo, not measurements. Portion sizes "
            "and recipes vary, so adjust the values before logging."
        )
    return out
