#!/usr/bin/env python3
"""
Analyze document samples to extract exact dimensions, shapes, and page counts.
Create bounding box templates for each document type.
"""

import cv2
import numpy as np
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent))

from app.scanner.preprocess import ImagePreprocessor
from app.scanner.utils import load_image, pdf_to_images


def analyze_document_dimensions():
    """Analyze samples to extract document specifications."""
    samples_dir = Path("/opt/HostFlow/samples")
    output_file = Path("/app/document_specs.json")
    
    if not samples_dir.exists():
        print(f"Samples directory not found: {samples_dir}")
        return
    
    preprocessor = ImagePreprocessor(target_dpi=300)
    specs = {}
    
    # Find all image and PDF files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        image_files.extend(samples_dir.rglob(ext))
    
    print(f"Found {len(image_files)} sample image files")
    
    for sample_path in image_files:
        try:
            # Determine document type from path
            doc_type = infer_document_type(sample_path)
            
            # Load image
            image = load_image(sample_path)
            if image is None:
                continue
            
            # Process to get clean document (pass doc_type for better detection)
            processed = preprocessor.process(image, doc_type_hint=doc_type)
            
            # Get dimensions
            h, w = processed.shape[:2]
            aspect_ratio = w / h if h > 0 else 1.0
            
            # Calculate area
            area = w * h
            
            # Store specs
            if doc_type not in specs:
                specs[doc_type] = {
                    "dimensions": [],
                    "aspect_ratios": [],
                    "areas": [],
                    "pages": 1,  # Default, will be updated for PDFs
                    "shape": "rectangular"  # Default
                }
            
            specs[doc_type]["dimensions"].append({"width": int(w), "height": int(h)})
            specs[doc_type]["aspect_ratios"].append(aspect_ratio)
            specs[doc_type]["areas"].append(area)
            
            print(f"Analyzed: {sample_path.name} -> {doc_type}: {w}x{h} (aspect: {aspect_ratio:.2f})")
            
        except Exception as e:
            print(f"Failed to analyze {sample_path}: {e}")
    
    # Calculate averages and ranges for each document type
    document_specs = {}
    
    for doc_type, data in specs.items():
        if not data["dimensions"]:
            continue
        
        dimensions = data["dimensions"]
        aspect_ratios = data["aspect_ratios"]
        areas = data["areas"]
        
        # Calculate statistics
        avg_width = np.mean([d["width"] for d in dimensions])
        avg_height = np.mean([d["height"] for d in dimensions])
        avg_aspect = np.mean(aspect_ratios)
        
        min_width = min(d["width"] for d in dimensions)
        max_width = max(d["width"] for d in dimensions)
        min_height = min(d["height"] for d in dimensions)
        max_height = max(d["height"] for d in dimensions)
        
        # Calculate tolerance (10% variation allowed)
        width_tolerance = (max_width - min_width) / avg_width if avg_width > 0 else 0.1
        height_tolerance = (max_height - min_height) / avg_height if avg_height > 0 else 0.1
        
        document_specs[doc_type] = {
            "average_dimensions": {
                "width": int(avg_width),
                "height": int(avg_height)
            },
            "aspect_ratio": float(avg_aspect),
            "dimension_range": {
                "width": {"min": int(min_width), "max": int(max_width)},
                "height": {"min": int(min_height), "max": int(max_height)}
            },
            "tolerance": {
                "width": float(width_tolerance),
                "height": float(height_tolerance)
            },
            "sample_count": len(dimensions),
            "pages": data["pages"],
            "shape": data["shape"]
        }
    
    # Save specs
    with open(output_file, 'w') as f:
        json.dump(document_specs, f, indent=2)
    
    print(f"\n{'='*60}")
    print("DOCUMENT SPECIFICATIONS")
    print(f"{'='*60}")
    for doc_type, spec in document_specs.items():
        print(f"\n{doc_type}:")
        print(f"  Average: {spec['average_dimensions']['width']}x{spec['average_dimensions']['height']}")
        print(f"  Aspect ratio: {spec['aspect_ratio']:.2f}")
        print(f"  Range: {spec['dimension_range']['width']['min']}-{spec['dimension_range']['width']['max']} x {spec['dimension_range']['height']['min']}-{spec['dimension_range']['height']['max']}")
        print(f"  Samples: {spec['sample_count']}")
    
    print(f"\nSpecs saved to: {output_file}")
    return document_specs


def infer_document_type(path: Path) -> str:
    """Infer document type from file path."""
    path_str = str(path).lower()
    
    if "passport" in path_str or "paszport" in path_str:
        return "passport"
    elif "licence" in path_str or "prawo jazdy" in path_str or "pj" in path_str:
        return "driver_license"
    elif "op" in path_str or "dowod" in path_str or "identity" in path_str:
        return "id_card"
    elif "karta pobytu" in path_str or "kp" in path_str:
        return "residence_card"
    elif "tacho" in path_str:
        return "tachograph_card"
    elif "adr" in path_str:
        return "adr_card"
    elif "decyzja" in path_str or "decision" in path_str:
        return "decision"
    else:
        return "unknown"


if __name__ == "__main__":
    analyze_document_dimensions()

