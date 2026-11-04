"""AI features built on the provider abstraction: grounded assistant and vision extraction."""

import json

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
Return JSON: {"ingredients_text": str, "contains_statement": str|null, "may_contain_statement": str|null,
"legibility": "good"|"partial"|"poor", "language": str}"""

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


def build_context(products: list[dict], sources: list[dict], profile: dict | None) -> str:
    return json.dumps({"products": products, "sources": sources, "active_profile": profile}, default=str)[:60000]


def ask(provider: AIProvider, question: str, context_json: str, history: list[dict]) -> AIResult:
    msgs = [
        {"role": h["role"], "content": h["content"][:4000]}
        for h in history[-8:]
        if h.get("role") in ("user", "assistant")
    ]
    msgs.append({"role": "user", "content": f"CONTEXT (JSON):\n{context_json}\n\nQUESTION:\n{question[:2000]}"})
    return provider.generate(ASSISTANT_SYSTEM, msgs, temperature=0.2)


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
