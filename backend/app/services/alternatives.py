"""Healthier alternatives and N-way comparison."""

import logging
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FamilyProfile, Product, ProductAlternative, ProductComparison
from app.services import product_service as ps
from app.services.barcode import InvalidBarcode, parse_barcode
from app.services.providers import openfoodfacts as off
from app.services.providers.base import ProviderError

log = logging.getLogger(__name__)

OBJECTIVES = {
    "overall": ("score", "desc", "Best overall score"),
    "lowest_sugar": ("added_sugars", "asc", "Lowest sugar"),
    "lowest_sodium": ("sodium_mg", "asc", "Lowest sodium"),
    "lowest_saturated_fat": ("saturated_fat", "asc", "Lowest saturated fat"),
    "highest_protein": ("protein", "desc", "Highest protein"),
    "highest_fiber": ("fiber", "desc", "Highest fiber"),
    "lowest_calories": ("energy_kcal", "asc", "Fewest calories"),
    "fewest_additives": ("additive_count", "asc", "Fewest additives of concern"),
}


def _metrics(db: Session, product: Product, profiles: list[FamilyProfile]) -> dict:
    analysis = ps.analyze_product(db, product, profiles)
    n = ps.nutrition_input(product)
    hl = analysis["score"]["highlights"]
    concern = [
        i
        for i in analysis["ingredients"]
        if i["ingredient"] and i["ingredient"]["concern_level"] in ("caution", "concern")
    ]
    sugar = None
    if n:
        sugar = n.added_sugars if n.added_sugars is not None else n.sugars
    return {
        "product": ps.product_summary(db, product),
        "score": analysis["score"]["overall"],
        "grade": analysis["score"]["grade"],
        "color": analysis["score"]["color"],
        "confidence": analysis["score"]["confidence"],
        "nova_group": analysis["score"]["components"]["processing"].get("nova_group"),
        "nova_source": analysis["score"]["components"]["processing"].get("nova_source"),
        "basis": "100ml" if product.is_beverage else "100g",
        "energy_kcal": n.energy_kcal if n else None,
        "added_sugars": sugar,
        "sugar_is_total": bool(n and n.added_sugars is None),
        "saturated_fat": n.saturated_fat if n else None,
        "sodium_mg": round(n.sodium * 1000) if n and n.sodium is not None else None,
        "protein": n.protein if n else None,
        "fiber": n.fiber if n else None,
        "additive_count": len({i["ingredient"]["slug"] for i in concern}),
        "additives_of_concern": sorted({i["ingredient"]["name"] for i in concern}),
        "allergens_contains": [a["name"] for a in analysis["allergens"] if a["status"] == "contains"],
        "highlights": {k: [x["name"] for x in v] for k, v in hl.items() if isinstance(v, list) and v},
        "compatibility": [
            {"profile_id": c["profile_id"], "profile_name": c["profile_name"], "verdict": c["verdict"]}
            for c in analysis["compatibility"]
        ],
        "ingredient_slugs": {i["ingredient"]["slug"] for i in analysis["ingredients"] if i["ingredient"]},
        "ingredient_names": [i["ingredient"]["name"] for i in analysis["ingredients"] if i["ingredient"]],
    }


