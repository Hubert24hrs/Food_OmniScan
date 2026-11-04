"""Admin & moderation API. Every route checks the role server-side; every mutation is audit-logged."""

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.deps import DB, Admin, Moderator, request_ip
from app.models import (
    AdminAuditLog,
    AdminUser,
    AIUsageRecord,
    CommunitySubmission,
    FoodScan,
    Ingredient,
    LaboratoryReport,
    Notification,
    Product,
    ProductBarcode,
    ProductRecall,
    ReviewReport,
    ScanHistory,
    ScientificSource,
    ScoringMethodology,
    ScoringRule,
    Subscription,
    SubscriptionEntitlement,
    User,
    UserReview,
)
from app.services import product_service as ps
from app.services.audit import audit, snapshot
from app.services.barcode import parse_barcode
from app.services.knowledge import invalidate_kb
from app.services.nutrition import NutritionInput
from app.services.providers.base import ProviderProduct
from app.services.scoring.default_methodology import flatten_rules
from app.services.scoring.engine import ScoringInputs, compute_score

router = APIRouter(prefix="/admin", tags=["admin"])


def _now():
    return datetime.now(UTC)


# ------------------------------------------------------------------ dashboard


@router.get("/stats")
def stats(db: DB, _: Moderator):
    since = _now() - timedelta(days=30)
    scans_30 = db.scalar(select(func.count()).select_from(FoodScan).where(FoodScan.created_at >= since)) or 0
    by_status = dict(
        db.execute(
            select(FoodScan.status, func.count()).where(FoodScan.created_at >= since).group_by(FoodScan.status)
        ).all()
    )
    return {
        "users": db.scalar(select(func.count()).select_from(User)),
        "active_users_30d": db.scalar(
            select(func.count(func.distinct(FoodScan.user_id))).where(FoodScan.created_at >= since)
        ),
        "products": db.scalar(select(func.count()).select_from(Product)),
        "products_by_source": dict(db.execute(select(Product.source, func.count()).group_by(Product.source)).all()),
        "pending_submissions": db.scalar(
            select(func.count()).select_from(CommunitySubmission).where(CommunitySubmission.status == "pending")
        ),
        "scans_30d": scans_30,
        "scan_status_30d": by_status,
        "scan_success_rate_30d": round(by_status.get("found", 0) / scans_30, 3) if scans_30 else None,
        "ingredients": db.scalar(select(func.count()).select_from(Ingredient)),
        "ingredients_pending_verification": db.scalar(
            select(func.count()).select_from(Ingredient).where(Ingredient.verification_status != "verified")
        ),
        "subscriptions_by_tier": dict(
            db.execute(
                select(Subscription.tier, func.count())
                .where(Subscription.status == "active")
                .group_by(Subscription.tier)
            ).all()
        ),
        "ai_cost_30d_usd": round(
            db.scalar(
                select(func.coalesce(func.sum(AIUsageRecord.est_cost_usd), 0.0)).where(
                    AIUsageRecord.created_at >= since
                )
            )
            or 0.0,
            4,
        ),
        "active_methodology": ps.active_methodology(db)["version"],
    }


