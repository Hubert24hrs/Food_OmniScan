"""USDA FoodData Central adapter (Branded Foods).

Docs: https://fdc.nal.usda.gov/api-guide
- Requires a free api.data.gov key (USDA_API_KEY). DEMO_KEY works for light testing.
- Default limit: 1,000 requests/hour per key.
- FDC data is public domain (CC0 1.0). Cite "USDA FoodData Central".
Branded food nutrients are reported per 100 g (or 100 ml) by FDC.
"""

import httpx

from app.core.config import get_settings
from app.services.nutrition import NutritionInput
from app.services.providers.base import (
    ProviderProduct,
    ProviderUnavailable,
    request_with_retry,
)

LICENSE = "CC0 1.0 (public domain)"
ATTRIBUTION = "U.S. Department of Agriculture, Agricultural Research Service. FoodData Central."

# FDC nutrient numbers
N = {
    "208": "energy_kcal",
    "204": "fat",
    "606": "saturated_fat",
    "605": "trans_fat",
    "601": "cholesterol_mg",
    "307": "sodium_mg",
    "205": "carbohydrates",
    "269": "sugars",
    "539": "added_sugars",
    "291": "fiber",
    "203": "protein",
}

BEVERAGE_WORDS = ("beverage", "drink", "soda", "juice", "water", "tea", "coffee", "milk")


def enabled() -> bool:
    return bool(get_settings().usda_api_key)


def _nutrition(food: dict) -> NutritionInput | None:
    vals: dict[str, float] = {}
    for fn in food.get("foodNutrients") or []:
        num = str(fn.get("nutrientNumber") or (fn.get("nutrient") or {}).get("number") or "")
        key = N.get(num)
        val = fn.get("value", fn.get("amount"))
        if key and val is not None:
            vals.setdefault(key, float(val))
    if not vals:
        return None
    sodium_mg = vals.pop("sodium_mg", None)
    serving = food.get("servingSize")
    unit = (food.get("servingSizeUnit") or "").lower()
    serving_g = float(serving) if serving and unit in ("g", "grm", "ml", "mlt") else None
    ni = NutritionInput(**vals, sodium=sodium_mg / 1000 if sodium_mg is not None else None, serving_size_g=serving_g)
    return ni if ni.core_present() else None


def normalize(food: dict) -> ProviderProduct:
    cat = food.get("brandedFoodCategory") or food.get("foodCategory")
    if isinstance(cat, dict):
        cat = cat.get("description")
    is_bev = bool(cat and any(w in cat.lower() for w in BEVERAGE_WORDS))
    n = _nutrition(food)
    if n:
        n.is_beverage = is_bev
    gtin = (food.get("gtinUpc") or "").strip() or None
    fdc_id = str(food.get("fdcId"))
    serving = food.get("servingSize")
    return ProviderProduct(
        source="usda",
        source_id=fdc_id,
        barcode=gtin,
        name=(food.get("description") or "").title() or None,
        brand=food.get("brandName") or food.get("brandOwner"),
        manufacturer=food.get("brandOwner"),
        category_label=cat,
        categories_tags=[],
        countries_tags=["en:united-states"] if food.get("marketCountry", "United States") == "United States" else [],
        serving_size=f"{serving:g} {food.get('servingSizeUnit', '')}".strip()
        if serving
        else food.get("householdServingFullText"),
        ingredients_text=food.get("ingredients") or None,
        ingredients_lang="en",
        nutrition=n,
        url=f"https://fdc.nal.usda.gov/food-details/{fdc_id}/nutrients",
        license=LICENSE,
        attribution=ATTRIBUTION,
        is_beverage=is_bev,
        raw={
            k: food.get(k)
            for k in (
                "fdcId",
                "gtinUpc",
                "description",
                "brandOwner",
                "brandedFoodCategory",
                "publishedDate",
                "modifiedDate",
                "dataSource",
            )
        },
    )


def _get(path: str, params: dict) -> httpx.Response:
    s = get_settings()
    with httpx.Client(timeout=12.0) as c:
        r = request_with_retry(c, "GET", f"{s.usda_base_url}{path}", params={**params, "api_key": s.usda_api_key})
    if r.status_code != 200:
        raise ProviderUnavailable(f"FDC returned {r.status_code}")
    return r


def find_by_gtin(barcode: str) -> ProviderProduct | None:
    if not enabled():
        return None
    r = _get("/foods/search", {"query": barcode, "dataType": "Branded", "pageSize": 10})
    want = barcode.lstrip("0")
    for food in r.json().get("foods", []):
        if (food.get("gtinUpc") or "").lstrip("0") == want:
            return normalize(food)
    return None


def search(query: str, page_size: int = 20) -> list[ProviderProduct]:
    if not enabled():
        return []
    r = _get("/foods/search", {"query": query, "dataType": "Branded", "pageSize": page_size})
    return [normalize(f) for f in r.json().get("foods", [])]
