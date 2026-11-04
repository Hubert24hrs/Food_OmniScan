"""Parse a raw ingredient statement (label text or OCR output) into a structured tree.

Handles nested parentheses/brackets, percentages, E-numbers and Codex INS numbers
(common on African and Asian labels, e.g. "Emulsifier (INS 471)"), class-name prefixes
("Emulsifiers: E471, soy lecithin") and the precautionary "may contain" statement,
which is separated from the ingredient list because it means something different.
"""

import re
from dataclasses import dataclass, field

from app.data.allergens import PRECAUTIONARY_PATTERNS
from app.services.text import normalize_term

_LABEL_PREFIX = re.compile(
    r"^\s*(?:list of )?(?:ingredients?|ingr[eé]dients?|zutaten|ingredientes|ingredienti|ingredi[eë]nten|"
    r"sammens[æa]tning|ainesosat|składniki)\s*[:\-–]?\s*",
    re.I,
)
_PAL = re.compile(r"(?:^|[.;,]\s*|\s)(" + "|".join(PRECAUTIONARY_PATTERNS) + r")\b(.*)$", re.I | re.S)
_ALLERGY_ADVICE = re.compile(r"\b(?:allergy advice|allergen information|contains)\s*:\s*([^.]*)\.?", re.I)
_PERCENT = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_ENUM = re.compile(r"\b(?:e|ins)\s?-?\s?(\d{3,4})\s?([a-z]|\([iv]+\))?\b", re.I)
_BARE_INS = re.compile(r"^\(?(\d{3,4}[a-z]?)\)?$", re.I)

ADDITIVE_CLASSES = {
    "emulsifier",
    "emulsifiers",
    "stabiliser",
    "stabilisers",
    "stabilizer",
    "stabilizers",
    "thickener",
    "thickeners",
    "thickening agent",
    "gelling agent",
    "preservative",
    "preservatives",
    "colour",
    "colours",
    "color",
    "colors",
    "colouring",
    "antioxidant",
    "antioxidants",
    "acidity regulator",
    "acidity regulators",
    "acid",
    "acids",
    "acidulant",
    "raising agent",
    "raising agents",
    "leavening agent",
    "leavening agents",
    "flavour enhancer",
    "flavour enhancers",
    "flavor enhancer",
    "flavor enhancers",
    "sweetener",
    "sweeteners",
    "humectant",
    "humectants",
    "anti-caking agent",
    "anticaking agent",
    "glazing agent",
    "flour treatment agent",
    "firming agent",
    "emulsifying salts",
    "bulking agent",
    "antifoaming agent",
    "carrier",
    "dough conditioner",
}

# Bare INS numbers inside a class group, e.g. "Flavour enhancer (621, 627)"
_CLASS_PREFIX = re.compile(r"^([a-z][a-z \-]+?)\s*:\s*(.+)$", re.I)


@dataclass
class ParsedIngredient:
    text: str  # as written (trimmed)
    normalized: str  # matching form without percentages/E-numbers
    depth: int = 0
    percent: float | None = None
    e_numbers: list[str] = field(default_factory=list)
    function_hint: str | None = None  # additive class if stated on label
    children: list["ParsedIngredient"] = field(default_factory=list)

    def flatten(self) -> list["ParsedIngredient"]:
        out = [self]
        for c in self.children:
            out.extend(c.flatten())
        return out


@dataclass
class ParsedStatement:
    ingredients: list[ParsedIngredient]
    precautionary_text: str | None
    contains_statement: str | None
    raw: str
    confidence: float  # how parseable the statement looked (0..1)

    def flat(self) -> list[ParsedIngredient]:
        out: list[ParsedIngredient] = []
        for i in self.ingredients:
            out.extend(i.flatten())
        return out


def _split_top_level(s: str) -> list[str]:
    parts, buf, depth = [], [], 0
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch in ",;" and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip(" .\n\t")]


def _split_head_and_inner(s: str) -> tuple[str, str | None, str]:
    """'cream filling (sugar, palm oil) 12%' -> ('cream filling', 'sugar, palm oil', ' 12%')."""
    start = None
    for idx, ch in enumerate(s):
        if ch in "([{":
            start = idx
            break
    if start is None:
        return s, None, ""
    depth = 0
    for idx in range(start, len(s)):
        if s[idx] in "([{":
            depth += 1
        elif s[idx] in ")]}":
            depth -= 1
            if depth == 0:
                return s[:start], s[start + 1 : idx], s[idx + 1 :]
    return s[:start], s[start + 1 :], ""  # unbalanced (common in OCR)