@router.get("/scans/failed")
def failed_scans(db: DB, _: Moderator, limit: int = Query(100, le=500)):
    rows = db.execute(
        select(FoodScan.barcode, FoodScan.status, func.count().label("n"), func.max(FoodScan.created_at))
        .where(FoodScan.status.in_(["not_found", "invalid", "error"]))
        .group_by(FoodScan.barcode, FoodScan.status)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    return [{"barcode": b, "status": s, "count": n, "last_seen": t.isoformat() if t else None} for b, s, n, t in rows]


# ------------------------------------------------------------------ submissions


@router.get("/submissions")
def list_submissions(db: DB, _: Moderator, status: str = Query("pending"), limit: int = Query(50, le=200)):
    rows = db.scalars(
        select(CommunitySubmission)
        .where(CommunitySubmission.status == status)
        .order_by(CommunitySubmission.created_at)
        .limit(limit)
    ).all()
    return [
        {
            "id": s.id,
            "kind": s.kind,
            "barcode": s.barcode,
            "product_id": s.product_id,
            "payload": s.payload,
            "images": [f"/api/v1/uploads/{i}" for i in s.images],
            "ocr_confidence": s.ocr_confidence,
            "status": s.status,
            "user_id": s.user_id,
            "created_at": s.created_at.isoformat(),
        }
        for s in rows
    ]


class ReviewIn(BaseModel):
    action: str = Field(pattern="^(approve|reject|needs_info)$")
    notes: str | None = Field(default=None, max_length=2000)
    edits: dict | None = None  # moderator corrections applied on approval


@router.post("/submissions/{sid}/review")
def review_submission(sid: str, body: ReviewIn, db: DB, mod: Moderator, request: Request):
    s = db.get(CommunitySubmission, sid)
    if not s:
        raise HTTPException(404, "Submission not found")
    if s.status not in ("pending", "needs_info"):
        raise HTTPException(409, f"Submission already {s.status}")
    before = snapshot(s, ["status", "review_notes"])
    s.reviewer_id, s.review_notes, s.reviewed_at = mod.id, body.notes, _now()
    if body.action != "approve":
        s.status = "rejected" if body.action == "reject" else "needs_info"
    else:
        payload = {**s.payload, **(body.edits or {})}
        if s.kind == "report":
            s.status = "approved"
        elif s.kind == "correction" and s.product_id and not payload.get("name"):
            s.status = "approved"  # free-text report acknowledged; edits are applied via product PATCH
        else:
            bc = parse_barcode(payload.get("barcode") or s.barcode)
            nut = payload.get("nutrition")
            n = (
                NutritionInput(
                    **{k: v for k, v in (nut or {}).items() if k in NutritionInput.__dataclass_fields__},
                    is_beverage=bool(payload.get("is_beverage")),
                )
                if nut
                else None
            )
            pp = ProviderProduct(
                source="community",
                source_id=f"sub:{s.id}",
                barcode=bc.raw,
                name=payload.get("name"),
                brand=payload.get("brand"),
                category_label=payload.get("category"),
                quantity=payload.get("quantity"),
                serving_size=payload.get("serving_size"),
                ingredients_text=payload.get("ingredients_text"),
                ingredients_lang="en",
                nutrition=n if n and n.core_present() else None,
                countries_tags=[f"en:{c.lower()}" for c in payload.get("countries", [])],
                labels_tags=[f"en:{x}" for x in payload.get("labels", [])],
                is_beverage=bool(payload.get("is_beverage")),
                license="Contributed by Food omniScan users",
                attribution="Community contribution, moderator-verified",
                images={
                    ("front" if i == 0 else f"photo{i}"): f"/api/v1/uploads/{img}" for i, img in enumerate(s.images)
                },
                image_url=f"/api/v1/uploads/{s.images[0]}" if s.images else None,
            )
            # Approved community data replaces a stale provider record for this barcode.
            existing = db.scalar(select(ProductBarcode).where(ProductBarcode.gtin14 == bc.gtin14))
            if existing:
                p = existing.product
                p.source, p.source_id, p.verified_at = "community", pp.source_id, None
            product = ps.upsert_product(db, pp, bc, {"all": "community"})
            product.source, product.verified_at, product.verified_by = "community", _now(), mod.id
            product.nafdac_number = payload.get("nafdac_number")
            s.product_id, s.status = product.id, "approved"
        db.add(
            Notification(
                user_id=s.user_id,
                kind="submission",
                title="Your product submission was approved",
                body=f"Thanks for adding {s.payload.get('name') or s.barcode}!",
                data={"submission_id": s.id, "product_id": s.product_id},
            )
        )
    audit(
        db,
        mod,
        f"submission.{body.action}",
        "community_submission",
        s.id,
        before=before,
        after=snapshot(s, ["status", "review_notes", "product_id"]),
        ip=request_ip(request),
    )
    db.commit()
    return {"id": s.id, "status": s.status, "product_id": s.product_id}


# ------------------------------------------------------------------ products


@router.get("/products")
def admin_products(
    db: DB,
    _: Moderator,
    q: str | None = None,
    source: str | None = None,
    status: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    stmt = select(Product)
    if q:
        stmt = stmt.where(Product.search_text.ilike(f"%{q.lower()}%"))
    if source:
        stmt = stmt.where(Product.source == source)
    if status:
        stmt = stmt.where(Product.status == status)
    rows = db.scalars(stmt.order_by(Product.updated_at.desc()).offset(offset).limit(limit)).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "brand": p.brand_text,
            "source": p.source,
            "status": p.status,
            "completeness": p.completeness,
            "barcodes": [b.barcode for b in p.barcodes],
            "verified_at": p.verified_at.isoformat() if p.verified_at else None,
            "last_synced_at": p.last_synced_at.isoformat() if p.last_synced_at else None,
        }
        for p in rows
    ]


