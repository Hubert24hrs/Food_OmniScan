"""Idempotent reference-data seed: sources, ingredient KB, default methodology, plan matrix.

Run: python -m app.db.seed
No product records are seeded: products come from real data sources or verified submissions.
"""

from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.data.content_seed import ARTICLES, LOCAL_INGREDIENT_NAMES, RECIPES
from app.data.ingredients_seed import INGREDIENTS
from app.data.sources_seed import SOURCES
from app.models import (
    Article,
    FoodAdditive,
    Ingredient,
    IngredientSynonym,
    Recipe,
    ScientificSource,
    ScoringMethodology,
    ScoringRule,
    SubscriptionEntitlement,
)
from app.services.entitlements import DEFAULT_MATRIX
from app.services.knowledge import invalidate_kb
from app.services.scoring.default_methodology import DEFAULT_METHODOLOGY, flatten_rules
from app.services.text import normalize_term


def seed_sources(db: Session) -> int:
    n = 0
    for s in SOURCES:
        if db.scalar(select(ScientificSource).where(ScientificSource.key == s["key"])):
            continue
        db.add(
            ScientificSource(
                **{
                    k: s.get(k)
                    for k in (
                        "key",
                        "title",
                        "authors",
                        "publisher",
                        "year",
                        "url",
                        "doi",
                        "source_type",
                        "evidence_quality",
                        "summary",
                    )
                },
                verified=False,
            )
        )
        n += 1
    db.flush()
    return n


def seed_ingredients(db: Session) -> int:
    n = 0
    used_terms = {t for (t,) in db.execute(select(IngredientSynonym.term)).all()}
    used_enums = {e for (e,) in db.execute(select(FoodAdditive.e_number)).all()}
    for d in INGREDIENTS:
        ing = db.scalar(select(Ingredient).where(Ingredient.slug == d["slug"]))
        if ing is None:
            ing = Ingredient(
                slug=d["slug"],
                name=d["name"],
                us_name=d.get("us_name"),
                category=d["category"],
                function=d["function"],
                plain_language=d["plain_language"],
                concern_level=d["concern_level"],
                concern_summary=d["concern_summary"],
                e_number=d["e_number"],
                is_additive=bool(d["e_number"]),
                vegan=d["vegan"],
                vegetarian=d["vegetarian"],
                halal_concern=d["halal_concern"],
                allergen_code=d["allergen_code"],
                flags=d["flags"],
                fodmap=d["fodmap"],
                regulatory_notes=d["regulatory_notes"],
                source_keys=d["source_keys"],
                verification_status="pending",
            )
            db.add(ing)
            db.flush()
            n += 1
        terms = [(t, None) for t in [d["name"], *d["synonyms"]]] + [
            (t, "regional") for t in d.get("regional_synonyms", [])
        ]
        if d.get("us_name"):
            terms.append((d["us_name"], "US"))
        for t, region in terms:
            nt = normalize_term(t)
            if nt and nt not in used_terms:
                db.add(IngredientSynonym(ingredient_id=ing.id, term=nt, language="en", region=region))
                used_terms.add(nt)
        if d["e_number"] and d["e_number"] not in used_enums:
            db.add(
                FoodAdditive(
                    e_number=d["e_number"],
                    ingredient_id=ing.id,
                    additive_class=d["category"],
                    eu_status="not_authorised"
                    if d["slug"] in ("titanium-dioxide", "potassium-bromate", "propylparaben", "azodicarbonamide")
                    else "authorised",
                )
            )
            used_enums.add(d["e_number"])
    db.flush()
    invalidate_kb()
    return n


def seed_methodology(db: Session) -> bool:
    if db.scalar(select(ScoringMethodology).where(ScoringMethodology.version == DEFAULT_METHODOLOGY["version"])):
        return False
    has_active = db.scalar(select(ScoringMethodology).where(ScoringMethodology.is_active.is_(True)))
    m = ScoringMethodology(
        version=DEFAULT_METHODOLOGY["version"],
        name=DEFAULT_METHODOLOGY["name"],
        config=DEFAULT_METHODOLOGY,
        is_active=has_active is None,
        notes="Initial US FDA-basis methodology.",
        published_at=datetime.now(UTC),
    )
    db.add(m)
    db.flush()
    for r in flatten_rules(DEFAULT_METHODOLOGY):
        db.add(ScoringRule(methodology_id=m.id, **r))
    db.flush()
    return True


def seed_entitlements(db: Session) -> int:
    n = 0
    for feature, tiers in DEFAULT_MATRIX.items():
        for tier, limit in tiers.items():
            if not db.scalar(
                select(SubscriptionEntitlement).where(
                    SubscriptionEntitlement.tier == tier, SubscriptionEntitlement.feature == feature
                )
            ):
                db.add(SubscriptionEntitlement(tier=tier, feature=feature, monthly_limit=limit))
                n += 1
    db.flush()
    return n


_LANG = {"yoruba": "yo", "igbo": "ig", "hausa": "ha"}


def seed_local_names(db: Session) -> int:
    """Yoruba, Igbo and Hausa names as synonyms of existing KB ingredients (region NG)."""
    n = 0
    for row in LOCAL_INGREDIENT_NAMES:
        english = normalize_term(row["name"].split("(")[0])
        alt = normalize_term(row["name"].split("(")[1].rstrip(")")) if "(" in row["name"] else None
        syn = db.scalar(select(IngredientSynonym).where(IngredientSynonym.term.in_([t for t in (english, alt) if t])))
        if syn is None:
            continue
        for key, lang in _LANG.items():
            term = normalize_term(row.get(key) or "")
            if not term:
                continue
            if db.scalar(
                select(IngredientSynonym).where(IngredientSynonym.term == term, IngredientSynonym.language == lang)
            ):
                continue
            db.add(IngredientSynonym(ingredient_id=syn.ingredient_id, term=term, language=lang, region="NG"))
            n += 1
    db.flush()
    invalidate_kb()
    return n


def seed_recipes(db: Session) -> int:
    n = 0
    for r in RECIPES:
        if db.scalar(select(Recipe).where(Recipe.title == r["title"], Recipe.created_by.is_(None))):
            continue
        db.add(Recipe(**r, nutrition=None, nutrition_is_estimate=True, verified=False, is_public=True))
        n += 1
    db.flush()
    return n


def seed_articles(db: Session) -> int:
    n = 0
    for a in ARTICLES:
        if db.scalar(select(Article).where(Article.slug == a["slug"])):
            continue
        db.add(Article(**a, status="published", published_at=datetime.now(UTC)))
        n += 1
    db.flush()
    return n


SEED_LOCK_ID = 727_466_401  # arbitrary constant: "only one process seeds at a time"


def run(db: Session) -> dict:
    if db.get_bind().dialect.name == "postgresql":
        # Several workers/instances start together; the others wait here, then find the rows already present.
        db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": SEED_LOCK_ID})
    out = {
        "sources": seed_sources(db),
        "ingredients": seed_ingredients(db),
        "methodology": seed_methodology(db),
        "entitlements": seed_entitlements(db),
        "local_names": seed_local_names(db),
        "recipes": seed_recipes(db),
        "articles": seed_articles(db),
    }
    db.commit()
    return out


if __name__ == "__main__":
    import app.models  # noqa: F401
    from app.db.session import Base, SessionLocal, engine

    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        print(run(s))
