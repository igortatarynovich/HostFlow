"""
Document specifications - exact dimensions, shapes, and page counts for each document type.
Used for creating bounding boxes and improving detection accuracy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional
import json
import logging

from backend.app.document_types.registry import normalize_input_doc_type

logger = logging.getLogger(__name__)


# Standard document dimensions (in pixels at 300 DPI)
# These are based on real document sizes
DOCUMENT_SPECS: Dict[str, Dict] = {
    "id_card": {
        "standard_size_mm": {"width": 85.6, "height": 53.98},  # ID-1 format (credit card size)
        "aspect_ratio": 1.585,
        "tolerance": {"width": 0.05, "height": 0.05},  # 5% tolerance
        "pages": 1,
        "shape": "rectangular",
        "corners": "rounded"
    },
    "passport": {
        "standard_size_mm": {"width": 125, "height": 88},  # Standard passport size
        "aspect_ratio": 1.42,
        "tolerance": {"width": 0.05, "height": 0.05},
        "pages": 32,  # Typical passport pages
        "shape": "rectangular",
        "corners": "sharp"
    },
    "driver_license": {
        "standard_size_mm": {"width": 85.6, "height": 53.98},  # Same as ID card
        "aspect_ratio": 1.585,
        "tolerance": {"width": 0.05, "height": 0.05},
        "pages": 1,
        "shape": "rectangular",
        "corners": "rounded"
    },
    "residence_card": {
        "standard_size_mm": {"width": 85.6, "height": 53.98},
        "aspect_ratio": 1.585,
        "tolerance": {"width": 0.05, "height": 0.05},
        "pages": 1,
        "shape": "rectangular",
        "corners": "rounded"
    },
    "tachograph_card": {
        "standard_size_mm": {"width": 85.6, "height": 53.98},
        "aspect_ratio": 1.585,
        "tolerance": {"width": 0.05, "height": 0.05},
        "pages": 1,
        "shape": "rectangular",
        "corners": "rounded"
    },
    "adr_card": {
        "standard_size_mm": {"width": 85.6, "height": 53.98},
        "aspect_ratio": 1.585,
        "tolerance": {"width": 0.05, "height": 0.05},
        "pages": 1,
        "shape": "rectangular",
        "corners": "rounded"
    },
    "decision": {
        "standard_size_mm": {"width": 210, "height": 297},  # A4
        "aspect_ratio": 0.707,
        "tolerance": {"width": 0.1, "height": 0.1},
        "pages": 1,
        "shape": "rectangular",
        "corners": "sharp"
    },
}


CANONICAL_TO_SPEC_KEY: Dict[str, str] = {
    "national_identity_card": "id_card",
    "adr_certificate": "adr_card",
}


def _resolve_spec_key(doc_type: str) -> str:
    canonical = normalize_input_doc_type(doc_type)
    return CANONICAL_TO_SPEC_KEY.get(canonical, canonical)


def mm_to_pixels(mm: float, dpi: int = 300) -> int:
    """Convert millimeters to pixels at given DPI."""
    return int(mm * dpi / 25.4)


def get_document_spec(doc_type: str, dpi: int = 300) -> Optional[Dict]:
    """Get document specification for given type."""
    spec_key = _resolve_spec_key(doc_type)
    if spec_key not in DOCUMENT_SPECS:
        return None
    
    spec = DOCUMENT_SPECS[spec_key].copy()
    spec["pixel_dimensions"] = {
        "width": mm_to_pixels(spec["standard_size_mm"]["width"], dpi),
        "height": mm_to_pixels(spec["standard_size_mm"]["height"], dpi)
    }
    
    # Calculate tolerance in pixels
    spec["pixel_tolerance"] = {
        "width": int(spec["pixel_dimensions"]["width"] * spec["tolerance"]["width"]),
        "height": int(spec["pixel_dimensions"]["height"] * spec["tolerance"]["height"])
    }
    
    return spec


def load_custom_specs(specs_file: Path = Path("/app/document_specs.json")) -> Dict:
    """Load custom document specs from analyzed samples."""
    if specs_file.exists():
        try:
            with open(specs_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load custom specs: {e}")
    return {}


def get_document_spec_with_custom(doc_type: str, dpi: int = 300) -> Optional[Dict]:
    """Get document specification, using custom specs if available."""
    spec_key = _resolve_spec_key(doc_type)
    # Try custom specs first (from analyzed samples)
    custom_specs = load_custom_specs()
    if spec_key in custom_specs:
        custom = custom_specs[spec_key]
        # Convert custom specs to standard format
        avg_dims = custom.get("average_dimensions", {})
        if avg_dims:
            # Calculate mm from pixels (assuming 300 DPI)
            width_mm = (avg_dims["width"] / 300) * 25.4
            height_mm = (avg_dims["height"] / 300) * 25.4
            
            spec = {
                "standard_size_mm": {"width": width_mm, "height": height_mm},
                "aspect_ratio": custom.get("aspect_ratio", width_mm / height_mm if height_mm > 0 else 1.0),
                "tolerance": custom.get("tolerance", {"width": 0.1, "height": 0.1}),
                "pages": custom.get("pages", 1),
                "shape": custom.get("shape", "rectangular"),
                "corners": "rounded" if "card" in doc_type else "sharp"
            }
            
            # Convert to pixels at target DPI
            spec["pixel_dimensions"] = {
                "width": mm_to_pixels(spec["standard_size_mm"]["width"], dpi),
                "height": mm_to_pixels(spec["standard_size_mm"]["height"], dpi)
            }
            
            spec["pixel_tolerance"] = {
                "width": int(spec["pixel_dimensions"]["width"] * spec["tolerance"]["width"]),
                "height": int(spec["pixel_dimensions"]["height"] * spec["tolerance"]["height"])
            }
            
            logger.info(f"Using custom spec for {doc_type}: {spec['pixel_dimensions']}")
            return spec
    
    # Fall back to standard specs
    return get_document_spec(doc_type, dpi)


def get_bounding_box_for_document(
    doc_type: str,
    image_width: int,
    image_height: int,
    dpi: int = 300
) -> Optional[tuple]:
    """
    Get expected bounding box for document type in given image.
    
    Returns:
        (x, y, width, height) bounding box or None
    """
    spec = get_document_spec(doc_type, dpi)
    if not spec:
        return None
    
    expected_w = spec["pixel_dimensions"]["width"]
    expected_h = spec["pixel_dimensions"]["height"]
    
    # Calculate maximum possible size based on image dimensions
    # Document should fit within image with some margin
    max_w = int(image_width * 0.9)  # 90% of image width
    max_h = int(image_height * 0.9)  # 90% of image height
    
    # Scale document size to fit if needed
    scale_w = max_w / expected_w if expected_w > max_w else 1.0
    scale_h = max_h / expected_h if expected_h > max_h else 1.0
    scale = min(scale_w, scale_h, 1.0)  # Don't scale up
    
    actual_w = int(expected_w * scale)
    actual_h = int(expected_h * scale)
    
    # Center the bounding box
    x = (image_width - actual_w) // 2
    y = (image_height - actual_h) // 2
    
    return (x, y, actual_w, actual_h)