class ProductPatch(BaseModel):
    name: str | None = Field(default=None, max_length=300)
    brand_text: str | None = Field(default=None, max_length=300)
    ingredients_text: str | None = Field(default=None, max_length=10000)
    nova_group: int | None = Field(default=None, ge=1, le=4)
    is_beverage: bool | None = None
    status: str | None = Field(default=None, pattern="^(active|hidden)$")
    nafdac_number: str | None = Field(default=None, max_length=40)
    verify: bool = False
    reason: str = Field(min_length=3, max_length=500)


PRODUCT_FIELDS = [
    "name",
    "brand_text",
    "ingredients_text",
    "nova_group",
    "nova_source",
    "is_beverage",
    "status",
    "nafdac_number",
    "verified_at",
]


@router.patch("/products/{pid}")
def patch_product(pid: str, body: ProductPatch, db: DB, mod: Moderator, request: Request):
    p = db.get(Product, pid)
    if not p:
        raise HTTPException(404, "Product not found")
    before = snapshot(p, PRODUCT_FIELDS)
    data = body.model_dump(exclude_unset=True, exclude={"verify", "reason"})
    for k, v in data.items():
        setattr(p, k, v)
    if "nova_group" in data:
        p.nova_source = "admin"
    if "ingredients_text" in data:
        ps._store_ingredients(db, p)
    if body.verify:
        p.verified_at, p.verified_by = _now(), mod.id
        if p.source == "off":
            p.source = "admin"  # stop provider refresh from overwriting verified edits
    audit(
        db,
        mod,
        "product.update",
        "product",
        p.id,
        before=before,
        after=snapshot(p, PRODUCT_FIELDS),
        ip=request_ip(request),
        note=body.reason,
    )
    db.commit()
    return {"id": p.id, "status": p.status}


# ------------------------------------------------------------------ ingredients


