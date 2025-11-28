# This file has been refactored to use the new scanner module
# Old image processing functions (_enhance_image, _find_document_contour, etc.) 
# have been replaced with ImagePreprocessor from backend.app.scanner.preprocess
# 
# The old functions are kept below for reference but are no longer used.
# They can be safely removed in a future cleanup.

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence, Literal
from uuid import UUID, uuid4

import cv2  # type: ignore
import numpy as np
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models import Document, ScanPage, ScanSession
from backend.app.models.enums import (
    DocumentKind,
    DocumentRequestedFrom,
    DocumentStatus,
    ScanPageStatus,
    ScanSessionStatus,
)
from backend.app.modules.documents.storage import (
    get_uploads_root,
    register_document_upload,
    sanitize_filename,
)
from backend.app.services.scanner_presets import ScannerPreset, get_preset
from backend.app.scanner import DocumentScannerService, ScanResult
import shutil

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
SCANNER_STORAGE_DIR = "scanner"
# Use /api/uploads instead of /uploads to avoid conflict with root StaticFiles mount
UPLOAD_PREFIX = "/api/uploads/"


def _uploads_root() -> Path:
    return get_uploads_root()


def _session_dir(session_id: str) -> Path:
    root = _uploads_root()
    path = root / SCANNER_STORAGE_DIR / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _relative_path(path: Path) -> str:
    return path.relative_to(_uploads_root()).as_posix()


def _public_url(path: Path | str | None, cache_bust: bool = True) -> Optional[str]:
    """Generate public URL for uploaded file.
    
    Args:
        path: File path (relative or absolute Path, or string)
        cache_bust: If True, add timestamp query parameter to prevent caching
    """
    if not path:
        return None
    rel = path if isinstance(path, str) else _relative_path(path)
    url = f"{UPLOAD_PREFIX}{rel.lstrip('/')}"
    
    # Add cache-busting parameter to prevent browser from showing old images
    if cache_bust:
        # Use file modification time as cache buster
        try:
            full_path = _uploads_root() / rel
            if full_path.exists():
                import time
                mtime = int(full_path.stat().st_mtime)
                url = f"{url}?v={mtime}"
        except Exception:
            # Fallback to current timestamp if file doesn't exist or error
            import time
            url = f"{url}?v={int(time.time())}"
    
    return url


async def create_scan_session(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    candidate_id: str,
    document_type: str,
    preset_code: Optional[str] = None,
    document_kind_id: Optional[str] = None,
    expected_pages: Optional[Sequence[str]] = None,
    meta: Optional[dict] = None,
) -> ScanSession:
    # Auto-select preset based on document_type if not provided
    if not preset_code:
        from backend.app.services.scanner_presets import get_preset_for_doc_type, get_preset
        try:
            preset_obj = get_preset_for_doc_type(document_type)
            preset_code = preset_obj.code
        except (KeyError, ValueError) as e:
            import logging
            logger = logging.getLogger("backend.app.services.scanner")
            logger.error(f"[scanner] Failed to get preset for document_type={document_type}: {e}")
            # Try fallback to additional_document preset
            try:
                preset_obj = get_preset("additional_document")
                preset_code = "additional_document"
            except (KeyError, ValueError):
                raise HTTPException(
                    status_code=422,
                    detail=f"No scanner preset available for document type: {document_type}"
                )
    else:
        from backend.app.services.scanner_presets import get_preset
        try:
            preset_obj = get_preset(preset_code)
        except KeyError as e:
            import logging
            logger = logging.getLogger("backend.app.services.scanner")
            logger.error(f"[scanner] Preset not found: preset_code={preset_code}: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Scanner preset not found: {preset_code}"
            )
    
    preset = preset_obj
    pages = list(expected_pages or preset.expected_pages)
    if not pages:
        raise HTTPException(status_code=422, detail="preset_has_no_pages")

    session = ScanSession(
        tenant_id=str(tenant_id),
        candidate_id=candidate_id,
        document_type=document_type,
        document_kind_id=document_kind_id,
        preset_code=preset.code,
        expected_pages=pages,
        meta=meta or {},
        status=ScanSessionStatus.in_progress,
    )
    db.add(session)
    await db.flush()

    scan_pages: List[ScanPage] = []
    for idx, code in enumerate(pages):
        scan_pages.append(
            ScanPage(
                id=str(uuid4()),
                session_id=session.id,
                page_code=code,
                page_index=idx,
                status=ScanPageStatus.pending,
            )
        )
    db.add_all(scan_pages)
    await db.commit()
    return await get_scan_session(db, tenant_id=tenant_id, session_id=session.id)


