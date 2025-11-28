#!/usr/bin/env python3
"""
Test document detection on real sample images
"""
import sys
import cv2
import numpy as np
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.scanner.preprocess import ImagePreprocessor

def test_detection_on_samples():
    """Test document detection on sample images"""
    # Try multiple possible paths
    possible_paths = [
        Path("/opt/HostFlow/samples"),
        Path("samples"),
        Path("/app/samples"),
    ]
    samples_dir = None
    for path in possible_paths:
        if path.exists():
            samples_dir = path
            break
    
    if not samples_dir:
        print("❌ Samples directory not found. Tried:")
        for path in possible_paths:
            print(f"   - {path}")
        return
    
    print(f"✅ Using samples directory: {samples_dir}")
    
    # Find sample images
    sample_files = list(samples_dir.rglob("*.jpg")) + list(samples_dir.rglob("*.jpeg")) + list(samples_dir.rglob("*.png"))
    
    if not sample_files:
        print("❌ No sample images found")
        return
    
    print(f"Found {len(sample_files)} sample images")
    print("=" * 60)
    
    preprocessor = ImagePreprocessor(target_dpi=300)
    
    success_count = 0
    fail_count = 0
    
    for img_path in sample_files[:10]:  # Test first 10
        print(f"\n📄 Testing: {img_path.name}")
        
        # Load image
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"  ❌ Failed to load image")
            fail_count += 1
            continue
        
        print(f"  Image size: {image.shape[1]}x{image.shape[0]}")
        
        # Try to detect document
        try:
            # Convert to grayscale for detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Try processing with different doc types
            doc_types = ["driver_license", "passport", "id_card", None]
            detected = False
            
            for doc_type in doc_types:
                try:
                    processed = preprocessor.process(
                        image,
                        doc_type_hint=doc_type,
                        enhancement_mode="standard"
                    )
                    
                    # Check if processing succeeded (image was cropped/warped)
                    if processed is not None and processed.size > 0:
                        # Compare sizes - if processed is significantly different, detection worked
                        orig_area = image.shape[0] * image.shape[1]
                        proc_area = processed.shape[0] * processed.shape[1]
                        ratio = proc_area / orig_area
                        
                        if ratio < 0.95:  # Processed image is smaller (likely cropped)
                            print(f"  ✅ Detection successful with doc_type={doc_type}")
                            print(f"     Original: {image.shape[1]}x{image.shape[0]} ({orig_area:,} px²)")
                            print(f"     Processed: {processed.shape[1]}x{processed.shape[0]} ({proc_area:,} px²)")
                            print(f"     Ratio: {ratio:.2%}")
                            detected = True
                            success_count += 1
                            break
                except Exception as e:
                    continue
            
            if not detected:
                print(f"  ❌ Detection failed - document not found")
                fail_count += 1
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"Results: ✅ {success_count} successful, ❌ {fail_count} failed")
    print(f"Success rate: {success_count/(success_count+fail_count)*100:.1f}%")

if __name__ == "__main__":
    test_detection_on_samples()

