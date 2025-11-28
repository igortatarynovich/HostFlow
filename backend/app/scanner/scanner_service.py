"""
Main Document Scanner Service - orchestrates all components.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

from .classify import DocumentClassifier
from .contour_6points import Contour6Points
from .document_types import is_passport_type
from .export import DocumentExporter
from .extract_fields import FieldExtractor
from .frame_quality import FrameQualityAnalyzer
from .passport_processor import PassportProcessor
from .pdf_builder import PDFBuilder
from .preprocess import ImagePreprocessor
from .utils import load_image, pdf_to_images
from .validators import DocumentValidator

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of document scanning."""
    document_type: str
    pages: int
    fields: Dict[str, str]
    pdf_path: Optional[str] = None
    quality_metrics: Optional[Dict] = None
    validation_errors: Optional[Dict[str, List[str]]] = None


class DocumentScannerService:
    """Main service for document scanning, processing, and data extraction."""
    
    def __init__(self, target_dpi: int = 300):
        self.target_dpi = target_dpi
        self.preprocessor = ImagePreprocessor(target_dpi=target_dpi)
        self.classifier = DocumentClassifier()
        self.field_extractor = FieldExtractor()
        self.pdf_builder = PDFBuilder(target_dpi=target_dpi)
        self.validator = DocumentValidator()
        self.passport_processor = PassportProcessor(target_dpi=target_dpi)
        self.quality_analyzer = FrameQualityAnalyzer()
        self.exporter = DocumentExporter(target_dpi=target_dpi)
    
    def scan_document(
        self,
        input_path: Path | str,
        output_dir: Optional[Path] = None,
        doc_type_hint: Optional[str] = None,
        enhancement_mode: str = "standard",
        manual_contour: Optional[dict] = None
    ) -> ScanResult:
        """
        Scan and process a document.
        
        Args:
            input_path: Path to input file (image or PDF)
            output_dir: Optional directory for output files
            doc_type_hint: Optional hint for document type
            
        Returns:
            ScanResult with processed document and extracted data
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        logger.info(f"Scanning document: {input_path}")
        
        # Setup output directory
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load pages
        if input_path.suffix.lower() == ".pdf":
            pages = pdf_to_images(input_path)
        else:
            image = load_image(input_path)
            if image is None:
                raise ValueError(f"Failed to load image: {input_path}")
            pages = [image]
        
        if not pages:
            raise ValueError("No pages found in document")
        
        logger.info(f"Loaded {len(pages)} pages")
        
        # Try to classify from filename if no hint provided
        if not doc_type_hint:
            doc_type_hint = self.classifier.classify_from_filename(input_path.name)
        
        # Process first page for classification
        first_page_processed = self.preprocessor.process(pages[0])
        
        # Classify document type - always classify, even if hint provided
        # This enables auto-detection
        doc_type, confidence = self.classifier.classify(first_page_processed)
        
        # If classification failed or confidence is low, try with OCR
        if doc_type == "unknown" or confidence < 0.5:
            try:
                import pytesseract
                ocr_text = pytesseract.image_to_string(first_page_processed, lang="eng+pol+rus")
                doc_type_ocr, confidence_ocr = self.classifier.classify(first_page_processed, ocr_text=ocr_text)
                if confidence_ocr > confidence:
                    doc_type = doc_type_ocr
                    confidence = confidence_ocr
            except Exception as e:
                logger.warning(f"OCR classification failed: {e}")
        
        # Use hint only if classification failed completely
        if doc_type == "unknown" and doc_type_hint:
            doc_type = doc_type_hint
            confidence = 0.8
            logger.info(f"Using hint as fallback: {doc_type}")
        
        logger.info(f"Classified as: {doc_type} (confidence: {confidence:.2f})")
        
        # Special handling for passports
        if is_passport_type(doc_type):
            return self._process_passport(input_path, output_dir, doc_type)
        
        # Process all pages
        processed_pages: List[np.ndarray] = []
        all_fields: Dict[str, str] = {}
        processed_image_paths: List[Path] = []
        
        for i, page in enumerate(pages):
            logger.debug(f"Processing page {i + 1}/{len(pages)}")
            
            # Normalize page (pass doc_type for better detection)
            # Use provided enhancement_mode or fall back to document type based selection
            final_enhancement_mode = enhancement_mode
            if final_enhancement_mode == "standard":
                if doc_type in ("id_card", "driver_license", "passport"):
                    final_enhancement_mode = "photo"
                elif doc_type in ("decision", "contract"):
                    final_enhancement_mode = "strong"
            
            processed = self.preprocessor.process(
                page, 
                doc_type_hint=doc_type if i == 0 else None,
                enhancement_mode=final_enhancement_mode,
                manual_contour=manual_contour if i == 0 else None  # Use manual contour only for first page
            )
            processed_pages.append(processed)
            
            # Save processed image as JPG (for frontend display)
            if output_dir:
                try:
                    import cv2
                    img_path = output_dir / f"page_{i+1}_processed.jpg"
                    # Use higher quality for better cameras (95 instead of 92)
                    cv2.imwrite(str(img_path), processed, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    processed_image_paths.append(img_path)
                    logger.debug(f"Saved processed image: {img_path}")
                except Exception as e:
                    logger.warning(f"Failed to save processed image for page {i + 1}: {e}")
            
            # Extract fields (focus on first few pages)
            if i < 3:  # First 3 pages typically have data
                try:
                    fields = self.field_extractor.extract(processed, doc_type)
                    # Merge fields (later pages may have better extraction)
                    for key, value in fields.items():
                        if value and (key not in all_fields or not all_fields[key]):
                            all_fields[key] = value
                except Exception as e:
                    logger.warning(f"Field extraction failed for page {i + 1}: {e}")
        
        # Validate fields
        validation_errors = self.validator.validate_fields(all_fields, doc_type)
        
        # Quality metrics
        quality_metrics = self.validator.validate_image_quality(processed_pages[0])
        
        # Build PDF
        pdf_path = None
        if output_dir:
            pdf_path = output_dir / f"{input_path.stem}_processed.pdf"
            success = self.pdf_builder.build_pdf(processed_pages, pdf_path, title=doc_type)
            if success:
                pdf_path = str(pdf_path)
            else:
                pdf_path = None
        
        # Add classification confidence to quality metrics
        if quality_metrics is None:
            quality_metrics = {}
        quality_metrics["classification_confidence"] = confidence
        
        # Build result
        result = ScanResult(
            document_type=doc_type,
            pages=len(processed_pages),
            fields=all_fields,
            pdf_path=pdf_path,
            quality_metrics=quality_metrics,
            validation_errors=validation_errors if validation_errors else None,
        )
        
        logger.info(f"Scan complete: {doc_type}, {len(processed_pages)} pages, {len(all_fields)} fields")
        return result
    
    def _process_passport(
        self,
        input_path: Path,
        output_dir: Optional[Path],
        doc_type: str
    ) -> ScanResult:
        """Process passport with special handling for all pages."""
        logger.info("Processing as passport (all pages)")
        
        # Use passport processor
        passport_result = self.passport_processor.process_passport(input_path, output_dir)
        
        # Build PDF
        pdf_path = None
        if output_dir and "processed_images" in passport_result:
            pdf_path = output_dir / f"{input_path.stem}_processed.pdf"
            success = self.pdf_builder.build_pdf(
                passport_result["processed_images"],
                pdf_path,
                title="Passport"
            )
            if success:
                pdf_path = str(pdf_path)
            else:
                pdf_path = None
        
        # Validate fields
        validation_errors = self.validator.validate_fields(passport_result["fields"], doc_type)
        
        # Quality metrics from first page
        quality_metrics = None
        if passport_result["processed_images"]:
            quality_metrics = self.validator.validate_image_quality(
                passport_result["processed_images"][0]
            )
        
        return ScanResult(
            document_type=doc_type,
            pages=passport_result["pages"],
            fields=passport_result["fields"],
            pdf_path=pdf_path,
            quality_metrics=quality_metrics,
            validation_errors=validation_errors if validation_errors else None,
        )
    
    def scan_to_json(
        self,
        input_path: Path | str,
        output_dir: Optional[Path] = None,
        doc_type_hint: Optional[str] = None
    ) -> Dict:
        """
        Scan document and return JSON result.
        
        Returns:
            Dictionary with document_type, pages, and fields
        """
        result = self.scan_document(input_path, output_dir, doc_type_hint)
        
        return {
            "document_type": result.document_type,
            "pages": result.pages,
            "fields": result.fields,
        }

