"""Explainable, versioned product scoring.

Pure functions: the same inputs and methodology config always give the same result
(`inputs_hash` proves it). Every point gained or lost is recorded as an adjustment with
a reason, an evidence type and source keys.
"""

import hashlib
import json
from dataclasses import dataclass, field

from app.services.allergens import US_MAJOR, AllergenFinding
from app.services.ingredient_parser import ParsedStatement
from app.services.knowledge import Match
from app.services.nutrition import FDA_DV, NutritionInput, fop_level, percent_dv

ADDED_SUGAR_FLAG = "added_sugar"


@dataclass
class ScoringInputs:
    nutrition: NutritionInput | None = None
    statement: ParsedStatement | None = None
    matches: list[Match] = field(default_factory=list)
    nova_group: int | None = None
    nova_source: str | None = None  # off | admin | None (we estimate)
    allergens: dict[str, AllergenFinding] = field(default_factory=dict)
    labels_tags: list[str] = field(default_factory=list)
    active_recalls: list[dict] = field(default_factory=list)
    lab_reports: list[dict] = field(default_factory=list)  # verified only
    is_beverage: bool = False


def _adj(
    code: str, points: float, reason: str, evidence: str = "regulatory", sources: list | None = None, **extra
) -> dict:
    d = {
        "code": code,
        "points": round(points, 1),
        "reason": reason,
        "evidence_type": evidence,
        "source_keys": sources or [],
    }
    d.update(extra)
    return d


def _ramp(value: float, low: float, high: float, max_points: float) -> float:
    if value <= low:
        return 0.0
    if value >= high:
        return max_points
    return (value - low) / (high - low) * max_points


# ---------------------------------------------------------------------------------- components


def _added_sugar_basis(inp: ScoringInputs) -> tuple[float | None, str]:
    n = inp.nutrition
    if n.added_sugars is not None:
        return n.added_sugars, "label_added_sugars"
    has_added = any(m.entry and ADDED_SUGAR_FLAG in m.entry.flags for m in inp.matches)
    if inp.statement and inp.statement.ingredients:
        if not has_added:
            return 0.0, "no_added_sugar_in_ingredients"
        return n.sugars, "total_sugars_proxy"
    return n.sugars, "total_sugars_unverified"


