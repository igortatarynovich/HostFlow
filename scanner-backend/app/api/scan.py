from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import time
import logging
import zipfile
from io import BytesIO

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None

logger = logging.getLogger(__name__)

SCAN_STORAGE_ROOT = Path(os.getenv("SCAN_STORAGE_ROOT", "/data/uploads/scanner")).resolve()
SCAN_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
LOGS_DIR = SCAN_STORAGE_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/scan", tags=["scan-processor"])


@router.get("/health")
async def scan_health():
    return {"status": "ok"}
MAX_DETECT_SIDE = 1600
MAX_PROCESS_SIDE = 2000
RAW_SUFFIX = "_raw.png"
PROC_SUFFIX = "_processed.png"
FINAL_PDF_NAME = "final.pdf"

TEMPLATE_MAP: Dict[str, Dict[str, Any]] = {
    "ID": {"aspect": 1.586, "expected_pages": 2},
    "DRIVER_LICENSE": {"aspect": 1.586, "expected_pages": 2},
    "TACHO_CARD": {"aspect": 1.586, "expected_pages": 2},
    "CODE95_CARD": {"aspect": 1.586, "expected_pages": 2},
    "PASSPORT_SPREAD": {"aspect": 1.408, "expected_pages": 1},
    "A4": {"aspect": 0.707, "expected_pages": 1},
}


async def _read_image(upload: UploadFile) -> np.ndarray:
    data = await upload.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    last_error: Optional[str] = None
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    # Apply EXIF orientation if present (helps with phone captures)
    try:
        with Image.open(BytesIO(data)) as pil_exif:
            pil_exif = ImageOps.exif_transpose(pil_exif)
            img = cv2.cvtColor(np.array(pil_exif.convert("RGB")), cv2.COLOR_RGB2BGR)
    except Exception:
        pass
    if img is None and pillow_heif is not None:
        try:
            heif_file = pillow_heif.read_heif(data)
            pil_img = Image.frombytes(
                heif_file.mode, heif_file.size, heif_file.data, "raw"
            )
            pil_img = ImageOps.exif_transpose(pil_img)
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as exc:
            last_error = f"read_heif: {exc}"
            logger.warning("heif decode failed via read_heif: %s", exc)
            try:
                from io import BytesIO
                pil_img = Image.open(BytesIO(data))
                pil_img = ImageOps.exif_transpose(pil_img)
                img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
            except Exception as exc2:
                last_error = f"Image.open: {exc2}"
                logger.error("heif decode failed via Image.open: %s", exc2)
                img = None
    if img is None:
        raise ValueError(f"cannot decode image{': ' + last_error if last_error else ''}")
    return img


def _parse_size(size_json: Optional[str]) -> Optional[Tuple[float, float]]:
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
    x_sum = pts.sum(axis=1)
    x_diff = np.diff(pts, axis=1)[:, 0]
    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = pts[np.argmin(x_sum)]  # tl
    ordered[2] = pts[np.argmax(x_sum)]  # br
    ordered[1] = pts[np.argmin(x_diff)]  # tr
    ordered[3] = pts[np.argmax(x_diff)]  # bl
    return ordered


def _extreme_from_six(pts: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [(min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys))]


def _normalize_contour_points(pts: List[Tuple[float, float]]) -> np.ndarray:
    """
    Accept 4-6 points (unordered). Preserve user geometry:
    - If 6 points: take extreme corners from all points.
    - If 4 points: use them as-is.
    Order points TL, TR, BR, BL.
    Validate area/convexity; raise ValueError on anomalies.
    """
    if len(pts) < 4 or len(pts) > 6:
        raise ValueError("invalid_points_count")
    base_pts: List[Tuple[float, float]] = pts[:6]
    if len(base_pts) == 6:
        base_pts = _extreme_from_six(base_pts)
    arr = np.array(base_pts, dtype=np.float32)
    hull = cv2.convexHull(arr)
    hull_pts = hull.reshape(-1, 2) if hull is not None else arr
    ordered = _order_points(hull_pts)
    area = cv2.contourArea(ordered)
    if area <= 1.0:
        raise ValueError("non_positive_area")
    if not cv2.isContourConvex(ordered.reshape(-1, 1, 2)):
        raise ValueError("non_convex_contour")
    return ordered


