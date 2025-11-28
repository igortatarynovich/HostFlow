"""
Validation utilities for document scanner.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DocumentValidator:
    """Validate extracted fields and document quality."""
    
    def validate_fields(self, fields: Dict[str, str], doc_type: str) -> Dict[str, List[str]]:
        """
        Validate extracted fields.
        
        Args:
            fields: Extracted fields dictionary
            doc_type: Document type
            
        Returns:
            Dictionary with validation errors by field name
        """
        errors: Dict[str, List[str]] = {}
        
        # Common validations
        if "document_number" in fields:
            doc_num = fields["document_number"]
            if len(doc_num) < 3:
                errors.setdefault("document_number", []).append("Document number too short")
        
        # Date validations
        for date_field in ["issue_date", "expiry_date", "date_of_birth"]:
            if date_field in fields:
                date_str = fields[date_field]
                if not self._is_valid_date(date_str):
                    errors.setdefault(date_field, []).append(f"Invalid date format: {date_str}")
        
        # Document-specific validations
        if doc_type == "passport":
            if "document_number" not in fields or not fields["document_number"]:
                errors.setdefault("document_number", []).append("Passport number is required")
        
        return errors
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if date string is in valid format (YYYY-MM-DD)."""
        try:
            parts = date_str.split("-")
            if len(parts) != 3:
                return False
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
                return False
            return True
        except (ValueError, IndexError):
            return False
    
    def validate_image_quality(self, image) -> Dict[str, any]:
        """
        Validate image quality metrics.
        
        Args:
            image: Image array
            
        Returns:
            Dictionary with quality metrics
        """
        import cv2
        import numpy as np
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Sharpness (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Brightness
        brightness = gray.mean() / 255.0
        
        # Contrast
        contrast = gray.std() / 255.0
        
        return {
            "sharpness": float(laplacian_var),
            "brightness": float(brightness),
            "contrast": float(contrast),
            "is_acceptable": laplacian_var > 50 and 0.2 < brightness < 0.9,
        }

