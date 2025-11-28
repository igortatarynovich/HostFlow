from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError


_ROOT = Path(os.environ.get("UPLOAD_DIR") or Path(__file__).resolve().parents[2] / "uploads")
LOGO_ROOT = _ROOT / "tenant-logos"
LOGO_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_HEIGHT = 32
MAX_WIDTH = 160


async def save_tenant_logo(tenant_id: str, upload: UploadFile) -> Tuple[str, Dict[str, object]]:
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    try:
        image = Image.open(BytesIO(data))
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Invalid image")

    image = image.convert("RGBA")
    width, height = image.size
    if width <= 0 or height <= 0:
        raise HTTPException(status_code=400, detail="Invalid image dimensions")

    scale = min(1.0, MAX_WIDTH / width, MAX_HEIGHT / height)
    if scale < 1.0:
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        image = image.resize(new_size, Image.LANCZOS)
        width, height = image.size

    target_dir = LOGO_ROOT / tenant_id
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "logo.png"
    image.save(path, format="PNG")

    public_url = f"/uploads/tenant-logos/{tenant_id}/logo.png"
    meta = {
        "width": width,
        "height": height,
        "content_type": "image/png",
        "source_content_type": content_type,
        "bytes": path.stat().st_size,
    }
    return public_url, meta