def _warp_with_fixed_aspect(
    img: np.ndarray, pts: List[Tuple[float, float]], template_aspect_ratio: Optional[float]
) -> Tuple[np.ndarray, List[Tuple[float, float]]]:
    """
    Warp using normalized rectangle from 4-6 input points and fixed output size (width=MAX_PROCESS_SIDE).
    """
    ordered = _normalize_contour_points(pts)
    target_w = int(MAX_PROCESS_SIDE)
    if template_aspect_ratio and template_aspect_ratio > 0:
        target_h = int(max(1, round(target_w / template_aspect_ratio)))
    else:
        width_a = np.linalg.norm(ordered[1] - ordered[0])
        width_b = np.linalg.norm(ordered[2] - ordered[3])
        height_a = np.linalg.norm(ordered[0] - ordered[3])
        height_b = np.linalg.norm(ordered[1] - ordered[2])
        avg_w = max(1.0, (width_a + width_b) / 2.0)
        avg_h = max(1.0, (height_a + height_b) / 2.0)
        ar = avg_w / avg_h if avg_h else 1.0
        target_h = int(max(1, round(target_w / ar)))
    dst = np.array(
        [[0, 0], [target_w - 1, 0], [target_w - 1, target_h - 1], [0, target_h - 1]],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(ordered, dst)
    warped = cv2.warpPerspective(img, M, (target_w, target_h), flags=cv2.INTER_LINEAR)
    # Trim black borders if present (threshold >5)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 5, 255, cv2.THRESH_BINARY)
    nz = cv2.findNonZero(mask)
    if nz is not None and len(nz) > 0:
        x, y, w, h = cv2.boundingRect(nz)
        if w > 0 and h > 0 and (w != target_w or h != target_h):
            warped = warped[y : y + h, x : x + w]
            # Resize back to target long side 2000 while preserving aspect
            wh = warped.shape[1], warped.shape[0]
            long_side = max(wh)
            if long_side > 0:
                scale = MAX_PROCESS_SIDE / long_side
                new_w = int(max(1, round(wh[0] * scale)))
                new_h = int(max(1, round(wh[1] * scale)))
                warped = cv2.resize(warped, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            if template_aspect_ratio and warped.shape[1] > 0 and warped.shape[0] > 0:
                ar_now = max(warped.shape[1], warped.shape[0]) / max(1, min(warped.shape[1], warped.shape[0]))
                if abs(ar_now - template_aspect_ratio) / template_aspect_ratio > 0.15:
                    logger.warning("warp aspect drift: %s vs template %s", ar_now, template_aspect_ratio)
    contour = [(float(p[0]), float(p[1])) for p in ordered]
    return warped, contour


def _points_from_contour(
    manual_contour: str,
    fallback_shape: Tuple[int, int],
    src_size: Optional[Tuple[float, float]],
    target_size: Tuple[int, int],
) -> List[Tuple[float, float]]:
    def _scale_points(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if not src_size:
            return points
        sw, sh = src_size
        tw, th = target_size
        sx = tw / sw
        sy = th / sh
        return [(x * sx, y * sy) for (x, y) in points]

    try:
        raw = json.loads(manual_contour)
        pts: List[Tuple[float, float]] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and "x" in item and "y" in item:
                    pts.append((float(item["x"]), float(item["y"])))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    pts.append((float(item[0]), float(item[1])))
        elif isinstance(raw, dict):
            keys = ["p1", "p2", "p3", "p4", "p5", "p6"]
            for k in keys:
                p = raw.get(k)
                if p and isinstance(p, dict) and "x" in p and "y" in p:
                    pts.append((float(p["x"]), float(p["y"])))
        if len(pts) > 6:
            pts = pts[:6]
        if len(pts) >= 4:
            return _scale_points(pts)
    except Exception:
        pass

    h, w = fallback_shape
    return _scale_points([(0, 0), (w, 0), (w, h), (0, h)])


def _perspective_crop(img: np.ndarray, contour: List[Tuple[float, float]]) -> np.ndarray:
    pts = _order_points(np.array(contour, dtype=np.float32))
    (tl, tr, br, bl) = pts
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = int(max(width_a, width_b))
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = int(max(height_a, height_b))
    max_width = max(1, max_width)
    max_height = max(1, max_height)
    dst = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(img, M, (max_width, max_height), flags=cv2.INTER_LINEAR)
    return warped


def apply_filter(img: np.ndarray, mode: str | None) -> np.ndarray:
    mode = (mode or "standard").lower()

    if mode in ("document", "bw", "black_white"):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        thr = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            17,
            8,
        )
        return cv2.cvtColor(thr, cv2.COLOR_GRAY2BGR)

    if mode == "photo":
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        boosted = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        # gentle contrast blend to keep details
        boosted = cv2.addWeighted(img, 0.4, boosted, 0.6, 0)
        return boosted

    # standard
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8))
    cl = clahe.apply(gray)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharp = cv2.filter2D(cl, -1, sharpen_kernel)
    return cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)


