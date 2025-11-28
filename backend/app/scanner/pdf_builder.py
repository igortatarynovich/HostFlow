"""
Build high-quality PDF documents from processed images.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class PDFBuilder:
    """Build PDF documents from processed images."""
    
    def __init__(self, target_dpi: int = 300):
        self.target_dpi = target_dpi
        # A4 dimensions at target DPI
        self.a4_width = int(210 * target_dpi / 25.4)  # 210mm in pixels
        self.a4_height = int(297 * target_dpi / 25.4)  # 297mm in pixels
    
    def build_pdf(
        self,
        images: List[np.ndarray],
        output_path: Path | str,
        title: Optional[str] = None
    ) -> bool:
        """
        Build PDF from list of images.
        
        Args:
            images: List of processed images (A4, 300 DPI)
            output_path: Path to output PDF
            title: Optional PDF title
            
        Returns:
            True if successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not images:
                logger.error("No images provided for PDF")
                return False
            
            logger.info(f"Building PDF with {len(images)} pages to {output_path}")
            
            # Convert OpenCV images to PIL Images
            pil_images = []
            for i, img in enumerate(images):
                # Ensure image is A4 size
                if img.shape[:2] != (self.a4_height, self.a4_width):
                    img = self._resize_to_a4(img)
                
                # Convert BGR to RGB
                if len(img.shape) == 3:
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                else:
                    rgb_img = img
                
                pil_img = Image.fromarray(rgb_img)
                pil_images.append(pil_img)
            
            # Save as PDF with high quality
            # Use optimize=False and quality=100 for best quality
            save_kwargs = {
                "resolution": self.target_dpi,
                "title": title or "Document",
                "optimize": False,  # Don't optimize - preserve quality
            }
            
            if len(pil_images) == 1:
                pil_images[0].save(
                    str(output_path),
                    "PDF",
                    **save_kwargs
                )
            else:
                # Multi-page PDF
                pil_images[0].save(
                    str(output_path),
                    "PDF",
                    save_all=True,
                    append_images=pil_images[1:],
                    **save_kwargs
                )
            
            logger.info(f"PDF saved successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to build PDF: {e}")
            return False
    
    def _resize_to_a4(self, image: np.ndarray) -> np.ndarray:
        """Resize image to A4 format at target DPI."""
        h, w = image.shape[:2]
        
        # Calculate aspect ratios
        image_aspect = w / h
        a4_aspect = self.a4_width / self.a4_height
        
        # Fit image to A4 while preserving aspect ratio
        if abs(image_aspect - a4_aspect) < 0.01:
            # Already A4 aspect, just resize
            return cv2.resize(
                image, (self.a4_width, self.a4_height),
                interpolation=cv2.INTER_LANCZOS4
            )
        
        # Fit to A4
        if image_aspect > a4_aspect:
            # Image is wider, fit to width
            new_w = self.a4_width
            new_h = int(self.a4_height * (h / w) * (w / self.a4_width))
        else:
            # Image is taller, fit to height
            new_h = self.a4_height
            new_w = int(self.a4_width * (w / h) * (h / self.a4_height))
        
        resized = cv2.resize(
            image, (new_w, new_h),
            interpolation=cv2.INTER_LANCZOS4
        )
        
        # Create A4 canvas with white background
        a4_image = np.ones((self.a4_height, self.a4_width, 3), dtype=np.uint8) * 255
        
        # Center the resized image
        y_offset = (self.a4_height - new_h) // 2
        x_offset = (self.a4_width - new_w) // 2
        a4_image[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
        
        return a4_image