def score_nutrition(inp: ScoringInputs, cfg: dict) -> dict:
    n = inp.nutrition
    if n is None or len(n.core_present()) < 4:
        return {
            "assessed": False,
            "score": None,
            "adjustments": [],
            "notes": ["Nutrition facts are missing or incomplete."],
        }
    c = cfg["nutrition"]
    bev = inp.is_beverage or n.is_beverage
    factor = c["beverage_reference_ml"] / 100.0 if bev else 1.0
    basis_label = f"per {c['beverage_reference_ml']} ml (12 fl oz)" if bev else "per 100 g"
    adjustments: list[dict] = []
    notes: list[str] = []
    score = 100.0
    lo, full = c["low_pct_dv"], c["full_penalty_pct_dv"]

    sugar_value, sugar_basis = _added_sugar_basis(inp)
    values = {"added_sugars": sugar_value, "saturated_fat": n.saturated_fat, "sodium": n.sodium}
    for key, rule in c["negatives"].items():
        v = values[key]
        if v is None:
            notes.append(f"{key.replace('_', ' ')} not reported, so not assessed")
            continue
        amount = v * factor
        pct = percent_dv("sodium" if key == "sodium" else rule["dv_key"], amount)
        pen = _ramp(pct, lo, full, rule["max_penalty"])
        if key == "added_sugars" and sugar_basis == "total_sugars_proxy":
            notes.append(
                "Added sugars aren't reported, so total sugars were used because the ingredients include "
                "added sugar. This can overstate added sugar."
            )
        if key == "added_sugars" and sugar_basis == "no_added_sugar_in_ingredients":
            notes.append("No added sugar appears in the ingredient list; naturally occurring sugars aren't penalised.")
        if pen > 0:
            unit_amt = f"{amount * 1000:.0f} mg" if key == "sodium" else f"{amount:.1f} g"
            level = "high" if pct >= c["high_pct_dv"] else "moderate"
            label = {
                "added_sugars": "Added sugars" if sugar_basis == "label_added_sugars" else "Sugars",
                "saturated_fat": "Saturated fat",
                "sodium": "Sodium",
            }[key]
            adjustments.append(
                _adj(
                    f"nutrition.{key}",
                    -pen,
                    f"{label} is {level}: {unit_amt} {basis_label} = {pct:.0f}% of the FDA Daily Value "
                    f"(FDA treats ≥{c['high_pct_dv']}% DV as high).",
                    "product_measurement",
                    ["fda_21cfr101_9", "fda_5_20_rule"],
                    pct_dv=pct,
                )
            )
            score -= pen

    if n.energy_kcal is not None:
        e = c["energy"]["beverage" if bev else "food"]
        kcal = n.energy_kcal * factor
        pen = _ramp(kcal, e["low_kcal"], e["high_kcal"], e["max_penalty"])
        if pen > 0:
            adjustments.append(
                _adj("nutrition.energy", -pen, f"Energy density: {kcal:.0f} kcal {basis_label}.", "product_measurement")
            )
            score -= pen

    if n.trans_fat is not None and n.trans_fat * factor > c["trans_fat"]["threshold_g"]:
        adjustments.append(
            _adj(
                "nutrition.trans_fat",
                -c["trans_fat"]["penalty"],
                f"Contains {n.trans_fat * factor:.1f} g trans fat {basis_label}. Industrial trans fat "
                "raises LDL cholesterol.",
                "regulatory",
                ["fda_pho_2015"],
            )
        )
        score -= c["trans_fat"]["penalty"]

    p = c["positives"]
    if n.fiber is not None:
        if n.fiber >= p["fiber"]["high_g"]:
            adjustments.append(
                _adj(
                    "nutrition.fiber",
                    p["fiber"]["high_bonus"],
                    f"High in fiber ({n.fiber:.1f} g/100 g).",
                    "product_measurement",
                    ["eu_reg_1924_2006"],
                )
            )
            score += p["fiber"]["high_bonus"]
        elif n.fiber >= p["fiber"]["source_g"]:
            adjustments.append(
                _adj(
                    "nutrition.fiber",
                    p["fiber"]["source_bonus"],
                    f"Source of fiber ({n.fiber:.1f} g/100 g).",
                    "product_measurement",
                    ["eu_reg_1924_2006"],
                )
            )
            score += p["fiber"]["source_bonus"]
    if n.protein is not None and n.energy_kcal:
        pe = n.protein * 4 / n.energy_kcal * 100
        if pe >= p["protein"]["high_pct_energy"]:
            adjustments.append(
                _adj(
                    "nutrition.protein",
                    p["protein"]["high_bonus"],
                    f"High in protein ({pe:.0f}% of calories).",
                    "product_measurement",
                    ["eu_reg_1924_2006"],
                )
            )
            score += p["protein"]["high_bonus"]
        elif pe >= p["protein"]["source_pct_energy"]:
            adjustments.append(
                _adj(
                    "nutrition.protein",
                    p["protein"]["source_bonus"],
                    f"Source of protein ({pe:.0f}% of calories).",
                    "product_measurement",
                    ["eu_reg_1924_2006"],
                )
            )
            score += p["protein"]["source_bonus"]
    if n.fruits_veg_nuts_pct is not None:
        fv = p["fruits_veg_nuts"]
        bonus = _ramp(n.fruits_veg_nuts_pct, fv["min_pct"], fv["full_pct"], fv["max_bonus"])
        if bonus > 0:
            adjustments.append(
                _adj(
                    "nutrition.fruits_veg",
                    bonus,
                    f"About {n.fruits_veg_nuts_pct:.0f}% fruit, vegetables, legumes or nuts.",
                    "estimate",
                )
            )
            score += bonus
    missing = {"saturated_fat", "sodium", "energy_kcal", "sugars"} - set(n.core_present())
    return {
        "assessed": True,
        "score": round(max(0.0, min(100.0, score))),
        "adjustments": adjustments,
        "notes": notes,
        "basis": basis_label,
        "sugar_basis": sugar_basis,
        "missing": sorted(missing),
    }


