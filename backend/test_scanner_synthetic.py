#!/usr/bin/env python3
"""
Synthetic scanner testing - creates test images with different conditions
and tests the preprocessing algorithm.
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


def create_test_document(width=800, height=500, bg_color=(240, 240, 240), doc_color=(255, 255, 255)):
    """Create a synthetic document on a background."""
    # Create background
    image = np.full((height, width, 3), bg_color, dtype=np.uint8)
    
    # Add texture to background (simulate fabric/wood)
    noise = np.random.randint(-10, 10, image.shape, dtype=np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Add document (slightly smaller than image)
    margin = 50
    doc_x1, doc_y1 = margin, margin
    doc_x2, doc_y2 = width - margin, height - margin
    
    # Draw document rectangle
    cv2.rectangle(image, (doc_x1, doc_y1), (doc_x2, doc_y2), doc_color, -1)
    
    # Add some text-like patterns on document
    cv2.putText(image, "DOCUMENT", (doc_x1 + 20, doc_y1 + 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(image, "Test Content", (doc_x1 + 20, doc_y1 + 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    
    return image, (doc_x1, doc_y1, doc_x2, doc_y2)


def test_conditions():
    """Test preprocessing with different conditions."""
    preprocessor = ImagePreprocessor(target_dpi=300)
    
    conditions = {
        "light_bg": ((240, 240, 240), (255, 255, 255)),  # Light background, white doc
        "dark_bg": ((50, 50, 50), (255, 255, 255)),     # Dark background, white doc
        "medium_bg": ((150, 150, 150), (255, 255, 255)), # Medium background
        "similar_colors": ((230, 230, 230), (250, 250, 250)),  # Similar colors
    }
    
    results = []
    
    for condition_name, (bg_color, doc_color) in conditions.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing condition: {condition_name}")
        logger.info(f"{'='*60}")
        
        # Create test image
        test_image, true_bbox = create_test_document(bg_color=bg_color, doc_color=doc_color)
        
        # Test different transformations
        transformations = {
            "straight": lambda img: img,
            "rotated_5": lambda img: rotate_image(img, 5),
            "rotated_15": lambda img: rotate_image(img, 15),
            "perspective": lambda img: add_perspective(img),
        }
        
        for trans_name, transform_func in transformations.items():
            logger.info(f"\n  Transformation: {trans_name}")
            
            # Apply transformation
            transformed = transform_func(test_image.copy())
            
            # Process
            try:
                processed = preprocessor.process(transformed)
                
                # Check if cropped (size should be significantly different)
                h_orig, w_orig = transformed.shape[:2]
                h_proc, w_proc = processed.shape[:2]
                
                size_ratio = (h_proc * w_proc) / (h_orig * w_orig)
                was_cropped = size_ratio < 0.9  # More than 10% reduction
                
                result = {
                    "condition": condition_name,
                    "transformation": trans_name,
                    "was_cropped": was_cropped,
                    "size_ratio": size_ratio,
                    "original_size": (w_orig, h_orig),
                    "processed_size": (w_proc, h_proc),
                    "success": True
                }
                
                logger.info(f"    Original: {w_orig}x{h_orig}")
                logger.info(f"    Processed: {w_proc}x{h_proc}")
                logger.info(f"    Size ratio: {size_ratio:.2f}")
                logger.info(f"    Cropped: {was_cropped}")
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"    ERROR: {e}")
                results.append({
                    "condition": condition_name,
                    "transformation": trans_name,
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
    
    # Per condition stats
    logger.info("\nPer condition:")
    for condition_name in conditions.keys():
        condition_results = [r for r in results if r.get("condition") == condition_name]
        if condition_results:
            success_count = sum(1 for r in condition_results if r.get("success", False))
            crop_count = sum(1 for r in condition_results if r.get("was_cropped", False))
            logger.info(f"  {condition_name}: {success_count}/{len(condition_results)} success, {crop_count} cropped")
    
    return results


def rotate_image(image, angle):
    """Rotate image by angle degrees."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), borderValue=(240, 240, 240))
    return rotated


def add_perspective(image):
    """Add perspective distortion."""
    h, w = image.shape[:2]
    pts1 = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    pts2 = np.float32([[w*0.1, h*0.1], [w*0.9, h*0.05], [w*0.95, h*0.95], [w*0.05, h*0.9]])
    M = cv2.getPerspectiveTransform(pts1, pts2)
    warped = cv2.warpPerspective(image, M, (w, h), borderValue=(240, 240, 240))
    return warped


if __name__ == "__main__":
    test_conditions()

