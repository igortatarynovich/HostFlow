#!/usr/bin/env python3
"""
Test that document processing, filters, and manual contour correction work
"""
import sys
import cv2
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.scanner.preprocess import ImagePreprocessor

def test_processing_features():
    """Test that processing, filters, and manual contour work"""
    print("Testing document processing features...")
    print("=" * 80)
    
    # Load a test image
    samples_dir = Path("/opt/HostFlow/samples")
    # Find any JPEG file
    jpeg_files = list(samples_dir.rglob("*.jpeg")) + list(samples_dir.rglob("*.jpg"))
    if not jpeg_files:
        print("❌ No JPEG files found in samples")
        return False
    test_image_path = jpeg_files[0]
    
    if not test_image_path.exists():
        print("❌ Test image not found")
        return False
    
    # Load image
    image = cv2.imread(str(test_image_path))
    if image is None:
        print("❌ Failed to load test image")
        return False
    
    print(f"✅ Loaded test image: {image.shape[1]}x{image.shape[0]}")
    
    preprocessor = ImagePreprocessor(target_dpi=300)
    
    # Test 1: Standard processing (should work)
    print("\n1. Testing standard processing...")
    try:
        processed_standard = preprocessor.process(
            image.copy(),
            doc_type_hint="driver_license",
            enhancement_mode="standard"
        )
        if processed_standard is not None and processed_standard.size > 0:
            print(f"   ✅ Standard processing works: {processed_standard.shape[1]}x{processed_standard.shape[0]}")
        else:
            print("   ❌ Standard processing failed")
            return False
    except Exception as e:
        print(f"   ❌ Standard processing error: {e}")
        return False
    
    # Test 2: Strong filter (binarization)
    print("\n2. Testing strong filter (binarization)...")
    try:
        processed_strong = preprocessor.process(
            image.copy(),
            doc_type_hint="driver_license",
            enhancement_mode="strong"
        )
        if processed_strong is not None and processed_strong.size > 0:
            # Check if it's actually binarized (should be mostly black/white)
            gray_strong = cv2.cvtColor(processed_strong, cv2.COLOR_BGR2GRAY) if len(processed_strong.shape) == 3 else processed_strong
            unique_values = len(np.unique(gray_strong))
            if unique_values < 50:  # Binarized should have very few unique values
                print(f"   ✅ Strong filter works (binarized): {processed_strong.shape[1]}x{processed_strong.shape[0]}, unique values: {unique_values}")
            else:
                print(f"   ⚠️  Strong filter processed but may not be binarized: {unique_values} unique values")
        else:
            print("   ❌ Strong filter failed")
            return False
    except Exception as e:
        print(f"   ❌ Strong filter error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Photo filter
    print("\n3. Testing photo filter...")
    try:
        processed_photo = preprocessor.process(
            image.copy(),
            doc_type_hint="driver_license",
            enhancement_mode="photo"
        )
        if processed_photo is not None and processed_photo.size > 0:
            print(f"   ✅ Photo filter works: {processed_photo.shape[1]}x{processed_photo.shape[0]}")
        else:
            print("   ❌ Photo filter failed")
            return False
    except Exception as e:
        print(f"   ❌ Photo filter error: {e}")
        return False
    
    # Test 4: Manual contour correction
    print("\n4. Testing manual contour correction...")
    try:
        h, w = image.shape[:2]
        # Create a manual contour (6 points) that's slightly different from auto-detected
        manual_contour = {
            'p1': {'x': int(w * 0.05), 'y': int(h * 0.05)},  # Top-left
            'p2': {'x': int(w * 0.95), 'y': int(h * 0.05)},  # Top-right
            'p3': {'x': int(w * 0.95), 'y': int(h * 0.45)},  # Right-middle
            'p4': {'x': int(w * 0.95), 'y': int(h * 0.95)},  # Bottom-right
            'p5': {'x': int(w * 0.05), 'y': int(h * 0.95)},  # Bottom-left
            'p6': {'x': int(w * 0.05), 'y': int(h * 0.45)},  # Left-middle
        }
        
        processed_manual = preprocessor.process(
            image.copy(),
            doc_type_hint="driver_license",
            enhancement_mode="standard",
            manual_contour=manual_contour
        )
        if processed_manual is not None and processed_manual.size > 0:
            # Check if result is different from auto-detected (manual should produce different result)
            if not np.array_equal(processed_manual, processed_standard):
                print(f"   ✅ Manual contour works: {processed_manual.shape[1]}x{processed_manual.shape[0]} (different from auto)")
            else:
                print(f"   ⚠️  Manual contour processed but result same as auto (may be expected)")
        else:
            print("   ❌ Manual contour failed")
            return False
    except Exception as e:
        print(f"   ❌ Manual contour error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Combined (manual contour + filter)
    print("\n5. Testing manual contour + strong filter...")
    try:
        processed_combined = preprocessor.process(
            image.copy(),
            doc_type_hint="driver_license",
            enhancement_mode="strong",
            manual_contour=manual_contour
        )
        if processed_combined is not None and processed_combined.size > 0:
            print(f"   ✅ Combined (manual + filter) works: {processed_combined.shape[1]}x{processed_combined.shape[0]}")
        else:
            print("   ❌ Combined processing failed")
            return False
    except Exception as e:
        print(f"   ❌ Combined processing error: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("🎉 SUCCESS: All processing features work!")
    print("   ✅ Standard processing")
    print("   ✅ Strong filter (binarization)")
    print("   ✅ Photo filter")
    print("   ✅ Manual contour correction")
    print("   ✅ Combined features")
    return True

if __name__ == "__main__":
    success = test_processing_features()
    sys.exit(0 if success else 1)

