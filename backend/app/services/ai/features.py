"""AI features built on the provider abstraction: grounded assistant and vision extraction."""

import json
import re

from app.services.ai.provider import AIProvider, AIResult

MEDICAL_DISCLAIMER = (
    "General nutrition information, not medical advice. For allergies, medical conditions, "
    "pregnancy or medication interactions, talk to a qualified healthcare professional."
)

ASSISTANT_SYSTEM = """You are the Food omniScan nutrition assistant. The primary audience is in the United States, so
use US conventions (FDA Daily Values, Nutrition Facts terms, US spelling, ounces alongside grams where helpful).

STRICT GROUNDING RULES:
1. Answer using ONLY the JSON context provided (product records, ingredient knowledge base, score breakdown,
   sources). Never invent ingredients, nutrient values, lab results, recalls, certifications or safety claims.
2. If the context doesn't contain the answer, say you don't have that information. For a product, suggest
   checking the package or scanning the nutrition label.
3. When you cite a fact, name its origin: e.g. "(label data via Open Food Facts)", "(FDA Daily Value)", or the source
   key in square brackets like [fda_21cfr101_9]. Only cite source keys that appear in the context.
4. Distinguish clearly between regulatory findings, product measurements, published research and estimates.
5. Never diagnose, prescribe, or say a food is medically safe for a condition or allergy. For allergies, repeat the
   allergen status exactly as given ("contains", "may contain", "not detected", "unknown") and remind the user to
   read the physical label.
6. Meal ideas and substitutions may use general culinary knowledge, but any nutrient numbers for them must be
   labelled as rough estimates.
7. Be concise: short paragraphs or bullet points, plain language."""

VISION_INGREDIENTS = """Transcribe the INGREDIENTS statement and any allergen statements ("Contains:", "May contain")
exactly as printed in this photo. Do not correct, translate, or add anything. If text is unreadable write [illegible].
If the label is not in English, also give a faithful English translation of the ingredients and statements.
Return JSON: {"ingredients_text": str, "contains_statement": str|null, "may_contain_statement": str|null,
"legibility": "good"|"partial"|"poor", "language": str (ISO 639-1),
"english_translation": {"ingredients_text": str, "contains_statement": str|null,
"may_contain_statement": str|null} | null}"""

VISION_NUTRITION = """Transcribe the nutrition panel in this photo exactly as printed, one row per line, keeping units and
%DV values (e.g. "Total Fat 8g 10%"). Include the serving size line and whether values are per serving or per 100 g.
Do not compute or estimate anything. Return JSON: {"panel_text": str, "format": "us_nutrition_facts"|"eu_table"|"other",
"legibility": "good"|"partial"|"poor"}"""

VISION_FRONT = """Identify the packaged product in this photo from visible text only. Do not guess at text you can't read.
Return JSON: {"product_name": str|null, "brand": str|null, "variant": str|null, "visible_barcode_digits": str|null,
"net_quantity": str|null, "visible_claims": [str], "confidence": 0.0-1.0}"""

VISION_MEAL = """Identify the foods on this plate. For each item give a typical name (include US, European, African or other
regional dish names where recognisable, e.g. jollof rice, egusi soup), the likely preparation, and an estimated portion
in grams with a low/high range. Then give ROUGH estimated calories, protein, carbs, fat and fiber for each item.
These are estimates, not measurements. Return JSON: {"items": [{"name": str, "preparation": str|null,
"portion_g": number, "portion_range_g": [number, number], "energy_kcal": number, "protein_g": number, "carbs_g": number,
"fat_g": number, "fiber_g": number, "confidence": 0.0-1.0}], "notes": str}"""


_CONTAINS = re.compile(r"^\s*contains\s*:?\s*", re.I)
_MAY_CONTAIN = re.compile(r"^\s*(may contain|may also contain|produced in a facility[^:]*)\s*:?\s*", re.I)


def ingredients_with_statements(extracted: dict) -> str:
    """Ingredients text plus allergen statements, each labelled so the parser reads them correctly.

    Vision output often drops the "Contains:" / "May contain" prefix ("WHEAT."), which would
    otherwise turn a precautionary statement into an ingredient or lose it entirely.
    """
    parts = [(extracted.get("ingredients_text") or "").strip()]
    contains = (extracted.get("contains_statement") or "").strip()
    may = (extracted.get("may_contain_statement") or "").strip()
    if contains:
        parts.append("Contains: " + _CONTAINS.sub("", contains))
    if may:
        parts.append(may if _MAY_CONTAIN.match(may) else "May contain: " + may)
    return "\n".join(p for p in parts if p)


def build_context(products: list[dict], sources: list[dict], profile: dict | None) -> str:
    return json.dumps({"products": products, "sources": sources, "active_profile": profile}, default=str)[:60000]


