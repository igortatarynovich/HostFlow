"""
Specialized processor for passports - handles all pages including empty ones.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
from PIL import Image

from .extract_fields import FieldExtractor
from .preprocess import ImagePreprocessor
from .utils import load_image, pdf_to_images

logger = logging.getLogger(__name__)


class PassportProcessor:
    """Process complete passports including all pages."""
    
    def __init__(self, target_dpi: int = 300):
        self.preprocessor = ImagePreprocessor(target_dpi=target_dpi)
        self.field_extractor = FieldExtractor()
        self.target_dpi = target_dpi
    
    def process_passport(
        self,
        input_path: Path | str,
        output_dir: Optional[Path] = None
    ) -> Dict:
        """
        Process complete passport (all pages).
        
        Args:
            input_path: Path to passport PDF or image
            output_dir: Optional directory for output files
            
        Returns:
            Dictionary with processed pages and extracted fields
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Passport file not found: {input_path}")
        
        logger.info(f"Processing passport: {input_path}")
        
        # Load all pages
        if input_path.suffix.lower() == ".pdf":
            pages = pdf_to_images(input_path)
        else:
            image = load_image(input_path)
            if image is None:
                raise ValueError(f"Failed to load image: {input_path}")
            pages = [image]
        
        if not pages:
            raise ValueError("No pages found in passport")
        
        logger.info(f"Found {len(pages)} pages in passport")
        
        # Process each page
        processed_pages: List[np.ndarray] = []
        all_fields: Dict[str, str] = {}
        
        for i, page in enumerate(pages):
            logger.debug(f"Processing page {i + 1}/{len(pages)}")
            
            # Normalize page
            processed = self.preprocessor.process(page)
            processed_pages.append(processed)
            
            # Extract fields from first few pages (usually contain data)
            if i < 3:  # First 3 pages typically have data
                try:
                    fields = self.field_extractor.extract(processed, "passport")
                    # Merge fields (later pages may have better extraction)
                    for key, value in fields.items():
                        if value and (key not in all_fields or not all_fields[key]):
                            all_fields[key] = value
                except Exception as e:
                    logger.warning(f"Field extraction failed for page {i + 1}: {e}")
        
        # Build result
        result = {
            "pages": len(processed_pages),
            "fields": all_fields,
            "processed_images": processed_pages,
        }
        
        # Save processed pages if output directory provided
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for i, processed_img in enumerate(processed_pages):
                page_path = output_dir / f"page_{i + 1:02d}.jpg"
                cv2.imwrite(str(page_path), processed_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                logger.debug(f"Saved processed page {i + 1} to {page_path}")
        
        logger.info(f"Passport processing complete: {len(processed_pages)} pages, {len(all_fields)} fields extracted")
        return result

