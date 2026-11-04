"""Personal dietary compatibility: one verdict per profile, separate from the general score.

Safety rules:
- An allergen the person avoids that the product contains is a *critical* alert. It is
  returned separately and is never averaged away by a good score.
- "Not detected" is never shown as "safe": the message always says to check the package.
- Missing data gives a yellow "can't verify" verdict, never green.
"""

import re
from dataclasses import dataclass, field

from app.services.allergens import AllergenFinding
from app.services.knowledge import Match
from app.services.nutrition import NutritionInput, percent_dv
from app.services.text import normalize_term

DIETS = {
    "vegan": "Vegan",
    "vegetarian": "Vegetarian",
    "pescatarian": "Pescatarian",
    "halal": "Halal (ingredient screen)",
    "kosher": "Kosher (label check)",
    "gluten_free": "Gluten-free",
    "dairy_free": "Dairy-free",
    "lactose_free": "Lactose-free",
    "low_fodmap": "Low-FODMAP (screen)",
    "keto": "Keto",
    "low_carb": "Low-carb",
    "high_protein": "High-protein",
    "low_sodium": "Low-sodium",
    "low_sugar": "Reduced sugar",
}

ALLERGEN_ALIASES = {
    "tree_nuts": "nuts",
    "soy": "soybeans",
    "egg": "eggs",
    "shellfish": "crustaceans",
    "peanut": "peanuts",
    "sulfites": "sulphites",
}

DISCLAIMER = (
    "Compatibility is based on the ingredient and allergen information available to us, which can be "
    "incomplete or out of date. Always read the physical label. This is not medical advice."
)


@dataclass
class ProfileSpec:
    id: str | None
    name: str
    allergens: list[dict] = field(default_factory=list)  # {code, severity, avoid_traces}
    diets: list[str] = field(default_factory=list)
    avoid_terms: list[str] = field(default_factory=list)


@dataclass
class ProductFacts:
    matches: list[Match]
    allergens: dict[str, AllergenFinding]
    nutrition: NutritionInput | None
    has_ingredients: bool
    labels_tags: list[str] = field(default_factory=list)
    analysis_tags: list[str] = field(default_factory=list)  # OFF ingredients_analysis_tags
    ingredient_names: list[str] = field(default_factory=list)
    added_sugar_basis: float | None = None
    is_beverage: bool = False


def _r(severity: str, rule: str, message: str, ingredient: str | None = None) -> dict:
    return {"severity": severity, "rule": rule, "message": message, "ingredient": ingredient}


def _entries(f: ProductFacts):
    return [(m, m.entry) for m in f.matches if m.entry and m.method != "class"]