def _log_entry(payload: Dict[str, Any], session_id: Optional[str]) -> None:
    try:
        entry = json.dumps(payload, ensure_ascii=False)
        log_files = [LOGS_DIR / "scan.log"]
        if session_id:
            log_files.append(LOGS_DIR / f"{session_id}.log")
        for log_path in log_files:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(entry + "\n")
    except Exception:
        # do not break pipeline on logging errors
        pass


def _resolve_template_ar(document_kind: Optional[str], template_aspect_ratio: Optional[str]) -> Optional[float]:
    try:
        if template_aspect_ratio:
            return float(template_aspect_ratio)
    except Exception:
        pass
    if document_kind:
        data = TEMPLATE_MAP.get(document_kind.upper())
        if data:
            return data.get("aspect")
    return None


def _parse_frame_rect(frame_rect: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    if not frame_rect:
        return None
    try:
        rect = json.loads(frame_rect)
        return (
            float(rect.get("x", 0)),
            float(rect.get("y", 0)),
            float(rect.get("width", 0)),
            float(rect.get("height", 0)),
        )
    except Exception:
        return None


def _detect_contour(
    img: np.ndarray,
    template_aspect_ratio: Optional[float],
    frame_rect: Optional[Tuple[float, float, float, float]],
) -> Tuple[Optional[List[Tuple[float, float]]], Optional[str]]:
    """
    Detect document contour on resized image.
    Returns (contour_pts, status) where status is None or "no_contour".
    """
    res_h, res_w = img.shape[:2]
    roi_img = img
    offset_x = 0
    offset_y = 0
    roi_w, roi_h = res_w, res_h
    if frame_rect:
        fx, fy, fw, fh = frame_rect
        fx = int(max(0, min(res_w, fx)))
        fy = int(max(0, min(res_h, fy)))
        fw = int(max(1, min(res_w - fx, fw)))
        fh = int(max(1, min(res_h - fy, fh)))
        # shrink ROI by padding 4% from each side to cut background
        pad_x = int(max(1, fw * 0.04))
        pad_y = int(max(1, fh * 0.04))
        fx = fx + pad_x
        fy = fy + pad_y
        fw = max(1, fw - 2 * pad_x)
        fh = max(1, fh - 2 * pad_y)
        fx = int(max(0, min(res_w - 1, fx)))
        fy = int(max(0, min(res_h - 1, fy)))
        fw = int(max(1, min(res_w - fx, fw)))
        fh = int(max(1, min(res_h - fy, fh)))
        offset_x, offset_y = fx, fy
        roi_w, roi_h = fw, fh
        roi_img = img[fy : fy + fh, fx : fx + fw]

    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    kernel = np.ones((3, 3), np.uint8)
    blur = cv2.GaussianBlur(enhanced, (5, 5), 0)
    edges = cv2.Canny(blur, 18, 80)
    gradient = cv2.morphologyEx(enhanced, cv2.MORPH_GRADIENT, kernel)
    thr = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        21,
        4,
    )
    edges_combined = cv2.bitwise_or(edges, gradient)
    edges_combined = cv2.bitwise_or(edges_combined, cv2.bitwise_not(thr))
    dilated = cv2.dilate(edges_combined, kernel)
    closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)
    closed = cv2.morphologyEx(closed, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Autodетект выключен: если есть frame_rect, используем его как прямоугольник; иначе no_contour
    if frame_rect:
        fx, fy, fw, fh = frame_rect
        rect_pts = np.array(
            [
                [fx, fy],
                [fx + fw, fy],
                [fx + fw, fy + fh],
                [fx, fy + fh],
            ],
            dtype=np.float32,
        )
        ordered = _order_points(rect_pts)
        contour = [(float(p[0]), float(p[1])) for p in ordered]
        mt = ((ordered[0][0] + ordered[1][0]) / 2, (ordered[0][1] + ordered[1][1]) / 2)
        mb = ((ordered[3][0] + ordered[2][0]) / 2, (ordered[3][1] + ordered[2][1]) / 2)
        contour_with_mid = contour + [mt, mb]
        return contour_with_mid, "frame_rect_fallback"
    return None, "no_contour"


@router.post("/process-page")
async def process_page(
    original: UploadFile = File(...),
    cropped: UploadFile | None = File(None),
    frame_rect: str | None = Form(None),
    original_size: str | None = Form(None),
    cropped_size: str | None = Form(None),
    manual_contour: str | None = Form(None),
    filter: str | None = Form(None),
    document_kind: str | None = Form(None),
    document_type_id: str | None = Form(None),
    page_code: str | None = Form(None),
    page_index: str | None = Form(None),
    template_aspect_ratio: str | None = Form(None),
    detect_only: str | None = Form(None),
    expected_pages: str | None = Form(None),
):
    try:
        session_id = document_type_id or "generic"
        dest_dir = SCAN_STORAGE_ROOT / session_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        meta_path = dest_dir / "session_meta.json"
        meta: Dict[str, Any] = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}

        # 1) Read original (and optional cropped)
        orig_img = await _read_image(original)
        crop_img = None
        if cropped is not None:
            try:
                crop_img = await _read_image(cropped)
            except Exception:
                crop_img = None
        orig_h, orig_w = orig_img.shape[:2]
        exp_pages_val: Optional[int] = None
        if expected_pages:
            try:
                exp_pages_val = int(expected_pages)
            except Exception:
                pass
        if exp_pages_val and exp_pages_val > 0:
            if meta.get("expected_pages") and meta["expected_pages"] != exp_pages_val:
                meta["expected_pages"] = exp_pages_val
            else:
                meta["expected_pages"] = exp_pages_val
        if document_kind:
            meta["document_kind"] = document_kind
        if document_type_id:
            meta["document_type_id"] = document_type_id
        meta["session_id"] = session_id
        if page_index is not None:
            try:
                page_idx_int = int(page_index)
            except Exception:
                raise HTTPException(status_code=400, detail="INVALID_PAGE_INDEX")
        else:
            raise HTTPException(status_code=400, detail="PAGE_INDEX_REQUIRED")
        if meta.get("expected_pages") is not None and page_idx_int >= meta["expected_pages"]:
            raise HTTPException(status_code=400, detail="EXTRA_PAGE")

        # 2) Select base image: cropped if provided; else crop original by frame_rect; else full original
        frame_rect_raw = _parse_frame_rect(frame_rect)
        src_size = _parse_size(cropped_size) or _parse_size(original_size) or (orig_w, orig_h)
        base_img = crop_img if crop_img is not None else orig_img
        base_frame_used = False
        if crop_img is None and frame_rect_raw:
            sw, sh = src_size
            fx, fy, fw, fh = frame_rect_raw
            scale_fx = orig_w / sw if sw else 1.0
            scale_fy = orig_h / sh if sh else 1.0
            fx = int(max(0, min(orig_w, fx * scale_fx)))
            fy = int(max(0, min(orig_h, fy * scale_fy)))
            fw = int(max(1, min(orig_w - fx, fw * scale_fx)))
            fh = int(max(1, min(orig_h - fy, fh * scale_fy)))
            base_img = orig_img[fy : fy + fh, fx : fx + fw]
            base_frame_used = True
        base_h, base_w = base_img.shape[:2]

        # 3) Downscale for detection and processing on base image
        max_side_base = max(base_w, base_h)
        scale_det = 1.0
        if max_side_base > MAX_DETECT_SIDE:
            scale_det = MAX_DETECT_SIDE / max_side_base
        resized_det = cv2.resize(base_img, (int(base_w * scale_det), int(base_h * scale_det)), interpolation=cv2.INTER_AREA)
        res_h_det, res_w_det = resized_det.shape[:2]

        scale_proc = 1.0
        if max_side_base > MAX_PROCESS_SIDE:
            scale_proc = MAX_PROCESS_SIDE / max_side_base
        resized_proc = cv2.resize(base_img, (int(base_w * scale_proc), int(base_h * scale_proc)), interpolation=cv2.INTER_AREA)
        res_h_proc, res_w_proc = resized_proc.shape[:2]

        contour_scaled: Optional[List[Tuple[float, float]]] = None
        manual_contour_raw = None
        doc_img = None
        detection_mode: Optional[str] = None
        detect_status: Optional[str] = None
        detect_roi: Optional[Tuple[int, int, int, int]] = None
        if frame_rect_raw or base_frame_used:
            pad_x = int(max(1, resized_det.shape[1] * 0.04))
            pad_y = int(max(1, resized_det.shape[0] * 0.04))
            detect_roi = (
                pad_x,
                pad_y,
                max(1, resized_det.shape[1] - 2 * pad_x),
                max(1, resized_det.shape[0] - 2 * pad_y),
            )

        # detect_only flag
        detect_flag = (detect_only is not None and str(detect_only).lower() in ("1", "true", "yes"))
        template_ar = _resolve_template_ar(document_kind, template_aspect_ratio)

        final_contour: Optional[List[Tuple[float, float]]] = None
        proc_start = time.time()

        # detect_only branch (autodetect disabled, use frame_rect rectangle only)
        if detect_flag:
            if not detect_roi:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "NO_CONTOUR_IN_FRAME", "message": "Document contour not found in frame ROI"},
                )
            contour_scaled_det, detector_status = _detect_contour(resized_det, template_ar, detect_roi)
            if not contour_scaled_det:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "NO_CONTOUR_IN_FRAME", "message": "Document contour not found in frame ROI"},
                )
            ordered = _order_points(np.array(contour_scaled_det[:4], dtype=np.float32))
            mt = ((ordered[0][0] + ordered[1][0]) / 2, (ordered[0][1] + ordered[1][1]) / 2)
            mb = ((ordered[3][0] + ordered[2][0]) / 2, (ordered[3][1] + ordered[2][1]) / 2)
            contour_out = [(float(p[0]), float(p[1])) for p in ordered] + [mt, mb]
            return {"status": "ok", "contour": contour_out, "image_size": {"width": res_w_det, "height": res_h_det}}

        if manual_contour:
            manual_contour_raw = manual_contour
            detection_mode = "manual"
            detect_status = "manual"
            contour_pts = _points_from_contour(
                manual_contour,
                (res_h_proc, res_w_proc),
                _parse_size(cropped_size) or (base_w, base_h),
                (res_w_proc, res_h_proc),
            )
            contour_scaled = contour_pts
            try:
                doc_img, final_contour = _warp_with_fixed_aspect(resized_proc, contour_pts, template_ar)
            except ValueError as exc:
                _log_entry(
                    {
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "session_id": session_id,
                        "mode": detection_mode,
                        "has_frame_rect": bool(frame_rect_raw),
                        "has_manual_contour": True,
                        "detect_status": "BAD_CONTOUR",
                        "error_detail": str(exc),
                        "input_contour": contour_pts,
                    },
                    session_id,
                )
                raise HTTPException(
                    status_code=422,
                    detail={"code": "BAD_CONTOUR", "message": "Document contour invalid"},
                )
        else:
            # Autodetect disabled: use frame_rect rectangle if available, otherwise error
            if not frame_rect_raw and not base_frame_used:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "NO_CONTOUR_IN_FRAME", "message": "Document contour not found in frame ROI"},
                )
            contour_scaled_det, detector_status = _detect_contour(resized_det, template_ar, detect_roi)
            if contour_scaled_det:
                detection_mode = "frame_rect"
                detect_status = detector_status or "frame_rect_fallback"
                sx = res_w_proc / res_w_det
                sy = res_h_proc / res_h_det
                contour_scaled = [(p[0] * sx, p[1] * sy) for p in contour_scaled_det]
                try:
                    doc_img, final_contour = _warp_with_fixed_aspect(resized_proc, contour_scaled, template_ar)
                except ValueError as exc:
                    detection_mode = "frame_rect"
                    detect_status = "BAD_CONTOUR"
                    _log_entry(
                        {
                            "ts": datetime.utcnow().isoformat() + "Z",
                            "session_id": session_id,
                            "mode": detection_mode,
                            "has_frame_rect": bool(frame_rect_raw),
                            "has_manual_contour": bool(manual_contour),
                            "detect_status": detect_status,
                            "error_detail": str(exc),
                            "input_contour": contour_scaled,
                        },
                        session_id,
                    )
                    raise HTTPException(
                        status_code=422,
                        detail={"code": "BAD_CONTOUR", "message": "Document contour invalid"},
                    )
            else:
                detection_mode = "frame_rect"
                detect_status = "no_contour"
                _log_entry(
                    {
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "session_id": session_id,
                        "mode": detection_mode,
                        "has_frame_rect": bool(frame_rect_raw),
                        "has_manual_contour": bool(manual_contour),
                        "detect_status": detect_status,
                    },
                    session_id,
                )
                if base_frame_used or frame_rect_raw:
                    fallback_name = f"{page_idx_int}_frame_fallback.png"
                    fallback_path = dest_dir / fallback_name
                    try:
                        _, fb_buf = cv2.imencode(".png", resized_proc)
                        fallback_path.write_bytes(fb_buf.tobytes())
                    except Exception:
                        fallback_path = None
                    detail_payload: Dict[str, Any] = {
                        "code": "NO_CONTOUR_IN_FRAME",
                        "message": "No document contour in frame, fallback crop used",
                    }
                    if fallback_path:
                        detail_payload["processed_url"] = f"/api/uploads/scanner/{session_id}/{fallback_path.name}"
                    raise HTTPException(status_code=422, detail=detail_payload)
                raise HTTPException(
                    status_code=422,
                    detail={"code": "NO_CONTOUR", "message": "Document contour not found"},
                )

        if doc_img is None:
            raise HTTPException(status_code=422, detail="unable to crop document")

        # Reject auto-detected crops that effectively take the entire frame (contour/rect invalid).
        # Allow if user provided manual_contour or frame_rect explicitly.
        crop_h, crop_w = doc_img.shape[:2]
        frame_area = res_w_proc * res_h_proc
        crop_area = crop_w * crop_h
        if frame_area > 0 and crop_area / frame_area > 0.98 and not manual_contour_raw and not frame_rect_raw:
            if detect_flag:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "NO_CONTOUR_IN_FRAME", "message": "Document contour not found in frame ROI"},
                )
            raise HTTPException(
                status_code=422,
                detail={"code": "DOCUMENT_NOT_CROPPED", "message": "Document contour not cropped or invalid"},
            )

        # Normalize long side to MAX_PROCESS_SIDE
        max_side_doc = max(doc_w := doc_img.shape[1], doc_h := doc_img.shape[0])
        if max_side_doc > 0 and max_side_doc != MAX_PROCESS_SIDE:
            scale_norm = MAX_PROCESS_SIDE / max_side_doc
            new_w = int(max(1, round(doc_w * scale_norm)))
            new_h = int(max(1, round(doc_h * scale_norm)))
            doc_img = cv2.resize(doc_img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        processed = apply_filter(doc_img, filter)
        processing_ms = int((time.time() - proc_start) * 1000)

        # Save
        page_base = str(page_idx_int) if page_index is not None else (page_code or str(uuid.uuid4()))
        raw_path = dest_dir / f"{page_base}{RAW_SUFFIX}"
        proc_path = dest_dir / f"{page_base}{PROC_SUFFIX}"
        # save raw (warped)
        _, raw_buf = cv2.imencode(".png", doc_img)
        raw_path.write_bytes(raw_buf.tobytes())
        _, buf = cv2.imencode(".png", processed)
        proc_path.write_bytes(buf.tobytes())
        proc_url = f"/api/uploads/scanner/{session_id}/{proc_path.name}"

        # Update session meta with received page
        pages = set(meta.get("pages", []))
        pages.add(page_idx_int)
        meta["pages"] = sorted(list(pages))
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

        # Log for training/analytics
        proc_h, proc_w = processed.shape[:2]
        log_payload = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "document_kind": document_kind,
            "document_type_id": document_type_id,
            "page_code": page_code,
            "page_index": page_index,
            "expected_pages": meta.get("expected_pages"),
            "original_size": [orig_w, orig_h],
            "resized_size": [res_w_proc, res_h_proc],
            "frame_rect": frame_rect_raw,
            "manual_contour_raw": manual_contour_raw,
            "manual_contour_scaled": contour_scaled,
            "final_contour": final_contour,
            "filter_name": filter or "standard",
            "processed_path": str(proc_path),
            "raw_path": str(raw_path),
            "detect_only": detect_flag,
            "template_aspect_ratio": template_ar,
            "processing_ms": processing_ms,
            "mode": detection_mode or ("manual" if manual_contour else "detect"),
            "has_frame_rect": bool(frame_rect_raw),
            "has_manual_contour": bool(manual_contour),
            "detect_status": detect_status or ("strict" if final_contour else "no_contour"),
            "base_frame_used": base_frame_used,
        }
        _log_entry(log_payload, session_id)

        return {
            "processed_url": proc_url,
            "page_index": page_idx_int,
            "width": proc_w,
            "height": proc_h,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/batch")
async def batch_process(
    original_files: List[UploadFile] = File(...),
    document_kind: str | None = Form(None),
    document_type_id: str | None = Form(None),
    template_aspect_ratio: str | None = Form(None),
    filter: str | None = Form(None),
    mode: str | None = Form("single_pdf"),
):
    if not original_files:
        raise HTTPException(status_code=400, detail="NO_FILES")
    session_id = document_type_id or f"batch_{uuid.uuid4().hex}"
    dest_dir = SCAN_STORAGE_ROOT / session_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    meta_path = dest_dir / "session_meta.json"
    meta: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    expected_pages = len(original_files)
    meta["expected_pages"] = expected_pages
    if document_kind:
        meta["document_kind"] = document_kind
    if document_type_id:
        meta["document_type_id"] = document_type_id
    meta["session_id"] = session_id

    template_ar = _resolve_template_ar(document_kind, template_aspect_ratio)
    processed_files: List[Path] = []
    raw_files: List[Path] = []
    page_indices: List[int] = []

    for idx, upload in enumerate(original_files):
        try:
            orig_img = await _read_image(upload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"INVALID_IMAGE_{idx}") from exc
        orig_h, orig_w = orig_img.shape[:2]
        max_side = max(orig_w, orig_h)
        scale_det = 1.0
        if max_side > MAX_DETECT_SIDE:
            scale_det = MAX_DETECT_SIDE / max_side
        resized_det = cv2.resize(orig_img, (int(orig_w * scale_det), int(orig_h * scale_det)), interpolation=cv2.INTER_AREA)
        res_h_det, res_w_det = resized_det.shape[:2]

        scale_proc = 1.0
        if max_side > MAX_PROCESS_SIDE:
            scale_proc = MAX_PROCESS_SIDE / max_side
        resized_proc = cv2.resize(orig_img, (int(orig_w * scale_proc), int(orig_h * scale_proc)), interpolation=cv2.INTER_AREA)
        res_h_proc, res_w_proc = resized_proc.shape[:2]

        detect_roi = None
        pad_x = int(max(1, resized_det.shape[1] * 0.04))
        pad_y = int(max(1, resized_det.shape[0] * 0.04))
        detect_roi = (
            pad_x,
            pad_y,
            max(1, resized_det.shape[1] - 2 * pad_x),
            max(1, resized_det.shape[0] - 2 * pad_y),
        )
        contour_scaled_det, status = _detect_contour(resized_det, template_ar, detect_roi)
        if not contour_scaled_det:
            _log_entry(
                {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "session_id": session_id,
                    "mode": "batch_item",
                    "page_index": idx,
                    "detect_status": status or "no_contour",
                },
                session_id,
            )
            raise HTTPException(status_code=422, detail={"status": "NO_CONTOUR", "page_index": idx})

        sx = res_w_proc / res_w_det
        sy = res_h_proc / res_h_det
        contour_scaled = [(p[0] * sx, p[1] * sy) for p in contour_scaled_det]
        try:
            doc_img, final_contour = _warp_with_fixed_aspect(resized_proc, contour_scaled, template_ar)
        except ValueError as exc:
            _log_entry(
                {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "session_id": session_id,
                    "mode": "batch_item",
                    "page_index": idx,
                    "detect_status": "BAD_CONTOUR",
                    "error_detail": str(exc),
                    "input_contour": contour_scaled,
                },
                session_id,
            )
            raise HTTPException(status_code=422, detail={"status": "BAD_CONTOUR", "page_index": idx})

        max_side_doc = max(doc_img.shape[1], doc_img.shape[0])
        if max_side_doc > 0 and max_side_doc != MAX_PROCESS_SIDE:
            scale_norm = MAX_PROCESS_SIDE / max_side_doc
            new_w = int(max(1, round(doc_img.shape[1] * scale_norm)))
            new_h = int(max(1, round(doc_img.shape[0] * scale_norm)))
            doc_img = cv2.resize(doc_img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        processed_img = apply_filter(doc_img, filter)
        page_base = str(idx)
        raw_path = dest_dir / f"{page_base}{RAW_SUFFIX}"
        proc_path = dest_dir / f"{page_base}{PROC_SUFFIX}"
        _, raw_buf = cv2.imencode(".png", orig_img)
        raw_path.write_bytes(raw_buf.tobytes())
        _, proc_buf = cv2.imencode(".png", processed_img)
        proc_path.write_bytes(proc_buf.tobytes())
        raw_files.append(raw_path)
        processed_files.append(proc_path)
        page_indices.append(idx)
        _log_entry(
            {
                "ts": datetime.utcnow().isoformat() + "Z",
                "session_id": session_id,
                "mode": "batch_item",
                "page_index": idx,
                "detect_status": "ok",
                "final_contour": final_contour,
                "processed_path": str(proc_path),
            },
            session_id,
        )

    meta["pages"] = sorted(list(set(meta.get("pages", [])) | set(page_indices)))
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    processed_urls = [f"/api/uploads/scanner/{session_id}/{p.name}" for p in processed_files]
    mode_norm = (mode or "single_pdf").lower()
    response_payload: Dict[str, Any] = {
        "session_id": session_id,
        "mode": mode_norm,
        "processed_urls": processed_urls,
        "expected_pages": expected_pages,
    }

    if mode_norm == "zip":
        pdf_paths: List[Path] = []
        for p in processed_files:
            pdf_path = dest_dir / f"{p.stem}.pdf"
            with Image.open(p) as img:
                img.convert("RGB").save(pdf_path)
            pdf_paths.append(pdf_path)
        zip_path = dest_dir / "batch.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for pdf in pdf_paths:
                zf.write(pdf, arcname=pdf.name)
        response_payload["zip_url"] = f"/api/uploads/scanner/{session_id}/{zip_path.name}"
    else:
        images_sorted = []
        for p in sorted(processed_files, key=lambda x: int(Path(x).stem)):
            images_sorted.append(p)
        pdf_path = dest_dir / "batch.pdf"
        try:
            pil_images = []
            for p in images_sorted:
                with Image.open(p) as img:
                    pil_images.append(img.convert("RGB"))
            pil_images[0].save(pdf_path, save_all=True, append_images=pil_images[1:] or [])
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        response_payload["pdf_url"] = f"/api/uploads/scanner/{session_id}/{pdf_path.name}"

    _log_entry(
        {
            "ts": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "mode": "batch",
            "expected_pages": expected_pages,
            "pages": page_indices,
            "result": "ok",
            "output_mode": mode_norm,
        },
        session_id,
    )
    return response_payload


@router.post("/build-pdf")
async def build_pdf(
    session_id: str = Form(...),
    document_kind: str | None = Form(None),
    document_type_id: str | None = Form(None),
):
    dest_dir = SCAN_STORAGE_ROOT / session_id
    if not dest_dir.exists():
        raise HTTPException(status_code=404, detail="session_not_found")
    meta_path = dest_dir / "session_meta.json"
    meta: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    expected = meta.get("expected_pages")
    if expected is None:
        raise HTTPException(status_code=422, detail={"code": "MISSING_EXPECTED_PAGES"})
    pages_list = meta.get("pages", [])
    try:
        page_indices = sorted(int(p) for p in pages_list)
    except Exception:
        page_indices = sorted(pages_list)
    expected_range = set(range(expected))
    present_set = set(page_indices)
    missing_pages = sorted(list(expected_range - present_set))
    extra_pages = sorted([p for p in present_set if p >= expected])
    if extra_pages:
        _log_entry(
            {
                "ts": datetime.utcnow().isoformat() + "Z",
                "session_id": session_id,
                "expected_pages": expected,
                "pages": page_indices,
                "result": "EXTRA_PAGES",
                "extra_pages": extra_pages,
            },
            session_id,
        )
        raise HTTPException(status_code=422, detail={"code": "EXTRA_PAGES", "extra_pages": extra_pages})
    if missing_pages:
        _log_entry(
            {
                "ts": datetime.utcnow().isoformat() + "Z",
                "session_id": session_id,
                "expected_pages": expected,
                "pages": page_indices,
                "result": "MISSING_PAGES",
                "missing_pages": missing_pages,
            },
            session_id,
        )
        raise HTTPException(status_code=422, detail={"code": "MISSING_PAGES", "missing_pages": missing_pages})
    page_indices = list(range(expected))
    images_sorted = []
    for idx in page_indices:
        proc_file = dest_dir / f"{idx}{PROC_SUFFIX}"
        if not proc_file.exists():
            raise HTTPException(status_code=500, detail="PAGE_FILE_MISSING")
        images_sorted.append(proc_file)
    pdf_name = f"document_{(document_kind or 'doc').lower()}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.pdf"
    pdf_path = dest_dir / pdf_name
    try:
        pil_images = []
        for p in images_sorted:
            with Image.open(p) as img:
                pil_images.append(img.convert("RGB"))
        pil_images[0].save(pdf_path, save_all=True, append_images=pil_images[1:] or [])
        url = f"/api/uploads/scanner/{session_id}/{pdf_path.name}"
        _log_entry(
            {
                "ts": datetime.utcnow().isoformat() + "Z",
                "session_id": session_id,
                "document_kind": document_kind,
                "document_type_id": document_type_id,
                "pages": [p.name for p in images_sorted],
                "pdf": pdf_path.name,
                "expected_pages": expected,
                "result": "OK",
            },
            session_id,
        )
        return {"pdf_url": url}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
