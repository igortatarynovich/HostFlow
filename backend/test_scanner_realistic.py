#!/usr/bin/env python3
"""
Realistic scanner testing - simulates real-world conditions.
"""

import cv2
import numpy as np
from pathlib import Path
import sys
import logging

sys.path.insert(0, str(Path(__file__).parent))

from app.scanner.preprocess import ImagePreprocessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_realistic_document_scene():
    """Create realistic document on various backgrounds."""
    width, height = 1920, 1080  # Typical phone resolution
    
    scenes = []
    
    # Scene 1: Light fabric background (beige/tan)
    bg = np.full((height, width, 3), (220, 200, 180), dtype=np.uint8)
    # Add fabric texture
    for i in range(0, height, 10):
        cv2.line(bg, (0, i), (width, i), (210, 190, 170), 1)
    # Add noise
    noise = np.random.randint(-15, 15, bg.shape, dtype=np.int16)
    bg = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Add document (ID card size ~85x54mm, scaled for image)
    doc_w, doc_h = 600, 380  # Document size in pixels
    doc_x = (width - doc_w) // 2 + np.random.randint(-100, 100)
    doc_y = (height - doc_h) // 2 + np.random.randint(-50, 50)
    
    # Draw white document
    cv2.rectangle(bg, (doc_x, doc_y), (doc_x + doc_w, doc_y + doc_h), (255, 255, 255), -1)
    # Add shadow
    shadow = np.zeros((doc_h + 10, doc_w + 10, 3), dtype=np.uint8)
    cv2.ellipse(shadow, (doc_w//2 + 5, doc_h//2 + 5), (doc_w//2, 20), 0, 0, 360, (0, 0, 0), -1)
    shadow = cv2.GaussianBlur(shadow, (21, 21), 0)
    shadow_alpha = shadow[:, :, 0].astype(np.float32) / 255.0 * 0.3
    for c in range(3):
        bg[doc_y+5:doc_y+doc_h+15, doc_x+5:doc_x+doc_w+15, c] = (
            bg[doc_y+5:doc_y+doc_h+15, doc_x+5:doc_x+doc_w+15, c].astype(np.float32) * (1 - shadow_alpha) +
            shadow[:, :, c].astype(np.float32) * shadow_alpha
        ).astype(np.uint8)
    
    # Add some text on document
    cv2.putText(bg, "DOCUMENT", (doc_x + 20, doc_y + 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    cv2.putText(bg, "Name: TEST", (doc_x + 20, doc_y + 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    
    scenes.append(("light_fabric", bg, (doc_x, doc_y, doc_x + doc_w, doc_y + doc_h)))
    
    # Scene 2: Dark wood background
    bg = np.full((height, width, 3), (100, 80, 60), dtype=np.uint8)
    # Add wood grain
    for i in range(0, width, 5):
        cv2.line(bg, (i, 0), (i, height), (110, 90, 70), 1)
    noise = np.random.randint(-10, 10, bg.shape, dtype=np.int16)
    bg = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    doc_x = (width - doc_w) // 2
    doc_y = (height - doc_h) // 2
    cv2.rectangle(bg, (doc_x, doc_y), (doc_x + doc_w, doc_y + doc_h), (255, 255, 255), -1)
    cv2.putText(bg, "DOCUMENT", (doc_x + 20, doc_y + 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    
    scenes.append(("dark_wood", bg, (doc_x, doc_y, doc_x + doc_w, doc_y + doc_h)))
    
    # Scene 3: White/light background (worst case)
    bg = np.full((height, width, 3), (250, 250, 250), dtype=np.uint8)
    doc_x = (width - doc_w) // 2
    doc_y = (height - doc_h) // 2
    cv2.rectangle(bg, (doc_x, doc_y), (doc_x + doc_w, doc_y + doc_h), (255, 255, 255), -1)
    cv2.putText(bg, "DOCUMENT", (doc_x + 20, doc_y + 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (10, 10, 10), 2)  # Very light text
    
    scenes.append(("white_bg", bg, (doc_x, doc_y, doc_x + doc_w, doc_y + doc_h)))
    
    return scenes


def add_realistic_distortions(image, bbox):
    """Add realistic camera distortions."""
    distortions = []
    
    # Original
    distortions.append(("original", image))
    
    # Slight rotation
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, 3, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), borderValue=(220, 200, 180))
    distortions.append(("rotated_3deg", rotated))
    
    # Perspective
    pts1 = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    pts2 = np.float32([[w*0.05, h*0.05], [w*0.95, h*0.02], [w*0.98, h*0.98], [w*0.02, h*0.95]])
    M = cv2.getPerspectiveTransform(pts1, pts2)
    perspective = cv2.warpPerspective(image, M, (w, h), borderValue=(220, 200, 180))
    distortions.append(("perspective", perspective))
    
    # Bright lighting
    bright = cv2.convertScaleAbs(image, alpha=1.15, beta=25)
    distortions.append(("bright", bright))
    
    # Dark lighting
    dark = cv2.convertScaleAbs(image, alpha=0.85, beta=-15)
    distortions.append(("dark", dark))
    
    return distortions


def test_realistic():
    """Test with realistic scenes."""
    preprocessor = ImagePreprocessor(target_dpi=300)
    
    scenes = create_realistic_document_scene()
    results = []
    
    for scene_name, scene_image, true_bbox in scenes:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing scene: {scene_name}")
        logger.info(f"{'='*60}")
        
        distortions = add_realistic_distortions(scene_image, true_bbox)
        
        for dist_name, dist_image in distortions:
            logger.info(f"\n  Distortion: {dist_name}")
            
            try:
                processed = preprocessor.process(dist_image)
                
                h_orig, w_orig = dist_image.shape[:2]
                h_proc, w_proc = processed.shape[:2]
                
                size_ratio = (h_proc * w_proc) / (h_orig * w_orig)
                was_cropped = size_ratio < 0.85  # More than 15% reduction
                
                # Calculate if document area was correctly identified
                true_area = (true_bbox[2] - true_bbox[0]) * (true_bbox[3] - true_bbox[1])
                proc_area = w_proc * h_proc
                area_ratio = proc_area / true_area if true_area > 0 else 0
                
                result = {
                    "scene": scene_name,
                    "distortion": dist_name,
                    "was_cropped": was_cropped,
                    "size_ratio": size_ratio,
                    "area_ratio": area_ratio,
                    "original_size": (w_orig, h_orig),
                    "processed_size": (w_proc, h_proc),
                    "success": True
                }
                
                logger.info(f"    Original: {w_orig}x{h_orig}")
                logger.info(f"    Processed: {w_proc}x{h_proc}")
                logger.info(f"    Size ratio: {size_ratio:.2f}")
                logger.info(f"    Area ratio: {area_ratio:.2f}")
                logger.info(f"    Cropped: {was_cropped}")
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"    ERROR: {e}")
                results.append({
                    "scene": scene_name,
                    "distortion": dist_name,
                    "success": False,
                    "error": str(e)
                })
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    
    total = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    cropped = sum(1 for r in results if r.get("was_cropped", False))
    
    logger.info(f"Total tests: {total}")
    logger.info(f"Successful: {successful}/{total} ({100*successful/total:.1f}%)")
    logger.info(f"Document cropped: {cropped}/{successful} ({100*cropped/successful:.1f}% of successful)")
    
    # Per scene stats
    logger.info("\nPer scene:")
    for scene_name in ["light_fabric", "dark_wood", "white_bg"]:
        scene_results = [r for r in results if r.get("scene") == scene_name]
        if scene_results:
            success_count = sum(1 for r in scene_results if r.get("success", False))
            crop_count = sum(1 for r in scene_results if r.get("was_cropped", False))
            avg_area_ratio = np.mean([r.get("area_ratio", 0) for r in scene_results if r.get("success", False)])
            logger.info(f"  {scene_name}: {success_count}/{len(scene_results)} success, {crop_count} cropped, avg area ratio: {avg_area_ratio:.2f}")
    
    return results


if __name__ == "__main__":
    test_realistic()

