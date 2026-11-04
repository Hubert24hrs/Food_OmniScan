"""Secure image upload handling: size/type validation, EXIF stripping by re-encoding."""

import io
import os
import secrets

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

ALLOWED = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard


def validate_image(data: bytes, max_mb: int) -> str:
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"Image larger than {max_mb} MB")
    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt = im.format
            im.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(415, "Unsupported or corrupt image") from None
    if fmt not in ALLOWED:
        raise HTTPException(415, "Only JPEG, PNG or WebP images are accepted")
    return ALLOWED[fmt]


def save_image(data: bytes, upload_dir: str, max_mb: int) -> str:
    """Re-encode to JPEG (strips EXIF/GPS metadata), downscale, return the stored filename."""
    validate_image(data, max_mb)
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGB")
        im.thumbnail((2000, 2000))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=85, optimize=True)
    os.makedirs(upload_dir, exist_ok=True)
    name = f"{secrets.token_hex(16)}.jpg"
    with open(os.path.join(upload_dir, name), "wb") as f:
        f.write(out.getvalue())
    return name