async def get_scan_session(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    session_id: str,
    for_update: bool = False,
) -> ScanSession:
    stmt = (
        select(ScanSession)
        .where(ScanSession.id == session_id, ScanSession.tenant_id == str(tenant_id))
        .options(selectinload(ScanSession.pages))
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()
    session_obj = await db.scalar(stmt)
    if not session_obj:
        raise HTTPException(status_code=404, detail="scan_session_not_found")
    return session_obj


async def get_scan_session_by_id(
    db: AsyncSession,
    session_id: str,
    for_update: bool = False,
) -> ScanSession:
    """Load scan session by ID without tenant_id check (for public endpoints)."""
    stmt = (
        select(ScanSession)
        .where(ScanSession.id == session_id)
        .options(selectinload(ScanSession.pages))
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()
    session_obj = await db.scalar(stmt)
    if not session_obj:
        raise HTTPException(status_code=404, detail="scan_session_not_found")
    return session_obj


async def upload_scan_page(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    session_id: str,
    page_code: str,
    upload: UploadFile,
    rotation: int = 0,
    applied_filter: Optional[str] = None,
    meta: Optional[dict] = None,
) -> ScanSession:
    if upload.size and upload.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="file_too_large")
    session = await get_scan_session(db, tenant_id=tenant_id, session_id=session_id, for_update=True)
    
    # Allow re-upload if session is done or failed (user wants to retry)
    # Block only if session is currently processing
    if session.status == ScanSessionStatus.processing:
        raise HTTPException(status_code=409, detail="session_processing")

    matching_page = next((p for p in session.pages if p.page_code == page_code), None)
    if not matching_page:
        raise HTTPException(status_code=404, detail="page_not_found")

    # Allow re-uploading pages - delete old file if exists
    dest_dir = _session_dir(session.id)
    extension = Path(upload.filename or "scan.jpg").suffix or ".jpg"
    original_name = f"{page_code}-original{extension}"
    dest_path = dest_dir / sanitize_filename(original_name)

    # Remove old processed files if re-uploading
    if matching_page.original_path:
        old_orig_path = _uploads_root() / matching_page.original_path
        old_orig_dir = old_orig_path.parent
        
        # Delete original file
        if old_orig_path.exists():
            old_orig_path.unlink()
        
        # Remove processed files (all formats)
        if matching_page.processed_path:
            old_proc_path = _uploads_root() / matching_page.processed_path
            if old_proc_path.exists():
                old_proc_path.unlink()
        
        # Remove other format files (PNG, TIFF, PDF)
        for fmt in ['jpg', 'png', 'tiff', 'pdf']:
            fmt_path = old_orig_dir / f"{page_code}-processed.{fmt}"
            if fmt_path.exists():
                fmt_path.unlink()
        
        # Also check for any files with this page_code prefix
        try:
            for existing_file in old_orig_dir.glob(f"{page_code}-*"):
                if existing_file.is_file():
                    existing_file.unlink()
        except Exception:
            pass  # Ignore errors during cleanup

    data = await upload.read()
    dest_path.write_bytes(data)

    matching_page.original_path = _relative_path(dest_path)
    matching_page.status = ScanPageStatus.uploaded
    matching_page.rotation = rotation % 360
    matching_page.applied_filter = applied_filter
    matching_page.meta = meta or {}
    # Reset processed fields when re-uploading
    matching_page.processed_path = None
    matching_page.quality_score = None
    if matching_page.meta:
        matching_page.meta.pop("quality_level", None)
        matching_page.meta.pop("processed_pdf_path", None)
    matching_page.issues = None
    
    # Reset session status to in_progress if it was done/failed (allowing retry)
    if session.status in {ScanSessionStatus.done, ScanSessionStatus.failed}:
        session.status = ScanSessionStatus.in_progress

    await db.commit()
    return await get_scan_session(db, tenant_id=tenant_id, session_id=session_id)


async def process_scan_session(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    session_id: str,
) -> ScanSession:
    session = await get_scan_session(db, tenant_id=tenant_id, session_id=session_id, for_update=True)
    preset = get_preset(session.preset_code)

    pending = [page for page in session.pages if page.status in (ScanPageStatus.uploaded, ScanPageStatus.processing)]
    if not pending:
        raise HTTPException(status_code=409, detail="no_pages_to_process")

    session.status = ScanSessionStatus.processing
    await db.commit()

    try:
        # Use new professional DocumentScannerService
        target_dpi = getattr(preset, 'target_dpi', 300)
        scanner_service = DocumentScannerService(target_dpi=target_dpi)
        
        # Process all pages with new scanner
        all_extracted_fields = {}
        detected_doc_type = session.document_type
        session_dir = _session_dir(session.id)
        root = _uploads_root()
        
        for page in session.pages:
            # Skip if already processed successfully
            if page.status == ScanPageStatus.ok and page.processed_path:
                logger.debug(f"Skipping already processed page {page.page_code}")
                continue
            
            if page.original_path:
                orig_path = root / page.original_path
                if not orig_path.exists():
                    page.status = ScanPageStatus.error
                    page.issues = ["missing_file"]
                    continue
                
                # Apply rotation if needed before processing
                if page.rotation:
                    import cv2
                    image = cv2.imread(str(orig_path))
                    if image is not None:
                        rotations = (page.rotation // 90) % 4
                        for _ in range(rotations):
                            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                        # Save rotated image temporarily
                        temp_path = session_dir / f"{page.page_code}-rotated.jpg"
                        cv2.imwrite(str(temp_path), image)
                        orig_path = temp_path
                
                # Process with new scanner service
                try:
                    # Get enhancement mode from page meta if available
                    enhancement_mode = "standard"
                    if page.meta and "enhancement_mode" in page.meta:
                        enhancement_mode = page.meta["enhancement_mode"]
                    elif session.document_type in ("id_card", "driver_license", "passport"):
                        enhancement_mode = "photo"
                    elif session.document_type in ("decision", "contract"):
                        enhancement_mode = "strong"
                    
                    # Get manual contour from page meta if available
                    manual_contour = None
                    if page.meta and "manual_contour" in page.meta:
                        manual_contour = page.meta["manual_contour"]
                    
                    scan_result = scanner_service.scan_document(
                        input_path=orig_path,
                        output_dir=session_dir,
                        doc_type_hint=session.document_type,
                        enhancement_mode=enhancement_mode,
                        manual_contour=manual_contour
                    )
                    
                    # Save processed image as JPG (required for frontend display)
                    # The scanner service should have saved processed images, but we need to map them to page codes
                    processed_img_path = session_dir / f"{page.page_code}-processed.jpg"
                    
                    # Check if scanner saved a processed image (page_1_processed.jpg, etc.)
                    # For single page documents, use page_1_processed.jpg
                    scanner_processed_path = session_dir / "page_1_processed.jpg"
                    if scanner_processed_path.exists():
                        # Copy to page-specific name
                        import shutil
                        shutil.copy2(scanner_processed_path, processed_img_path)
                        page.processed_path = _relative_path(processed_img_path)
                    else:
                        # Fallback: process image directly if scanner didn't save it
                        try:
                            import cv2
                            image = cv2.imread(str(orig_path))
                            if image is not None:
                                from backend.app.scanner.preprocess import ImagePreprocessor
                                preprocessor = ImagePreprocessor(target_dpi=target_dpi)
                                processed_image = preprocessor.process(image)
                                cv2.imwrite(str(processed_img_path), processed_image, [cv2.IMWRITE_JPEG_QUALITY, 92])
                                page.processed_path = _relative_path(processed_img_path)
                        except Exception as e:
                            import logging
                            logger = logging.getLogger("backend.app.services.scanner")
                            logger.warning(f"Failed to save processed image for {page.page_code}: {e}")
                    
                    # Update status and quality metrics
                    if scan_result.quality_metrics:
                        page.quality_score = scan_result.quality_metrics.get("overall_score")
                        if not page.meta:
                            page.meta = {}
                        page.meta["quality_level"] = scan_result.quality_metrics.get("quality_level", "unknown")
                        page.issues = scan_result.quality_metrics.get("issues", [])
                    
                    # Determine page status based on quality
                    quality_level = page.meta.get("quality_level", "unknown") if page.meta else "unknown"
                    page.status = (
                        ScanPageStatus.needs_review
                        if quality_level in ("very_poor", "poor") or (page.issues and len(page.issues) > 0)
                        else ScanPageStatus.ok
                    )
                    
                    # Collect extracted fields and update document type from first page
                    if len(all_extracted_fields) == 0 and scan_result.fields:
                        all_extracted_fields.update(scan_result.fields)
                    
                    # Update detected document type (use first successful classification)
                    if scan_result.document_type and scan_result.document_type != "unknown":
                        # Get confidence from quality metrics
                        confidence = 0.7  # Default
                        if scan_result.quality_metrics:
                            confidence = scan_result.quality_metrics.get('classification_confidence', 0.7)
                        
                        # Always update detected_doc_type from scan result
                        detected_doc_type = scan_result.document_type
                        
                        # Update session.document_type if confidence is high enough
                        # This enables auto-detection
                        if confidence >= 0.6:
                            old_doc_type = session.document_type
                            session.document_type = detected_doc_type
                            import logging
                            logger = logging.getLogger("backend.app.services.scanner")
                            logger.info(f"Auto-detected document type: {old_doc_type} -> {detected_doc_type} (confidence: {confidence:.2f})")
                    
                    page.updated_at = datetime.now(timezone.utc)
                    
                except Exception as e:
                    import logging
                    logger = logging.getLogger("backend.app.services.scanner")
                    logger.error(f"Failed to process page {page.page_code}: {e}", exc_info=True)
                    page.status = ScanPageStatus.error
                    page.issues = ["processing_failed"]
        
        # Store extracted data in session meta
        if not session.meta:
            session.meta = {}
        session.meta["extracted_fields"] = all_extracted_fields
        session.meta["detected_document_type"] = detected_doc_type
        
        session.status = ScanSessionStatus.done
        session.processed_at = datetime.now(timezone.utc)
        session.failed_reason = None
        session.quality_summary = _build_summary(session.pages)
    except Exception as exc:  # pragma: no cover - safety fallback
        session.status = ScanSessionStatus.failed
        session.failed_reason = str(exc)
        raise HTTPException(status_code=500, detail="processing_failed") from exc
    finally:
        await db.commit()
    return await get_scan_session(db, tenant_id=tenant_id, session_id=session_id)


def _process_page(page: ScanPage, preset: ScannerPreset) -> None:
    root = _uploads_root()
    if not page.original_path:
        page.status = ScanPageStatus.error
        page.issues = ["missing_file"]
        return
    orig_path = root / page.original_path  # type: ignore[arg-type]
    image = cv2.imread(str(orig_path))
    if image is None:
        page.status = ScanPageStatus.error
        page.issues = ["file_not_readable"]
        return

    if page.rotation:
        rotations = (page.rotation // 90) % 4
        for _ in range(rotations):
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)

    # Use new professional preprocessing pipeline
    target_dpi = getattr(preset, 'target_dpi', 300)
    preprocessor = ImagePreprocessor(target_dpi=target_dpi)
    processed = preprocessor.process(image)
    
    # Apply custom filter if specified (after preprocessing)
    if page.applied_filter:
        processed = _apply_filter(processed, page.applied_filter)
    
    # Calculate quality metrics
    gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = gray.mean() / 255.0
    
    issues: List[str] = []
    if sharpness < preset.min_sharpness:
        issues.append("too_blurry")
    if brightness < preset.min_brightness:
        issues.append("too_dark")
    elif brightness > preset.max_brightness:
        issues.append("too_bright")
    
    score = _quality_score(sharpness, brightness, preset)
    quality_level = _quality_level(score, sharpness, brightness, preset)
    
    # Save in multiple formats (JPG, PNG, TIFF)
    session_dir = _session_dir(page.session_id)
    output_base = session_dir / page.page_code
    jpg_path = output_base.parent / f"{page.page_code}-processed.jpg"
    png_path = output_base.parent / f"{page.page_code}-processed.png"
    tiff_path = output_base.parent / f"{page.page_code}-processed.tiff"
    
    cv2.imwrite(str(jpg_path), processed, [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(str(png_path), processed, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    cv2.imwrite(str(tiff_path), processed)
    
    # Use JPG as default processed_path
    output_path = jpg_path

    # Save processed path (JPG is default)
    page.processed_path = _relative_path(output_path)
    
    # Generate PDF if Pillow is available (save path in meta)
    pdf_path = output_base.parent / f"{page.page_code}-processed.pdf"
    try:
        from PIL import Image
        pil_image = Image.fromarray(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB))
        target_dpi = getattr(preset, 'target_dpi', 300)
        pil_image.save(str(pdf_path), "PDF", resolution=target_dpi)
        if not page.meta:
            page.meta = {}
        page.meta["processed_pdf_path"] = _relative_path(pdf_path)
    except ImportError:
        pass
    except Exception:
        pass
    
    # Don't reject pages - always process them, even if document detection failed
    # User can manually review if needed
    page.status = (
        ScanPageStatus.needs_review
        if issues or quality_level in ("very_poor", "poor")
        else ScanPageStatus.ok
    )
    page.quality_score = score
    if not page.meta:
        page.meta = {}
    page.meta["quality_level"] = quality_level
    page.issues = issues
    page.updated_at = datetime.now(timezone.utc)


def _apply_filter(image, filter_name: Optional[str]) -> np.ndarray:
    """Apply image filter (grayscale, binarization, etc.)."""
    if not filter_name:
        return image
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    
    if filter_name == "grayscale":
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    elif filter_name == "binarization":
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    elif filter_name == "binarization_adaptive":
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    elif filter_name == "binarization_color":
        # Color binarization - preserve color but enhance contrast
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    elif filter_name == "antialiasing":
        # Antialiasing filter - smooth edges
        return cv2.bilateralFilter(image, 9, 75, 75)
    elif filter_name == "magic_color":
        # Magic Color filter - enhance colors and contrast
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    return image


def _quality_level(score: float, sharpness: float, brightness: float, preset: ScannerPreset) -> str:
    """Determine quality level: very_poor, poor, fair, good, excellent."""
    if score < 0.3:
        return "very_poor"
    elif score < 0.5:
        return "poor"
    elif score < 0.7:
        return "fair"
    elif score < 0.9:
        return "good"
    else:
        return "excellent"


def _quality_score(sharpness: float, brightness: float, preset: ScannerPreset) -> float:
    sharp_component = min(1.0, max(0.0, sharpness / max(preset.min_sharpness, 1)))
    brightness_center = (preset.min_brightness + preset.max_brightness) / 2
    brightness_range = preset.max_brightness - preset.min_brightness
    if brightness_range <= 0:
        brightness_component = 1.0
    else:
        brightness_component = 1.0 - (abs(brightness - brightness_center) / brightness_range)
        brightness_component = max(0.0, min(1.0, brightness_component))
    return round((0.65 * sharp_component) + (0.35 * brightness_component), 3)


def _build_summary(pages: Sequence[ScanPage]) -> dict:
    summary = {}
    for page in pages:
        key = page.status.value if isinstance(page.status, ScanPageStatus) else str(page.status)
        summary[key] = summary.get(key, 0) + 1
    summary["total"] = len(pages)
    summary["ok_ratio"] = round(
        summary.get(ScanPageStatus.ok.value, 0) / len(pages), 3
    ) if pages else 0.0
    return summary


async def attach_scan_session(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    session_id: str,
    uploaded_by: Optional[str],
) -> dict:
    session = await get_scan_session(db, tenant_id=tenant_id, session_id=session_id, for_update=True)
    if session.status != ScanSessionStatus.done:
        raise HTTPException(status_code=409, detail="session_not_processed")
    if session.attached_at:
        raise HTTPException(status_code=409, detail="session_already_attached")

    attached_docs: List[dict] = []
    root = _uploads_root()
    for page in session.pages:
        if not page.processed_path:
            continue
        source_path = root / page.processed_path
        if not source_path.exists():
            continue
        doc = Document(
            tenant_id=str(tenant_id),
            candidate_id=session.candidate_id,
            doc_type=session.document_type,
            kind=DocumentKind.driver,
            custom_name=f"{session.document_type}:{page.page_code}",
            status=DocumentStatus.received,
            requested_from=DocumentRequestedFrom.driver,
            source="scanner",
            meta={"scanner_page_id": page.id, "issues": page.issues or []},
        )
        db.add(doc)
        await db.flush()

        doc_dir = root / "documents" / doc.id
        doc_dir.mkdir(parents=True, exist_ok=True)
        dest_path = doc_dir / f"{sanitize_filename(page.page_code)}.jpg"
        shutil.copy2(source_path, dest_path)
        rel_doc_path = dest_path.relative_to(root).as_posix()
        stat = dest_path.stat()

        await register_document_upload(
            document_id=doc.id,
            rel_path=rel_doc_path,
            original_name=dest_path.name,
            size=stat.st_size,
            mime="image/jpeg",
            uploaded_by=uploaded_by,
        )

        attached_docs.append(
            {
                "candidate_document_id": doc.id,
                "page_code": page.page_code,
                "url": _public_url(rel_doc_path),
            }
        )

    session.attached_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return {"attached_documents": attached_docs}


def serialize_scan_session(session: ScanSession) -> dict:
    return {
        "id": session.id,
        "candidate_id": session.candidate_id,
        "document_type": session.document_type,
        "document_kind_id": session.document_kind_id,
        "preset_code": session.preset_code,
        "status": session.status.value,
        "expected_pages": session.expected_pages,
        "quality_summary": session.quality_summary or {},
        "processed_at": session.processed_at,
        "attached_at": session.attached_at,
        "failed_reason": session.failed_reason,
        "can_attach_to_candidate": session.status == ScanSessionStatus.done and session.attached_at is None,
        "pages": [
            {
                "id": page.id,
                "page_code": page.page_code,
                "status": page.status.value,
                "quality_score": page.quality_score,
                "quality_level": (page.meta or {}).get("quality_level", "unknown"),
                "issues": page.issues or [],
                "rotation": page.rotation,
                "applied_filter": page.applied_filter,
                "preview_url": _public_url(page.processed_path) if page.processed_path else _public_url(page.original_path),
                "original_url": _public_url(page.original_path),
                "export_urls": {
                    "jpg": _public_url(page.processed_path),
                    "png": _public_url(str(page.processed_path).replace("-processed.jpg", "-processed.png") if page.processed_path else None),
                    "tiff": _public_url(str(page.processed_path).replace("-processed.jpg", "-processed.tiff") if page.processed_path else None),
                    "pdf": _public_url((page.meta or {}).get("processed_pdf_path")) if page.meta and "processed_pdf_path" in page.meta else None,
                } if page.processed_path else {},
            }
            for page in sorted(session.pages, key=lambda p: p.page_index)
        ],
        "upload_limits": {"max_pages": len(session.expected_pages), "max_file_size_mb": MAX_FILE_SIZE_BYTES // (1024 * 1024)},
        # Include extracted fields if available
        "extracted_fields": (session.meta or {}).get("extracted_fields", {}),
        "detected_document_type": (session.meta or {}).get("detected_document_type", session.document_type),
    }