def evaluate(profile: ProfileSpec, f: ProductFacts) -> dict:
    reasons: list[dict] = []
    critical: list[dict] = []

    # ---------------------------------------------------------------- allergens
    for a in profile.allergens:
        code = ALLERGEN_ALIASES.get(a["code"], a["code"])
        finding = f.allergens.get(code)
        if finding is None:
            continue
        sev = a.get("severity", "severe")
        name = finding.name
        evidence = ", ".join(sorted({e["text"] for e in finding.evidence if e.get("text")}))[:200] or None
        if finding.status == "contains":
            alert = {
                "allergen": code,
                "name": name,
                "status": "contains",
                "severity": sev,
                "message": f"Contains {name.lower()}" + (f" ({evidence})" if evidence else "") + ".",
            }
            critical.append(alert)
            reasons.append(_r("red", f"allergen.{code}", alert["message"], evidence))
        elif finding.status == "may_contain":
            refined = any(e["source"] == "refined_oil" for e in finding.evidence)
            msg = (
                f"Contains {evidence}, a highly refined oil usually exempt from allergen labelling. Check with "
                "your allergist."
                if refined
                else f"May contain {name.lower()} (precautionary or cross-contact statement)."
            )
            strict = a.get("avoid_traces", True) or sev == "anaphylaxis"
            color = "red" if strict and not refined and sev in ("severe", "anaphylaxis") else "yellow"
            if color == "red":
                critical.append(
                    {"allergen": code, "name": name, "status": "may_contain", "severity": sev, "message": msg}
                )
            reasons.append(_r(color, f"allergen.{code}", msg, evidence))
        elif finding.status == "unknown":
            reasons.append(
                _r(
                    "yellow",
                    f"allergen.{code}",
                    f"No ingredient information, so we can't check for {name.lower()}. Check the package.",
                )
            )
        else:
            reasons.append(
                _r(
                    "green",
                    f"allergen.{code}",
                    f"{name} not detected in the listed ingredients. This "
                    "isn't a guarantee, so always check the package.",
                )
            )

    entries = _entries(f)
    analysis = set(f.analysis_tags)
    labels = set(f.labels_tags)
    n = f.nutrition

    def need_ingredients(rule: str, label: str) -> bool:
        if not f.has_ingredients:
            reasons.append(_r("yellow", rule, f"Ingredient list unavailable, so we can't verify {label}."))
            return False
        return True

    # ---------------------------------------------------------------- diets
    for diet in profile.diets:
        label = DIETS.get(diet, diet)
        rule = f"diet.{diet}"
        if diet in ("vegan", "vegetarian"):
            if not need_ingredients(rule, label.lower()):
                continue
            bad = [e for _, e in entries if getattr(e, diet) == "no"]
            maybe = [e for _, e in entries if getattr(e, diet) == "maybe"]
            if diet == "vegan":
                bad += [
                    e
                    for _, e in entries
                    if e.allergen_code in ("milk", "eggs", "fish", "crustaceans", "molluscs") and e not in bad
                ]
            if bad or f"en:non-{diet}" in analysis:
                names = ", ".join(sorted({e.display_name() for e in bad})) or "per Open Food Facts analysis"
                reasons.append(_r("red", rule, f"Not {diet}: {names}.", names))
            elif maybe or f"en:maybe-{diet}" in analysis:
                names = ", ".join(sorted({e.display_name() for e in maybe}))
                reasons.append(
                    _r(
                        "yellow",
                        rule,
                        f"May not be {diet}: the source of {names or 'some ingredients'} isn't stated.",
                        names or None,
                    )
                )
            else:
                reasons.append(_r("green", rule, f"No non-{diet} ingredients found."))
        elif diet == "pescatarian":
            if not need_ingredients(rule, label.lower()):
                continue
            meat = [e for _, e in entries if e.category == "meat" or e.slug in ("lard", "tallow", "gelatin")]
            reasons.append(
                _r("red", rule, "Contains meat: " + ", ".join(e.name for e in meat) + ".")
                if meat
                else _r("green", rule, "No meat ingredients found.")
            )
        elif diet == "halal":
            if not need_ingredients(rule, "halal suitability"):
                continue
            bad = [e for _, e in entries if e.halal_concern == "yes"]
            maybe = [e for _, e in entries if e.halal_concern == "maybe"]
            certified = "en:halal" in labels
            if bad:
                reasons.append(
                    _r(
                        "red",
                        rule,
                        "Contains " + ", ".join(e.name for e in bad) + ", which isn't halal.",
                        ", ".join(e.name for e in bad),
                    )
                )
            elif maybe and not certified:
                reasons.append(
                    _r(
                        "yellow",
                        rule,
                        "Source not stated for: "
                        + ", ".join(e.name for e in maybe)
                        + ". Look for halal certification.",
                        ", ".join(e.name for e in maybe),
                    )
                )
            else:
                reasons.append(
                    _r(
                        "green" if certified else "yellow",
                        rule,
                        "Halal label reported by the data source."
                        if certified
                        else "No haram ingredients found, but we can't verify halal certification.",
                    )
                )
        elif diet == "kosher":
            reasons.append(
                _r("green", rule, "Kosher label reported by the data source.")
                if "en:kosher" in labels
                else _r("yellow", rule, "We can only check for a kosher certification mark, and none is on record.")
            )
        elif diet in ("gluten_free", "dairy_free"):
            code = "gluten" if diet == "gluten_free" else "milk"
            fd = f.allergens.get(code)
            if not fd or fd.status == "unknown":
                reasons.append(_r("yellow", rule, f"Can't verify {label.lower()}: no ingredient information."))
            elif fd.status == "contains":
                ev = ", ".join(sorted({e["text"] for e in fd.evidence}))
                reasons.append(_r("red", rule, f"Not {label.lower()}: contains {ev}.", ev))
            elif fd.status == "may_contain":
                reasons.append(_r("yellow", rule, f"May contain {fd.name.lower()} (cross-contact)."))
            else:
                certified = diet == "gluten_free" and "en:gluten-free" in labels
                reasons.append(
                    _r(
                        "green",
                        rule,
                        "Labelled gluten-free."
                        if certified
                        else f"No {fd.name.lower()} detected in the listed ingredients.",
                    )
                )
        elif diet == "lactose_free":
            if not need_ingredients(rule, "lactose content"):
                continue
            if "en:lactose-free" in labels or "en:no-lactose" in labels:
                reasons.append(_r("green", rule, "Labelled lactose-free."))
                continue
            dairy = [
                e for _, e in entries if e.slug == "lactose" or (e.allergen_code == "milk" and e.category == "dairy")
            ]
            if dairy:
                names = ", ".join(sorted({e.name for e in dairy}))
                reasons.append(_r("red", rule, f"Contains dairy that may contain lactose: {names}.", names))
            else:
                reasons.append(_r("green", rule, "No lactose-containing ingredients found."))
        elif diet == "low_fodmap":
            if not need_ingredients(rule, "FODMAP content"):
                continue
            high = sorted({e.name for _, e in entries if e.fodmap == "high"})
            reasons.append(
                _r(
                    "yellow",
                    rule,
                    "Contains high-FODMAP ingredients: " + ", ".join(high) + ". Tolerance depends on the amount.",
                    ", ".join(high),
                )
                if high
                else _r("green", rule, "No common high-FODMAP ingredients found (screening only).")
            )
        elif diet in ("keto", "low_carb", "high_protein", "low_sodium", "low_sugar"):
            if n is None:
                reasons.append(_r("yellow", rule, f"Nutrition facts unavailable, so we can't check {label.lower()}."))
                continue
            reasons.append(_nutrient_rule(diet, label, n, f))
        else:
            reasons.append(_r("yellow", rule, f"'{label}' isn't a preference we can check automatically yet."))

    # ---------------------------------------------------------------- custom avoid list
    if profile.avoid_terms:
        haystack = [normalize_term(x) for x in f.ingredient_names]
        slugs = {e.slug: e for _, e in entries}
        for term in profile.avoid_terms:
            t = normalize_term(term)
            if not t:
                continue
            hit = next((h for h in haystack if re.search(r"(?<![\w])" + re.escape(t) + r"(?![\w])", h)), None)
            if hit is None and t.replace(" ", "-") in slugs:
                hit = slugs[t.replace(" ", "-")].name
            if hit is None:
                hit = next(
                    (
                        e.name
                        for e in slugs.values()
                        if normalize_term(e.name) == t or (e.e_number and e.e_number.lower() == t)
                    ),
                    None,
                )
            if hit:
                reasons.append(_r("red", f"avoid.{t}", f"Contains '{term}', which is on your avoid list ({hit}).", hit))
            elif f.has_ingredients:
                reasons.append(_r("green", f"avoid.{t}", f"'{term}' not found in the ingredients."))
            else:
                reasons.append(_r("yellow", f"avoid.{t}", f"Can't check for '{term}': ingredient list unavailable."))

    if any(r["severity"] == "red" for r in reasons):
        verdict = "red"
    elif any(r["severity"] == "yellow" for r in reasons):
        verdict = "yellow"
    elif reasons:
        verdict = "green"
    else:
        verdict = "green" if f.has_ingredients else "yellow"
    order = {"red": 0, "yellow": 1, "green": 2}
    reasons.sort(key=lambda r: order[r["severity"]])
    return {
        "profile_id": profile.id,
        "profile_name": profile.name,
        "verdict": verdict,
        "critical_allergen_alerts": critical,
        "reasons": reasons,
        "disclaimer": DISCLAIMER,
    }