class IngredientPatch(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    us_name: str | None = Field(default=None, max_length=200)
    function: str | None = Field(default=None, max_length=300)
    plain_language: str | None = Field(default=None, max_length=4000)
    concern_level: str | None = Field(default=None, pattern="^(beneficial|neutral|caution|concern|unknown)$")
    concern_summary: str | None = Field(default=None, max_length=4000)
    regulatory_notes: list[dict] | None = None
    source_keys: list[str] | None = None
    flags: list[str] | None = None
    vegan: str | None = Field(default=None, pattern="^(yes|no|maybe)$")
    vegetarian: str | None = Field(default=None, pattern="^(yes|no|maybe)$")
    halal_concern: str | None = Field(default=None, pattern="^(yes|no|maybe)$")
    verify: bool = False
    reason: str = Field(min_length=3, max_length=500)


ING_FIELDS = [
    "name",
    "us_name",
    "function",
    "plain_language",
    "concern_level",
    "concern_summary",
    "regulatory_notes",
    "source_keys",
    "flags",
    "vegan",
    "vegetarian",
    "halal_concern",
    "verification_status",
]


@router.patch("/ingredients/{slug}")
def patch_ingredient(slug: str, body: IngredientPatch, db: DB, admin: Admin, request: Request):
    i = db.scalar(select(Ingredient).where(Ingredient.slug == slug))
    if not i:
        raise HTTPException(404, "Ingredient not found")
    before = snapshot(i, ING_FIELDS)
    data = body.model_dump(exclude_unset=True, exclude={"verify", "reason"})
    if "source_keys" in data:
        known = {
            k
            for (k,) in db.execute(
                select(ScientificSource.key).where(ScientificSource.key.in_(data["source_keys"]))
            ).all()
        }
        missing = set(data["source_keys"]) - known
        if missing:
            raise HTTPException(422, f"Unknown source keys: {sorted(missing)}")
    for k, v in data.items():
        setattr(i, k, v)
    if body.verify:
        i.verification_status, i.verified_by, i.verified_at = "verified", admin.id, _now()
    audit(
        db,
        admin,
        "ingredient.update",
        "ingredient",
        slug,
        before=before,
        after=snapshot(i, ING_FIELDS),
        ip=request_ip(request),
        note=body.reason,
    )
    db.commit()
    invalidate_kb()
    return {"slug": slug, "verification_status": i.verification_status}


# ------------------------------------------------------------------ scoring methodology


@router.get("/methodologies")
def methodologies(db: DB, _: Moderator):
    rows = db.scalars(select(ScoringMethodology).order_by(ScoringMethodology.created_at.desc())).all()
    return [
        {
            "id": m.id,
            "version": m.version,
            "name": m.name,
            "is_active": m.is_active,
            "notes": m.notes,
            "published_at": m.published_at.isoformat() if m.published_at else None,
            "config": m.config,
        }
        for m in rows
    ]


class MethodologyIn(BaseModel):
    version: str = Field(pattern=r"^[0-9]{4}\.[0-9]{1,2}-[a-z]{2,4}\.[0-9]+$")
    name: str = Field(max_length=120)
    config: dict
    notes: str = Field(min_length=3, max_length=4000)
    activate: bool = False


@router.post("/methodologies", status_code=201)
def publish_methodology(body: MethodologyIn, db: DB, admin: Admin, request: Request):
    """Publish a new immutable methodology version. Validated by dry-running the engine."""
    if db.scalar(select(ScoringMethodology).where(ScoringMethodology.version == body.version)):
        raise HTTPException(409, "Version already exists; versions are immutable")
    cfg = {**body.config, "version": body.version, "name": body.name}
    try:
        w = cfg["weights"]
        if set(w) != {"nutrition", "ingredients", "processing", "dietary_suitability", "product_concerns"}:
            raise ValueError("weights must cover all five components")
        if abs(sum(w.values()) - 100) > 1e-6:
            raise ValueError("weights must sum to 100")
        compute_score(
            ScoringInputs(
                nutrition=NutritionInput(
                    energy_kcal=100, fat=1, saturated_fat=1, carbohydrates=10, sugars=5, protein=3, salt=0.1
                )
            ),
            cfg,
        )
    except (KeyError, TypeError, ValueError, StopIteration) as e:
        raise HTTPException(422, f"Invalid methodology config: {e}")
    m = ScoringMethodology(
        version=body.version,
        name=body.name,
        config=cfg,
        notes=body.notes,
        created_by=admin.id,
        published_at=_now(),
        is_active=False,
    )
    db.add(m)
    db.flush()
    for r in flatten_rules(cfg):
        db.add(ScoringRule(methodology_id=m.id, **r))
    audit(
        db,
        admin,
        "methodology.publish",
        "scoring_methodology",
        m.version,
        after={"version": m.version},
        ip=request_ip(request),
        note=body.notes,
    )
    if body.activate:
        _activate(db, m, admin, request)
    db.commit()
    return {"id": m.id, "version": m.version, "is_active": m.is_active}


def _activate(db, m: ScoringMethodology, admin: User, request: Request) -> None:
    prev = db.scalar(select(ScoringMethodology).where(ScoringMethodology.is_active.is_(True)))
    if prev:
        prev.is_active = False
    m.is_active = True
    audit(
        db,
        admin,
        "methodology.activate",
        "scoring_methodology",
        m.version,
        before={"active": prev.version if prev else None},
        after={"active": m.version},
        ip=request_ip(request),
    )


@router.post("/methodologies/{version}/activate")
def activate_methodology(version: str, db: DB, admin: Admin, request: Request):
    m = db.scalar(select(ScoringMethodology).where(ScoringMethodology.version == version))
    if not m:
        raise HTTPException(404, "Version not found")
    _activate(db, m, admin, request)
    db.commit()
    return {"active": m.version}


# ------------------------------------------------------------------ research: sources, lab reports, recalls


class SourceIn(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_]{3,80}$")
    title: str = Field(max_length=500)
    authors: str | None = Field(default=None, max_length=500)
    publisher: str | None = Field(default=None, max_length=200)
    year: int | None = Field(default=None, ge=1900, le=2100)
    url: str | None = Field(default=None, max_length=500, pattern=r"^https://")
    doi: str | None = Field(default=None, max_length=120)
    source_type: str = Field(pattern="^(regulation|guideline|peer_reviewed|agency_opinion|lab_report|database)$")
    evidence_quality: str = Field("moderate", pattern="^(high|moderate|low|very_low)$")
    summary: str | None = Field(default=None, max_length=4000)
    verified: bool = False


@router.post("/sources", status_code=201)
def create_source(body: SourceIn, db: DB, admin: Admin, request: Request):
    if db.scalar(select(ScientificSource).where(ScientificSource.key == body.key)):
        raise HTTPException(409, "Source key exists")
    s = ScientificSource(**body.model_dump(), verified_by=admin.id if body.verified else None)
    db.add(s)
    audit(db, admin, "source.create", "scientific_source", body.key, after=body.model_dump(), ip=request_ip(request))
    db.commit()
    return {"key": s.key}


@router.post("/sources/{key}/verify")
def verify_source(key: str, db: DB, admin: Admin, request: Request):
    s = db.scalar(select(ScientificSource).where(ScientificSource.key == key))
    if not s:
        raise HTTPException(404, "Source not found")
    s.verified, s.verified_by = True, admin.id
    audit(db, admin, "source.verify", "scientific_source", key, ip=request_ip(request))
    db.commit()
    return {"key": key, "verified": True}


class LabIn(BaseModel):
    product_id: str
    lab_name: str = Field(max_length=200)
    method: str | None = Field(default=None, max_length=200)
    batch: str | None = Field(default=None, max_length=80)
    tested_on: date | None = None
    analyte: str = Field(max_length=60)
    value: float | None = None
    unit: str = Field(max_length=20)
    threshold: float | None = None
    threshold_jurisdiction: str | None = Field(default=None, max_length=60)
    threshold_reference: str | None = Field(default=None, max_length=300)
    source_key: str | None = None
    verified: bool = False


@router.post("/lab-reports", status_code=201)
def create_lab(body: LabIn, db: DB, admin: Admin, request: Request):
    if not db.get(Product, body.product_id):
        raise HTTPException(404, "Product not found")
    src = (
        db.scalar(select(ScientificSource).where(ScientificSource.key == body.source_key)) if body.source_key else None
    )
    exceeds = (body.value > body.threshold) if body.value is not None and body.threshold is not None else None
    r = LaboratoryReport(
        **body.model_dump(exclude={"source_key"}),
        exceeds_threshold=exceeds,
        source_id=src.id if src else None,
        verified_by=admin.id if body.verified else None,
    )
    db.add(r)
    db.flush()
    audit(
        db,
        admin,
        "lab_report.create",
        "laboratory_report",
        r.id,
        after={"analyte": r.analyte, "value": r.value, "verified": r.verified},
        ip=request_ip(request),
    )
    db.commit()
    return {"id": r.id, "exceeds_threshold": exceeds}


class RecallIn(BaseModel):
    title: str = Field(max_length=300)
    reason: str = Field(max_length=4000)
    hazard: str | None = Field(default=None, max_length=60)
    jurisdiction: str = Field(max_length=10)
    authority: str = Field(max_length=80)
    recall_date: date | None = None
    url: str | None = Field(default=None, max_length=500, pattern=r"^https://")
    barcode: str | None = None
    product_id: str | None = None
    verified: bool = True
    notify_users: bool = True


@router.post("/recalls", status_code=201)
def create_recall(body: RecallIn, db: DB, admin: Admin, request: Request):
    product_id = body.product_id
    barcode = None
    if body.barcode:
        bc = parse_barcode(body.barcode)
        barcode = bc.raw
        pb = db.scalar(select(ProductBarcode).where(ProductBarcode.gtin14 == bc.gtin14))
        product_id = product_id or (pb.product_id if pb else None)
    r = ProductRecall(
        **body.model_dump(exclude={"barcode", "product_id", "notify_users"}), barcode=barcode, product_id=product_id
    )
    db.add(r)
    db.flush()
    notified = 0
    if body.verified and body.notify_users and product_id:
        for (uid,) in db.execute(
            select(ScanHistory.user_id).where(ScanHistory.product_id == product_id).distinct()
        ).all():
            db.add(
                Notification(
                    user_id=uid,
                    kind="recall",
                    title=f"Recall: {r.title}",
                    body=f"{r.authority} ({r.jurisdiction}): {r.reason}",
                    data={"recall_id": r.id, "product_id": product_id, "url": r.url},
                )
            )
            notified += 1
        r.notified_at = _now()
    audit(
        db,
        admin,
        "recall.create",
        "product_recall",
        r.id,
        after={"title": r.title, "notified": notified},
        ip=request_ip(request),
    )
    db.commit()
    return {"id": r.id, "notified_users": notified}


# ------------------------------------------------------------------ users, entitlements, audit, AI usage


@router.get("/users")
def users(db: DB, _: Admin, q: str | None = None, limit: int = Query(50, le=200), offset: int = 0):
    stmt = select(User)
    if q:
        stmt = stmt.where(User.email.ilike(f"%{q.lower()}%"))
    rows = db.scalars(stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role,
            "is_active": u.is_active,
            "country": u.country,
            "created_at": u.created_at.isoformat(),
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        }
        for u in rows
    ]