def _diff_reasons(base: dict, alt: dict) -> dict:
    better, worse = [], []

    def cmp(key: str, label: str, unit: str, lower_is_better: bool = True, tol: float = 0.05) -> None:
        a, b = base.get(key), alt.get(key)
        if a is None or b is None:
            return
        diff = b - a
        rel = abs(diff) / max(abs(a), 1e-6)
        if abs(diff) < 1e-9 or rel < tol:
            return
        good = diff < 0 if lower_is_better else diff > 0
        text = f"{'Less' if diff < 0 else 'More'} {label}: {b:g}{unit} vs {a:g}{unit} per {alt['basis']}"
        (better if good else worse).append(text)

    cmp("added_sugars", "sugar", " g")
    cmp("sodium_mg", "sodium", " mg")
    cmp("saturated_fat", "saturated fat", " g")
    cmp("energy_kcal", "calories", " kcal")
    cmp("protein", "protein", " g", lower_is_better=False)
    cmp("fiber", "fiber", " g", lower_is_better=False)
    if base["nova_group"] and alt["nova_group"] and alt["nova_group"] != base["nova_group"]:
        (better if alt["nova_group"] < base["nova_group"] else worse).append(
            f"Processing: NOVA {alt['nova_group']} vs {base['nova_group']}"
        )
    if alt["additive_count"] != base["additive_count"]:
        (better if alt["additive_count"] < base["additive_count"] else worse).append(
            f"{alt['additive_count']} additive(s) of concern vs {base['additive_count']}"
        )
    new_allergens = set(alt["allergens_contains"]) - set(base["allergens_contains"])
    if new_allergens:
        worse.append("Contains allergens the original doesn't: " + ", ".join(sorted(new_allergens)))
    removed = sorted(set(base["ingredient_names"]) - set(alt["ingredient_names"]))[:8]
    added = sorted(set(alt["ingredient_names"]) - set(base["ingredient_names"]))[:8]
    return {"better": better, "not_better": worse, "ingredients_removed": removed, "ingredients_added": added}


_COUNTRY_TAGS = {
    "US": "en:united-states",
    "GB": "en:united-kingdom",
    "NG": "en:nigeria",
    "FR": "en:france",
    "DE": "en:germany",
    "GH": "en:ghana",
    "KE": "en:kenya",
    "ZA": "en:south-africa",
    "CA": "en:canada",
}


def country_tag(country: str) -> str:
    """Open Food Facts country tag for an ISO code (e.g. NG -> en:nigeria)."""
    return _COUNTRY_TAGS.get(country.upper(), f"en:{country.lower()}")


def _candidates(db: Session, product: Product, limit: int) -> list[Product]:
    tags = list(product.categories_tags or [])
    found: dict[str, Product] = {}
    if product.category_id:
        for p in db.scalars(
            select(Product)
            .where(Product.category_id == product.category_id, Product.id != product.id, Product.status == "active")
            .limit(limit * 2)
        ).all():
            found[p.id] = p
    # Pull more from Open Food Facts for the most specific category (cached locally after the first time)
    if tags and len(found) < limit:
        try:
            for pp in off.search_category(tags[-1], page_size=30):
                if not pp.barcode or pp.barcode in {b.barcode for b in product.barcodes}:
                    continue
                try:
                    bc = parse_barcode(pp.barcode)
                except InvalidBarcode:
                    continue
                p = ps.upsert_product(db, pp, bc, {"name": "off"})
                if p.id != product.id:
                    found[p.id] = p
            db.commit()
        except ProviderError as e:
            log.info("OFF category search unavailable: %s", e)
    return list(found.values())


