"""Nutrient model, US FDA Daily Values, and nutrition-label text parsing.

US standards are the default: %DV uses the FDA Daily Values for adults and children
4 years and older (21 CFR 101.9). EU/UK per-100 g presentation is derived from the same data.
"""

import re
from dataclasses import asdict, dataclass, field

# FDA Daily Values (2,000 kcal reference), grams unless noted.
FDA_DV = {
    "fat": 78.0,
    "saturated_fat": 20.0,
    "cholesterol_mg": 300.0,
    "sodium_mg": 2300.0,
    "carbohydrates": 275.0,
    "fiber": 28.0,
    "added_sugars": 50.0,
    "protein": 50.0,
}

# Vitamins and minerals: key -> (label, unit, FDA Daily Value for adults, Open Food Facts key, FDC number).
# DVs from 21 CFR 101.9(c)(8)(iv) (2016 rule). Stored per 100 g in NutritionFacts.extra["micros"].
MICROS: dict[str, tuple[str, str, float, str, str]] = {
    "vitamin_d": ("Vitamin D", "mcg", 20, "vitamin-d", "328"),
    "calcium": ("Calcium", "mg", 1300, "calcium", "301"),
    "iron": ("Iron", "mg", 18, "iron", "303"),
    "potassium": ("Potassium", "mg", 4700, "potassium", "306"),
    "vitamin_a": ("Vitamin A", "mcg", 900, "vitamin-a", "320"),
    "vitamin_c": ("Vitamin C", "mg", 90, "vitamin-c", "401"),
    "vitamin_e": ("Vitamin E", "mg", 15, "vitamin-e", "323"),
    "vitamin_k": ("Vitamin K", "mcg", 120, "vitamin-k", "430"),
    "thiamin": ("Thiamin (B1)", "mg", 1.2, "vitamin-b1", "404"),
    "riboflavin": ("Riboflavin (B2)", "mg", 1.3, "vitamin-b2", "405"),
    "niacin": ("Niacin (B3)", "mg", 16, "vitamin-pp", "406"),
    "vitamin_b6": ("Vitamin B6", "mg", 1.7, "vitamin-b6", "415"),
    "folate": ("Folate", "mcg", 400, "vitamin-b9", "435"),
    "vitamin_b12": ("Vitamin B12", "mcg", 2.4, "vitamin-b12", "418"),
    "magnesium": ("Magnesium", "mg", 420, "magnesium", "304"),
    "zinc": ("Zinc", "mg", 11, "zinc", "309"),
    "phosphorus": ("Phosphorus", "mg", 1250, "phosphorus", "305"),
    "selenium": ("Selenium", "mcg", 55, "selenium", "317"),
}
_UNIT_FROM_G = {"mg": 1000, "mcg": 1_000_000}


def micros_from_off(nutriments: dict) -> dict:
    """OFF reports *_100g values in grams; convert to each micronutrient's label unit."""
    out = {}
    for key, (_, unit, _dv, off_key, _n) in MICROS.items():
        v = nutriments.get(f"{off_key}_100g")
        try:
            v = float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            v = None
        if v is not None and v >= 0:
            out[key] = round(v * _UNIT_FROM_G[unit], 3)
    return out


def scale_micros(micros: dict | None, factor: float) -> dict:
    return {k: round(v * factor, 3) for k, v in (micros or {}).items() if v is not None}


NUTRIENT_FIELDS = (
    "energy_kcal",
    "energy_kj",
    "fat",
    "saturated_fat",
    "trans_fat",
    "cholesterol_mg",
    "carbohydrates",
    "sugars",
    "added_sugars",
    "fiber",
    "protein",
    "salt",
    "sodium",
)


