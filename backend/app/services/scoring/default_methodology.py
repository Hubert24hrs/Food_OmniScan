"""Default scoring methodology (US FDA basis). Admins publish new versions via the API.

Any change to these numbers must ship as a new `version` so stored scores stay traceable.
"""

DEFAULT_METHODOLOGY: dict = {
    "version": "2026.11-us.1",
    "name": "Food omniScan Score, US FDA basis",
    "weights": {
        "nutrition": 40,
        "ingredients": 25,
        "processing": 15,
        "dietary_suitability": 10,
        "product_concerns": 10,
    },
    "grade_bands": [
        {"min": 75, "grade": "excellent", "color": "green", "label": "Excellent"},
        {"min": 50, "grade": "good", "color": "green", "label": "Good"},
        {"min": 35, "grade": "mediocre", "color": "amber", "label": "Mediocre"},
        {"min": 0, "grade": "poor", "color": "red", "label": "Poor"},
    ],
    # Fraction of the core weight (everything except product_concerns) that must be assessable.
    "min_coverage": 0.55,
    # Nutrition is 40% of the score; without it an overall score would mislead (e.g. sugar water).
    "require_nutrition": True,
    "nutrition": {
        "standard": "US_FDA_DV",
        # Foods are assessed per 100 g; beverages per FDA reference amount (12 fl oz = 360 ml).
        "beverage_reference_ml": 360,
        "low_pct_dv": 5,  # FDA 5/20 rule: <=5% DV is low...
        "high_pct_dv": 20,  # ...>=20% DV is high
        "full_penalty_pct_dv": 30,  # penalty ramps from low_pct_dv to this value
        "negatives": {
            "added_sugars": {"max_penalty": 60, "dv_key": "added_sugars"},
            "saturated_fat": {"max_penalty": 50, "dv_key": "saturated_fat"},
            "sodium": {"max_penalty": 50, "dv_key": "sodium_mg"},
        },
        "energy": {
            "food": {"low_kcal": 120, "high_kcal": 500, "max_penalty": 20},
            "beverage": {"low_kcal": 40, "high_kcal": 200, "max_penalty": 25},
        },
        "trans_fat": {"threshold_g": 0.2, "penalty": 30},
        "positives": {
            # EU 1924/2006 claim levels: source >=3 g/100 g, high >=6 g/100 g
            "fiber": {"source_g": 3, "high_g": 6, "source_bonus": 5, "high_bonus": 10},
            # protein as % of energy: source >=12%, high >=20%
            "protein": {"source_pct_energy": 12, "high_pct_energy": 20, "source_bonus": 4, "high_bonus": 8},
            "fruits_veg_nuts": {"min_pct": 40, "full_pct": 80, "max_bonus": 8},
        },
    },
    "ingredients": {
        "concern": {"penalty": 25, "max_total": 60},
        "caution": {"penalty": 10, "max_total": 40},
        "added_sugar_first": 12,
        "added_sugar_top3": 6,
        "multiple_added_sugars": {"min_types": 3, "penalty": 5},
        "undisclosed": {"penalty": 2, "max_total": 6},
        "beneficial_top3": {"bonus": 3, "max_total": 9},
    },
    "processing": {"nova_scores": {"1": 100, "2": 85, "3": 60, "4": 10}},
    "dietary_suitability": {
        "major_allergen_contains": 6,
        "major_allergen_may_contain": 2,
        "allergen_max_total": 30,
        "high_fodmap": {"penalty": 2, "max_total": 6},
        "caffeine": 5,
        "alcohol": 10,
    },
    "product_concerns": {
        "active_recall_score": 0,
        "lab_exceedance_penalty": 40,
    },
    "ceilings": {
        # A product with poor nutrition cannot be rescued by other components.
        "nutrition_margin": {"below": 50, "margin": 10},
        "ultra_processed_max": 64,
        "concern_ingredient_max": 49,
        "partially_hydrogenated_max": 34,
        "active_recall_max": 0,
    },
}


def flatten_rules(config: dict) -> list[dict]:
    """Produce browsable ScoringRule rows from a config."""
    rules: list[dict] = []

    def walk(component: str, prefix: str, node) -> None:
        if isinstance(node, dict) and not all(isinstance(v, (int, float, str, bool)) for v in node.values()):
            for k, v in node.items():
                walk(component, f"{prefix}.{k}" if prefix else k, v)
        else:
            rules.append(
                {
                    "component": component,
                    "code": prefix or component,
                    "params": node if isinstance(node, dict) else {"value": node},
                }
            )

    for comp in ("nutrition", "ingredients", "processing", "dietary_suitability", "product_concerns", "ceilings"):
        walk(comp, "", config.get(comp, {}))
    rules.append({"component": "weights", "code": "weights", "params": config["weights"]})
    return rules