def _nutrient_rule(diet: str, label: str, n: NutritionInput, f: ProductFacts) -> dict:
    rule = f"diet.{diet}"
    if diet in ("keto", "low_carb"):
        if n.carbohydrates is None:
            return _r("yellow", rule, "Carbohydrates not reported.")
        net = n.carbohydrates - (n.fiber or 0)
        red, yellow = (10, 5) if diet == "keto" else (20, 10)
        sev = "red" if net > red else "yellow" if net > yellow else "green"
        return _r(sev, rule, f"{net:.1f} g net carbs per 100 g ({label}: aim ≤{yellow} g; >{red} g doesn't fit).")
    if diet == "high_protein":
        if n.protein is None or not n.energy_kcal:
            return _r("yellow", rule, "Protein or calories not reported.")
        pe = n.protein * 4 / n.energy_kcal * 100
        sev = "green" if pe >= 20 else "yellow"
        return _r(sev, rule, f"Protein provides {pe:.0f}% of calories (high protein is ≥20%).")
    if diet == "low_sodium":
        if n.sodium is None:
            return _r("yellow", rule, "Sodium not reported.")
        mg = n.sodium * 1000 * (3.6 if f.is_beverage else 1)
        basis = "per 12 fl oz" if f.is_beverage else "per 100 g"
        sev = "red" if mg >= 460 else "yellow" if mg > 140 else "green"
        return _r(sev, rule, f"{mg:.0f} mg sodium {basis} (FDA 'low sodium' is ≤140 mg; ≥460 mg = 20% DV is high).")
    # low_sugar
    sugar = f.added_sugar_basis if f.added_sugar_basis is not None else n.sugars
    if sugar is None:
        return _r("yellow", rule, "Sugars not reported.")
    amount = sugar * (3.6 if f.is_beverage else 1)
    pct = percent_dv("added_sugars", amount)
    sev = "red" if pct >= 20 else "yellow" if pct > 5 else "green"
    basis = "per 12 fl oz" if f.is_beverage else "per 100 g"
    return _r(sev, rule, f"{amount:.1f} g added sugar {basis} = {pct:.0f}% DV.")