@dataclass
class NutritionInput:
    """All values per 100 g (or 100 ml for beverages). Missing = None, never 0."""

    energy_kcal: float | None = None
    energy_kj: float | None = None
    fat: float | None = None
    saturated_fat: float | None = None
    trans_fat: float | None = None
    cholesterol_mg: float | None = None
    carbohydrates: float | None = None
    sugars: float | None = None
    added_sugars: float | None = None
    fiber: float | None = None
    protein: float | None = None
    salt: float | None = None
    sodium: float | None = None  # grams
    fruits_veg_nuts_pct: float | None = None
    serving_size_g: float | None = None
    is_beverage: bool = False
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Derive the missing half of linked pairs; salt = sodium x 2.5 (EU 1169/2011 Annex XIV).
        if self.sodium is None and self.salt is not None:
            self.sodium = round(self.salt / 2.5, 4)
        if self.salt is None and self.sodium is not None:
            self.salt = round(self.sodium * 2.5, 4)
        if self.energy_kcal is None and self.energy_kj is not None:
            self.energy_kcal = round(self.energy_kj / 4.184, 1)
        if self.energy_kj is None and self.energy_kcal is not None:
            self.energy_kj = round(self.energy_kcal * 4.184, 1)

    @property
    def unit(self) -> str:
        return "100ml" if self.is_beverage else "100g"

    def core_present(self) -> list[str]:
        core = ["energy_kcal", "fat", "saturated_fat", "carbohydrates", "sugars", "protein", "sodium"]
        return [k for k in core if getattr(self, k) is not None]

    def per_serving(self) -> dict | None:
        if not self.serving_size_g:
            return None
        f = self.serving_size_g / 100.0
        return {k: round(v * f, 2) for k in NUTRIENT_FIELDS if (v := getattr(self, k)) is not None}

    def to_dict(self) -> dict:
        return asdict(self)


def percent_dv(nutrient: str, value: float | None) -> float | None:
    """%DV for a value in the units used by NutritionInput (sodium in grams)."""
    if value is None:
        return None
    if nutrient == "sodium":
        return round(value * 1000 / FDA_DV["sodium_mg"] * 100, 1)
    if nutrient in FDA_DV:
        return round(value / FDA_DV[nutrient] * 100, 1)
    return None


def fop_level(pct: float | None) -> str | None:
    """FDA proposed front-of-package level: Low (<=5% DV), Med (6-19%), High (>=20%)."""
    if pct is None:
        return None
    if pct <= 5:
        return "low"
    if pct >= 20:
        return "high"
    return "medium"


def from_off(product: dict) -> NutritionInput | None:
    n = product.get("nutriments") or {}
    if not n:
        return None

    def g(key: str) -> float | None:
        v = n.get(f"{key}_100g")
        try:
            return float(v) if v is not None and v != "" else None
        except (TypeError, ValueError):
            return None

    kcal = g("energy-kcal")
    kj = g("energy-kj")
    if kcal is None and kj is None and g("energy") is not None:
        kj = g("energy")  # OFF 'energy' is kJ
    chol = g("cholesterol")
    serving_q = product.get("serving_quantity")
    try:
        serving_g = float(serving_q) if serving_q not in (None, "") else None
    except (TypeError, ValueError):
        serving_g = None
    ni = NutritionInput(
        energy_kcal=kcal,
        energy_kj=kj,
        fat=g("fat"),
        saturated_fat=g("saturated-fat"),
        trans_fat=g("trans-fat"),
        cholesterol_mg=chol * 1000 if chol is not None else None,
        carbohydrates=g("carbohydrates"),
        sugars=g("sugars"),
        added_sugars=g("added-sugars"),
        fiber=g("fiber"),
        protein=g("proteins"),
        salt=g("salt"),
        sodium=g("sodium"),
        fruits_veg_nuts_pct=g("fruits-vegetables-nuts-estimate-from-ingredients") or g("fruits-vegetables-nuts"),
        serving_size_g=serving_g if serving_g and serving_g > 0 else None,
    )
    micros = micros_from_off(n)
    if micros:
        ni.extra["micros"] = micros
    return ni if ni.core_present() else None


# --------------------------------------------------------------------------- label OCR parsing

