#!/usr/bin/env python3
"""
Comprehensive scanner testing on samples with different conditions.
Tests various lighting, angles, backgrounds, and positions.
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
import logging

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.app.scanner.preprocess import ImagePreprocessor
from backend.app.scanner.scanner_service import DocumentScannerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def simulate_conditions(image: np.ndarray, condition: str) -> np.ndarray:
    """Simulate different capture conditions."""
    h, w = image.shape[:2]
    
    if condition == "bright":
        # Simulate bright lighting
        image = cv2.convertScaleAbs(image, alpha=1.2, beta=30)
    elif condition == "dark":
        # Simulate dark lighting
        image = cv2.convertScaleAbs(image, alpha=0.7, beta=-20)
    elif condition == "low_contrast":
        # Simulate low contrast
        image = cv2.convertScaleAbs(image, alpha=0.8, beta=40)
    elif condition == "rotated_5":
        # Rotate 5 degrees
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, 5, 1.0)
        image = cv2.warpAffine(image, M, (w, h), borderValue=(255, 255, 255))
    elif condition == "rotated_15":
        # Rotate 15 degrees
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, 15, 1.0)
        image = cv2.warpAffine(image, M, (w, h), borderValue=(255, 255, 255))
    elif condition == "perspective":
        # Add perspective distortion
        pts1 = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        pts2 = np.float32([[w*0.1, h*0.1], [w*0.9, h*0.05], [w*0.95, h*0.95], [w*0.05, h*0.9]])
        M = cv2.getPerspectiveTransform(pts1, pts2)
        image = cv2.warpPerspective(image, M, (w, h), borderValue=(255, 255, 255))
    elif condition == "noisy":
        # Add noise
        noise = np.random.randint(0, 20, image.shape, dtype=np.uint8)
        image = cv2.add(image, noise)
    
    return image


def test_on_samples():
    """Test scanner on samples with different conditions."""
    samples_dir = Path("/opt/HostFlow/samples")
    output_dir = Path("/tmp/scanner_test_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not samples_dir.exists():
        logger.error(f"Samples directory not found: {samples_dir}")
        return
    
    scanner = DocumentScannerService(target_dpi=300)
    preprocessor = ImagePreprocessor(target_dpi=300)
    
    conditions = [
        "original",
        "bright",
        "dark",
        "low_contrast",
        "rotated_5",
        "rotated_15",
        "perspective",
        "noisy"
    ]
    
    results = []
    
    # Find all image files
    image_files = []
    for root, _, files in os.walk(samples_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(Path(root) / file)
    
    if not image_files:
        logger.error("No image files found in samples directory")
        return
    
    logger.info(f"Found {len(image_files)} sample images")
    
    for img_path in image_files[:5]:  # Test first 5 images
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {img_path.name}")
        logger.info(f"{'='*60}")
        
        # Load original image
        original = cv2.imread(str(img_path))
        if original is None:
            logger.warning(f"Failed to load {img_path}")
            continue
        
        for condition in conditions:
            logger.info(f"\n  Condition: {condition}")
            
            # Simulate condition
            if condition == "original":
                test_image = original.copy()
            else:
                test_image = simulate_conditions(original.copy(), condition)
            
            # Test preprocessing
            try:
                processed = preprocessor.process(test_image)
                
                # Check if document was cropped (size should be different)
                h_orig, w_orig = test_image.shape[:2]
                h_proc, w_proc = processed.shape[:2]
                
                # Calculate if cropping happened (significant size change)
                size_change = abs((h_proc * w_proc) / (h_orig * w_orig) - 1.0)
                was_cropped = size_change > 0.1  # More than 10% size change
                
                # Save results
                condition_dir = output_dir / img_path.stem / condition
                condition_dir.mkdir(parents=True, exist_ok=True)
                
                # Save original test image
                cv2.imwrite(str(condition_dir / "input.jpg"), test_image)
                
                # Save processed image
                cv2.imwrite(str(condition_dir / "processed.jpg"), processed)
                
                result = {
                    "image": img_path.name,
                    "condition": condition,
                    "was_cropped": was_cropped,
                    "size_change": size_change,
                    "original_size": (w_orig, h_orig),
                    "processed_size": (w_proc, h_proc),
                    "success": True
                }
                
                logger.info(f"    Original: {w_orig}x{h_orig}, Processed: {w_proc}x{h_proc}")
                logger.info(f"    Cropped: {was_cropped}, Size change: {size_change:.2%}")
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"    ERROR: {e}")
                results.append({
                    "image": img_path.name,
                    "condition": condition,
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
    for condition in conditions:
        condition_results = [r for r in results if r.get("condition") == condition]
        if condition_results:
            success_count = sum(1 for r in condition_results if r.get("success", False))
            crop_count = sum(1 for r in condition_results if r.get("was_cropped", False))
            logger.info(f"  {condition}: {success_count}/{len(condition_results)} success, {crop_count} cropped")
    
    logger.info(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    test_on_samples()

