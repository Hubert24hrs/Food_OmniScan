"""In-memory ingredient knowledge base and matcher.

Built from the `ingredients`/`ingredient_synonyms` tables (or directly from the seed for
pure unit tests). Matching order, highest confidence first:
  1. E-number / INS number on the label           (0.98)
  2. exact synonym of the whole ingredient name   (1.00)
  3. longest known phrase contained in the name   (0.6–0.9, scaled by coverage)
Unmatched ingredients are returned as such; nothing is guessed.
"""

import re
import threading
from dataclasses import dataclass, field

from app.data.ingredients_seed import INGREDIENTS
from app.services.ingredient_parser import ParsedIngredient
from app.services.text import normalize_term


@dataclass
class KBEntry:
    slug: str
    name: str
    category: str
    function: str | None
    concern_level: str
    flags: list[str]
    e_number: str | None = None
    us_name: str | None = None
    vegan: str = "yes"
    vegetarian: str = "yes"
    halal_concern: str = "no"
    allergen_code: str | None = None
    fodmap: str | None = None
    concern_summary: str | None = None
    plain_language: str | None = None
    regulatory_notes: list = field(default_factory=list)
    source_keys: list = field(default_factory=list)
    verification_status: str = "pending"

    def display_name(self, region: str = "US") -> str:
        if region == "US" and self.us_name:
            return self.us_name
        return self.name


@dataclass
class Match:
    parsed: ParsedIngredient
    entry: KBEntry | None
    confidence: float
    method: str  # e_number | exact | phrase | none


