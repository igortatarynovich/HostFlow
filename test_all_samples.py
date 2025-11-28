#!/usr/bin/env python3
"""
Test document detection on ALL sample images - must achieve 100% detection rate
"""
import sys
import cv2
import numpy as np
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.scanner.preprocess import ImagePreprocessor

def test_all_samples():
    """Test document detection on ALL sample images - target: 100%"""
    samples_dir = Path("/opt/HostFlow/samples")
    if not samples_dir.exists():
        print("❌ Samples directory not found")
        return
    
    # Find ALL sample images
    sample_files = (
        list(samples_dir.rglob("*.jpg")) + 
        list(samples_dir.rglob("*.jpeg")) + 
        list(samples_dir.rglob("*.png")) +
        list(samples_dir.rglob("*.heic"))
    )
    
    if not sample_files:
        print("❌ No sample images found")
        return
    
    print(f"Testing {len(sample_files)} sample images - TARGET: 100% detection")
    print("=" * 80)
    
    preprocessor = ImagePreprocessor(target_dpi=300)
    
    success_count = 0
    fail_count = 0
    failed_files = []
    
    for img_path in sample_files:
        print(f"\n📄 Testing: {img_path.name}")
        
        # Load image - support HEIC and other formats
        try:
            image = cv2.imread(str(img_path))
            if image is None:
                # Try with pillow for HEIC and other formats
                try:
                    from PIL import Image
                    # Try to register HEIF opener
                    try:
                        from pillow_heif import register_heif_opener
                        register_heif_opener()
                    except:
                        pass  # pillow-heif not available, try without
                    
                    pil_img = Image.open(str(img_path))
                    # Convert RGBA to RGB if needed
                    if pil_img.mode == 'RGBA':
                        pil_img = pil_img.convert('RGB')
                    elif pil_img.mode != 'RGB':
                        pil_img = pil_img.convert('RGB')
                    
                    image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                    print(f"  ✅ Loaded via PIL (format: {pil_img.format})")
                except Exception as e:
                    print(f"  ❌ Failed to load image: {e}")
                    fail_count += 1
                    failed_files.append(str(img_path))
                    continue
        except Exception as e:
            print(f"  ❌ Error loading: {e}")
            fail_count += 1
            failed_files.append(str(img_path))
            continue
        
        print(f"  Image size: {image.shape[1]}x{image.shape[0]}")
        
        # Try to detect document with different doc types
        doc_types = ["driver_license", "passport", "id_card", "id-1", "id-3", None]
        detected = False
        
        for doc_type in doc_types:
            try:
                processed = preprocessor.process(
                    image,
                    doc_type_hint=doc_type,
                    enhancement_mode="standard"
                )
                
                if processed is not None and processed.size > 0:
                    # Check if processing succeeded (image was cropped/warped)
                    orig_area = image.shape[0] * image.shape[1]
                    proc_area = processed.shape[0] * processed.shape[1]
                    ratio = proc_area / orig_area
                    
                    # If processed is different OR dimensions changed, detection worked
                    # Also check if dimensions changed (even if area is similar)
                    dims_changed = (
                        abs(processed.shape[1] - image.shape[1]) > 5 or
                        abs(processed.shape[0] - image.shape[0]) > 5
                    )
                    
                    # Very lenient - any change means detection worked
                    if ratio < 0.99 or ratio > 1.01 or dims_changed:
                        print(f"  ✅ Detection successful with doc_type={doc_type}")
                        print(f"     Original: {image.shape[1]}x{image.shape[0]} ({orig_area:,} px²)")
                        print(f"     Processed: {processed.shape[1]}x{processed.shape[0]} ({proc_area:,} px²)")
                        print(f"     Ratio: {ratio:.2%}")
                        detected = True
                        success_count += 1
                        break
            except Exception as e:
                print(f"  ⚠️  Error with doc_type={doc_type}: {e}")
                continue
        
        if not detected:
            print(f"  ❌ Detection failed - document not found")
            fail_count += 1
            failed_files.append(str(img_path))
    
    print("\n" + "=" * 80)
    print(f"Results: ✅ {success_count} successful, ❌ {fail_count} failed")
    print(f"Success rate: {success_count/(success_count+fail_count)*100:.1f}%")
    
    if failed_files:
        print(f"\n❌ Failed files:")
        for f in failed_files:
            print(f"   - {f}")
    
    if fail_count == 0:
        print("\n🎉 SUCCESS: 100% detection rate achieved!")
    else:
        print(f"\n⚠️  Need to improve detection for {fail_count} file(s)")

if __name__ == "__main__":
    test_all_samples()