def score_ingredients(inp: ScoringInputs, cfg: dict) -> dict:
    st = inp.statement
    if not st or not st.ingredients:
        return {"assessed": False, "score": None, "adjustments": [], "notes": ["Ingredient list unavailable."]}
    c = cfg["ingredients"]
    adjustments: list[dict] = []
    score = 100.0
    seen: set[str] = set()
    concern_total = caution_total = undisclosed_total = beneficial_total = 0.0
    for m in inp.matches:
        e = m.entry
        if not e or e.slug in seen or m.method == "class":
            continue
        seen.add(e.slug)
        if e.concern_level == "concern" and concern_total < c["concern"]["max_total"]:
            pen = min(c["concern"]["penalty"], c["concern"]["max_total"] - concern_total)
            concern_total += pen
            adjustments.append(
                _adj(
                    f"ingredient.concern.{e.slug}",
                    -pen,
                    f"{e.display_name()}: {e.concern_summary or 'concern'}",
                    "regulatory",
                    e.source_keys,
                    ingredient=e.slug,
                )
            )
        elif e.concern_level == "caution" and caution_total < c["caution"]["max_total"]:
            pen = min(c["caution"]["penalty"], c["caution"]["max_total"] - caution_total)
            caution_total += pen
            adjustments.append(
                _adj(
                    f"ingredient.caution.{e.slug}",
                    -pen,
                    f"{e.display_name()}: {e.concern_summary or 'use with caution'}",
                    "published_research" if "chassaing_2015" in e.source_keys else "regulatory",
                    e.source_keys,
                    ingredient=e.slug,
                )
            )
        if "undisclosed" in e.flags and undisclosed_total < c["undisclosed"]["max_total"]:
            undisclosed_total += c["undisclosed"]["penalty"]
            adjustments.append(
                _adj(
                    f"ingredient.undisclosed.{e.slug}",
                    -c["undisclosed"]["penalty"],
                    f"'{m.parsed.text.strip()}' doesn't say exactly what it contains.",
                    "unverified",
                    ingredient=e.slug,
                )
            )
    score -= concern_total + caution_total + undisclosed_total

    # Position-based rules use top-level ingredients (labels list them by descending weight).
    top = [inp_m for inp_m in inp.matches if inp_m.parsed.depth == 0]
    top_non_water = [m for m in top if not (m.entry and m.entry.slug == "water")]
    sugar_positions = [i for i, m in enumerate(top_non_water) if m.entry and ADDED_SUGAR_FLAG in m.entry.flags]
    if sugar_positions and sugar_positions[0] == 0:
        score -= c["added_sugar_first"]
        adjustments.append(
            _adj(
                "ingredient.added_sugar_first",
                -c["added_sugar_first"],
                "An added sugar is the main ingredient.",
                "product_measurement",
                ["who_sugars_2015"],
            )
        )
    elif sugar_positions and sugar_positions[0] < 3:
        score -= c["added_sugar_top3"]
        adjustments.append(
            _adj(
                "ingredient.added_sugar_top3",
                -c["added_sugar_top3"],
                "An added sugar is among the first three ingredients.",
                "product_measurement",
                ["who_sugars_2015"],
            )
        )
    sugar_types = {m.entry.slug for m in inp.matches if m.entry and ADDED_SUGAR_FLAG in m.entry.flags}
    if len(sugar_types) >= c["multiple_added_sugars"]["min_types"]:
        score -= c["multiple_added_sugars"]["penalty"]
        adjustments.append(
            _adj(
                "ingredient.multiple_sugars",
                -c["multiple_added_sugars"]["penalty"],
                f"{len(sugar_types)} different added sugars are used.",
                "product_measurement",
            )
        )
    for m in top_non_water[:3]:
        if m.entry and m.entry.concern_level == "beneficial" and beneficial_total < c["beneficial_top3"]["max_total"]:
            beneficial_total += c["beneficial_top3"]["bonus"]
            score += c["beneficial_top3"]["bonus"]
            adjustments.append(
                _adj(
                    f"ingredient.beneficial.{m.entry.slug}",
                    c["beneficial_top3"]["bonus"],
                    f"{m.entry.name} is a main ingredient.",
                    "published_research",
                    ingredient=m.entry.slug,
                )
            )

    flat = [m for m in inp.matches if m.method != "class"]
    matched = sum(1 for m in flat if m.entry)
    match_rate = matched / len(flat) if flat else 0.0
    notes = []
    if match_rate < 0.85:
        notes.append(f"{len(flat) - matched} ingredient(s) aren't in our database yet and weren't assessed.")
    return {
        "assessed": True,
        "score": round(max(0.0, min(100.0, score))),
        "adjustments": adjustments,
        "notes": notes,
        "match_rate": round(match_rate, 2),
        "parse_confidence": st.confidence,
    }


