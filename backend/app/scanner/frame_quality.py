"""
Frame quality assessment for document scanning.
Evaluates sharpness, lighting, glare, perspective, and stability.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FrameQualityAnalyzer:
    """Analyzes frame quality for auto-capture decisions."""
    
    def __init__(
        self,
        blur_threshold: float = 0.3,
        min_brightness: int = 50,
        max_brightness: int = 240,
        max_glare_ratio: float = 0.15,
        max_perspective_distortion: float = 0.25,
        min_area_ratio: float = 0.2,
        max_area_ratio: float = 0.8,
    ):
        self.blur_threshold = blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.max_glare_ratio = max_glare_ratio
        self.max_perspective_distortion = max_perspective_distortion
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
    
    def analyze(
        self,
        image: np.ndarray,
        document_contour: Optional[np.ndarray] = None,
    ) -> Dict:
        """
        Analyze frame quality.
        
        Args:
            image: Input image (BGR or grayscale)
            document_contour: Optional 4-point document contour
            
        Returns:
            Dictionary with quality metrics and hints
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        h, w = gray.shape
        
        # 1. Sharpness / Blur Score
        sharpness_score = self._calculate_sharpness(gray)
        is_sharp = sharpness_score >= self.blur_threshold
        
        # 2. Lighting
        brightness_score, brightness_level = self._analyze_brightness(gray)
        is_well_lit = self.min_brightness <= brightness_level <= self.max_brightness
        
        # 3. Glare detection
        glare_score, glare_ratio = self._detect_glare(gray)
        has_glare = glare_ratio > self.max_glare_ratio
        
        # 4. Perspective and tilt
        perspective_score = 1.0
        tilt_angle = 0.0
        if document_contour is not None and len(document_contour) >= 4:
            perspective_score, tilt_angle = self._analyze_perspective(document_contour, w, h)
        
        is_perspective_ok = perspective_score >= (1.0 - self.max_perspective_distortion)
        
        # 5. Document area coverage
        area_ratio = 1.0
        if document_contour is not None:
            area = cv2.contourArea(document_contour)
            area_ratio = area / (w * h)
        
        is_area_ok = self.min_area_ratio <= area_ratio <= self.max_area_ratio
        
        # Overall quality
        passed = (
            is_sharp and
            is_well_lit and
            not has_glare and
            is_perspective_ok and
            is_area_ok
        )
        
        # Generate hints
        hints = []
        if not is_sharp:
            hints.append("Держите телефон неподвижно")
        if brightness_level < self.min_brightness:
            hints.append("Документ слишком тёмный")
        elif brightness_level > self.max_brightness:
            hints.append("Слишком яркое освещение")
        if has_glare:
            hints.append("Уберите блики")
        if not is_perspective_ok:
            hints.append("Слишком сильный наклон")
        if area_ratio < self.min_area_ratio:
            hints.append("Поднимите телефон выше")
        elif area_ratio > self.max_area_ratio:
            hints.append("Отодвиньте телефон дальше")
        
        return {
            "passed": passed,
            "sharpness": {
                "score": float(sharpness_score),
                "passed": is_sharp,
            },
            "brightness": {
                "score": float(brightness_score),
                "level": int(brightness_level),
                "passed": is_well_lit,
            },
            "glare": {
                "score": float(glare_score),
                "ratio": float(glare_ratio),
                "passed": not has_glare,
            },
            "perspective": {
                "score": float(perspective_score),
                "tilt_angle": float(tilt_angle),
                "passed": is_perspective_ok,
            },
            "area": {
                "ratio": float(area_ratio),
                "passed": is_area_ok,
            },
            "hints": hints,
        }
    
    def _calculate_sharpness(self, gray: np.ndarray) -> float:
        """Calculate image sharpness using Laplacian variance."""
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        # Normalize to 0-1 range (typical values: 0-500)
        normalized = min(1.0, variance / 500.0)
        return normalized
    
    def _analyze_brightness(self, gray: np.ndarray) -> Tuple[float, int]:
        """Analyze brightness level."""
        mean_brightness = np.mean(gray)
        
        # Score: 1.0 if in optimal range, decreases outside
        if self.min_brightness <= mean_brightness <= self.max_brightness:
            score = 1.0
        elif mean_brightness < self.min_brightness:
            # Too dark
            score = max(0.0, mean_brightness / self.min_brightness)
        else:
            # Too bright
            score = max(0.0, (255 - mean_brightness) / (255 - self.max_brightness))
        
        return score, int(mean_brightness)
    
    def _detect_glare(self, gray: np.ndarray) -> Tuple[float, float]:
        """Detect glare (overexposed regions)."""
        # Threshold for glare (very bright pixels)
        glare_threshold = 240
        glare_pixels = np.sum(gray > glare_threshold)
        total_pixels = gray.size
        glare_ratio = glare_pixels / total_pixels
        
        # Score: 1.0 if no glare, decreases with glare
        score = max(0.0, 1.0 - (glare_ratio / self.max_glare_ratio))
        
        return score, glare_ratio
    
    def _analyze_perspective(
        self,
        contour: np.ndarray,
        image_width: int,
        image_height: int,
    ) -> Tuple[float, float]:
        """Analyze perspective distortion and tilt."""
        if len(contour) < 4:
            return 0.0, 0.0
        
        # Order points: top-left, top-right, bottom-right, bottom-left
        pts = contour.reshape(-1, 2)
        
        # Calculate side lengths
        top_length = np.linalg.norm(pts[1] - pts[0])
        right_length = np.linalg.norm(pts[2] - pts[1])
        bottom_length = np.linalg.norm(pts[3] - pts[2])
        left_length = np.linalg.norm(pts[0] - pts[3])
        
        # Check if opposite sides are similar length (good perspective)
        top_bottom_diff = abs(top_length - bottom_length) / max(top_length, bottom_length, 1)
        left_right_diff = abs(left_length - right_length) / max(left_length, right_length, 1)
        
        # Perspective score (1.0 = perfect rectangle, 0.0 = severe distortion)
        perspective_score = 1.0 - max(top_bottom_diff, left_right_diff)
        
        # Calculate tilt angle (deviation from horizontal)
        top_angle = np.arctan2(pts[1][1] - pts[0][1], pts[1][0] - pts[0][0])
        tilt_angle_deg = np.degrees(top_angle)
        
        # Normalize to 0-90 degrees
        tilt_angle_deg = abs(tilt_angle_deg % 90)
        if tilt_angle_deg > 45:
            tilt_angle_deg = 90 - tilt_angle_deg
        
        return perspective_score, tilt_angle_deg

