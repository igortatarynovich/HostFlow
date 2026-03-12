"""
6-point document contour detection and manipulation.
Reduces to 4-point perspective warp for manual contours to avoid stitching artefacts.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Contour6Points:
    """
    Manages 6-point document contour (p1..p6) but warps using 4 corners:
    p1: top-left, p2: top-right, p3: right-center, p4: bottom-right,
    p5: bottom-left, p6: left-center.
    """

    def __init__(self, points: Optional[List[Tuple[float, float]]] = None):
        if points is None:
            self.points: Optional[List[Tuple[float, float]]] = None
        elif len(points) == 4:
            self.points = self._quad_to_6points(points)
        elif len(points) == 6:
            self.points = points
        else:
            raise ValueError(f"Expected 4 or 6 points, got {len(points)}")

    @staticmethod
    def _quad_to_6points(quad: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        p1 = np.array(quad[0])
        p2 = np.array(quad[1])
        p3 = np.array(quad[2])
        p4 = np.array(quad[3])
        p3_mid = (p2 + p3) / 2
        p6_mid = (p4 + p1) / 2
        return [
            tuple(p1),
            tuple(p2),
            tuple(p3_mid),
            tuple(p3),
            tuple(p4),
            tuple(p6_mid),
        ]

    def to_4points(self) -> List[Tuple[float, float]]:
        if self.points is None:
            return []
        return [
            self.points[0],  # top-left
            self.points[1],  # top-right
            self.points[3],  # bottom-right
            self.points[4],  # bottom-left
        ]

    def to_numpy(self) -> np.ndarray:
        if self.points is None:
            return np.array([])
        return np.array(self.points, dtype=np.float32)

    def validate(self) -> Tuple[bool, List[str]]:
        if self.points is None or len(self.points) < 4:
            return False, ["Недостаточно точек"]
        errors: List[str] = []
        pts = np.array(self.points)
        width = np.max(pts[:, 0]) - np.min(pts[:, 0])
        height = np.max(pts[:, 1]) - np.min(pts[:, 1])
        min_size = 50
        if width < min_size or height < min_size:
            errors.append(f"Документ слишком маленький (минимум {min_size}px)")
        return len(errors) == 0, errors

    def warp_perspective_6points(
        self,
        image: np.ndarray,
        output_width: Optional[int] = None,
        output_height: Optional[int] = None,
    ) -> np.ndarray:
        """
        Apply perspective transform using only the 4 corner points to a rectangle.
        This avoids duplicated halves that happened with piecewise affine.
        """
        if self.points is None or len(self.points) < 4:
            return image

        quad_pts = self.to_4points()
        if len(quad_pts) < 4:
            return image

        if output_width is None or output_height is None:
            widthA = np.linalg.norm(np.array(quad_pts[1]) - np.array(quad_pts[0]))
            widthB = np.linalg.norm(np.array(quad_pts[2]) - np.array(quad_pts[3]))
            heightA = np.linalg.norm(np.array(quad_pts[3]) - np.array(quad_pts[0]))
            heightB = np.linalg.norm(np.array(quad_pts[2]) - np.array(quad_pts[1]))
            output_width = max(int(max(widthA, widthB)), 100)
            output_height = max(int(max(heightA, heightB)), 100)

        src_pts = np.array(quad_pts, dtype=np.float32)
        dst_pts = np.array(
            [
                [0, 0],
                [output_width - 1, 0],
                [output_width - 1, output_height - 1],
                [0, output_height - 1],
            ],
            dtype=np.float32,
        )

        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(
            image,
            M,
            (output_width, output_height),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
        return warped