def estimate_nova(inp: ScoringInputs) -> int | None:
    """Rough NOVA estimate from ingredient markers (Monteiro et al. 2019). Always labelled as an estimate."""
    st = inp.statement
    if not st or not st.ingredients:
        return None
    entries = [m.entry for m in inp.matches if m.entry and m.method != "class"]
    if any("upf_marker" in e.flags for e in entries):
        return 4
    top = [m for m in inp.matches if m.parsed.depth == 0 and m.method != "class"]
    culinary = {"sugar", "salt", "olive-oil", "sunflower-oil", "vegetable-oil", "butter", "honey", "vinegar"}
    if len(top) == 1:
        e = top[0].entry
        if e and e.slug in culinary:
            return 2
        return 1 if e else None
    if any(e.slug in culinary or e.category in ("oil", "sugar", "seasoning") for e in entries):
        return 3
    return 3 if len(top) > 1 else 1


def score_processing(inp: ScoringInputs, cfg: dict) -> dict:
    nova, source = inp.nova_group, inp.nova_source
    if nova is None:
        nova = estimate_nova(inp)
        source = "estimated" if nova else None
    if nova is None:
        return {"assessed": False, "score": None, "adjustments": [], "notes": ["Processing level unknown."]}
    s = cfg["processing"]["nova_scores"][str(nova)]
    label = {
        1: "unprocessed or minimally processed",
        2: "a processed culinary ingredient",
        3: "processed",
        4: "ultra-processed",
    }[nova]
    reason = f"NOVA group {nova}: {label}" + (" (estimated from ingredients)" if source == "estimated" else "") + "."
    return {
        "assessed": True,
        "score": s,
        "nova_group": nova,
        "nova_source": source,
        "adjustments": [
            _adj(
                "processing.nova",
                s - 100,
                reason,
                "estimate" if source == "estimated" else "published_research",
                ["monteiro_2019_upf"],
            )
        ]
        if s < 100
        else [],
        "notes": [],
    }