def find_alternatives(
    db: Session,
    product: Product,
    profiles: list[FamilyProfile],
    *,
    objective: str = "overall",
    exclude_ingredients: list[str] | None = None,
    brand: str | None = None,
    compatible_only: bool = True,
    limit: int = 10,
    country: str | None = None,
) -> dict:
    base = _metrics(db, product, profiles)
    exclude = {e.strip().lower() for e in (exclude_ingredients or []) if e.strip()}
    results = []
    for cand in _candidates(db, product, limit * 3):
        m = _metrics(db, cand, profiles)
        if m["score"] is None:
            continue
        if objective == "overall" and (base["score"] is not None and m["score"] <= base["score"] + 4):
            continue
        if objective != "overall":
            key, direction, _ = OBJECTIVES[objective]
            if m.get(key) is None or base.get(key) is None:
                continue
            if (direction == "asc" and m[key] >= base[key]) or (direction == "desc" and m[key] <= base[key]):
                continue
            if base["score"] is not None and m["score"] < base["score"] - 10:
                continue  # don't trade a big overall drop for one nutrient
        if compatible_only and any(c["verdict"] == "red" for c in m["compatibility"]):
            continue
        if exclude and (
            exclude & m["ingredient_slugs"] or any(x in n.lower() for x in exclude for n in m["ingredient_names"])
        ):
            continue
        if brand and (m["product"]["brand"] or "").lower() != brand.lower():
            continue
        m["sold_in_country"] = bool(country) and country_tag(country) in (cand.countries_tags or [])
        m["reasons"] = _diff_reasons(base, m)
        m["score_delta"] = (m["score"] - base["score"]) if base["score"] is not None else None
        results.append(m)

    key, direction, label = OBJECTIVES.get(objective, OBJECTIVES["overall"])
    results.sort(key=lambda r: r.get(key) if r.get(key) is not None else 0, reverse=direction == "desc")
    if country:
        # Products sold where the user shops come first; the objective order is kept within each group.
        results.sort(key=lambda r: not r["sold_in_country"])
    results = results[:limit]
    version = ps.active_methodology(db)["version"]
    for r in results:
        pid = r["product"]["id"]
        row = db.scalar(
            select(ProductAlternative).where(
                ProductAlternative.product_id == product.id,
                ProductAlternative.alternative_product_id == pid,
                ProductAlternative.methodology_version == version,
            )
        )
        if row is None:
            db.add(
                ProductAlternative(
                    product_id=product.id,
                    alternative_product_id=pid,
                    methodology_version=version,
                    score_delta=r["score_delta"] or 0,
                    reasons=r["reasons"],
                )
            )
    db.commit()
    for r in results + [base]:
        r.pop("ingredient_slugs", None)
        r.pop("ingredient_names", None)
    return {
        "base": base,
        "objective": objective,
        "objective_label": label,
        "alternatives": results,
        "country": country,
        "price_comparison": "Shelf prices reported by users are shown on each product page (Plus). "
        "No retailer price feed is connected.",
    }


def compare(
    db: Session,
    products: list[Product],
    profiles: list[FamilyProfile],
    objective: str = "overall",
    user_id: str | None = None,
    save: bool = True,
) -> dict:
    metrics = [_metrics(db, p, profiles) for p in products]
    key, direction, label = OBJECTIVES.get(objective, OBJECTIVES["overall"])
    ranked = [m for m in metrics if m.get(key) is not None]
    best = None
    if ranked:
        best_m = (max if direction == "desc" else min)(ranked, key=lambda m: m[key])
        best = {
            "product_id": best_m["product"]["id"],
            "name": best_m["product"]["name"],
            "objective": label,
            "value": best_m[key],
        }
    rows = []
    for k, title, unit in [
        ("score", "Score", ""),
        ("nova_group", "NOVA group", ""),
        ("energy_kcal", "Calories", " kcal"),
        ("added_sugars", "Sugar", " g"),
        ("saturated_fat", "Saturated fat", " g"),
        ("sodium_mg", "Sodium", " mg"),
        ("protein", "Protein", " g"),
        ("fiber", "Fiber", " g"),
        ("additive_count", "Additives of concern", ""),
    ]:
        rows.append({"key": k, "label": title, "unit": unit, "values": [m.get(k) for m in metrics]})
    for m in metrics:
        m.pop("ingredient_slugs", None)
        m.pop("ingredient_names", None)
    result = {
        "objective": objective,
        "objective_label": label,
        "products": metrics,
        "rows": rows,
        "best": best,
        "notes": [
            "Values are per 100 g (food) or 100 ml (drinks), so products can be compared directly.",
            "Price per serving isn't available: no reliable pricing data source is connected.",
        ],
    }
    if save:
        token = secrets.token_urlsafe(12)
        db.add(
            ProductComparison(
                user_id=user_id,
                product_ids=[p.id for p in products],
                objective=objective,
                result=result,
                share_token=token,
            )
        )
        db.commit()
        result["share_token"] = token
    return result
