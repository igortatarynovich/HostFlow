#!/usr/bin/env python3
"""
Debug single image to understand why detection fails
"""
import sys
import cv2
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))
from app.scanner.preprocess import ImagePreprocessor

def debug_image(img_path_str):
    """Debug why detection fails on specific image"""
    img_path = Path(img_path_str)
    
    # Load image
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
            print(f"Failed to load: {e}")
            return
    
    print(f"Image: {img_path.name}")
    print(f"Size: {image.shape[1]}x{image.shape[0]}")
    
    preprocessor = ImagePreprocessor(target_dpi=300)
    
    # Try with different doc types
    for doc_type in [None, "driver_license", "passport", "id_card"]:
        print(f"\nTrying doc_type={doc_type}")
        try:
            processed = preprocessor.process(image, doc_type_hint=doc_type, enhancement_mode="standard")
            if processed is not None:
                orig_area = image.shape[0] * image.shape[1]
                proc_area = processed.shape[0] * processed.shape[1]
                ratio = proc_area / orig_area
                print(f"  Processed: {processed.shape[1]}x{processed.shape[0]}")
                print(f"  Ratio: {ratio:.2%}")
                if ratio < 0.95 or ratio > 1.05:
                    print(f"  ✅ DETECTED!")
                    return
                else:
                    print(f"  ❌ No detection (ratio too close to 1.0)")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        debug_image(sys.argv[1])
    else:
        debug_image("/opt/HostFlow/samples/RAJAN RAJESH/WhatsApp Image 2025-11-24 at 21.31.46.jpeg")