def score_dietary(inp: ScoringInputs, cfg: dict) -> dict:
    """General dietary suitability: how many people can eat this. Not personal compatibility."""
    if not inp.allergens or all(f.status == "unknown" for f in inp.allergens.values()):
        return {"assessed": False, "score": None, "adjustments": [], "notes": ["Allergen information unavailable."]}
    c = cfg["dietary_suitability"]
    score, total, adjustments = 100.0, 0.0, []
    for code in US_MAJOR:
        f = inp.allergens.get(code)
        if not f or total >= c["allergen_max_total"]:
            continue
        if f.status == "contains":
            pen = c["major_allergen_contains"]
        elif f.status == "may_contain":
            pen = c["major_allergen_may_contain"]
        else:
            continue
        pen = min(pen, c["allergen_max_total"] - total)
        total += pen
        adjustments.append(
            _adj(
                f"dietary.allergen.{code}",
                -pen,
                f"{'Contains' if f.status == 'contains' else 'May contain'} {f.name.lower()}, "
                "a US major food allergen.",
                "regulatory",
                ["us_falcpa_faster"],
            )
        )
    score -= total
    fod = 0.0
    for m in inp.matches:
        if m.entry and m.entry.fodmap == "high" and fod < c["high_fodmap"]["max_total"]:
            fod += c["high_fodmap"]["penalty"]
            adjustments.append(
                _adj(
                    f"dietary.fodmap.{m.entry.slug}",
                    -c["high_fodmap"]["penalty"],
                    f"{m.entry.name} is high-FODMAP (relevant to IBS).",
                    "published_research",
                )
            )
    score -= fod
    slugs = {m.entry.slug for m in inp.matches if m.entry}
    if "caffeine" in slugs:
        score -= c["caffeine"]
        adjustments.append(
            _adj(
                "dietary.caffeine",
                -c["caffeine"],
                "Contains caffeine, which isn't suitable for children or recommended in pregnancy at high intake.",
                "regulatory",
                ["eu_reg_1169_2011"],
            )
        )
    if "alcohol" in slugs:
        score -= c["alcohol"]
        adjustments.append(_adj("dietary.alcohol", -c["alcohol"], "Contains alcohol.", "regulatory"))
    return {"assessed": True, "score": round(max(0.0, score)), "adjustments": adjustments, "notes": []}


def score_concerns(inp: ScoringInputs, cfg: dict) -> dict:
    c = cfg["product_concerns"]
    if inp.active_recalls:
        return {
            "assessed": True,
            "score": c["active_recall_score"],
            "notes": [],
            "adjustments": [
                _adj("concern.recall", -100, f"Active recall: {r['title']} ({r['authority']}).", "regulatory")
                for r in inp.active_recalls
            ],
        }
    if not inp.lab_reports:
        return {
            "assessed": False,
            "score": None,
            "adjustments": [],
            "notes": [
                "No verified laboratory testing for this product (heavy metals, pesticides, microplastics) "
                "is on file. This means unknown, not safe or unsafe."
            ],
        }
    score, adjustments = 100.0, []
    for r in inp.lab_reports:
        if r.get("exceeds_threshold"):
            score -= c["lab_exceedance_penalty"]
            adjustments.append(
                _adj(
                    f"concern.lab.{r['analyte']}",
                    -c["lab_exceedance_penalty"],
                    f"{r['analyte'].title()} measured at {r['value']} {r['unit']}, above the "
                    f"{r.get('threshold_jurisdiction') or ''} threshold of {r['threshold']} {r['unit']} "
                    f"({r['lab_name']}, {r.get('tested_on') or 'date not given'}).",
                    "product_measurement",
                )
            )
    return {
        "assessed": True,
        "score": round(max(0.0, score)),
        "adjustments": adjustments,
        "notes": [f"{len(inp.lab_reports)} verified lab result(s) on file."],
    }


# ---------------------------------------------------------------------------------- detection


