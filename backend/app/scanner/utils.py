"""
Utility functions for the document scanner module.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# A4 dimensions at 300 DPI
A4_WIDTH_300DPI = 2480  # 210mm * 300 / 25.4
A4_HEIGHT_300DPI = 3508  # 297mm * 300 / 25.4


def load_image(path: Path | str) -> Optional[np.ndarray]:
    """Load image from file path, supporting various formats."""
    try:
        path = Path(path)
        if not path.exists():
            logger.error(f"Image file not found: {path}")
            return None
        
        # Try OpenCV first (fast, supports common formats)
        image = cv2.imread(str(path))
        if image is not None:
            return image
        
        # Fallback to PIL for formats OpenCV doesn't support
        try:
            pil_image = Image.open(path)
            # Convert PIL to OpenCV format (RGB -> BGR)
            if pil_image.mode == "RGBA":
                # Convert RGBA to RGB with white background
                rgb_image = Image.new("RGB", pil_image.size, (255, 255, 255))
                rgb_image.paste(pil_image, mask=pil_image.split()[3])
                pil_image = rgb_image
            elif pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
            
            np_image = np.array(pil_image)
            # Convert RGB to BGR for OpenCV
            cv_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
            return cv_image
        except Exception as e:
            logger.error(f"Failed to load image with PIL: {e}")
            return None
    except Exception as e:
        logger.error(f"Error loading image from {path}: {e}")
        return None


def pdf_to_images(pdf_path: Path | str) -> list[np.ndarray]:
    """Convert PDF to list of images (one per page)."""
    try:
        from pdf2image import convert_from_path
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return []
        
        # Convert PDF pages to PIL Images
        pil_images = convert_from_path(
            str(pdf_path),
            dpi=300,  # High resolution for better OCR
            fmt="RGB",
        )
        
        # Convert PIL Images to OpenCV format
        images = []
        for pil_img in pil_images:
            np_image = np.array(pil_img)
            cv_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
            images.append(cv_image)
        
        logger.info(f"Converted PDF {pdf_path} to {len(images)} images")
        return images
    except ImportError:
        logger.error("pdf2image not installed. Install with: pip install pdf2image")
        return []
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
        return []


def save_image(image: np.ndarray, path: Path | str, quality: int = 95) -> bool:
    """Save image to file."""
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine format from extension
        ext = path.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        elif ext == ".png":
            cv2.imwrite(str(path), image, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        elif ext == ".tiff" or ext == ".tif":
            cv2.imwrite(str(path), image)
        else:
            # Default to JPEG
            path = path.with_suffix(".jpg")
            cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        
        return True
    except Exception as e:
        logger.error(f"Error saving image to {path}: {e}")
        return False


def resize_to_a4_300dpi(image: np.ndarray) -> np.ndarray:
    """Resize image to A4 format at 300 DPI."""
    h, w = image.shape[:2]
    
    # Calculate aspect ratios
    image_aspect = w / h
    a4_aspect = A4_WIDTH_300DPI / A4_HEIGHT_300DPI
    
    if abs(image_aspect - a4_aspect) < 0.01:
        # Already A4 aspect ratio, just resize
        return cv2.resize(image, (A4_WIDTH_300DPI, A4_HEIGHT_300DPI), interpolation=cv2.INTER_LANCZOS4)
    
    # Fit to A4 while preserving aspect ratio
    if image_aspect > a4_aspect:
        # Image is wider, fit to width
        new_w = A4_WIDTH_300DPI
        new_h = int(A4_HEIGHT_300DPI * (h / w) * (w / A4_WIDTH_300DPI))
    else:
        # Image is taller, fit to height
        new_h = A4_HEIGHT_300DPI
        new_w = int(A4_WIDTH_300DPI * (w / h) * (h / A4_HEIGHT_300DPI))
    
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    
    # Create A4 canvas with white background
    a4_image = np.ones((A4_HEIGHT_300DPI, A4_WIDTH_300DPI, 3), dtype=np.uint8) * 255
    
    # Center the resized image
    y_offset = (A4_HEIGHT_300DPI - new_h) // 2
    x_offset = (A4_WIDTH_300DPI - new_w) // 2
    a4_image[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    
    return a4_image

