"""
Document type classification based on text content, MRZ, structure, and format.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

import pytesseract

from .document_types import DOCUMENT_TYPES, DocumentTypeInfo, get_document_type_info

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Classify document type based on various features."""
    
    def __init__(self):
        self.mrz_pattern = re.compile(
            r'[A-Z0-9<]{30,}[\n\r]+[A-Z0-9<]{30,}',  # MRZ typically has 2-3 lines
            re.MULTILINE
        )
    
    def classify(self, image, ocr_text: Optional[str] = None) -> Tuple[str, float]:
        """
        Classify document type from image.
        
        Args:
            image: Preprocessed image (numpy array)
            ocr_text: Optional pre-extracted OCR text
            
        Returns:
            Tuple of (document_type, confidence)
        """
        # Extract text if not provided
        if ocr_text is None:
            try:
                ocr_text = pytesseract.image_to_string(image, lang="eng+pol+rus")
            except Exception as e:
                logger.warning(f"OCR failed for classification: {e}")
                ocr_text = ""
        
        ocr_text_lower = ocr_text.lower()
        
        # Check for MRZ (strong indicator of passport/ID)
        has_mrz = self._detect_mrz(ocr_text)
        
        # Score each document type
        scores: Dict[str, float] = {}
        
        for doc_type, info in DOCUMENT_TYPES.items():
            score = 0.0
            
            # Keyword matching (improved scoring)
            keyword_matches = sum(1 for keyword in info.keywords if keyword.lower() in ocr_text_lower)
            if keyword_matches > 0:
                # More keywords = higher score, but with diminishing returns
                score += min(1.0, keyword_matches * 0.4)
            
            # MRZ support check
            if has_mrz and info.mrz_supported:
                score += 0.5  # Strong indicator
            elif has_mrz and not info.mrz_supported:
                score -= 0.3  # Penalize if MRZ found but type doesn't support it
            
            # Structure-based hints
            if info.is_passport:
                # Passports often have "PASSPORT" or country codes
                if re.search(r'\bP[A-Z]{2}\d{6,9}\b', ocr_text.upper()):  # Passport number pattern
                    score += 0.4
                if re.search(r'\b[A-Z]{3}\b', ocr_text.upper()):  # Country codes
                    score += 0.2
                if "passport" in ocr_text_lower or "paszport" in ocr_text_lower:
                    score += 0.3
            
            # Polish-specific patterns
            if "prawo jazdy" in ocr_text_lower or "kategoria" in ocr_text_lower:
                if doc_type == "driver_license":
                    score += 0.5
            if "karta pobytu" in ocr_text_lower or "trc" in ocr_text_lower:
                if doc_type == "residence_permit":
                    score += 0.5
            if "decyzja" in ocr_text_lower:
                if doc_type == "decision":
                    score += 0.5
            if "tacho" in ocr_text_lower or "tachograf" in ocr_text_lower:
                if doc_type == "tachograph_card":
                    score += 0.5
            if "adr" in ocr_text_lower:
                if doc_type == "adr_certificate":
                    score += 0.5
            if "kp" in ocr_text_lower or "kwalifikacji" in ocr_text_lower:
                if doc_type == "qualification_card":
                    score += 0.5
            
            scores[doc_type] = max(0.0, score)
        
        # Find best match
        if not scores or max(scores.values()) == 0:
            # Default to passport if MRZ found, otherwise unknown
            if has_mrz:
                return "passport", 0.5
            return "unknown", 0.0
        
        best_type = max(scores.items(), key=lambda x: x[1])
        confidence = min(1.0, best_type[1])
        
        # Normalize confidence (if max score is low, reduce confidence)
        if best_type[1] < 0.3:
            confidence *= 0.5
        
        logger.info(f"Classified as {best_type[0]} with confidence {confidence:.2f}")
        return best_type[0], confidence
    
    def _detect_mrz(self, text: str) -> bool:
        """Detect if text contains MRZ (Machine Readable Zone)."""
        # MRZ typically has 2-3 lines of 30+ characters with < characters
        if self.mrz_pattern.search(text):
            return True
        
        # Alternative: look for lines with many < characters (MRZ filler)
        lines = text.split('\n')
        mrz_like_lines = 0
        for line in lines:
            if len(line) >= 30 and line.count('<') >= 5:
                mrz_like_lines += 1
        
        return mrz_like_lines >= 2
    
    def classify_from_filename(self, filename: str) -> Optional[str]:
        """Try to classify from filename hints."""
        filename_lower = filename.lower()
        
        # Direct matches
        for doc_type, info in DOCUMENT_TYPES.items():
            for keyword in info.keywords:
                if keyword.lower() in filename_lower:
                    return doc_type
        
        # Pattern matches
        if "passport" in filename_lower or "paszport" in filename_lower:
            return "passport"
        if "trc" in filename_lower or "karta pobytu" in filename_lower:
            return "residence_permit"
        if "prawo jazdy" in filename_lower or "license" in filename_lower:
            return "driver_license"
        if "kp" in filename_lower or "kwalifikacji" in filename_lower:
            return "qualification_card"
        if "adr" in filename_lower:
            return "adr_certificate"
        if "tacho" in filename_lower:
            return "tachograph_card"
        if "lekarskie" in filename_lower or "medical" in filename_lower:
            return "medical_certificate"
        if "psycho" in filename_lower:
            return "psychological_test"
        if "decyzja" in filename_lower or "decision" in filename_lower:
            return "decision"
        
        return None

