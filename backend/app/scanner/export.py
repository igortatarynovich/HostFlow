"""
Export processed documents to various formats (JPG, PNG, PDF).
Includes metadata support.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
from PIL import Image, PngImagePlugin

logger = logging.getLogger(__name__)


class DocumentExporter:
    """Export documents to various formats with metadata."""
    
    def __init__(self, target_dpi: int = 300):
        self.target_dpi = target_dpi
    
    def export_jpg(
        self,
        image: np.ndarray,
        output_path: Path | str,
        quality: int = 95,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Export image as JPEG."""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert BGR to RGB if needed
            if len(image.shape) == 3:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = image
            
            pil_image = Image.fromarray(rgb_image)
            
            # Add metadata if provided
            if metadata:
                exif = pil_image.getexif()
                # Add custom metadata (JPEG doesn't support all metadata types)
                # Store in a separate JSON file
                metadata_path = output_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)
            
            # Save JPEG
            pil_image.save(
                str(output_path),
                "JPEG",
                quality=quality,
                optimize=False,
            )
            
            logger.info(f"Exported JPEG: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export JPEG: {e}")
            return False
    
    def export_png(
        self,
        image: np.ndarray,
        output_path: Path | str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Export image as PNG with metadata."""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert BGR to RGB if needed
            if len(image.shape) == 3:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = image
            
            pil_image = Image.fromarray(rgb_image)
            
            # Add metadata to PNG
            if metadata:
                meta = PngImagePlugin.PngInfo()
                for key, value in metadata.items():
                    meta.add_text(str(key), str(value))
                pil_image.save(str(output_path), "PNG", pnginfo=meta)
            else:
                pil_image.save(str(output_path), "PNG")
            
            logger.info(f"Exported PNG: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export PNG: {e}")
            return False
    
    def export_pdf(
        self,
        images: List[np.ndarray],
        output_path: Path | str,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Export images as PDF."""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not images:
                logger.error("No images provided for PDF")
                return False
            
            # Convert OpenCV images to PIL Images
            pil_images = []
            for img in images:
                if len(img.shape) == 3:
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                else:
                    rgb_img = img
                pil_img = Image.fromarray(rgb_img)
                pil_images.append(pil_img)
            
            # Save as PDF
            if len(pil_images) == 1:
                pil_images[0].save(
                    str(output_path),
                    "PDF",
                    resolution=self.target_dpi,
                    title=title or "Document",
                    optimize=False,
                )
            else:
                pil_images[0].save(
                    str(output_path),
                    "PDF",
                    resolution=self.target_dpi,
                    title=title or "Document",
                    save_all=True,
                    append_images=pil_images[1:],
                    optimize=False,
                )
            
            # Save metadata separately
            if metadata:
                metadata_path = output_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"Exported PDF: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export PDF: {e}")
            return False
    
    def create_metadata(
        self,
        document_type: str,
        source: str = "camera",
        contour_points: Optional[List] = None,
        manual_correction: bool = False,
        enhancement_mode: str = "standard",
        **kwargs
    ) -> Dict:
        """Create metadata dictionary for exported document."""
        metadata = {
            "document_type": document_type,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "enhancement_mode": enhancement_mode,
            "manual_correction": manual_correction,
            "target_dpi": self.target_dpi,
        }
        
        if contour_points:
            metadata["contour_points"] = contour_points
        
        # Add any additional metadata
        metadata.update(kwargs)
        
        return metadata

