from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.v1.profiles import resolve_profiles
from app.core import ratelimit
from app.core.config import get_settings
from app.core.deps import DB, CurrentUser, OptionalUser
from app.models import (
    CommunitySubmission,
    FoodScan,
    Product,
    ProductComparison,
    ScanHistory,
    User,
    UserReview,
)
from app.services import alternatives as alt_svc
from app.services import entitlements as ent
from app.services import product_service as ps
from app.services.barcode import InvalidBarcode, parse_barcode
from app.services.providers import openfoodfacts as off
from app.services.providers import usda
from app.services.providers.base import ProviderError

router = APIRouter(tags=["products"])


def region_of(user: User | None) -> str:
    if user is None or (user.country or "US") == "US":
        return "US"
    return "EU"


def product_out(db, p: Product) -> dict:
    n = p.nutrition_per_100()
    ni = ps.nutrition_input(p)
    prov = (p.raw_data or {}).get("provenance", {})
    return {
        "id": p.id,
        "name": p.name,
        "brand": p.brand_text,
        "quantity": p.quantity,
        "serving_size": p.serving_size,
        "barcodes": [{"barcode": b.barcode, "format": b.format} for b in p.barcodes],
        "categories": p.categories_tags,
        "category": p.category.name if p.category else None,
        "countries": p.countries_tags,
        "labels": p.labels_tags,
        "packaging": p.packaging_text,
        "packaging_tags": p.packaging_tags,
        "image_url": p.image_url,
        "images": [{"kind": i.kind, "url": i.url} for i in p.images],
        "ingredients_text": p.ingredients_text,
        "nova_group": p.nova_group,
        "nova_source": p.nova_source,
        "nutriscore_grade": p.nutriscore_grade,
        "is_beverage": p.is_beverage,
        "nafdac_number": p.nafdac_number,
        "nutrition": None
        if n is None
        else {
            "basis": n.basis,
            "per_100": {
                k: getattr(n, k)
                for k in (
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
            },
            "serving_size_g": n.serving_size_g,
            "per_serving": ni.per_serving() if ni else None,
            "source": n.source,
        },
        "provenance": {
            "source": p.source,
            "source_url": p.source_url,
            "license": p.source_license,
            "attribution": (p.raw_data or {}).get("attribution"),
            "fields": prov,
            "last_synced_at": p.last_synced_at.isoformat() if p.last_synced_at else None,
            "verified_at": p.verified_at.isoformat() if p.verified_at else None,
        },
        "completeness": p.completeness,
    }


def _record_scan(
    db,
    user: User | None,
    *,
    barcode: str | None,
    product: Product | None,
    status: str,
    scan_type: str,
    client_id: str | None = None,
    scanned_at: datetime | None = None,
    profile_id: str | None = None,
) -> None:
    if user is None:
        return
    if client_id and db.scalar(select(FoodScan).where(FoodScan.user_id == user.id, FoodScan.client_id == client_id)):
        return
    db.add(
        FoodScan(
            user_id=user.id,
            profile_id=profile_id,
            scan_type=scan_type,
            barcode=barcode,
            product_id=product.id if product else None,
            status=status,
            client_id=client_id,
            client_scanned_at=scanned_at,
        )
    )
    if product:
        h = db.scalar(select(ScanHistory).where(ScanHistory.user_id == user.id, ScanHistory.product_id == product.id))
        ts = scanned_at or datetime.now(UTC)
        if h:
            h.scan_count += 1
            h.hidden = False
            last = h.last_scanned_at if h.last_scanned_at.tzinfo else h.last_scanned_at.replace(tzinfo=UTC)
            h.last_scanned_at = max(last, ts if ts.tzinfo else ts.replace(tzinfo=UTC))
        else:
            db.add(
                ScanHistory(
                    user_id=user.id,
                    product_id=product.id,
                    profile_id=profile_id,
                    first_scanned_at=ts,
                    last_scanned_at=ts,
                )
            )
    db.commit()


@router.get("/products/barcode/{code}")
def scan_barcode(
    code: str,
    db: DB,
    user: OptionalUser,
    request: Request,
    profile_ids: list[str] | None = Query(default=None),
    refresh: bool = False,
):
    """Primary scan endpoint: validate barcode, look it up, analyse it, record history."""
    ratelimit.enforce(request, "scan", get_settings().rate_limit_per_minute)
    try:
        res = ps.lookup_barcode(db, code, force_refresh=refresh)
    except InvalidBarcode as e:
        _record_scan(db, user, barcode=code[:14], product=None, status="invalid", scan_type="barcode")
        raise HTTPException(422, {"code": "invalid_barcode", "message": str(e)})
    if res.status == "provider_unavailable":
        _record_scan(db, user, barcode=res.barcode.raw, product=None, status="error", scan_type="barcode")
        raise HTTPException(
            503,
            {
                "code": "provider_unavailable",
                "barcode": res.barcode.raw,
                "message": "Product databases are unreachable right now. Try again shortly.",
                "detail": res.message,
            },
        )
    if res.status == "not_found":
        _record_scan(db, user, barcode=res.barcode.raw, product=None, status="not_found", scan_type="barcode")
        pending = db.scalar(
            select(func.count())
            .select_from(CommunitySubmission)
            .where(CommunitySubmission.barcode == res.barcode.raw, CommunitySubmission.status == "pending")
        )
        raise HTTPException(
            404,
            {
                "code": "product_not_found",
                "barcode": res.barcode.raw,
                "format": res.barcode.format,
                "sources_checked": res.sources,
                "pending_submissions": pending,
                "message": "We couldn't find this product. You can add it by photographing the label.",
            },
        )
    profiles = resolve_profiles(db, user, profile_ids)
    analysis = ps.analyze_product(db, res.product, profiles, region_of(user))
    _record_scan(
        db,
        user,
        barcode=res.barcode.raw,
        product=res.product,
        status="found",
        scan_type="barcode",
        profile_id=profiles[0].id if profiles else None,
    )
    return {
        "product": product_out(db, res.product),
        "analysis": analysis,
        "sources": res.sources,
        "stale": res.stale,
        "message": res.message,
    }


@router.get("/products/search")
def search(
    db: DB,
    q: str = Query(min_length=2, max_length=120),
    source: str = Query("all", pattern="^(local|all)$"),
    page: int = Query(1, ge=1, le=20),
    request: Request = None,
):
    ratelimit.enforce(request, "search", 30)
    local = ps.search_local(db, q, limit=20, offset=(page - 1) * 20)
    results = [ps.product_summary(db, p) for p in local]
    remote_error = None
    if source == "all" and len(results) < 10:
        seen = {r["barcode"] for r in results}
        remote = []
        try:
            remote = usda.search(q, 10) if usda.enabled() else []
        except ProviderError as e:
            remote_error = str(e)
        try:
            remote += off.search(q, page=page, page_size=15, country="united-states")
        except ProviderError as e:
            remote_error = str(e)
        for pp in remote:
            if not pp.barcode or pp.barcode in seen:
                continue
            try:
                bc = parse_barcode(pp.barcode)
            except InvalidBarcode:
                continue
            p = ps.upsert_product(db, pp, bc, {"name": pp.source})
            seen.add(pp.barcode)
            results.append(ps.product_summary(db, p))
        db.commit()
    return {"query": q, "results": results, "remote_error": remote_error}


def _get_product(db, product_id: str) -> Product:
    p = db.get(Product, product_id)
    if not p or p.status != "active":
        raise HTTPException(404, "Product not found")
    return p


@router.get("/products/{product_id}")
def get_product(product_id: str, db: DB, user: OptionalUser, profile_ids: list[str] | None = Query(default=None)):
    p = _get_product(db, product_id)
    profiles = resolve_profiles(db, user, profile_ids)
    return {"product": product_out(db, p), "analysis": ps.analyze_product(db, p, profiles, region_of(user))}


@router.get("/products/{product_id}/alternatives")
def alternatives(
    product_id: str,
    db: DB,
    user: OptionalUser,
    objective: str = Query("overall", pattern="^(" + "|".join(alt_svc.OBJECTIVES) + ")$"),
    exclude: list[str] | None = Query(default=None),
    brand: str | None = None,
    compatible_only: bool = True,
    profile_ids: list[str] | None = Query(default=None),
):
    p = _get_product(db, product_id)
    if user:
        ent.require_quota(db, user, "alternatives")
    res = alt_svc.find_alternatives(
        db,
        p,
        resolve_profiles(db, user, profile_ids),
        objective=objective,
        exclude_ingredients=exclude,
        brand=brand,
        compatible_only=compatible_only,
    )
    if user:
        ent.record_usage(db, user, "alternatives", "internal", None)
    return res


class CompareIn(BaseModel):
    product_ids: list[str] = Field(min_length=2, max_length=6)
    objective: str = "overall"
    profile_ids: list[str] | None = None


@router.post("/compare")
def compare(body: CompareIn, db: DB, user: OptionalUser):
    if body.objective not in alt_svc.OBJECTIVES:
        raise HTTPException(422, "Unknown objective")
    if user:
        ent.require_quota(db, user, "comparisons")
    products = [_get_product(db, pid) for pid in dict.fromkeys(body.product_ids)]
    if len(products) < 2:
        raise HTTPException(422, "Pick at least two different products")
    res = alt_svc.compare(
        db, products, resolve_profiles(db, user, body.profile_ids), body.objective, user.id if user else None
    )
    if user:
        ent.record_usage(db, user, "comparisons", "internal", None)
    return res


@router.get("/compare/{token}")
def shared_comparison(token: str, db: DB):
    row = db.scalar(select(ProductComparison).where(ProductComparison.share_token == token))
    if not row:
        raise HTTPException(404, "Comparison not found")
    res = dict(row.result)
    # Shared reports never expose the sharer's personal compatibility data
    for prod in res.get("products", []):
        prod.pop("compatibility", None)
    res["created_at"] = row.created_at.isoformat()
    return res


# ------------------------------------------------------------------ reviews


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, max_length=120)
    body: str | None = Field(default=None, max_length=2000)


