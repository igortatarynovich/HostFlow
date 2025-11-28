#!/usr/bin/env python3
"""
Quick test - just check if all images process successfully
"""
import sys
import cv2
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.scanner.preprocess import ImagePreprocessor

def test_all_samples():
    """Test document detection on ALL sample images - target: 100%"""
    samples_dir = Path("/opt/HostFlow/samples")
    if not samples_dir.exists():
        print("❌ Samples directory not found")
        return
    
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
        print(f"📄 {img_path.name}...", end=" ", flush=True)
        
        # Load image
        try:
            image = cv2.imread(str(img_path))
            if image is None:
                try:
                    from PIL import Image
                    try:
                        from pillow_heif import register_heif_opener
                        register_heif_opener()
                    except:
                        pass
                    pil_img = Image.open(str(img_path))
                    if pil_img.mode == 'RGBA':
                        pil_img = pil_img.convert('RGB')
                    elif pil_img.mode != 'RGB':
                        pil_img = pil_img.convert('RGB')
                    image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                except Exception as e:
                    print(f"❌ Load failed: {e}")
                    fail_count += 1
                    failed_files.append(str(img_path))
                    continue
        except Exception as e:
            print(f"❌ Error: {e}")
            fail_count += 1
            failed_files.append(str(img_path))
            continue
        
        # Try to detect document
        doc_types = ["driver_license", "passport", "id_card", None]
        detected = False
        
        for doc_type in doc_types:
            try:
                processed = preprocessor.process(
                    image,
                    doc_type_hint=doc_type,
                    enhancement_mode="standard"
                )
                
                if processed is not None and processed.size > 0:
                    orig_area = image.shape[0] * image.shape[1]
                    proc_area = processed.shape[0] * processed.shape[1]
                    ratio = proc_area / orig_area
                    dims_changed = (
                        abs(processed.shape[1] - image.shape[1]) > 5 or
                        abs(processed.shape[0] - image.shape[0]) > 5
                    )
                    
                    if ratio < 0.99 or ratio > 1.01 or dims_changed:
                        print(f"✅")
                        detected = True
                        success_count += 1
                        break
            except Exception as e:
                continue
        
        if not detected:
            print(f"❌")
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
        return True
    else:
        print(f"\n⚠️  Need to improve detection for {fail_count} file(s)")
        return False

if __name__ == "__main__":
    test_all_samples()

