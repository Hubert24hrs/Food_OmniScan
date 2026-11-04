"""Open Food Facts adapter (API v2).

Docs: https://openfoodfacts.github.io/documentation/
- Requests identify the app with a User-Agent (required by OFF).
- OFF rate limits: about 100 product reads/min and 10 searches/min per IP. Cache results
  (see product_service) and never bulk-crawl the API; use the data dumps for bulk.
- Data is under the Open Database License (ODbL); images under CC BY-SA. Attribution is
  stored with each product and shown in the UI.
"""

import httpx

from app.core.config import get_settings
from app.services.nutrition import from_off
from app.services.providers.base import (
    BEVERAGE_TAGS,
    ProviderProduct,
    ProviderUnavailable,
    request_with_retry,
)

FIELDS = ",".join(
    [
        "code",
        "product_name",
        "product_name_en",
        "generic_name",
        "brands",
        "brand_owner",
        "categories_tags",
        "categories",
        "quantity",
        "serving_size",
        "serving_quantity",
        "countries_tags",
        "labels_tags",
        "packaging",
        "packaging_tags",
        "ingredients_text",
        "ingredients_text_en",
        "lang",
        "allergens_tags",
        "traces_tags",
        "additives_tags",
        "ingredients_analysis_tags",
        "nova_group",
        "nutriscore_grade",
        "nutriments",
        "image_front_url",
        "image_ingredients_url",
        "image_nutrition_url",
        "manufacturing_places",
        "last_modified_t",
        "nutrition_data_per",
    ]
)

LICENSE = "ODbL 1.0 (database), CC BY-SA 3.0 (images)"
ATTRIBUTION = "Data from Open Food Facts (openfoodfacts.org), available under the Open Database License."


def _client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(timeout=s.off_timeout_seconds, headers={"User-Agent": s.off_user_agent}, follow_redirects=True)


def _items(text: str) -> int:
    return text.count(",") + text.count(";") + 1


def pick_ingredients(p: dict) -> tuple[str | None, str | None]:
    """Prefer English (US-first), unless the English text is a truncated stub of the main-language list."""
    en = (p.get("ingredients_text_en") or "").strip()
    main = (p.get("ingredients_text") or "").strip()
    lang = p.get("lang")
    if en and (not main or main == en or _items(en) * 1.5 >= _items(main)):
        return en, "en"
    if main:
        return main, lang
    return None, None


def normalize(p: dict) -> ProviderProduct:
    s = get_settings()
    code = str(p.get("code") or "")
    cats = p.get("categories_tags") or []
    name = p.get("product_name_en") or p.get("product_name") or p.get("generic_name") or None
    ingredients, ingredients_lang = pick_ingredients(p)
    nova = p.get("nova_group")
    try:
        nova = int(nova) if nova not in (None, "") else None
    except (TypeError, ValueError):
        nova = None
    grade = (p.get("nutriscore_grade") or "").lower() or None
    if grade not in ("a", "b", "c", "d", "e"):
        grade = None
    nutrition = from_off(p)
    is_bev = bool(set(cats) & BEVERAGE_TAGS)
    if nutrition:
        nutrition.is_beverage = is_bev
    images = {
        k: v
        for k, v in {
            "front": p.get("image_front_url"),
            "ingredients": p.get("image_ingredients_url"),
            "nutrition": p.get("image_nutrition_url"),
        }.items()
        if v
    }
    brands = (p.get("brands") or "").split(",")[0].strip() or None
    return ProviderProduct(
        source="off",
        source_id=code,
        barcode=code or None,
        name=name,
        brand=brands,
        manufacturer=p.get("brand_owner") or None,
        categories_tags=cats,
        category_label=(p.get("categories") or "").split(",")[-1].strip() or None,
        quantity=p.get("quantity") or None,
        serving_size=p.get("serving_size") or None,
        countries_tags=p.get("countries_tags") or [],
        labels_tags=p.get("labels_tags") or [],
        packaging_text=p.get("packaging") or None,
        packaging_tags=p.get("packaging_tags") or [],
        ingredients_text=ingredients,
        ingredients_lang=ingredients_lang,
        allergens_tags=p.get("allergens_tags") or [],
        traces_tags=p.get("traces_tags") or [],
        additives_tags=p.get("additives_tags") or [],
        analysis_tags=p.get("ingredients_analysis_tags") or [],
        nova_group=nova if nova in (1, 2, 3, 4) else None,
        nutriscore_grade=grade,
        image_url=p.get("image_front_url"),
        images=images,
        nutrition=nutrition,
        url=f"{s.off_base_url}/product/{code}" if code else None,
        license=LICENSE,
        attribution=ATTRIBUTION,
        is_beverage=is_bev,
        raw={
            k: p.get(k)
            for k in (
                "code",
                "product_name",
                "brands",
                "categories_tags",
                "nutriments",
                "nova_group",
                "nutriscore_grade",
                "last_modified_t",
                "nutrition_data_per",
            )
            if k in p
        },
    )


def get_product(barcode: str) -> ProviderProduct | None:
    s = get_settings()
    with _client() as c:
        r = request_with_retry(c, "GET", f"{s.off_base_url}/api/v2/product/{barcode}.json", params={"fields": FIELDS})
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise ProviderUnavailable(f"OFF returned {r.status_code}")
    data = r.json()
    if data.get("status") != 1 or not data.get("product"):
        return None
    return normalize(data["product"])


def search(query: str, page: int = 1, page_size: int = 20, country: str | None = None) -> list[ProviderProduct]:
    s = get_settings()
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page": page,
        "page_size": page_size,
        "fields": FIELDS,
    }
    if country:
        params.update({"tagtype_0": "countries", "tag_contains_0": "contains", "tag_0": country})
    with _client() as c:
        r = request_with_retry(c, "GET", f"{s.off_base_url}/cgi/search.pl", params=params)
    if r.status_code != 200:
        raise ProviderUnavailable(f"OFF search returned {r.status_code}")
    return [normalize(p) for p in r.json().get("products", []) if p.get("code")]


def search_category(
    category_tag: str, page_size: int = 40, country: str | None = "en:united-states"
) -> list[ProviderProduct]:
    """Products in the same category, used to find healthier alternatives."""
    s = get_settings()
    params = {"categories_tags": category_tag, "fields": FIELDS, "page_size": page_size, "sort_by": "popularity_key"}
    if country:
        params["countries_tags"] = country
    with _client() as c:
        r = request_with_retry(c, "GET", f"{s.off_base_url}/api/v2/search", params=params)
    if r.status_code != 200:
        raise ProviderUnavailable(f"OFF category search returned {r.status_code}")
    return [normalize(p) for p in r.json().get("products", []) if p.get("code")]
