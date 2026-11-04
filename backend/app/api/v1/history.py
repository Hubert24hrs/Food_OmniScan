"""Scan history, offline scan sync, favourites/trusted/incompatible lists, notifications."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.products import _record_scan
from app.core.deps import DB, CurrentUser
from app.models import FavouriteProduct, Notification, Product, ScanHistory
from app.services import product_service as ps
from app.services.barcode import InvalidBarcode

router = APIRouter(tags=["history"])


@router.get("/history")
def history(db: DB, user: CurrentUser, limit: int = Query(50, le=200), offset: int = 0):
    rows = db.scalars(
        select(ScanHistory)
        .where(ScanHistory.user_id == user.id, ScanHistory.hidden.is_(False))
        .order_by(ScanHistory.last_scanned_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    out = []
    for h in rows:
        p = db.get(Product, h.product_id)
        if p:
            out.append(
                {
                    "id": h.id,
                    "product": ps.product_summary(db, p),
                    "scan_count": h.scan_count,
                    "first_scanned_at": h.first_scanned_at.isoformat(),
                    "last_scanned_at": h.last_scanned_at.isoformat(),
                }
            )
    return out


@router.delete("/history/{history_id}", status_code=204)
def hide_history(history_id: str, db: DB, user: CurrentUser):
    h = db.get(ScanHistory, history_id)
    if not h or h.user_id != user.id:
        raise HTTPException(404, "Not found")
    h.hidden = True
    db.commit()


class QueuedScan(BaseModel):
    client_id: str = Field(min_length=8, max_length=64)
    barcode: str = Field(max_length=20)
    scanned_at: datetime
    profile_id: str | None = None


@router.post("/scans/sync")
def sync_scans(body: list[QueuedScan], db: DB, user: CurrentUser):
    """Offline-first mobile clients queue scans and upload them here. Idempotent on client_id."""
    if len(body) > 200:
        raise HTTPException(422, "At most 200 scans per sync")
    results = []
    for q in body:
        try:
            res = ps.lookup_barcode(db, q.barcode)
        except InvalidBarcode as e:
            _record_scan(
                db,
                user,
                barcode=q.barcode[:14],
                product=None,
                status="invalid",
                scan_type="barcode",
                client_id=q.client_id,
                scanned_at=q.scanned_at,
            )
            results.append({"client_id": q.client_id, "status": "invalid", "message": str(e)})
            continue
        status = res.status if res.status != "provider_unavailable" else "retry_later"
        if status != "retry_later":
            _record_scan(
                db,
                user,
                barcode=res.barcode.raw,
                product=res.product,
                status="found" if res.product else "not_found",
                scan_type="barcode",
                client_id=q.client_id,
                scanned_at=q.scanned_at,
                profile_id=q.profile_id,
            )
        results.append(
            {
                "client_id": q.client_id,
                "status": status,
                "product": ps.product_summary(db, res.product) if res.product else None,
            }
        )
    return {"results": results}


LIST_TYPES = "^(favourite|trusted|incompatible)$"


class FavIn(BaseModel):
    product_id: str
    list_type: str = Field("favourite", pattern=LIST_TYPES)
    note: str | None = Field(default=None, max_length=300)
    profile_id: str | None = None


@router.get("/favourites")
def list_favs(db: DB, user: CurrentUser, list_type: str = Query("favourite", pattern=LIST_TYPES)):
    rows = db.scalars(
        select(FavouriteProduct)
        .where(FavouriteProduct.user_id == user.id, FavouriteProduct.list_type == list_type)
        .order_by(FavouriteProduct.created_at.desc())
    ).all()
    return [
        {
            "id": r.id,
            "list_type": r.list_type,
            "note": r.note,
            "created_at": r.created_at.isoformat(),
            "product": ps.product_summary(db, db.get(Product, r.product_id)),
        }
        for r in rows
        if db.get(Product, r.product_id)
    ]


@router.post("/favourites", status_code=201)
def add_fav(body: FavIn, db: DB, user: CurrentUser):
    if not db.get(Product, body.product_id):
        raise HTTPException(404, "Product not found")
    row = db.scalar(
        select(FavouriteProduct).where(
            FavouriteProduct.user_id == user.id,
            FavouriteProduct.product_id == body.product_id,
            FavouriteProduct.list_type == body.list_type,
        )
    )
    if row is None:
        row = FavouriteProduct(user_id=user.id, product_id=body.product_id, list_type=body.list_type)
        db.add(row)
    row.note, row.profile_id = body.note, body.profile_id
    db.commit()
    return {"id": row.id, "list_type": row.list_type}


@router.delete("/favourites/{fav_id}", status_code=204)
def del_fav(fav_id: str, db: DB, user: CurrentUser):
    row = db.get(FavouriteProduct, fav_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()


@router.get("/notifications")
def notifications(db: DB, user: CurrentUser, unread_only: bool = False):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    rows = db.scalars(stmt.order_by(Notification.created_at.desc()).limit(100)).all()
    return [
        {
            "id": n.id,
            "kind": n.kind,
            "title": n.title,
            "body": n.body,
            "data": n.data,
            "read": n.read_at is not None,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


@router.post("/notifications/{nid}/read", status_code=204)
def mark_read(nid: str, db: DB, user: CurrentUser):
    from datetime import UTC
    from datetime import datetime as dt

    n = db.get(Notification, nid)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Not found")
    n.read_at = dt.now(UTC)
    db.commit()
