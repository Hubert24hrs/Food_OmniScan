"""Community product submissions (unknown products and corrections) and image uploads."""

import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.v1.analysis import NutritionPer100
from app.core.config import get_settings
from app.core.deps import DB, CurrentUser
from app.models import CommunitySubmission, ProductBarcode
from app.services.barcode import InvalidBarcode, parse_barcode
from app.services.uploads import save_image

router = APIRouter(tags=["submissions"])


class SubmissionIn(BaseModel):
    barcode: str = Field(max_length=20)
    name: str = Field(min_length=2, max_length=300)
    brand: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=160)
    quantity: str | None = Field(default=None, max_length=80)
    serving_size: str | None = Field(default=None, max_length=80)
    ingredients_text: str | None = Field(default=None, max_length=10000)
    nutrition: NutritionPer100 | None = None
    nutrition_basis: str = Field(default="100g", pattern="^(100g|100ml)$")
    is_beverage: bool = False
    countries: list[str] = Field(default_factory=lambda: ["US"])
    labels: list[str] = Field(default_factory=list)  # e.g. "usda-organic", "gluten-free"
    nafdac_number: str | None = Field(default=None, max_length=40)
    image_ids: list[str] = Field(default_factory=list, max_length=6)
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    user_corrected_ocr: bool = False


@router.post("/submissions", status_code=201)
def submit(body: SubmissionIn, db: DB, user: CurrentUser):
    try:
        bc = parse_barcode(body.barcode)
    except InvalidBarcode as e:
        raise HTTPException(422, {"code": "invalid_barcode", "message": str(e)})
    existing = db.scalar(select(ProductBarcode).where(ProductBarcode.gtin14 == bc.gtin14))
    dup = db.scalar(
        select(func.count())
        .select_from(CommunitySubmission)
        .where(
            CommunitySubmission.user_id == user.id,
            CommunitySubmission.barcode == bc.raw,
            CommunitySubmission.status == "pending",
        )
    )
    if dup:
        raise HTTPException(409, "You already have a pending submission for this barcode.")
    upload_dir = get_settings().upload_dir
    for img in body.image_ids:
        if not img.endswith(".jpg") or "/" in img or "\\" in img or not os.path.exists(os.path.join(upload_dir, img)):
            raise HTTPException(422, f"Unknown image id {img}")
    s = CommunitySubmission(
        user_id=user.id,
        kind="correction" if existing else "new_product",
        barcode=bc.raw,
        product_id=existing.product_id if existing else None,
        payload=body.model_dump(exclude={"image_ids"}),
        images=body.image_ids,
        ocr_confidence=body.ocr_confidence,
    )
    db.add(s)
    db.commit()
    return {
        "id": s.id,
        "status": s.status,
        "kind": s.kind,
        "message": "Thanks! A moderator will review it before it goes live.",
    }


@router.get("/submissions/mine")
def mine(db: DB, user: CurrentUser):
    rows = db.scalars(
        select(CommunitySubmission)
        .where(CommunitySubmission.user_id == user.id)
        .order_by(CommunitySubmission.created_at.desc())
    ).all()
    return [
        {
            "id": s.id,
            "kind": s.kind,
            "barcode": s.barcode,
            "status": s.status,
            "name": s.payload.get("name"),
            "review_notes": s.review_notes,
            "created_at": s.created_at.isoformat(),
            "product_id": s.product_id,
        }
        for s in rows
    ]


@router.post("/uploads", status_code=201)
async def upload(user: CurrentUser, image: UploadFile = File(...)):
    s = get_settings()
    data = await image.read()
    name = save_image(data, s.upload_dir, s.max_upload_mb)
    return {"image_id": name, "url": f"/api/v1/uploads/{name}"}


@router.get("/uploads/{name}")
def get_upload(name: str):
    if not name.endswith(".jpg") or "/" in name or "\\" in name or ".." in name:
        raise HTTPException(404, "Not found")
    path = os.path.join(get_settings().upload_dir, name)
    if not os.path.exists(path):
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
