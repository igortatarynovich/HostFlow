#!/usr/bin/env python3
"""
Test scanner on real document samples from /opt/HostFlow/samples
Run this on the HOST (not in container) to test with real samples
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import cv2
import numpy as np
from backend.app.scanner.preprocess import ImagePreprocessor
from backend.app.scanner.classify import DocumentClassifier
from backend.app.scanner.scanner_service import DocumentScannerService

def test_on_samples():
    """Test scanner on real document samples."""
    samples_dir = Path("/opt/HostFlow/samples")
    
    if not samples_dir.exists():
        print(f"ERROR: Samples directory not found: {samples_dir}")
        return
    
    # Find sample images
    sample_files = []
    for ext in ["*.pdf", "*.jpg", "*.jpeg", "*.png"]:
        sample_files.extend(list(samples_dir.rglob(ext)))
    
    print(f"Found {len(sample_files)} sample files")
    
    if not sample_files:
        print("No sample files found!")
        return
    
    preprocessor = ImagePreprocessor(target_dpi=300)
    classifier = DocumentClassifier()
    scanner = DocumentScannerService(target_dpi=300)
    
    success_count = 0
    fail_count = 0
    
    for sample_file in sample_files[:10]:  # Test first 10
        print(f"\n{'='*60}")
        print(f"Testing: {sample_file.name}")
        print(f"Path: {sample_file}")
        
        try:
            # Load image
            if sample_file.suffix.lower() == ".pdf":
                from backend.app.scanner.utils import pdf_to_images
                images = pdf_to_images(sample_file)
                if not images:
                    print("  ❌ Failed to load PDF")
                    fail_count += 1
                    continue
                image = images[0]
            else:
                image = cv2.imread(str(sample_file))
                if image is None:
                    print("  ❌ Failed to load image")
                    fail_count += 1
                    continue
            
            print(f"  ✓ Loaded image: {image.shape}")
            
            # Test preprocessing
            try:
                processed = preprocessor.process(image)
                print(f"  ✓ Preprocessed: {processed.shape}")
                
                # Check if contour was found
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                contour = preprocessor._find_document_contour(gray)
                if contour is not None:
                    print(f"  ✓ Document contour FOUND")
                else:
                    print(f"  ⚠ Document contour NOT found")
                
            except Exception as e:
                print(f"  ❌ Preprocessing failed: {e}")
                import traceback
                traceback.print_exc()
                fail_count += 1
                continue
            
            # Test classification
            try:
                doc_type, confidence = classifier.classify(processed)
                print(f"  ✓ Classified as: {doc_type} (confidence: {confidence:.2f})")
            except Exception as e:
                print(f"  ❌ Classification failed: {e}")
            
            # Test full scan
            try:
                result = scanner.scan_document(sample_file, output_dir=None)
                print(f"  ✓ Full scan: {result.document_type}, {len(result.fields)} fields")
                if result.quality_metrics:
                    print(f"    Quality: {result.quality_metrics.get('quality_level', 'unknown')}")
            except Exception as e:
                print(f"  ❌ Full scan failed: {e}")
                import traceback
                traceback.print_exc()
            
            success_count += 1
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {success_count} succeeded, {fail_count} failed")

if __name__ == "__main__":
    test_on_samples()

