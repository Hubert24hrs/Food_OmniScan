"""Product lookup, caching, persistence and full analysis."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models import (
    FamilyProfile,
    FoodBrand,
    FoodCategory,
    LaboratoryReport,
    Manufacturer,
    NutritionFacts,
    Product,
    ProductBarcode,
    ProductImage,
    ProductIngredient,
    ProductRecall,
    ProductScore,
    ProductWarning,
    ScoringMethodology,
)
from app.services import allergens as allergen_svc
from app.services.barcode import Barcode, parse_barcode
from app.services.compatibility import ProductFacts, ProfileSpec, evaluate
from app.services.ingredient_parser import parse_ingredients
from app.services.knowledge import get_kb
from app.services.nutrition import NUTRIENT_FIELDS, NutritionInput
from app.services.providers import openfoodfacts as off
from app.services.providers import usda
from app.services.providers.base import ProviderError, ProviderProduct
from app.services.scoring.default_methodology import DEFAULT_METHODOLOGY
from app.services.scoring.engine import ScoringInputs, _added_sugar_basis, compute_score
from app.services.text import normalize_term

log = logging.getLogger(__name__)
ANALYSIS_VERSION = "ing-1"


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


# ------------------------------------------------------------------------------ methodology


def active_methodology(db: Session) -> dict:
    row = db.scalar(select(ScoringMethodology).where(ScoringMethodology.is_active.is_(True)))
    return row.config if row else DEFAULT_METHODOLOGY


# ------------------------------------------------------------------------------ persistence


def _get_or_create_brand(db: Session, name: str | None, manufacturer: str | None) -> FoodBrand | None:
    if not name:
        return None
    key = normalize_term(name)[:200]
    brand = db.scalar(select(FoodBrand).where(FoodBrand.normalized_name == key))
    if brand:
        return brand
    man = None
    if manufacturer:
        mkey = normalize_term(manufacturer)[:200]
        man = db.scalar(select(Manufacturer).where(Manufacturer.normalized_name == mkey))
        if man is None:
            man = Manufacturer(name=manufacturer[:200], normalized_name=mkey)
            db.add(man)
            db.flush()
    brand = FoodBrand(name=name[:200], normalized_name=key, manufacturer_id=man.id if man else None)
    db.add(brand)
    db.flush()
    return brand


def _get_or_create_category(db: Session, tags: list[str], label: str | None, is_bev: bool) -> FoodCategory | None:
    code = tags[-1] if tags else (f"usda:{normalize_term(label)}" if label else None)
    if not code:
        return None
    cat = db.scalar(select(FoodCategory).where(FoodCategory.code == code))
    if cat is None:
        name = label or code.split(":", 1)[-1].replace("-", " ").title()
        cat = FoodCategory(code=code[:160], name=name[:160], is_beverage=is_bev)
        db.add(cat)
        db.flush()
    return cat


def _completeness(p: Product) -> float:
    checks = [
        bool(p.name),
        bool(p.brand_text),
        bool(p.ingredients_text),
        p.nutrition_per_100() is not None,
        bool(p.image_url),
        bool(p.category_id),
        p.nova_group is not None,
    ]
    return round(sum(checks) / len(checks), 2)


def _set_nutrition(
    db: Session, product: Product, n: NutritionInput | None, source: str, confidence: float = 1.0
) -> None:
    if n is None:
        return
    basis = "100ml" if n.is_beverage else "100g"
    existing = {nf.basis: nf for nf in product.nutrition}
    row = existing.get(basis) or existing.get("100g" if basis == "100ml" else "100ml")
    if row is None:
        row = NutritionFacts(product_id=product.id, basis=basis, source=source)
        product.nutrition.append(row)
    row.basis = basis
    for f in NUTRIENT_FIELDS:
        setattr(row, f, getattr(n, f))
    row.fruits_veg_nuts_pct = n.fruits_veg_nuts_pct
    row.serving_size_g = n.serving_size_g
    if n.extra.get("micros"):
        row.extra = {**(row.extra or {}), "micros": n.extra["micros"]}
    row.source = source
    row.confidence = confidence


def nutrition_input(product: Product) -> NutritionInput | None:
    row = product.nutrition_per_100()
    if row is None:
        return None
    return NutritionInput(
        **{f: getattr(row, f) for f in NUTRIENT_FIELDS},
        fruits_veg_nuts_pct=row.fruits_veg_nuts_pct,
        serving_size_g=row.serving_size_g,
        is_beverage=product.is_beverage or row.basis == "100ml",
        extra=dict(row.extra or {}),
    )


def _store_ingredients(db: Session, product: Product) -> None:
    product.ingredients.clear()
    db.flush()
    if not product.ingredients_text:
        return
    kb = get_kb(db)
    st = parse_ingredients(product.ingredients_text)
    for pos, p in enumerate(st.flat()):
        m = kb.match(p)
        product.ingredients.append(
            ProductIngredient(
                product_id=product.id,
                position=pos,
                depth=p.depth,
                raw_text=p.text[:300],
                ingredient_slug=m.entry.slug if m.entry else None,
                percent=p.percent,
                match_confidence=m.confidence,
                analysis_version=ANALYSIS_VERSION,
            )
        )


def merge_providers(primary: ProviderProduct | None, secondary: ProviderProduct | None) -> tuple[ProviderProduct, dict]:
    """Fill gaps in the primary record from the secondary. Returns (merged, field provenance)."""
    base = primary or secondary
    assert base is not None
    provenance: dict[str, str] = {}
    fields = (
        "name",
        "brand",
        "manufacturer",
        "ingredients_text",
        "nutrition",
        "serving_size",
        "image_url",
        "category_label",
        "quantity",
    )
    for f in fields:
        if getattr(base, f):
            provenance[f] = base.source
    if primary and secondary:
        for f in fields:
            if not getattr(primary, f) and getattr(secondary, f):
                setattr(primary, f, getattr(secondary, f))
                provenance[f] = secondary.source
        if primary.nutrition and secondary.nutrition:
            # US labels report added sugars; OFF often doesn't
            if primary.nutrition.added_sugars is None and secondary.nutrition.added_sugars is not None:
                primary.nutrition.added_sugars = secondary.nutrition.added_sugars
                provenance["added_sugars"] = secondary.source
        primary.is_beverage = primary.is_beverage or secondary.is_beverage
        if primary.nutrition:
            primary.nutrition.is_beverage = primary.is_beverage
    return base, provenance


def upsert_product(db: Session, pp: ProviderProduct, bc: Barcode | None, provenance: dict | None = None) -> Product:
    product = None
    if bc:
        pb = db.scalar(select(ProductBarcode).where(ProductBarcode.gtin14 == bc.gtin14))
        product = pb.product if pb else None
    if product is None:
        product = db.scalar(select(Product).where(Product.source == pp.source, Product.source_id == pp.source_id))
    created = product is None
    if created:
        product = Product(source=pp.source, source_id=pp.source_id)
        db.add(product)
        db.flush()
    elif product.source in ("community", "admin") and product.verified_at:
        # Verified curated data wins; only refresh provider metadata.
        product.last_synced_at = _now()
        return product

    brand = _get_or_create_brand(db, pp.brand, pp.manufacturer)
    category = _get_or_create_category(db, pp.categories_tags, pp.category_label, pp.is_beverage)
    product.name = (pp.name or "")[:300] or None
    product.brand_id = brand.id if brand else None
    product.brand_text = pp.brand
    product.category_id = category.id if category else None
    product.categories_tags = pp.categories_tags
    product.quantity = pp.quantity
    product.serving_size = pp.serving_size
    product.countries_tags = pp.countries_tags
    product.labels_tags = pp.labels_tags
    product.packaging_text = pp.packaging_text
    product.packaging_tags = pp.packaging_tags
    text_changed = product.ingredients_text != pp.ingredients_text
    product.ingredients_text = pp.ingredients_text
    product.ingredients_lang = pp.ingredients_lang
    product.allergens_tags = pp.allergens_tags
    product.traces_tags = pp.traces_tags
    product.additives_tags = pp.additives_tags
    product.ingredients_analysis_tags = pp.analysis_tags
    product.nova_group = pp.nova_group
    product.nova_source = "off" if pp.nova_group else None
    product.nutriscore_grade = pp.nutriscore_grade
    product.image_url = pp.image_url
    product.is_beverage = pp.is_beverage
    product.source_url = pp.url
    product.source_license = pp.license
    product.raw_data = {"provider": pp.raw, "provenance": provenance or {}, "attribution": pp.attribution}
    product.last_synced_at = _now()
    product.search_text = normalize_term(
        " ".join(filter(None, [pp.name, pp.brand, pp.category_label, (category.name if category else None)]))
    )

    if bc and not any(b.gtin14 == bc.gtin14 for b in product.barcodes):
        product.barcodes.append(ProductBarcode(gtin14=bc.gtin14, barcode=bc.raw, format=bc.format))
    _set_nutrition(db, product, pp.nutrition, (provenance or {}).get("nutrition", pp.source))
    existing_imgs = {(i.kind, i.url) for i in product.images}
    for kind, url in pp.images.items():
        if (kind, url) not in existing_imgs:
            product.images.append(ProductImage(product_id=product.id, kind=kind, url=url, source=pp.source))
    if created or text_changed or not product.ingredients:
        _store_ingredients(db, product)
    product.completeness = _completeness(product)
    db.flush()
    return product


# ------------------------------------------------------------------------------ lookup


class LookupResult:
    def __init__(
        self,
        product: Product | None,
        status: str,
        barcode: Barcode | None,
        sources: list[str],
        stale: bool = False,
        message: str | None = None,
    ):
        self.product, self.status, self.barcode, self.sources = product, status, barcode, sources
        self.stale, self.message = stale, message


def _load(db: Session, product_id: str) -> Product:
    return db.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.barcodes),
            selectinload(Product.nutrition),
            selectinload(Product.images),
            selectinload(Product.ingredients),
        )
    )


def lookup_barcode(db: Session, raw: str, force_refresh: bool = False) -> LookupResult:
    bc = parse_barcode(raw)  # raises InvalidBarcode
    s = get_settings()
    pb = db.scalar(select(ProductBarcode).where(ProductBarcode.gtin14 == bc.gtin14))
    cached = pb.product if pb else None
    if cached and cached.status != "active":
        cached = None
    if cached and not force_refresh:
        fresh = _aware(cached.last_synced_at) and _aware(cached.last_synced_at) > _now() - timedelta(
            hours=s.product_cache_hours
        )
        if fresh or cached.source in ("community", "admin"):
            return LookupResult(_load(db, cached.id), "found", bc, ["cache"])

    sources: list[str] = []
    primary = secondary = None
    errors: list[str] = []
    try:
        sources.append("open_food_facts")
        primary = off.get_product(bc.lookup_code)
    except ProviderError as e:
        errors.append(f"Open Food Facts: {e}")
        log.warning("OFF lookup failed for %s: %s", bc.raw, e)
    needs_us = (
        primary is None
        or primary.nutrition is None
        or not primary.ingredients_text
        or (
            primary.nutrition
            and primary.nutrition.added_sugars is None
            and "en:united-states" in primary.countries_tags
        )
    )
    if needs_us and usda.enabled():
        try:
            sources.append("usda_fdc")
            secondary = usda.find_by_gtin(bc.raw if bc.format != "UPCE" else bc.gtin14[2:])
        except ProviderError as e:
            errors.append(f"USDA FDC: {e}")
            log.warning("FDC lookup failed for %s: %s", bc.raw, e)

    if primary is None and secondary is None:
        if cached:
            return LookupResult(
                _load(db, cached.id),
                "found",
                bc,
                sources,
                stale=bool(errors),
                message="Showing saved data; live sources are unavailable." if errors else None,
            )
        if errors and len(errors) == len(sources):
            return LookupResult(None, "provider_unavailable", bc, sources, message="; ".join(errors))
        return LookupResult(None, "not_found", bc, sources)

    merged, provenance = merge_providers(primary, secondary)
    product = upsert_product(db, merged, bc, provenance)
    db.commit()
    return LookupResult(_load(db, product.id), "found", bc, sources)


def search_local(db: Session, q: str, limit: int = 20, offset: int = 0) -> list[Product]:
    qn = normalize_term(q)
    if not qn:
        return []
    stmt = select(Product).where(Product.status == "active")
    if qn.isdigit() and len(qn) >= 8:
        try:
            bc = parse_barcode(qn)
            stmt = stmt.join(ProductBarcode).where(ProductBarcode.gtin14 == bc.gtin14)
            return list(db.scalars(stmt.limit(limit)).all())
        except ValueError:
            pass
    if db.get_bind().dialect.name == "postgresql":
        from sqlalchemy import func

        tsq = func.plainto_tsquery("simple", qn)
        vec = func.to_tsvector("simple", func.coalesce(Product.search_text, ""))
        stmt = stmt.where(or_(vec.op("@@")(tsq), Product.search_text.ilike(f"%{qn}%"))).order_by(
            func.ts_rank(vec, tsq).desc()
        )
    else:
        for word in qn.split()[:6]:
            stmt = stmt.where(Product.search_text.ilike(f"%{word}%"))
        stmt = stmt.order_by(Product.completeness.desc())
    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


# ------------------------------------------------------------------------------ analysis


def _profile_spec(fp: FamilyProfile) -> ProfileSpec:
    return ProfileSpec(
        id=fp.id,
        name=fp.name,
        allergens=[
            {"code": a.allergen_code, "severity": a.severity, "avoid_traces": a.avoid_traces} for a in fp.allergens
        ],
        diets=[d.code for d in fp.dietary_preferences],
        avoid_terms=[r.term for r in fp.avoid_rules],
    )


def analyze_text(
    ingredients_text: str | None,
    nutrition: NutritionInput | None,
    *,
    nova_group: int | None = None,
    nova_source: str | None = None,
    allergens_tags=None,
    traces_tags=None,
    labels_tags=None,
    analysis_tags=None,
    is_beverage: bool = False,
    recalls=None,
    lab_reports=None,
    cfg: dict,
    profiles: list[ProfileSpec] | None = None,
    region: str = "US",
    kb=None,
) -> dict:
    kb = kb or get_kb()
    st = parse_ingredients(ingredients_text) if ingredients_text else None
    matches = [kb.match(p) for p in st.flat()] if st else []
    found = allergen_svc.detect_allergens(st, matches, allergens_tags, traces_tags)
    if nutrition is not None:
        nutrition.is_beverage = nutrition.is_beverage or is_beverage
    inputs = ScoringInputs(
        nutrition=nutrition,
        statement=st,
        matches=matches,
        nova_group=nova_group,
        nova_source=nova_source,
        allergens=found,
        labels_tags=labels_tags or [],
        active_recalls=recalls or [],
        lab_reports=lab_reports or [],
        is_beverage=is_beverage,
    )
    score = compute_score(inputs, cfg)
    ingredients = []
    for m in matches:
        e = m.entry
        ingredients.append(
            {
                "text": m.parsed.text,
                "normalized": m.parsed.normalized,
                "depth": m.parsed.depth,
                "percent": m.parsed.percent,
                "e_numbers": m.parsed.e_numbers,
                "is_group": m.method == "class",
                "match_method": m.method,
                "match_confidence": m.confidence,
                "ingredient": None
                if not e
                else {
                    "slug": e.slug,
                    "name": e.display_name(region),
                    "category": e.category,
                    "function": e.function,
                    "concern_level": e.concern_level,
                    "e_number": e.e_number,
                    "flags": e.flags,
                    "summary": e.concern_summary,
                    "verification_status": e.verification_status,
                },
            }
        )
    facts = ProductFacts(
        matches=matches,
        allergens=found,
        nutrition=nutrition,
        has_ingredients=bool(st and st.ingredients),
        labels_tags=labels_tags or [],
        analysis_tags=analysis_tags or [],
        ingredient_names=[m.parsed.text for m in matches],
        is_beverage=is_beverage,
        added_sugar_basis=_added_sugar_basis(inputs)[0] if nutrition else None,
    )
    compat = [evaluate(p, facts) for p in (profiles or [])]
    return {
        "score": score,
        "ingredients": ingredients,
        "ingredients_parse": None
        if not st
        else {
            "confidence": st.confidence,
            "precautionary_statement": st.precautionary_text,
            "contains_statement": st.contains_statement,
        },
        "allergens": allergen_svc.summary(found, region),
        "compatibility": compat,
    }


def analyze_product(
    db: Session, product: Product, profiles: list[FamilyProfile] | None = None, region: str = "US"
) -> dict:
    cfg = active_methodology(db)
    recalls = db.scalars(
        select(ProductRecall).where(
            ProductRecall.verified.is_(True),
            ProductRecall.status == "active",
            or_(
                ProductRecall.product_id == product.id,
                ProductRecall.barcode.in_([b.barcode for b in product.barcodes] or ["-"]),
            ),
        )
    ).all()
    labs = db.scalars(
        select(LaboratoryReport).where(LaboratoryReport.product_id == product.id, LaboratoryReport.verified.is_(True))
    ).all()
    recall_dicts = [
        {
            "id": r.id,
            "title": r.title,
            "authority": r.authority,
            "reason": r.reason,
            "url": r.url,
            "recall_date": r.recall_date.isoformat() if r.recall_date else None,
            "jurisdiction": r.jurisdiction,
        }
        for r in recalls
    ]
    lab_dicts = [
        {
            "id": r.id,
            "analyte": r.analyte,
            "value": r.value,
            "unit": r.unit,
            "threshold": r.threshold,
            "threshold_jurisdiction": r.threshold_jurisdiction,
            "exceeds_threshold": r.exceeds_threshold,
            "lab_name": r.lab_name,
            "method": r.method,
            "batch": r.batch,
            "tested_on": r.tested_on.isoformat() if r.tested_on else None,
        }
        for r in labs
    ]
    nutrition = nutrition_input(product)
    result = analyze_text(
        product.ingredients_text,
        nutrition,
        nova_group=product.nova_group,
        nova_source=product.nova_source,
        allergens_tags=product.allergens_tags,
        traces_tags=product.traces_tags,
        labels_tags=product.labels_tags,
        analysis_tags=product.ingredients_analysis_tags,
        is_beverage=product.is_beverage,
        recalls=recall_dicts,
        lab_reports=lab_dicts,
        cfg=cfg,
        profiles=[_profile_spec(p) for p in profiles or []],
        region=region,
        kb=get_kb(db),
    )
    sc = result["score"]
    stored = db.scalar(
        select(ProductScore).where(
            ProductScore.product_id == product.id,
            ProductScore.methodology_version == sc["methodology_version"],
            ProductScore.inputs_hash == sc["inputs_hash"],
        )
    )
    if stored is None:
        db.add(
            ProductScore(
                product_id=product.id,
                methodology_version=sc["methodology_version"],
                inputs_hash=sc["inputs_hash"],
                overall=sc["overall"],
                grade=sc["grade"],
                confidence=sc["confidence"],
                coverage=sc["coverage"],
                result={k: v for k, v in sc.items() if k != "highlights"},
            )
        )
        _refresh_warnings(db, product, sc)
        db.commit()
    result["recalls"] = recall_dicts
    result["lab_reports"] = lab_dicts
    result["contaminant_testing"] = {
        "has_product_specific_data": bool(lab_dicts),
        "message": "Verified laboratory results for this product are shown below."
        if lab_dicts
        else "No product-specific laboratory testing (heavy metals, pesticides, microplastics) is on file. We don't "
        "infer contamination from general research.",
    }
    return result


def _refresh_warnings(db: Session, product: Product, score: dict) -> None:
    db.query(ProductWarning).filter(ProductWarning.product_id == product.id).delete()
    for comp in score["components"].values():
        for a in comp["adjustments"]:
            if a["points"] < 0:
                sev = "concern" if a["points"] <= -20 else "caution" if a["points"] <= -6 else "info"
                db.add(
                    ProductWarning(
                        product_id=product.id,
                        code=a["code"][:80],
                        severity=sev,
                        title=a["reason"][:200],
                        explanation=a["reason"],
                        evidence_type=a["evidence_type"],
                        source_keys=a.get("source_keys", []),
                        methodology_version=score["methodology_version"],
                    )
                )


def product_summary(db: Session, product: Product) -> dict:
    """Light card for lists: uses latest stored score or computes one."""
    cfg = active_methodology(db)
    sc = db.scalar(
        select(ProductScore)
        .where(ProductScore.product_id == product.id, ProductScore.methodology_version == cfg["version"])
        .order_by(ProductScore.computed_at.desc())
    )
    if sc is None:
        res = analyze_product(db, product)
        overall, grade, color = res["score"]["overall"], res["score"]["grade"], res["score"]["color"]
    else:
        overall, grade = sc.overall, sc.grade
        color = sc.result.get("color", "grey")
    return {
        "id": product.id,
        "name": product.name,
        "brand": product.brand_text,
        "image_url": product.image_url,
        "barcode": product.barcodes[0].barcode if product.barcodes else None,
        "score": overall,
        "grade": grade,
        "color": color,
        "nova_group": product.nova_group,
        "category": product.categories_tags[-1] if product.categories_tags else None,
        "source": product.source,
    }