class UserPatch(BaseModel):
    role: str | None = Field(default=None, pattern="^(user|contributor|moderator|admin)$")
    is_active: bool | None = None
    grant_tier: str | None = Field(default=None, pattern="^(free|plus|premium|family)$")
    grant_days: int | None = Field(default=None, ge=1, le=3650)
    reason: str = Field(min_length=3, max_length=500)


@router.patch("/users/{uid}")
def patch_user(uid: str, body: UserPatch, db: DB, admin: Admin, request: Request):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id and (body.role not in (None, "admin") or body.is_active is False):
        raise HTTPException(400, "You can't demote or disable yourself")
    before = snapshot(u, ["role", "is_active"])
    if body.role:
        u.role = body.role
        grant = db.scalar(select(AdminUser).where(AdminUser.user_id == u.id))
        if body.role in ("moderator", "admin"):
            if grant is None:
                db.add(AdminUser(user_id=u.id, role=body.role, granted_by=admin.id))
            else:
                grant.role, grant.granted_by, grant.granted_at = body.role, admin.id, _now()
        elif grant is not None:
            db.delete(grant)
    if body.is_active is not None:
        u.is_active = body.is_active
    if body.grant_tier:
        db.add(
            Subscription(
                user_id=u.id,
                tier=body.grant_tier,
                status="active",
                provider="manual",
                current_period_end=_now() + timedelta(days=body.grant_days or 30),
            )
        )
    audit(
        db,
        admin,
        "user.update",
        "user",
        u.id,
        before=before,
        after={**snapshot(u, ["role", "is_active"]), "grant_tier": body.grant_tier},
        ip=request_ip(request),
        note=body.reason,
    )
    db.commit()
    return {"id": u.id, "role": u.role, "is_active": u.is_active}


