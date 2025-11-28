#!/usr/bin/env python3
"""
Test frontend document detection algorithm on real images
Simulates the browser-based detection
"""
import sys
import cv2
import numpy as np
from pathlib import Path
import json

# This is just a test script, no need for rgbToGray function

def test_frontend_detection():
    """Test frontend detection logic on sample images"""
    samples_dir = Path("/opt/HostFlow/samples")
    if not samples_dir.exists():
        print("❌ Samples directory not found")
        return
    
    sample_files = list(samples_dir.rglob("*.jpg")) + list(samples_dir.rglob("*.jpeg")) + list(samples_dir.rglob("*.png"))
    
    if not sample_files:
        print("❌ No sample images found")
        return
    
    print(f"Testing {len(sample_files)} images with frontend detection logic")
    print("=" * 60)
    
    for img_path in sample_files[:5]:
        print(f"\n📄 Testing: {img_path.name}")
        
        # Load image
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"  ❌ Failed to load")
            continue
        
        print(f"  Size: {image.shape[1]}x{image.shape[0]}")
        
        # Simulate frontend detection steps
        # 1. Downscale to max 400px width (as in frontend)
        scale = 400 / image.shape[1] if image.shape[1] > 400 else 1
        scaled_width = int(image.shape[1] * scale)
        scaled_height = int(image.shape[0] * scale)
        
        if scaled_width < 100 or scaled_height < 100:
            print(f"  ❌ Too small after scaling: {scaled_width}x{scaled_height}")
            continue
        
        print(f"  Scaled to: {scaled_width}x{scaled_height} (scale: {scale:.2f})")
        
        # 2. Convert to grayscale
        gray = cv2.cvtColor(cv2.resize(image, (scaled_width, scaled_height)), cv2.COLOR_BGR2GRAY)
        
        # 3. Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 4. Edge detection (Canny-like with low threshold)
        edges = cv2.Canny(blurred, 15, 45)  # Low threshold as in frontend
        
        # 5. Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"  Found {len(contours)} contours")
        
        # 6. Filter contours by size and shape
        valid_contours = []
        min_dimension = min(scaled_width, scaled_height) * 0.1  # 10% as in frontend
        
        for contour in contours:
            # Approximate to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(approx) >= 4:  # At least 4 points
                # Get bounding rect
                x, y, w, h = cv2.boundingRect(contour)
                
                # Check minimum size
                if w >= min_dimension and h >= min_dimension:
                    # Check aspect ratio
                    aspect_ratio = w / h if h > 0 else 0
                    if 0.2 <= aspect_ratio <= 5.0:  # As in frontend
                        # Reject square shapes (0.9-1.1)
                        if not (0.9 <= aspect_ratio <= 1.1):
                            # Check coverage
                            coverage = (w * h) / (scaled_width * scaled_height)
                            if 0.05 <= coverage <= 0.95:  # As in frontend
                                valid_contours.append({
                                    'contour': contour,
                                    'approx': approx,
                                    'bbox': (x, y, w, h),
                                    'aspect_ratio': aspect_ratio,
                                    'coverage': coverage
                                })
        
        print(f"  Valid contours: {len(valid_contours)}")
        
        if valid_contours:
            # Sort by area (largest first)
            valid_contours.sort(key=lambda c: c['bbox'][2] * c['bbox'][3], reverse=True)
            best = valid_contours[0]
            
            print(f"  ✅ Document detected!")
            print(f"     BBox: {best['bbox']}")
            print(f"     Aspect ratio: {best['aspect_ratio']:.2f}")
            print(f"     Coverage: {best['coverage']:.2%}")
        else:
            print(f"  ❌ No valid document found")
            print(f"     Edge pixels: {np.sum(edges > 0)}")
            print(f"     Edge density: {np.sum(edges > 0) / (scaled_width * scaled_height):.2%}")

if __name__ == "__main__":
    test_frontend_detection()