_NUM = r"(\d+(?:[.,]\d+)?)"
_LINE_PATTERNS: list[tuple[str, str, str]] = [
    # (field, regex, default unit)
    ("added_sugars", r"(?:includes|incl\.?)\s*" + _NUM + r"\s*(mg|g|9)?\s*added\s+sugars?", "g"),
    ("added_sugars", r"added\s+sugars?\s*" + _NUM + r"\s*(mg|g|9)?", "g"),
    (
        "saturated_fat",
        r"(?:saturated\s+fat|of\s+which\s+saturates|saturates|sat\.?\s*fat)\s*" + _NUM + r"\s*(mg|g|9)?",
        "g",
    ),
    ("trans_fat", r"trans\s+fat\s*" + _NUM + r"\s*(mg|g|9)?", "g"),
    ("fat", r"(?:total\s+fat|^fat|\bfat)\s*" + _NUM + r"\s*(mg|g|9)?", "g"),
    ("cholesterol_mg", r"cholesterol\s*" + _NUM + r"\s*(mg|g)?", "mg"),
    ("sodium", r"sodium\s*" + _NUM + r"\s*(mg|g|9)?", "mg"),
    ("salt", r"\bsalt\s*" + _NUM + r"\s*(mg|g|9)?", "g"),
    ("fiber", r"(?:dietary\s+fib(?:er|re)|fib(?:er|re))\s*" + _NUM + r"\s*(mg|g|9)?", "g"),
    ("sugars", r"(?:total\s+sugars?|of\s+which\s+sugars|^sugars?|\bsugars)\s*" + _NUM + r"\s*(mg|g|9)?", "g"),
    ("carbohydrates", r"(?:total\s+carbohydrates?|total\s+carb\.?|carbohydrates?)\s*" + _NUM + r"\s*(mg|g|9)?", "g"),
    ("protein", r"proteins?\s*" + _NUM + r"\s*(mg|g|9)?", "g"),
    ("energy_kcal", r"calories\s*" + _NUM, "kcal"),
    ("energy_kcal", _NUM + r"\s*kcal", "kcal"),
    ("energy_kcal", r"kcal\s*" + _NUM, "kcal"),
    ("energy_kj", _NUM + r"\s*kj", "kj"),
]
_PCT_AFTER = re.compile(r"(\d{1,3})\s*%")
# "Serving size 2/3 cup (55g)" -> 55; "Serving size 30g" -> 30
_SERVING_PAREN = re.compile(r"serving\s+size[^\n]*?\(\s*(\d+(?:[.,]\d+)?)\s*(g|ml)\s*\)", re.I)
_SERVING_BARE = re.compile(r"serving\s+size\s*:?\s*(\d+(?:[.,]\d+)?)\s*(g|ml)\b", re.I)
_PER100 = re.compile(r"per\s*100\s*(g|ml)", re.I)


def _ocr_fix(s: str) -> str:
    # Common OCR confusions inside numbers: O->0, l/I->1
    return re.sub(r"(?<=\d)[oO]|[oO](?=\d)", "0", re.sub(r"(?<=\d)[lI]|[lI](?=\d\b)", "1", s))