@router.get("/entitlements")
def get_entitlements(db: DB, _: Admin):
    return [
        {"tier": e.tier, "feature": e.feature, "monthly_limit": e.monthly_limit}
        for e in db.scalars(select(SubscriptionEntitlement).order_by(SubscriptionEntitlement.feature)).all()
    ]


class EntIn(BaseModel):
    tier: str = Field(pattern="^(free|plus|premium|family)$")
    feature: str = Field(max_length=40)
    monthly_limit: int | None = Field(default=None, ge=0)


@router.put("/entitlements")
def put_entitlement(body: EntIn, db: DB, admin: Admin, request: Request):
    e = db.scalar(
        select(SubscriptionEntitlement).where(
            SubscriptionEntitlement.tier == body.tier, SubscriptionEntitlement.feature == body.feature
        )
    )
    before = {"monthly_limit": e.monthly_limit} if e else None
    if e is None:
        e = SubscriptionEntitlement(tier=body.tier, feature=body.feature)
        db.add(e)
    e.monthly_limit = body.monthly_limit
    audit(
        db,
        admin,
        "entitlement.update",
        "subscription_entitlement",
        f"{body.tier}:{body.feature}",
        before=before,
        after={"monthly_limit": body.monthly_limit},
        ip=request_ip(request),
    )
    db.commit()
    return body


