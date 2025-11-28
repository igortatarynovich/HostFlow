"""
6-point document contour detection and manipulation.
Supports both 4-point (quad) and 6-point (hexagon) contours.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Contour6Points:
    """Manages 6-point document contour for better handling of curved documents."""
    
    def __init__(self, points: Optional[List[Tuple[float, float]]] = None):
        """
        Initialize with 6 points or convert from 4 points.
        
        Points order:
        - p1: top-left corner
        - p2: top-right corner
        - p3: right center
        - p4: bottom-right corner
        - p5: bottom-left corner
        - p6: left center
        """
        if points is None:
            self.points = None
        elif len(points) == 4:
            # Convert 4 points to 6 points
            self.points = self._quad_to_6points(points)
        elif len(points) == 6:
            self.points = points
        else:
            raise ValueError(f"Expected 4 or 6 points, got {len(points)}")
    
    @staticmethod
    def _quad_to_6points(quad: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Convert 4-point quad to 6-point contour."""
        p1 = np.array(quad[0])  # top-left
        p2 = np.array(quad[1])  # top-right
        p3 = np.array(quad[2])  # bottom-right
        p4 = np.array(quad[3])  # bottom-left
        
        # Calculate midpoints
        p3_mid = (p2 + p3) / 2  # right center
        p6_mid = (p4 + p1) / 2  # left center
        
        return [
            tuple(p1),
            tuple(p2),
            tuple(p3_mid),
            tuple(p3),
            tuple(p4),
            tuple(p6_mid),
        ]
    
    def to_4points(self) -> List[Tuple[float, float]]:
        """Convert 6-point contour back to 4-point quad."""
        if self.points is None:
            return []
        
        # Use corner points only
        return [
            self.points[0],  # top-left
            self.points[1],  # top-right
            self.points[3],  # bottom-right
            self.points[4],  # bottom-left
        ]
    
    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array for OpenCV."""
        if self.points is None:
            return np.array([])
        return np.array(self.points, dtype=np.float32)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate contour shape.
        
        Returns:
            (is_valid, errors)
        """
        if self.points is None or len(self.points) < 4:
            return False, ["Недостаточно точек"]
        
        errors = []
        pts = np.array(self.points)
        
        # Check for self-intersections (simplified)
        # Check minimum size
        width = np.max(pts[:, 0]) - np.min(pts[:, 0])
        height = np.max(pts[:, 1]) - np.min(pts[:, 1])
        
        min_size = 50  # pixels
        if width < min_size or height < min_size:
            errors.append(f"Документ слишком маленький (минимум {min_size}px)")
        
        # Check angles (should be reasonable)
        for i in range(len(pts)):
            p1 = pts[i]
            p2 = pts[(i + 1) % len(pts)]
            p3 = pts[(i + 2) % len(pts)]
            
            v1 = p2 - p1
            v2 = p3 - p2
            
            # Calculate angle
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-10)
            angle = np.arccos(np.clip(cos_angle, -1, 1))
            angle_deg = np.degrees(angle)
            
            if angle_deg < 10 or angle_deg > 170:
                errors.append(f"Угол {i} слишком острый или тупой ({angle_deg:.1f}°)")
        
        return len(errors) == 0, errors
    
    def warp_perspective_6points(
        self,
        image: np.ndarray,
        output_width: Optional[int] = None,
        output_height: Optional[int] = None,
    ) -> np.ndarray:
        """
        Apply perspective transformation using 6 points.
        Uses piecewise affine transformation for better handling of curved documents.
        """
        if self.points is None or len(self.points) < 4:
            return image
        
        pts = np.array(self.points, dtype=np.float32)
        
        # If 6 points, use piecewise affine transformation
        if len(pts) == 6:
            # Split into triangles and apply affine transformation
            # This handles curved documents better than single perspective transform
            
            # Calculate output dimensions
            if output_width is None or output_height is None:
                # Estimate from bounding box
                min_x, min_y = np.min(pts, axis=0)
                max_x, max_y = np.max(pts, axis=0)
                output_width = int(max_x - min_x)
                output_height = int(max_y - min_y)
                output_width = max(output_width, 100)
                output_height = max(output_height, 100)
            
            # Create destination points (rectangular)
            # Use 6 points in destination too for smoother transformation
            dst_pts = np.array([
                [0, 0],  # p1: top-left
                [output_width - 1, 0],  # p2: top-right
                [output_width - 1, output_height // 2],  # p3: right center
                [output_width - 1, output_height - 1],  # p4: bottom-right
                [0, output_height - 1],  # p5: bottom-left
                [0, output_height // 2],  # p6: left center
            ], dtype=np.float32)
            
            # Use piecewise affine transformation
            # Split into two regions: top and bottom
            h, w = image.shape[:2]
            
            # Top region: p1, p2, p3, p6
            top_src = np.array([pts[0], pts[1], pts[2], pts[5]], dtype=np.float32)
            top_dst = np.array([dst_pts[0], dst_pts[1], dst_pts[2], dst_pts[5]], dtype=np.float32)
            
            # Bottom region: p3, p4, p5, p6
            bottom_src = np.array([pts[2], pts[3], pts[4], pts[5]], dtype=np.float32)
            bottom_dst = np.array([dst_pts[2], dst_pts[3], dst_pts[4], dst_pts[5]], dtype=np.float32)
            
            # Create output image
            output = np.ones((output_height, output_width, 3), dtype=np.uint8) * 255
            
            # Apply affine transformation for top region
            M_top = cv2.getAffineTransform(top_src[:3], top_dst[:3])
            top_warped = cv2.warpAffine(
                image, M_top, (output_width, output_height // 2),
                flags=cv2.INTER_LANCZOS4,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(255, 255, 255)
            )
            output[:output_height // 2, :] = top_warped
            
            # Apply affine transformation for bottom region
            M_bottom = cv2.getAffineTransform(bottom_src[:3], bottom_dst[:3])
            bottom_warped = cv2.warpAffine(
                image, M_bottom, (output_width, output_height - output_height // 2),
                flags=cv2.INTER_LANCZOS4,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(255, 255, 255)
            )
            output[output_height // 2:, :] = bottom_warped
            
            return output
        
        # For 4 points, use standard perspective transform
        quad_pts = self.to_4points()
        if len(quad_pts) < 4:
            return image
        
        # Calculate output dimensions
        if output_width is None or output_height is None:
            # Estimate from contour
            width = int(np.linalg.norm(np.array(quad_pts[1]) - np.array(quad_pts[0])))
            height = int(np.linalg.norm(np.array(quad_pts[3]) - np.array(quad_pts[0])))
            output_width = max(width, 100)
            output_height = max(height, 100)
        
        # Order points: top-left, top-right, bottom-right, bottom-left
        src_pts = np.array(quad_pts, dtype=np.float32)
        dst_pts = np.array([
            [0, 0],
            [output_width - 1, 0],
            [output_width - 1, output_height - 1],
            [0, output_height - 1],
        ], dtype=np.float32)
        
        # Compute perspective transform
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        
        # Warp image
        warped = cv2.warpPerspective(
            image, M, (output_width, output_height),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
        
        return warped