def parse_nutrition_label(text: str) -> dict:
    """Parse OCR text from a Nutrition Facts (US) or nutrition declaration (EU) panel.

    Returns per-label-basis values plus per-field confidence. US panels are per serving;
    EU tables are usually per 100 g. When a %DV is printed, it is used to resolve the
    OCR 'g'->'9' confusion (e.g. 'Total Fat 89 10%' -> 8 g).
    """
    raw = text or ""
    lines = [_ocr_fix(ln.strip()) for ln in raw.replace("\r", "").split("\n") if ln.strip()]
    basis = "100g" if _PER100.search(raw) else "serving"
    if basis == "100g" and _PER100.search(raw).group(1).lower() == "ml":
        basis = "100ml"
    serving_m = _SERVING_PAREN.search(raw) or _SERVING_BARE.search(raw)
    serving_g = float(serving_m.group(1).replace(",", ".")) if serving_m else None

    values: dict[str, float] = {}
    conf: dict[str, float] = {}
    warnings: list[str] = []
    for line in lines:
        low = line.lower()
        for fld, pat, default_unit in _LINE_PATTERNS:
            if fld in values:
                continue
            m = re.search(pat, low)
            if not m:
                continue
            # 'fat' pattern must not swallow saturated/trans lines
            if fld == "fat" and re.search(r"saturat|trans", low):
                continue
            if fld == "sugars" and "added" in low:
                continue
            if fld == "carbohydrates" and "sugar" in low and "carbohydrate" not in low:
                continue
            val = float(m.group(1).replace(",", "."))
            unit = (m.group(2) if m.lastindex and m.lastindex >= 2 else None) or default_unit
            c = 0.9
            pct_m = _PCT_AFTER.search(low[m.end() :])
            if unit == "9":  # OCR read 'g' as '9': e.g. "89" was "8g"
                unit = "g"
                c = 0.6
            elif unit in ("g", "mg") and pct_m is None and default_unit == "g" and re.fullmatch(r"\d+9", m.group(1)):
                c = 0.7
            dv_key = {"sodium": "sodium_mg"}.get(fld, fld)
            if pct_m and dv_key in FDA_DV:
                pct = float(pct_m.group(1))
                expected = pct / 100 * FDA_DV[dv_key]
                cand = val / 1000 if (fld != "sodium" and unit == "mg") else val
                if fld == "sodium":
                    cand_mg = val * 1000 if unit == "g" else val
                    if expected and abs(cand_mg - expected) / expected > 0.5:
                        warnings.append(f"sodium value {val}{unit} disagrees with {pct:.0f}% DV")
                        c = 0.5
                    else:
                        c = 0.95
                elif expected and abs(cand - expected) / max(expected, 0.5) > 0.6:
                    # try dropping a trailing 9 that was really a 'g'
                    s = m.group(1)
                    if s.endswith("9") and len(s) > 1:
                        alt = float(s[:-1].replace(",", "."))
                        if abs(alt - expected) / max(expected, 0.5) <= 0.6:
                            val, c = alt, 0.85
                            warnings.append(f"{fld}: corrected OCR '{s}' to {alt} g using %DV")
                        else:
                            c = 0.5
                            warnings.append(f"{fld}: value disagrees with printed %DV")
                    else:
                        c = 0.5
                        warnings.append(f"{fld}: value disagrees with printed %DV")
                else:
                    c = 0.95
            if fld == "sodium":
                val = val / 1000 if unit == "mg" else val  # store grams
            elif fld == "cholesterol_mg":
                val = val * 1000 if unit == "g" else val
            elif unit == "mg":
                val = val / 1000
            values[fld] = round(val, 4)
            conf[fld] = c
    if "sodium" not in values and "salt" in values:
        values["sodium"] = round(values["salt"] / 2.5, 4)
        conf["sodium"] = conf["salt"] * 0.95

    overall = round(sum(conf.values()) / len(conf), 2) if conf else 0.0
    core = {"energy_kcal", "fat", "carbohydrates", "protein"}
    if not core.issubset(values):
        overall = round(overall * 0.7, 2)
        warnings.append("Some core nutrients were not found. Please review before saving.")
    return {
        "basis": basis,
        "serving_size_g": serving_g,
        "values": values,
        "field_confidence": conf,
        "confidence": overall,
        "warnings": warnings,
    }


def label_to_per100(parsed: dict, is_beverage: bool = False) -> NutritionInput | None:
    vals = dict(parsed.get("values") or {})
    if not vals:
        return None
    serving = parsed.get("serving_size_g")
    if parsed.get("basis") == "serving":
        if not serving:
            return None
        f = 100.0 / serving
        vals = {k: round(v * f, 3) for k, v in vals.items()}
    allowed = {k: vals.get(k) for k in NUTRIENT_FIELDS}
    return NutritionInput(**allowed, serving_size_g=serving, is_beverage=is_beverage)