@router.get("/audit-logs")
def audit_logs(db: DB, _: Admin, limit: int = Query(100, le=500), action: str | None = None):
    stmt = select(AdminAuditLog)
    if action:
        stmt = stmt.where(AdminAuditLog.action.like(f"{action}%"))
    rows = db.scalars(stmt.order_by(AdminAuditLog.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": r.id,
            "actor_id": r.actor_id,
            "action": r.action,
            "entity": r.entity,
            "entity_id": r.entity_id,
            "before": r.before,
            "after": r.after,
            "note": r.note,
            "ip": r.ip,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/ai-usage")
def ai_usage(db: DB, _: Admin, days: int = Query(30, le=365)):
    since = _now() - timedelta(days=days)
    rows = db.execute(
        select(
            AIUsageRecord.feature,
            AIUsageRecord.status,
            func.count(),
            func.sum(AIUsageRecord.input_tokens),
            func.sum(AIUsageRecord.output_tokens),
            func.sum(AIUsageRecord.est_cost_usd),
        )
        .where(AIUsageRecord.created_at >= since)
        .group_by(AIUsageRecord.feature, AIUsageRecord.status)
    ).all()
    return [
        {
            "feature": f,
            "status": s,
            "calls": n,
            "input_tokens": i or 0,
            "output_tokens": o or 0,
            "est_cost_usd": round(c or 0, 4),
        }
        for f, s, n, i, o, c in rows
    ]


class BroadcastIn(BaseModel):
    title: str = Field(max_length=200)
    body: str = Field(max_length=2000)
    country: str | None = Field(default=None, min_length=2, max_length=2)


@router.post("/notifications/broadcast")
def broadcast(body: BroadcastIn, db: DB, admin: Admin, request: Request):
    stmt = select(User.id).where(User.is_active.is_(True))
    if body.country:
        stmt = stmt.where(User.country == body.country.upper())
    ids = [u for (u,) in db.execute(stmt).all()]
    for uid in ids:
        db.add(Notification(user_id=uid, kind="announcement", title=body.title, body=body.body))
    audit(
        db,
        admin,
        "notification.broadcast",
        "notification",
        None,
        after={"title": body.title, "recipients": len(ids)},
        ip=request_ip(request),
    )
    db.commit()
    return {"recipients": len(ids)}


# ---------------------------------------------------------------- reported reviews


@router.get("/reviews/reported")
def reported_reviews(db: DB, mod: Moderator):
    """Reviews with open reports, most-reported first (hidden ones included)."""
    counts = (
        select(ReviewReport.review_id, func.count().label("n"))
        .where(~ReviewReport.resolved)
        .group_by(ReviewReport.review_id)
        .subquery()
    )
    rows = db.execute(
        select(UserReview, counts.c.n).join(counts, counts.c.review_id == UserReview.id).order_by(counts.c.n.desc())
    ).all()
    out = []
    for r, n in rows:
        reasons = db.scalars(
            select(ReviewReport.reason).where(ReviewReport.review_id == r.id, ~ReviewReport.resolved)
        ).all()
        out.append(
            {
                "id": r.id,
                "product_id": r.product_id,
                "rating": r.rating,
                "title": r.title,
                "body": r.body,
                "status": r.status,
                "reports": n,
                "reasons": sorted(set(reasons)),
                "created_at": r.created_at.isoformat(),
            }
        )
    return out


class ReviewModerationIn(BaseModel):
    action: str = Field(pattern="^(publish|hide)$")


@router.post("/reviews/{review_id}/moderate")
def moderate_review(review_id: str, body: ReviewModerationIn, db: DB, mod: Moderator, request: Request):
    r = db.get(UserReview, review_id)
    if not r:
        raise HTTPException(404, "Review not found")
    before = {"status": r.status}
    r.status = "published" if body.action == "publish" else "hidden"
    for rep in db.scalars(select(ReviewReport).where(ReviewReport.review_id == r.id, ~ReviewReport.resolved)).all():
        rep.resolved = True
    audit(
        db,
        mod,
        f"review.{body.action}",
        "user_review",
        r.id,
        before=before,
        after={"status": r.status},
        ip=request_ip(request),
    )
    db.commit()
    return {"id": r.id, "status": r.status}
