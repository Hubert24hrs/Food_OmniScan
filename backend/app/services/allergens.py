"""Allergen detection.

Status per allergen:
  contains     : declared or detected in the ingredient list
  may_contain  : precautionary statement ("may contain", "made in a facility...") or a
                 derivative that is usually exempt (highly refined oils) but not risk-free
  not_detected : ingredient list is known and nothing matched. This is NOT a safety guarantee
  unknown      : no ingredient information, so we cannot say anything
"""

import re
from dataclasses import dataclass, field

from app.data.allergens import ALLERGENS
from app.services.ingredient_parser import ParsedStatement
from app.services.knowledge import Match
from app.services.text import normalize_term

# Phrases that contain an allergen word but are not that allergen.
FALSE_FRIENDS: dict[str, list[str]] = {
    "milk": [
        "coconut milk",
        "coconut cream",
        "cocoa butter",
        "cacao butter",
        "shea butter",
        "peanut butter",
        "nut butter",
        "almond butter",
        "cashew butter",
        "butter beans",
        "butter bean",
        "cream of tartar",
        "soy milk",
        "soya milk",
        "oat milk",
        "rice milk",
        "almond milk",
        "milk thistle",
        "dairy free",
        "dairy-free",
        "non-dairy",
        "non dairy",
    ],
    "eggs": ["egg free", "eggless"],
    "nuts": ["nutmeg", "coconut", "doughnut", "donut", "butternut", "water chestnut", "nut free"],
    "gluten": ["buckwheat", "gluten free", "gluten-free"],
    "wheat": ["buckwheat", "wheat free", "wheat-free"],
    "fish": ["fish free"],
}

# Highly refined oils are exempt from allergen labelling under FALCPA (US) and EU 1169/2011.
REFINED_OIL_DERIVATIVES: dict[str, list[str]] = {
    "soybeans": ["soybean oil", "soya oil", "soy oil", "soya bean oil", "fully refined soybean oil"],
    "peanuts": ["peanut oil", "groundnut oil", "arachis oil"],
}

US_MAJOR = ["milk", "eggs", "fish", "crustaceans", "nuts", "peanuts", "wheat", "soybeans", "sesame"]
EU_14 = [
    "gluten",
    "crustaceans",
    "eggs",
    "fish",
    "peanuts",
    "soybeans",
    "milk",
    "nuts",
    "celery",
    "mustard",
    "sesame",
    "sulphites",
    "lupin",
    "molluscs",
]

_term_res = {
    code: re.compile(
        r"(?<![\w])("
        + "|".join(re.escape(normalize_term(t)) for t in sorted(a["terms"], key=len, reverse=True))
        + r")(?![\w])(?!\s?-?free)"
    )
    for code, a in ALLERGENS.items()
}
_off_tag_to_codes: dict[str, list[str]] = {}
for _code, _a in ALLERGENS.items():
    for _t in _a["off_tags"]:
        _off_tag_to_codes.setdefault(_t, []).append(_code)


@dataclass
class AllergenFinding:
    code: str
    name: str
    status: str
    evidence: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"code": self.code, "name": self.name, "status": self.status, "evidence": self.evidence}


def _strip(text: str, phrases: list[str]) -> str:
    for ph in phrases:
        text = re.sub(r"(?<![\w])" + re.escape(ph) + r"(?![\w])", " ", text)
    return text


def _scan(text: str, code: str) -> list[str]:
    cleaned = _strip(text, FALSE_FRIENDS.get(code, []) + REFINED_OIL_DERIVATIVES.get(code, []))
    return sorted(set(_term_res[code].findall(cleaned)))


def detect_allergens(
    statement: ParsedStatement | None,
    matches: list[Match] | None,
    off_allergen_tags: list[str] | None = None,
    off_trace_tags: list[str] | None = None,
) -> dict[str, AllergenFinding]:
    has_ingredients = bool(statement and statement.ingredients)
    has_tags = bool(off_allergen_tags) or bool(off_trace_tags)
    base_status = "not_detected" if (has_ingredients or has_tags) else "unknown"
    findings = {c: AllergenFinding(c, a["name"], base_status) for c, a in ALLERGENS.items()}

    def mark(code: str, status: str, ev: dict) -> None:
        f = findings[code]
        rank = {"unknown": 0, "not_detected": 1, "may_contain": 2, "contains": 3}
        if rank[status] > rank[f.status]:
            f.status = status
        if ev not in f.evidence:
            f.evidence.append(ev)

    if statement:
        ingredient_text = normalize_term(" , ".join(p.text for p in statement.ingredients))
        for code in ALLERGENS:
            for hit in _scan(ingredient_text, code):
                mark(code, "contains", {"source": "ingredients", "text": hit})
            for deriv in REFINED_OIL_DERIVATIVES.get(code, []):
                if re.search(r"(?<![\w])" + re.escape(deriv) + r"(?![\w])", ingredient_text):
                    mark(
                        code,
                        "may_contain",
                        {
                            "source": "refined_oil",
                            "text": deriv,
                            "note": "Highly refined oils are exempt from US and EU allergen labelling because refining "
                            "removes most protein. Unrefined or cold-pressed oil can still cause reactions.",
                        },
                    )
        if statement.contains_statement:
            cs = normalize_term(statement.contains_statement)
            for code in ALLERGENS:
                for hit in _scan(cs, code):
                    mark(code, "contains", {"source": "contains_statement", "text": hit})
        if statement.precautionary_text:
            pal = normalize_term(statement.precautionary_text)
            for code in ALLERGENS:
                if _scan(pal, code):
                    mark(
                        code, "may_contain", {"source": "precautionary_statement", "text": statement.precautionary_text}
                    )

    for m in matches or []:
        if m.entry and m.entry.allergen_code in findings and m.method != "class":
            code = m.entry.allergen_code
            # A partial phrase match ("coconut milk" -> milk) only counts if the false-friend-aware scan agrees.
            if m.method == "phrase" and not _scan(normalize_term(m.parsed.text), code):
                continue
            mark(code, "contains", {"source": "ingredient_match", "text": m.parsed.text})

    for tag in off_allergen_tags or []:
        for code in _off_tag_to_codes.get(tag, []):
            mark(code, "contains", {"source": "open_food_facts", "text": tag})
    for tag in off_trace_tags or []:
        for code in _off_tag_to_codes.get(tag, []):
            mark(code, "may_contain", {"source": "open_food_facts_traces", "text": tag})

    # Wheat implies gluten (EU) and vice versa only for wheat-specific evidence
    if findings["wheat"].status == "contains":
        mark("gluten", "contains", {"source": "derived", "text": "wheat"})
    return findings


def summary(findings: dict[str, AllergenFinding], region: str = "US") -> list[dict]:
    """Ordered list for display: the region's regulated allergens first."""
    primary = US_MAJOR if region == "US" else EU_14
    ordered = primary + [c for c in ALLERGENS if c not in primary]
    return [dict(findings[c].to_dict(), regulated_in_region=c in primary) for c in ordered]