def normalize_enumber(num: str, suffix: str | None) -> str:
    suf = (suffix or "").strip("()").lower()
    roman = {"i", "ii", "iii", "iv", "v", "vi"}
    if suf in roman:
        suf = ""
    return f"E{num}{suf}"


def _extract_enums(s: str) -> list[str]:
    return [normalize_enumber(m.group(1), m.group(2)) for m in _ENUM.finditer(s)]


def _clean_name(s: str) -> str:
    s = _PERCENT.sub(" ", s)
    s = _ENUM.sub(" ", s)
    s = re.sub(r"\b(?:min(?:imum)?|max(?:imum)?)\b\.?", " ", s, flags=re.I)
    return normalize_term(s)


def _parse_item(item: str, depth: int, parent_class: str | None = None) -> ParsedIngredient | None:
    item = item.strip().strip(".").strip()
    if not item:
        return None
    function_hint = parent_class
    m = _CLASS_PREFIX.match(item)
    if m and normalize_term(m.group(1)) in ADDITIVE_CLASSES:
        # "Emulsifiers: soy lecithin, E471" written without brackets
        cls = normalize_term(m.group(1))
        group = ParsedIngredient(text=item, normalized=cls, depth=depth, function_hint=cls)
        for sub in _split_top_level(m.group(2)):
            child = _parse_item(sub, depth + 1, cls)
            if child:
                group.children.append(child)
        return group

    head, inner, tail = _split_head_and_inner(item)
    pct_m = _PERCENT.search(tail) or _PERCENT.search(head) or (_PERCENT.fullmatch(inner.strip()) if inner else None)
    percent = float(pct_m.group(1).replace(",", ".")) if pct_m else None
    if percent is not None and percent > 100:
        percent = None
    head_norm = _clean_name(head)
    e_numbers = _extract_enums(head)
    node = ParsedIngredient(
        text=item, normalized=head_norm, depth=depth, percent=percent, e_numbers=e_numbers, function_hint=function_hint
    )

    if inner and not _PERCENT.fullmatch(inner.strip()):
        is_class = head_norm in ADDITIVE_CLASSES
        if is_class:
            node.function_hint = head_norm
        sub_items = _split_top_level(inner)
        # "lecithin (E322)" or "caramel (E150d)": the parentheses only annotate the head
        if (
            all(_ENUM.fullmatch(x.strip()) or (is_class and _BARE_INS.match(x.strip())) for x in sub_items)
            and sub_items
        ):
            for x in sub_items:
                bare = _BARE_INS.match(x.strip())
                if is_class:
                    code = _extract_enums(x) or ([f"E{bare.group(1).lower()}"] if bare else [])
                    child = ParsedIngredient(
                        text=x.strip(), normalized="", depth=depth + 1, e_numbers=code, function_hint=head_norm
                    )
                    node.children.append(child)
                else:
                    node.e_numbers.extend(_extract_enums(x))
        else:
            for sub in sub_items:
                child = _parse_item(sub, depth + 1, head_norm if is_class else None)
                if child:
                    node.children.append(child)
    return node


def parse_ingredients(text: str | None) -> ParsedStatement:
    raw = text or ""
    s = raw.replace("\r", " ").replace("\n", " ")
    s = _LABEL_PREFIX.sub("", s).strip()

    precautionary = None
    m = _PAL.search(s)
    if m:
        precautionary = (m.group(1) + m.group(2)).strip(" .")
        s = s[: m.start(1)].rstrip(" .;,")

    contains_stmt = None
    m2 = _ALLERGY_ADVICE.search(s)
    if m2:
        contains_stmt = m2.group(1).strip()
        s = (s[: m2.start()] + s[m2.end() :]).strip()

    # A trailing full stop ends the list; any later sentences (storage advice etc.) are dropped.
    body = s.split(". ")[0] if ". " in s and s.count(",") > 2 else s
    items = [p for p in (_parse_item(x, 0) for x in _split_top_level(body)) if p]

    confidence = _statement_confidence(raw, items)
    return ParsedStatement(items, precautionary, contains_stmt, raw, confidence)


def _statement_confidence(raw: str, items: list[ParsedIngredient]) -> float:
    if not raw.strip() or not items:
        return 0.0
    names = [i.normalized for i in items if i.normalized]
    if not names:
        return 0.2
    alpha = sum(c.isalpha() for c in raw) / max(1, len(raw))
    avg_len = sum(len(n) for n in names) / len(names)
    garbage = sum(1 for n in names if len(n) < 2 or not re.search(r"[a-z]{2,}", n)) / len(names)
    score = 0.4 + 0.3 * min(1.0, alpha / 0.7) + 0.3 * (1 - garbage)
    if avg_len > 60:  # probably failed to split
        score -= 0.3
    return round(max(0.0, min(1.0, score)), 2)