class KnowledgeBase:
    def __init__(self, entries: list[KBEntry], synonyms: dict[str, str]):
        self.by_slug = {e.slug: e for e in entries}
        self.by_enumber: dict[str, KBEntry] = {}
        for e in entries:
            if e.e_number and e.e_number.upper() not in self.by_enumber:
                self.by_enumber[e.e_number.upper()] = e
        self.synonyms = synonyms  # normalised term -> slug
        # Longest phrases first so "soy lecithin" wins over "soy", "cocoa butter" over "butter".
        terms = sorted(synonyms, key=len, reverse=True)
        self._phrase_re = (
            re.compile(r"(?<![\w])(" + "|".join(re.escape(t) for t in terms) + r")(?![\w])") if terms else None
        )

    # ------------------------------------------------------------------ build
    @classmethod
    def from_seed(cls) -> "KnowledgeBase":
        entries, syn = [], {}
        for d in INGREDIENTS:
            entries.append(_entry_from_dict(d))
            for t in [
                d["name"],
                d["slug"].replace("-", " "),
                *d["synonyms"],
                *d.get("regional_synonyms", []),
                *([d["us_name"]] if d.get("us_name") else []),
            ]:
                syn.setdefault(normalize_term(t), d["slug"])
        return cls(entries, syn)

    @classmethod
    def from_db(cls, db) -> "KnowledgeBase":
        from sqlalchemy import select

        from app.models import Ingredient, IngredientSynonym

        rows = db.scalars(select(Ingredient)).all()
        if not rows:
            return cls.from_seed()
        entries = [
            KBEntry(
                slug=r.slug,
                name=r.name,
                category=r.category,
                function=r.function,
                concern_level=r.concern_level,
                flags=list(r.flags or []),
                e_number=r.e_number,
                us_name=r.us_name,
                vegan=r.vegan,
                vegetarian=r.vegetarian,
                halal_concern=r.halal_concern,
                allergen_code=r.allergen_code,
                fodmap=r.fodmap,
                concern_summary=r.concern_summary,
                plain_language=r.plain_language,
                regulatory_notes=list(r.regulatory_notes or []),
                source_keys=list(r.source_keys or []),
                verification_status=r.verification_status,
            )
            for r in rows
        ]
        id_to_slug = {r.id: r.slug for r in rows}
        syn: dict[str, str] = {}
        for r in rows:
            syn.setdefault(normalize_term(r.name), r.slug)
            if r.us_name:
                syn.setdefault(normalize_term(r.us_name), r.slug)
        for s in db.scalars(select(IngredientSynonym)).all():
            syn.setdefault(s.term, id_to_slug.get(s.ingredient_id))
        return cls(entries, {k: v for k, v in syn.items() if v})

    # ------------------------------------------------------------------ match
    def match(self, p: ParsedIngredient) -> Match:
        name = p.normalized
        if name and p.function_hint == name and p.children:
            # Label class heading such as "Emulsifiers (...)": its children are the real ingredients.
            return Match(p, None, 1.0, "class")
        if name and name in self.synonyms:
            return Match(p, self.by_slug[self.synonyms[name]], 1.0, "exact")
        for code in p.e_numbers:
            e = self._lookup_enumber(code)
            if e:
                return Match(p, e, 0.98, "e_number")
        if not name:
            return Match(p, None, 0.0, "none")
        # Bare E-number written as the ingredient, e.g. "e330"
        m = re.fullmatch(r"e ?(\d{3,4}[a-z]?)", name)
        if m:
            e = self._lookup_enumber("E" + m.group(1))
            if e:
                return Match(p, e, 0.98, "e_number")
        if self._phrase_re:
            hits = self._phrase_re.findall(name)
            if hits:
                best = max(hits, key=len)
                coverage = len(best) / max(len(name), 1)
                return Match(p, self.by_slug[self.synonyms[best]], round(0.6 + 0.3 * coverage, 2), "phrase")
        return Match(p, None, 0.0, "none")

    def _lookup_enumber(self, code: str) -> KBEntry | None:
        code = code.upper()
        if code in self.by_enumber:
            return self.by_enumber[code]
        base = re.match(r"E\d{3,4}", code)
        if base and base.group(0) in self.by_enumber:
            return self.by_enumber[base.group(0)]
        # E150a-d share a family; E1400-1452 modified starches share one entry
        if base:
            num = int(base.group(0)[1:])
            if 1400 <= num <= 1452:
                return self.by_enumber.get("E1422")
            if code.startswith("E150"):
                return self.by_enumber.get("E150A")
        return None

    def search(self, q: str, limit: int = 20) -> list[KBEntry]:
        qn = normalize_term(q)
        if not qn:
            return []
        scored: dict[str, int] = {}
        for term, slug in self.synonyms.items():
            if term == qn:
                scored[slug] = max(scored.get(slug, 0), 100)
            elif term.startswith(qn):
                scored[slug] = max(scored.get(slug, 0), 80)
            elif qn in term:
                scored[slug] = max(scored.get(slug, 0), 50)
        for code, e in self.by_enumber.items():
            if qn.replace(" ", "").upper() == code:
                scored[e.slug] = 100
        ranked = sorted(scored.items(), key=lambda kv: (-kv[1], self.by_slug[kv[0]].name))
        return [self.by_slug[s] for s, _ in ranked[:limit]]


def _entry_from_dict(d: dict) -> KBEntry:
    return KBEntry(
        slug=d["slug"],
        name=d["name"],
        category=d["category"],
        function=d["function"],
        concern_level=d["concern_level"],
        flags=d["flags"],
        e_number=d["e_number"],
        us_name=d.get("us_name"),
        vegan=d["vegan"],
        vegetarian=d["vegetarian"],
        halal_concern=d["halal_concern"],
        allergen_code=d["allergen_code"],
        fodmap=d["fodmap"],
        concern_summary=d["concern_summary"],
        plain_language=d["plain_language"],
        regulatory_notes=d["regulatory_notes"],
        source_keys=d["source_keys"],
    )


_kb: KnowledgeBase | None = None
_lock = threading.Lock()


def get_kb(db=None) -> KnowledgeBase:
    global _kb
    with _lock:
        if _kb is None:
            _kb = KnowledgeBase.from_db(db) if db is not None else KnowledgeBase.from_seed()
        return _kb


def invalidate_kb() -> None:
    """Called after admin edits to ingredients so the next request rebuilds the index."""
    global _kb
    with _lock:
        _kb = None
