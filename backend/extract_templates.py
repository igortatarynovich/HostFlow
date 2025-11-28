#!/usr/bin/env python3
"""
Extract document templates from samples and save them for template matching.
"""

import cv2
import numpy as np
from pathlib import Path
import pickle
import sys

sys.path.insert(0, str(Path(__file__).parent))

from app.scanner.preprocess import ImagePreprocessor
from app.scanner.utils import load_image, pdf_to_images


def extract_templates_from_samples():
    """Extract templates from sample documents."""
    samples_dir = Path("/opt/HostFlow/samples")
    templates_dir = Path("/app/templates")
    templates_dir.mkdir(exist_ok=True)
    
    if not samples_dir.exists():
        print(f"Samples directory not found: {samples_dir}")
        return
    
    preprocessor = ImagePreprocessor(target_dpi=300)
    templates = {}
    
    # Find all image and PDF files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.pdf']:
        image_files.extend(samples_dir.rglob(ext))
    
    print(f"Found {len(image_files)} sample files")
    
    for sample_path in image_files[:20]:  # Limit to 20 for now
        try:
            # Determine document type from path
            doc_type = infer_document_type(sample_path)
            
            # Load image
            if sample_path.suffix.lower() == '.pdf':
                pages = pdf_to_images(sample_path)
                if not pages:
                    continue
                image = pages[0]  # Use first page
            else:
                image = load_image(sample_path)
                if image is None:
                    continue
            
            # Process image to get clean document
            processed = preprocessor.process(image)
            
            # Convert to grayscale and normalize
            if len(processed.shape) == 3:
                template = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            else:
                template = processed
            
            # Normalize size (max 400px)
            h, w = template.shape
            max_dim = 400
            if w > h:
                if w > max_dim:
                    scale = max_dim / w
                    template = cv2.resize(template, (max_dim, int(h * scale)), interpolation=cv2.INTER_AREA)
            else:
                if h > max_dim:
                    scale = max_dim / h
                    template = cv2.resize(template, (int(w * scale), max_dim), interpolation=cv2.INTER_AREA)
            
            # Save template
            if doc_type not in templates:
                templates[doc_type] = []
            
            template_path = templates_dir / f"{doc_type}_{len(templates[doc_type])}.png"
            cv2.imwrite(str(template_path), template)
            templates[doc_type].append({
                "path": str(template_path),
                "size": template.shape[::-1],  # (width, height)
                "aspect": template.shape[1] / template.shape[0] if template.shape[0] > 0 else 1.0
            })
            
            print(f"Extracted template: {sample_path.name} -> {doc_type}")
            
        except Exception as e:
            print(f"Failed to extract template from {sample_path}: {e}")
    
    # Save template index
    index_path = templates_dir / "templates_index.pkl"
    with open(index_path, 'wb') as f:
        pickle.dump(templates, f)
    
    print(f"\nExtracted {sum(len(t) for t in templates.values())} templates")
    print(f"Templates saved to: {templates_dir}")
    print(f"Template index saved to: {index_path}")


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
    extract_templates_from_samples()