def detect_highlights(inp: ScoringInputs) -> dict:
    groups = {
        "seed_oils": "seed_oil",
        "palm_oil": "palm_oil",
        "artificial_sweeteners": "artificial_sweetener",
        "sugar_alcohols": "sugar_alcohol",
        "artificial_colours": "artificial_colour",
        "natural_colours": "natural_colour",
        "flavourings": "flavouring",
        "flavour_enhancers": "flavour_enhancer",
        "preservatives": "preservative",
        "emulsifiers": "emulsifier",
        "thickeners": "thickener",
        "added_sugars": ADDED_SUGAR_FLAG,
        "hydrogenated_oils": "hydrogenated_oil",
        "partially_hydrogenated_oils": "partially_hydrogenated_oil",
        "ultra_processed_markers": "upf_marker",
        "undisclosed": "undisclosed",
        "whole_grains": "whole_grain",
    }
    out: dict[str, list[dict]] = {k: [] for k in groups}
    seen: dict[str, set] = {k: set() for k in groups}
    for m in inp.matches:
        e = m.entry
        if not e:
            continue
        for key, flag in groups.items():
            if flag in e.flags and e.slug not in seen[key]:
                seen[key].add(e.slug)
                out[key].append(
                    {"slug": e.slug, "name": e.display_name(), "e_number": e.e_number, "concern_level": e.concern_level}
                )
    labels = set(inp.labels_tags or [])
    out["organic"] = bool(labels & {"en:organic", "en:usda-organic", "en:eu-organic", "fr:ab-agriculture-biologique"})
    out["organic_note"] = (
        "Organic label reported by the data source."
        if out["organic"]
        else "No verified organic certification on record."
    )
    trans = inp.nutrition.trans_fat if inp.nutrition else None
    out["trans_fat_g_per_100"] = trans
    return out


def fop_summary(n: NutritionInput | None, bev: bool, ref_ml: int) -> dict | None:
    """FDA proposed front-of-package 'Nutrition Info box' levels, per label serving (or reference amount)."""
    if n is None:
        return None
    if n.serving_size_g:
        f, basis = n.serving_size_g / 100, f"per serving ({n.serving_size_g:g} {'ml' if bev else 'g'})"
    elif bev:
        f, basis = ref_ml / 100, f"per {ref_ml} ml"
    else:
        f, basis = 1.0, "per 100 g (serving size unknown)"
    sugar = n.added_sugars if n.added_sugars is not None else None
    out = {"basis": basis}
    for key, val, dv_key in (
        ("saturated_fat", n.saturated_fat, "saturated_fat"),
        ("sodium", n.sodium, "sodium"),
        ("added_sugars", sugar, "added_sugars"),
    ):
        pct = percent_dv(dv_key, val * f) if val is not None else None
        out[key] = {"pct_dv": pct, "level": fop_level(pct)}
    return out


# ---------------------------------------------------------------------------------- overall