@router.get("/products/{product_id}/reviews")
def list_reviews(product_id: str, db: DB):
    rows = db.scalars(
        select(UserReview)
        .where(UserReview.product_id == product_id, UserReview.status == "published")
        .order_by(UserReview.created_at.desc())
        .limit(50)
    ).all()
    avg = db.scalar(
        select(func.avg(UserReview.rating)).where(UserReview.product_id == product_id, UserReview.status == "published")
    )
    return {
        "average": round(avg, 2) if avg else None,
        "count": len(rows),
        "reviews": [
            {"id": r.id, "rating": r.rating, "title": r.title, "body": r.body, "created_at": r.created_at.isoformat()}
            for r in rows
        ],
    }


@router.put("/products/{product_id}/reviews")
def upsert_review(product_id: str, body: ReviewIn, db: DB, user: CurrentUser):
    _get_product(db, product_id)
    r = db.scalar(select(UserReview).where(UserReview.user_id == user.id, UserReview.product_id == product_id))
    if r is None:
        r = UserReview(user_id=user.id, product_id=product_id, rating=body.rating)
        db.add(r)
    r.rating, r.title, r.body = body.rating, body.title, body.body
    db.commit()
    return {"id": r.id, "rating": r.rating}


class ReportIn(BaseModel):
    field: str = Field(max_length=60)
    issue: str = Field(min_length=5, max_length=2000)
    suggested_value: str | None = Field(default=None, max_length=5000)


@router.post("/products/{product_id}/report", status_code=201)
def report_issue(product_id: str, body: ReportIn, db: DB, user: CurrentUser):
    p = _get_product(db, product_id)
    s = CommunitySubmission(
        user_id=user.id,
        kind="correction",
        product_id=p.id,
        barcode=p.barcodes[0].barcode if p.barcodes else None,
        payload=body.model_dump(),
    )
    db.add(s)
    db.commit()
    return {"id": s.id, "status": s.status}
