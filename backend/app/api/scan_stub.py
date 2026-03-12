from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image

uploads_root = Path(__file__).resolve().parent.parent / "uploads" / "scanner"
uploads_root.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/scan", tags=["scan-processor"])


async def _read_image(upload: UploadFile) -> np.ndarray:
    data = await upload.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("cannot decode image")
    return img


def _parse_size(size_json: Optional[str]) -> Optional[Tuple[float, float]]:
    """Parse {"width":..., "height":...} json string."""
    if not size_json:
        return None
    try:
        obj = json.loads(size_json)
        w = float(obj.get("width") or obj.get("w"))
        h = float(obj.get("height") or obj.get("h"))
        if w > 0 and h > 0:
            return (w, h)
    except Exception:
        return None
    return None


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order points: top-left, top-right, bottom-right, bottom-left."""
    xSum = pts.sum(axis=1)
    xDiff = np.diff(pts, axis=1)[:, 0]
    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = pts[np.argmin(xSum)]  # tl
    ordered[2] = pts[np.argmax(xSum)]  # br
    ordered[1] = pts[np.argmin(xDiff)]  # tr
    ordered[3] = pts[np.argmax(xDiff)]  # bl
    return ordered


def _points_from_contour(
    manual_contour: str,
    fallback_shape: Tuple[int, int],
    src_size: Optional[Tuple[float, float]],
    target_size: Tuple[int, int],
) -> List[Tuple[float, float]]:
    try:
        c = json.loads(manual_contour)
        if isinstance(c, list):
            pts = c
        else:
            pts = [c.get("p1"), c.get("p2"), c.get("p4"), c.get("p5")]
        pts = [(float(p["x"]), float(p["y"])) for p in pts if p]
        if len(pts) == 4:
            if src_size:
                sw, sh = src_size
                tw, th = target_size
                scale_x = tw / sw
                scale_y = th / sh
                pts = [(x * scale_x, y * scale_y) for (x, y) in pts]
            return pts
    except Exception:
        pass
    h, w = fallback_shape
    return [(0, 0), (w, 0), (w, h), (0, h)]


def _perspective_crop(img: np.ndarray, contour: List[Tuple[float, float]]) -> np.ndarray:
    pts = _order_points(np.array(contour, dtype=np.float32))
    (tl, tr, br, bl) = pts
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))
    maxWidth = max(1, maxWidth)
    maxHeight = max(1, maxHeight)
    dst = np.array(
        [[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight), flags=cv2.INTER_LINEAR)
    return warped


def _apply_filter(img: np.ndarray, mode: str | None) -> np.ndarray:
    mode = (mode or "standard").lower()
    if mode == "photo":
        return cv2.convertScaleAbs(img, alpha=1.1, beta=8)
    if mode in ("document", "bw", "black_white"):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 5)
        return cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)
    # standard: mild contrast via CLAHE
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    merged = cv2.merge((cl, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


@router.post("/process-page")
async def process_page(
    original: UploadFile = File(...),
    cropped: UploadFile = File(...),
    frame_rect: str | None = Form(None),
    original_size: str | None = Form(None),
    cropped_size: str | None = Form(None),
    manual_contour: str | None = Form(None),
    filter: str | None = Form(None),
    document_kind: str | None = Form(None),
    document_type_id: str | None = Form(None),
    page_code: str | None = Form(None),
    page_index: str | None = Form(None),
):
    """
    Process page using provided contour or frame rect:
    - Perspective crop
    - Apply filter (standard/photo/document)
    - Save as PNG
    """
    try:
        session_id = document_type_id or "generic"
        dest_dir = uploads_root / session_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{page_code or uuid.uuid4()}.png"

        # Load images
        orig_img = await _read_image(original)
        cropped_img = None
        try:
            cropped_img = await _read_image(cropped)
        except Exception:
            cropped_img = None

        orig_h, orig_w = orig_img.shape[:2]
        src_size = _parse_size(cropped_size) or _parse_size(original_size)
        img_to_process = cropped_img.copy() if cropped_img is not None else orig_img.copy()

        if manual_contour:
            contour_pts = _points_from_contour(
                manual_contour,
                (orig_img.shape[0], orig_img.shape[1]),
                src_size,
                (orig_w, orig_h),
            )
            warped = _perspective_crop(orig_img, contour_pts)
            img_to_process = warped
        elif frame_rect:
            try:
                rect = json.loads(frame_rect)
                x = float(rect.get('x', 0)); y = float(rect.get('y', 0))
                w = float(rect.get('width', orig_img.shape[1])); h = float(rect.get('height', orig_img.shape[0]))
                if src_size and (abs(src_size[0] - orig_w) / max(orig_w, 1) > 0.05 or abs(src_size[1] - orig_h) / max(orig_h, 1) > 0.05):
                    sw, sh = src_size
                    scale_x = orig_w / sw
                    scale_y = orig_h / sh
                    x *= scale_x; y *= scale_y; w *= scale_x; h *= scale_y
                x = int(max(0, x)); y = int(max(0, y))
                w = int(max(1, min(w, orig_img.shape[1] - x)))
                h = int(max(1, min(h, orig_img.shape[0] - y)))
                img_to_process = orig_img[y:y + h, x:x + w]
            except Exception:
                pass

        processed = _apply_filter(img_to_process, filter)

        # Save PNG for quality
        _, buf = cv2.imencode('.png', processed)
        dest_path.write_bytes(buf.tobytes())
        url = f"/api/uploads/scanner/{session_id}/{dest_path.name}"
        return {"processed_url": url}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/build-pdf")
async def build_pdf(
    session_id: str = Form(...),
    document_kind: str | None = Form(None),
    document_type_id: str | None = Form(None),
):
    """Build PDF from all PNG/JPG images in the session folder."""
    dest_dir = uploads_root / session_id
    if not dest_dir.exists():
        raise HTTPException(status_code=404, detail="session_not_found")
    images = sorted(list(dest_dir.glob("*.png")) + list(dest_dir.glob("*.jpg")))
    if not images:
        raise HTTPException(status_code=404, detail="no_pages")
    pdf_path = dest_dir / f"{session_id}.pdf"
    try:
        pil_images = []
        for p in images:
            with Image.open(p) as img:
                pil_images.append(img.convert("RGB"))
        pil_images[0].save(pdf_path, save_all=True, append_images=pil_images[1:] or [])
        url = f"/api/uploads/scanner/{session_id}/{pdf_path.name}"
        return {"pdf_url": url}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