def inputs_hash(inp: ScoringInputs, version: str) -> str:
    payload = {
        "v": version,
        "n": inp.nutrition.to_dict() if inp.nutrition else None,
        "i": [
            (
                m.parsed.normalized,
                m.parsed.depth,
                m.entry.slug if m.entry else None,
                m.entry.concern_level if m.entry else None,
            )
            for m in inp.matches
        ],
        "nova": [inp.nova_group, inp.nova_source],
        "a": sorted((k, f.status) for k, f in inp.allergens.items()),
        "r": sorted(r.get("id", r.get("title", "")) for r in inp.active_recalls),
        "l": sorted(str(r.get("id", r.get("analyte"))) for r in inp.lab_reports),
        "b": inp.is_beverage,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def compute_score(inp: ScoringInputs, cfg: dict) -> dict:
    comps = {
        "nutrition": score_nutrition(inp, cfg),
        "ingredients": score_ingredients(inp, cfg),
        "processing": score_processing(inp, cfg),
        "dietary_suitability": score_dietary(inp, cfg),
        "product_concerns": score_concerns(inp, cfg),
    }
    weights = cfg["weights"]
    for k, c in comps.items():
        c["weight"] = weights[k]
    core_total = sum(w for k, w in weights.items() if k != "product_concerns")
    core_assessed = sum(weights[k] for k, c in comps.items() if c["assessed"] and k != "product_concerns")
    coverage = core_assessed / core_total if core_total else 0.0
    assessed_weight = sum(weights[k] for k, c in comps.items() if c["assessed"])
    insufficient = coverage < cfg["min_coverage"] or not (
        comps["nutrition"]["assessed"] or comps["ingredients"]["assessed"]
    )
    if cfg.get("require_nutrition") and not comps["nutrition"]["assessed"]:
        insufficient = True

    overall = None
    caps: list[dict] = []
    if not insufficient and assessed_weight:
        raw = sum(c["score"] * weights[k] for k, c in comps.items() if c["assessed"]) / assessed_weight
        overall = raw
        ce = cfg["ceilings"]
        nut = comps["nutrition"]
        if nut["assessed"] and nut["score"] < ce["nutrition_margin"]["below"]:
            cap = nut["score"] + ce["nutrition_margin"]["margin"]
            if overall > cap:
                caps.append(
                    {
                        "code": "cap.nutrition",
                        "max": cap,
                        "reason": "Poor nutrition limits the overall score; other strengths can't fully offset it.",
                    }
                )
                overall = cap
        if comps["processing"].get("nova_group") == 4 and overall > ce["ultra_processed_max"]:
            caps.append(
                {
                    "code": "cap.ultra_processed",
                    "max": ce["ultra_processed_max"],
                    "reason": "Ultra-processed products can't be rated Excellent.",
                }
            )
            overall = ce["ultra_processed_max"]
        slugs = {m.entry.slug: m.entry for m in inp.matches if m.entry}
        if any(e.concern_level == "concern" for e in slugs.values()) and overall > ce["concern_ingredient_max"]:
            caps.append(
                {
                    "code": "cap.concern_ingredient",
                    "max": ce["concern_ingredient_max"],
                    "reason": "Contains an ingredient regulators have banned or restricted.",
                }
            )
            overall = ce["concern_ingredient_max"]
        if (
            any("partially_hydrogenated_oil" in e.flags for e in slugs.values())
            and overall > ce["partially_hydrogenated_max"]
        ):
            caps.append(
                {
                    "code": "cap.partially_hydrogenated",
                    "max": ce["partially_hydrogenated_max"],
                    "reason": "Contains partially hydrogenated oil (industrial trans fat).",
                }
            )
            overall = ce["partially_hydrogenated_max"]
        if inp.active_recalls:
            caps.append(
                {"code": "cap.recall", "max": ce["active_recall_max"], "reason": "Product has an active recall."}
            )
            overall = ce["active_recall_max"]
        overall = int(round(max(0.0, min(100.0, overall))))

    if overall is None:
        grade = {"grade": "insufficient_data", "color": "grey", "label": "Not enough data"}
    else:
        band = next(b for b in cfg["grade_bands"] if overall >= b["min"])
        grade = {"grade": band["grade"], "color": band["color"], "label": band["label"]}

    nova_estimated = comps["processing"].get("nova_source") == "estimated"
    match_rate = comps["ingredients"].get("match_rate", 0.0)
    if overall is None:
        confidence = "low"
    elif coverage >= 0.999 and not nova_estimated and match_rate >= 0.85:
        confidence = "high"
    elif coverage >= 0.8 and match_rate >= 0.6:
        confidence = "medium"
    else:
        confidence = "low"

    missing = [k for k, c in comps.items() if not c["assessed"]]
    return {
        "methodology_version": cfg["version"],
        "overall": overall,
        **grade,
        "confidence": confidence,
        "coverage": round(coverage, 2),
        "insufficient_data": insufficient,
        "missing_components": missing,
        "components": comps,
        "caps_applied": caps,
        "highlights": detect_highlights(inp),
        "front_of_pack": fop_summary(inp.nutrition, inp.is_beverage, cfg["nutrition"]["beverage_reference_ml"]),
        "daily_values": FDA_DV,
        "inputs_hash": inputs_hash(inp, cfg["version"]),
        "disclaimer": "This score is general nutrition information, not medical advice. It reflects the data "
        "available and the published methodology version shown.",
    }