def ask(
    provider: AIProvider, question: str, context_json: str, history: list[dict], language: str | None = None
) -> AIResult:
    msgs = [
        {"role": h["role"], "content": h["content"][:4000]}
        for h in history[-8:]
        if h.get("role") in ("user", "assistant")
    ]
    msgs.append({"role": "user", "content": f"CONTEXT (JSON):\n{context_json}\n\nQUESTION:\n{question[:2000]}"})
    return provider.generate(ASSISTANT_SYSTEM + language_instruction(language), msgs, temperature=0.2)


def vision(provider: AIProvider, task: str, mime: str, data: bytes) -> AIResult:
    prompt = {
        "ingredients": VISION_INGREDIENTS,
        "nutrition": VISION_NUTRITION,
        "front": VISION_FRONT,
        "meal": VISION_MEAL,
    }[task]
    return provider.generate(
        "You extract information from food packaging and meal photos for a food scanning app.",
        [{"role": "user", "content": prompt}],
        images=[(mime, data)],
        json_mode=True,
        temperature=0.0,
    )


LANGUAGES = {
    "en": "English",
    "pcm": "Nigerian Pidgin",
    "yo": "Yoruba",
    "ig": "Igbo",
    "ha": "Hausa",
    "fr": "French",
    "es": "Spanish",
}


def language_instruction(lang: str | None) -> str:
    if not lang or lang == "en":
        return ""
    name = LANGUAGES[lang]
    return (
        f"\n\nAnswer in {name}. Keep product names, ingredient names, numbers, units and source keys exactly as "
        f"they appear in the context. If you aren't confident in a {name} term, give the English term in brackets."
    )


RECIPE_SYSTEM = """You write home recipes for a food app. Follow the user's constraints exactly: never include an
ingredient that conflicts with the listed allergies, avoided ingredients or diets. Prefer whole foods. When the region
is Nigeria or West Africa, use familiar local dishes and ingredients available in Nigerian markets.
Quantities are typical home amounts. Nutrition values must be labelled as rough estimates.
Return JSON: {"title": str, "description": str, "cuisine": str, "servings": int, "time_minutes": int,
"ingredients": [{"name": str, "quantity": number|null, "unit": str|null, "note": str|null}], "steps": [str],
"diet_tags": [str], "tags": [str], "preparation_notes": str,
"nutrition_per_serving_estimate": {"energy_kcal": number, "protein": number, "carbohydrates": number, "fat": number,
"fiber": number, "sodium_mg": number}}"""

MEAL_PLAN_SYSTEM = """You plan meals for a food app. Follow allergies, avoided ingredients and diets exactly. Respect
the calorie target only approximately and say so. Use simple, affordable dishes; when the region is Nigeria or West
Africa, build the plan from familiar local dishes (e.g. moi moi, beans and plantain, efo riro with a swallow, jollof
rice, pepper soup, okra soup) balanced with vegetables and protein. If a budget is given, prefer cheaper staples.
Return JSON: {"name": str, "days": [{"day": int, "meals": [{"meal_type": "breakfast"|"lunch"|"dinner"|"snack",
"title": str, "description": str, "estimated_kcal": number}]}], "notes": str}"""

RECIPE_NUTRITION = """Estimate nutrition PER SERVING for this recipe from typical ingredient composition. These are
rough estimates, not measurements; say what assumptions you made. Return JSON: {"energy_kcal": number,
"protein": number, "carbohydrates": number, "fat": number, "fiber": number, "sugars": number, "sodium_mg": number,
"assumptions": str}"""


def constraints_text(profile: dict | None, extra: dict) -> str:
    c = {"profile": profile, **{k: v for k, v in extra.items() if v not in (None, "", [])}}
    return json.dumps(c, default=str)[:6000]


def generate_recipe(provider: AIProvider, request: str, constraints: str) -> AIResult:
    msg = f"CONSTRAINTS (JSON):\n{constraints}\n\nREQUEST:\n{request[:1000]}"
    return provider.generate(RECIPE_SYSTEM, [{"role": "user", "content": msg}], json_mode=True, temperature=0.6)


def generate_meal_plan(provider: AIProvider, days: int, constraints: str) -> AIResult:
    msg = f"CONSTRAINTS (JSON):\n{constraints}\n\nPlan {days} days of breakfast, lunch, dinner and one snack."
    return provider.generate(MEAL_PLAN_SYSTEM, [{"role": "user", "content": msg}], json_mode=True, temperature=0.6)


def estimate_recipe_nutrition(provider: AIProvider, recipe: dict) -> AIResult:
    msg = json.dumps(recipe, default=str)[:8000]
    return provider.generate(RECIPE_NUTRITION, [{"role": "user", "content": msg}], json_mode=True, temperature=0.0)
