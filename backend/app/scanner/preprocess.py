"""
Professional document scanner preprocessing - based on proven OpenCV algorithms.
Implements robust document detection and processing like Scanbot.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Professional document scanner preprocessor.
    Based on proven OpenCV algorithms for document scanning.
    """
    
    def __init__(self, target_dpi: int = 300):
        self.target_dpi = target_dpi
        # A4 dimensions at target DPI
        self.a4_width = int(210 * target_dpi / 25.4)  # 210mm in pixels
        self.a4_height = int(297 * target_dpi / 25.4)  # 297mm in pixels
        self.current_doc_type: Optional[str] = None
    
    def process(
        self, 
        image: np.ndarray, 
        doc_type_hint: Optional[str] = None,
        enhancement_mode: str = "standard",
        manual_contour: Optional[dict] = None
    ) -> np.ndarray:
        """
        Apply full normalization pipeline to image.
        
        Args:
            image: Input image (BGR format)
            doc_type_hint: Optional document type hint for better detection
            enhancement_mode: "standard", "strong", or "photo"
            
        Returns:
            Normalized image (high quality, color preserved)
        """
        logger.debug(f"Starting preprocessing: input shape={image.shape}, doc_type={doc_type_hint}, mode={enhancement_mode}")
        
        # Step 1: Convert to grayscale for analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Step 2: Detect document and warp perspective FIRST (before any processing)
        # This is critical - we need clean edges before processing
        # Store doc_type_hint for use in detection
        self.current_doc_type = doc_type_hint
        warped = self._detect_and_warp(image, gray, doc_type_hint, manual_contour=manual_contour)
        
        # Step 3: Deskew
        gray_warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY) if len(warped.shape) == 3 else warped
        deskewed = self._deskew(warped, gray_warped)
        
        # Step 4: Apply enhancement based on mode
        if enhancement_mode == "strong":
            enhanced = self._enhance_strong(deskewed)
        elif enhancement_mode == "photo":
            enhanced = self._enhance_photo(deskewed)
        else:  # standard
            enhanced = self._enhance_standard(deskewed)
        
        # Step 5: Resize maintaining aspect ratio
        final = self._resize_to_a4(enhanced)
        
        logger.debug(f"Preprocessing complete: output shape={final.shape}")
        return final
    
    def _enhance_standard(self, image: np.ndarray) -> np.ndarray:
        """Standard enhancement: auto-contrast, light denoise, light sharpening."""
        # Auto-contrast
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # Light denoise
        h, w = enhanced.shape[:2]
        if w < 1500 and h < 1500:
            enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, h=3, hColor=3, templateWindowSize=7, searchWindowSize=21)
        
        # Light sharpening
        if w > 1500 or h > 1500:
            return enhanced
        gaussian = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
        sharpened = cv2.addWeighted(enhanced, 1.1, gaussian, -0.1, 0)
        return sharpened
    
    def _enhance_strong(self, image: np.ndarray) -> np.ndarray:
        """Strong enhancement: binarization, brightness equalization, shadow removal."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Adaptive thresholding for binarization
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10
        )
        
        # Convert back to BGR
        result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        return result
    
    def _enhance_photo(self, image: np.ndarray) -> np.ndarray:
        """Photo/ID mode: preserve photo-realism, soft sharpening, white balance."""
        # White balance correction
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Soft contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge back
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # Soft sharpening
        gaussian = cv2.GaussianBlur(enhanced, (0, 0), 0.8)
        sharpened = cv2.addWeighted(enhanced, 1.05, gaussian, -0.05, 0)
        return sharpened
    
    def _deskew(self, image: np.ndarray, gray: np.ndarray) -> np.ndarray:
        """Detect and correct skew angle using HoughLines."""
        # Use HoughLines to detect text lines
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None or len(lines) == 0:
            return image
        
        # Calculate average angle
        angles = []
        for line in lines[:20]:  # Use first 20 lines
            rho, theta = line[0]  # HoughLines returns shape (N, 1, 2)
            angle = np.degrees(theta) - 90
            if -45 < angle < 45:  # Only consider reasonable angles
                angles.append(angle)
        
        if not angles:
            return image
        
        median_angle = np.median(angles)
        
        # Only correct if angle is significant (> 0.5 degrees)
        if abs(median_angle) < 0.5:
            return image
        
        # Rotate image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        
        return rotated
    
    def _detect_and_warp(
        self, 
        image: np.ndarray, 
        gray: np.ndarray,
        doc_type_hint: Optional[str] = None,
        manual_contour: Optional[dict] = None
    ) -> np.ndarray:
        """Detect document borders and apply perspective correction.
        Improved algorithm for textured backgrounds.
        Uses document specifications for better detection.
        """
        # Resize for faster processing (if image is too large)
        # But keep it larger for better edge detection
        h, w = gray.shape
        scale = 1.0
        if w > 2000 or h > 2000:  # Increased threshold for very large images
            scale = 2000.0 / max(w, h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized_gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            resized_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            resized_gray = gray
            resized_image = image
        
        # Strategy -1: Use manual contour if provided (user corrected it)
        if manual_contour:
            try:
                from backend.app.scanner.contour_6points import Contour6Points
                # Extract points from manual_contour dict
                # Frontend sends: {p1: {x, y, id}, p2: {x, y, id}, ...}
                def get_point(contour, key):
                    """Extract point coordinates from contour dict."""
                    point = contour.get(key, {})
                    if isinstance(point, dict):
                        return (point.get('x', 0), point.get('y', 0))
                    return (0, 0)
                
                points = [
                    get_point(manual_contour, 'p1'),
                    get_point(manual_contour, 'p2'),
                    get_point(manual_contour, 'p3'),
                    get_point(manual_contour, 'p4'),
                    get_point(manual_contour, 'p5'),
                    get_point(manual_contour, 'p6'),
                ]
                logger.info(f"Using manual contour with points: {points}")
                # Convert to Contour6Points
                contour_6pts = Contour6Points(points)
                
                # Scale points if image was resized
                if scale < 1.0:
                    scaled_points = [(p[0] * scale, p[1] * scale) for p in contour_6pts.points]
                    contour_6pts = Contour6Points(scaled_points)
                
                # Warp using manual contour (6 points)
                try:
                    # Use warp_perspective_6points for 6-point contours
                    warped = contour_6pts.warp_perspective_6points(resized_image)
                    logger.info("Using manual contour (6 points) for perspective correction")
                    return warped
                except Exception as e:
                    logger.warning(f"Manual contour warp failed: {e}, falling back to auto-detection")
            except Exception as e:
                logger.warning(f"Failed to use manual contour: {e}, falling back to auto-detection")
        
        # Strategy 0: Use document specifications to create search region
        # This helps narrow down the search area and improve accuracy
        search_region = None
        search_roi_gray = None
        search_roi_image = None
        roi_offset_x = 0
        roi_offset_y = 0
        
        if doc_type_hint:
            try:
                from backend.app.scanner.document_specs import get_document_spec_with_custom
                spec = get_document_spec_with_custom(doc_type_hint, self.target_dpi)
                if spec:
                    # Calculate expected document size in current image
                    expected_w = spec["pixel_dimensions"]["width"]
                    expected_h = spec["pixel_dimensions"]["height"]
                    
                    # Scale to image size (document might be smaller in photo)
                    scale_estimate = min(new_w / expected_w, new_h / expected_h) if expected_w > 0 and expected_h > 0 else 1.0
                    scale_estimate = min(scale_estimate, 2.0)  # Don't scale more than 2x
                    
                    scaled_w = int(expected_w * scale_estimate)
                    scaled_h = int(expected_h * scale_estimate)
                    
                    # Create search region (center of image with margins)
                    margin_x = int(scaled_w * 0.3)  # 30% margin
                    margin_y = int(scaled_h * 0.3)
                    
                    x = max(0, (new_w - scaled_w) // 2 - margin_x)
                    y = max(0, (new_h - scaled_h) // 2 - margin_y)
                    box_w = min(new_w - x, scaled_w + 2 * margin_x)
                    box_h = min(new_h - y, scaled_h + 2 * margin_y)
                    
                    search_region = (x, y, box_w, box_h)
                    roi_offset_x = x
                    roi_offset_y = y
                    
                    # Extract ROI
                    search_roi_gray = resized_gray[y:y+box_h, x:x+box_w]
                    if len(resized_image.shape) == 3:
                        search_roi_image = resized_image[y:y+box_h, x:x+box_w]
                    else:
                        search_roi_image = search_roi_gray
                    
                    logger.debug(f"Using document spec search region for {doc_type_hint}: {search_region}, expected: {scaled_w}x{scaled_h}")
            except Exception as e:
                logger.debug(f"Failed to get document spec: {e}")
        
        # Find document contour - try multiple strategies
        contour = None
        
        # Strategy 0a: Search in ROI first (if we have document spec)
        if search_roi_gray is not None:
            roi_contour = self._find_document_in_region(
                search_roi_gray, 
                search_roi_image if search_roi_image is not None else search_roi_gray,
                doc_type_hint,
                roi_offset_x,
                roi_offset_y
            )
            if roi_contour is not None:
                contour = roi_contour
                logger.info(f"Found document in spec-based search region")
        
        # Strategy 0b: Template matching (if templates available)
        # This is most reliable for known document types
        try:
            from backend.app.scanner.template_matcher import DocumentTemplateMatcher
            matcher = DocumentTemplateMatcher()
            template_result = matcher.find_document_multi_scale(resized_image)
            if template_result:
                contour, confidence = template_result
                if confidence > 0.4:
                    # Scale contour back to original size if needed
                    if scale < 1.0:
                        contour = (contour / scale).astype(np.int32)
                    logger.info(f"Found document via template matching: confidence={confidence:.2f}")
                    # Don't return yet - try other methods and use best result
        except Exception as e:
            logger.debug(f"Template matching failed: {e}")
            template_result = None
        
        # Strategy 1: Brightness-based detection (documents are usually brighter than background)
        # This works well on textured light backgrounds
        brightness_contour = self._find_document_by_brightness(resized_gray)
        
        # Strategy 2: Standard edge detection
        edge_contour = None
        if brightness_contour is None:
            logger.debug("Brightness detection failed, trying edge detection")
            edge_contour = self._find_document_contour(resized_gray)
        
        # Strategy 3: If failed, try with color-based detection
        color_contour = None
        if edge_contour is None:
            logger.debug("Edge detection failed, trying color-based detection")
            color_contour = self._find_document_by_color(resized_image)
        
        # Strategy 4: If still failed, try with enhanced contrast
        enhanced_contour = None
        if color_contour is None:
            logger.debug("Color detection failed, trying with enhanced contrast")
            enhanced = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(resized_gray)
            enhanced_contour = self._find_document_contour(enhanced)
        
        # Strategy 5: Last resort - adaptive threshold
        adaptive_contour = None
        if enhanced_contour is None:
            logger.debug("Enhanced contrast failed, trying adaptive threshold")
            adaptive = cv2.adaptiveThreshold(
                resized_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10
            )
            # Convert back to grayscale for contour detection
            adaptive_gray = cv2.cvtColor(cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR), cv2.COLOR_BGR2GRAY)
            adaptive_contour = self._find_document_contour(adaptive_gray)
        
        # Choose best contour (prefer template matching if confidence is good)
        # Template matching is most reliable for known document types
        if template_result and template_result[1] > 0.4:
            contour = template_result[0]
            if scale < 1.0:
                contour = (contour / scale).astype(np.int32)
            logger.info(f"Using template matching result: confidence={template_result[1]:.2f}")
        elif brightness_contour is not None:
            contour = brightness_contour
            logger.debug("Using brightness detection result")
        elif edge_contour is not None:
            contour = edge_contour
            logger.debug("Using edge detection result")
        elif color_contour is not None:
            contour = color_contour
            logger.debug("Using color detection result")
        elif enhanced_contour is not None:
            contour = enhanced_contour
            logger.debug("Using enhanced contrast result")
        elif adaptive_contour is not None:
            contour = adaptive_contour
            logger.debug("Using adaptive threshold result")
        
        if contour is None:
            logger.warning("Document contour not found after all attempts, using original image (no perspective correction)")
            return image
        
        # Scale contour back to original size
        if scale < 1.0:
            contour = (contour / scale).astype(np.int32)
        
        # Warp perspective
        try:
            warped = self._warp_perspective(image, contour)
            logger.info(f"Perspective correction applied successfully: warped to {warped.shape}")
            return warped
        except Exception as e:
            logger.warning(f"Perspective warp failed: {e}, using original")
            import traceback
            logger.debug(traceback.format_exc())
            return image
    
    def _find_document_contour(self, gray: np.ndarray) -> Optional[np.ndarray]:
        """
        Find document contour - improved for light and textured backgrounds.
        Uses multiple strategies to detect document edges.
        """
        h, w = gray.shape
        total_area = h * w
        
        # Strategy 1: Try multiple Canny thresholds (works on various backgrounds)
        for bilateral_d in [5, 9, 15]:  # Different bilateral filter strengths
            filtered = cv2.bilateralFilter(gray, bilateral_d, 75, 75)
            blurred = cv2.GaussianBlur(filtered, (5, 5), 0)
            
            # Try multiple Canny threshold combinations
            for low_mult in [0.3, 0.5, 0.7]:
                for high_mult in [1.5, 2.0, 3.0]:
                    median_val = np.median(blurred)
                    lower = int(max(10, low_mult * median_val))
                    upper = int(min(255, high_mult * median_val))
                    
                    if upper <= lower:
                        continue
                    
                    edged = cv2.Canny(blurred, lower, upper)
                    
                    # Morphological operations to close gaps
                    kernel = np.ones((5, 5), np.uint8)
                    edged = cv2.dilate(edged, kernel, iterations=3)
                    edged = cv2.erode(edged, kernel, iterations=2)
                    edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel, iterations=3)
                    
                    # Find contours
                    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    if contours:
                        contours = sorted(contours, key=cv2.contourArea, reverse=True)
                        
                        for contour in contours[:30]:  # Check more contours for 100% detection
                            peri = cv2.arcLength(contour, True)
                            if peri < 100:  # Lower minimum perimeter for small documents
                                continue
                            
                            epsilon = 0.02 * peri
                            approx = cv2.approxPolyDP(contour, epsilon, True)
                            
                            if len(approx) >= 4:
                                if len(approx) > 4:
                                    epsilon = 0.05 * peri
                                    approx = cv2.approxPolyDP(contour, epsilon, True)
                                
                                if len(approx) == 4:
                                    area = cv2.contourArea(approx)
                                    coverage = area / total_area
                                    
                                    # Very lenient coverage for 100% detection
                                    if 0.02 <= coverage <= 0.98:
                                        rect = self._order_points(approx.reshape(4, 2))
                                        width = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
                                        height = np.sqrt(((rect[3][0] - rect[0][0]) ** 2) + ((rect[3][1] - rect[0][1]) ** 2))
                                        aspect = max(width, height) / (min(width, height) + 1e-5)
                                        
                                        # Very lenient aspect ratio for 100% detection
                                        if 0.2 <= aspect <= 6.0:
                                            logger.info(f"Found document contour (Canny): coverage={coverage:.2f}, aspect={aspect:.2f}")
                                            return approx.reshape(4, 2)
        
        # Strategy 2: Gradient-based detection (works on light backgrounds)
        logger.debug("Canny failed, trying gradient-based detection")
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        if gradient_magnitude.max() > 0:
            gradient_magnitude = np.uint8(255 * gradient_magnitude / gradient_magnitude.max())
            _, grad_thresh = cv2.threshold(gradient_magnitude, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            kernel = np.ones((5, 5), np.uint8)
            grad_thresh = cv2.morphologyEx(grad_thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
            grad_thresh = cv2.dilate(grad_thresh, kernel, iterations=2)
            
            contours, _ = cv2.findContours(grad_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                contours = sorted(contours, key=cv2.contourArea, reverse=True)
                for contour in contours[:25]:  # Check more contours
                    peri = cv2.arcLength(contour, True)
                    if peri < 100:  # Lower minimum perimeter for small documents
                        continue
                    epsilon = 0.02 * peri
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    if len(approx) >= 4:
                        if len(approx) > 4:
                            epsilon = 0.05 * peri
                            approx = cv2.approxPolyDP(contour, epsilon, True)
                        if len(approx) == 4:
                            area = cv2.contourArea(approx)
                            coverage = area / total_area
                            # Very lenient coverage for 100% detection
                            if 0.02 <= coverage <= 0.98:
                                rect = self._order_points(approx.reshape(4, 2))
                                width = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
                                height = np.sqrt(((rect[3][0] - rect[0][0]) ** 2) + ((rect[3][1] - rect[0][1]) ** 2))
                                aspect = max(width, height) / (min(width, height) + 1e-5)
                                # Very lenient aspect ratio for 100% detection
                                if 0.2 <= aspect <= 6.0:
                                    logger.info(f"Found document contour (gradient): coverage={coverage:.2f}, aspect={aspect:.2f}")
                                    return approx.reshape(4, 2)
        
        # Strategy 3: Try adaptive threshold
        logger.debug("Gradient failed, trying adaptive threshold")
        return self._find_contour_adaptive(gray)
    
    def _find_contour_adaptive(self, gray: np.ndarray) -> Optional[np.ndarray]:
        """Find contour using adaptive threshold method with improved preprocessing."""
        h, w = gray.shape
        total_area = h * w
        
        # Preprocess to reduce texture
        filtered = cv2.bilateralFilter(gray, 15, 80, 80)
        
        # Try multiple adaptive threshold block sizes
        for block_size in [11, 15, 21]:
            adaptive = cv2.adaptiveThreshold(
                filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, 5
            )
            
            kernel = np.ones((5, 5), np.uint8)
            adaptive = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel, iterations=3)
            adaptive = cv2.dilate(adaptive, kernel, iterations=2)
            adaptive = cv2.erode(adaptive, kernel, iterations=1)
            
            contours, _ = cv2.findContours(adaptive, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            for contour in contours[:20]:  # Check more contours for 100% detection
                peri = cv2.arcLength(contour, True)
                if peri < 200:
                    continue
                
                epsilon = 0.03 * peri
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) >= 4:
                    if len(approx) > 4:
                        epsilon = 0.05 * peri
                        approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    if len(approx) == 4:
                        area = cv2.contourArea(approx)
                        coverage = area / total_area
                        
                        # Very lenient coverage for 100% detection
                        if 0.02 <= coverage <= 0.98:
                            # Check aspect ratio
                            rect = self._order_points(approx.reshape(4, 2))
                            width = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
                            height = np.sqrt(((rect[3][0] - rect[0][0]) ** 2) + ((rect[3][1] - rect[0][1]) ** 2))
                            aspect = max(width, height) / (min(width, height) + 1e-5)
                            
                            # Very lenient aspect ratio for 100% detection
                            if 0.2 <= aspect <= 6.0:
                                logger.info(f"Found contour via adaptive threshold: coverage={coverage:.2f}, aspect={aspect:.2f}")
                                return approx.reshape(4, 2)
        
        # Strategy 4: Last resort - try with even more lenient parameters
        logger.debug("All strategies failed, trying ultra-lenient detection")
        return self._find_contour_ultra_lenient(gray)
    
    def _find_contour_ultra_lenient(self, gray: np.ndarray) -> Optional[np.ndarray]:
        """Ultra-lenient detection as last resort for 100% detection rate."""
        h, w = gray.shape
        total_area = h * w
        
        # Try very aggressive Canny thresholds
        for blur_size in [(3, 3), (5, 5), (7, 7)]:
            blurred = cv2.GaussianBlur(gray, blur_size, 0)
            
            # Try very low thresholds
            for low in [5, 10, 15, 20]:
                for high in [30, 50, 70, 100]:
                    edged = cv2.Canny(blurred, low, high)
                    
                    # Aggressive morphological operations
                    kernel = np.ones((7, 7), np.uint8)
                    edged = cv2.dilate(edged, kernel, iterations=5)
                    edged = cv2.erode(edged, kernel, iterations=3)
                    edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel, iterations=5)
                    
                    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if not contours:
                        continue
                    
                    contours = sorted(contours, key=cv2.contourArea, reverse=True)
                    
                    for contour in contours[:5]:
                        peri = cv2.arcLength(contour, True)
                        if peri < 100:  # Very low minimum perimeter
                            continue
                        
                        # Try multiple epsilon values
                        for eps_ratio in [0.01, 0.02, 0.03, 0.05, 0.1]:
                            epsilon = eps_ratio * peri
                            approx = cv2.approxPolyDP(contour, epsilon, True)
                            
                            if len(approx) >= 4:
                                if len(approx) > 4:
                                    # Try to reduce to 4 points
                                    epsilon = 0.1 * peri
                                    approx = cv2.approxPolyDP(contour, epsilon, True)
                                
                                if len(approx) >= 4:
                                    # Take first 4 points if more
                                    if len(approx) > 4:
                                        approx = approx[:4]
                                    
                                    area = cv2.contourArea(approx)
                                    coverage = area / total_area
                                    
                                    # Ultra-lenient: accept almost anything
                                    if 0.01 <= coverage <= 0.99:
                                        rect = self._order_points(approx.reshape(4, 2))
                                        width = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
                                        height = np.sqrt(((rect[3][0] - rect[0][0]) ** 2) + ((rect[3][1] - rect[0][1]) ** 2))
                                        aspect = max(width, height) / (min(width, height) + 1e-5)
                                        
                                        # Ultra-lenient aspect ratio
                                        if 0.15 <= aspect <= 8.0:
                                            logger.info(f"Found contour via ultra-lenient: coverage={coverage:.2f}, aspect={aspect:.2f}")
                                            return approx.reshape(4, 2)
        
        # Final fallback: return full image as document if nothing found
        logger.warning("No contour found with any strategy, using full image as fallback")
        return np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
    
    def _warp_perspective(self, image: np.ndarray, contour: np.ndarray) -> np.ndarray:
        """Apply perspective transformation to correct document orientation."""
        # Order points: top-left, top-right, bottom-right, bottom-left
        rect = self._order_points(contour)
        (tl, tr, br, bl) = rect
        
        # Calculate dimensions - use average for more stable results
        width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        max_width = int(max(width_a, width_b))
        
        height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        max_height = int(max(height_a, height_b))
        
        # Calculate actual document dimensions from contour
        # Use the actual distances between corner points
        h, w = image.shape[:2]
        
        # Calculate coverage of document in original image
        doc_area = max_width * max_height
        img_area = w * h
        coverage = doc_area / img_area if img_area > 0 else 0.3
        
        # If document covers most of the image (>80%), it's likely the whole image
        # In this case, we should still crop to the detected rectangle
        # But if coverage is small (<30%), document is small in frame - scale up
        
        # For proper cropping, use the actual detected dimensions
        # Don't scale up if document is already large in frame
        if coverage < 0.3:
            # Small document - scale up to preserve detail
            scale_factor = 1.0 / np.sqrt(coverage) if coverage > 0 else 1.0
            scale_factor = min(scale_factor, 1.5)  # Don't scale more than 1.5x
            max_width = int(max_width * scale_factor)
            max_height = int(max_height * scale_factor)
        elif coverage > 0.9:
            # Document covers almost entire image - use detected size directly
            # This ensures we crop even if document is large
            pass
        else:
            # Medium coverage - use detected size, maybe slight scale
            pass
        
        # Ensure minimum reasonable size (don't make too small)
        min_width = max(400, int(w * 0.2))  # At least 20% of original or 400px
        min_height = max(300, int(h * 0.2))
        
        max_width = max(max_width, min_width)
        max_height = max(max_height, min_height)
        
        # Don't exceed original size too much (unless document is actually larger)
        # But allow up to 1.5x for perspective correction
        max_width = min(max_width, int(w * 1.5))
        max_height = min(max_height, int(h * 1.5))
        
        # Destination points
        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype="float32")
        
        # Compute perspective transform matrix
        M = cv2.getPerspectiveTransform(rect, dst)
        
        # Warp image with high-quality interpolation
        warped = cv2.warpPerspective(
            image, M, (max_width, max_height),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
        
        logger.debug(f"Warped from {image.shape} to {warped.shape}, coverage={coverage:.2f}")
        return warped
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Order points: top-left, top-right, bottom-right, bottom-left."""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Sum and difference to find corners
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # top-left (smallest sum)
        rect[2] = pts[np.argmax(s)]  # bottom-right (largest sum)
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right (smallest diff)
        rect[3] = pts[np.argmax(diff)]  # bottom-left (largest diff)
        
        return rect
    
    def _remove_background_soft(self, image: np.ndarray) -> np.ndarray:
        """Soft background removal - preserve color and quality like Scanbot.
        Very light enhancement to preserve natural document appearance.
        """
        # Convert to LAB for better processing
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Very light CLAHE - just subtle enhancement
        clahe = cv2.createCLAHE(clipLimit=1.3, tileGridSize=(8, 8))  # Reduced from 1.5
        l = clahe.apply(l)
        
        # Merge back
        enhanced = cv2.merge([l, a, b])
        result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        return result
    
    def _enhance_brightness_contrast(self, image: np.ndarray) -> np.ndarray:
        """Adjust brightness and contrast for optimal document visibility.
        More conservative approach to preserve natural colors for high-quality cameras.
        """
        # Convert to LAB
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Calculate current brightness
        mean_brightness = l.mean() / 255.0
        
        # Target brightness for documents (slightly bright)
        target_brightness = 0.75
        
        # Adjust if needed - more conservative
        if abs(mean_brightness - target_brightness) > 0.15:  # Only adjust if significantly off
            # Apply gamma correction
            gamma = target_brightness / (mean_brightness + 0.001)
            gamma = np.clip(gamma, 0.6, 1.8)  # More limited adjustment
            
            inv_gamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255
                            for i in np.arange(0, 256)]).astype("uint8")
            l = cv2.LUT(l, table)
        
        # More conservative contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))  # Reduced from 3.0
        l = clahe.apply(l)
        
        # Merge back
        enhanced = cv2.merge([l, a, b])
        result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        return result
    
    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """Remove noise while preserving edges.
        Lighter denoising for high-quality cameras to preserve detail.
        """
        # Use lighter denoising for high-quality images
        # Lower h values = less aggressive denoising = more detail preserved
        denoised = cv2.fastNlMeansDenoisingColored(
            image, None, 
            h=5,  # Reduced from 3 (actually increased, but h=5 is lighter than h=10)
            hColor=5,  # Reduced from 3
            templateWindowSize=7, 
            searchWindowSize=21
        )
        return denoised
    
    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        """Light sharpening - preserve quality like Scanbot.
        Subtle sharpening to enhance text without artifacts.
        """
        # Very subtle sharpening - high-quality cameras don't need much
        gaussian = cv2.GaussianBlur(image, (0, 0), 1.0)
        sharpened = cv2.addWeighted(image, 1.1, gaussian, -0.1, 0)  # More subtle
        return sharpened
    
    def _resize_to_a4(self, image: np.ndarray) -> np.ndarray:
        """Resize image maintaining aspect ratio - don't force A4, preserve document proportions.
        For high-quality cameras (iPhone 16 Pro Max), preserve more detail.
        """
        h, w = image.shape[:2]
        
        # For high-quality images, use higher resolution
        # iPhone 16 Pro Max can produce 4000+ px images
        # We want to preserve detail but not go overboard
        max_dimension = 3000  # Increased from 2000 for better quality
        
        # If image is already high quality and reasonable size, don't downscale too much
        if w > 2000 or h > 2000:
            # For very high-res images, scale down but preserve more detail
            max_dimension = 3500
        
        if w > h:
            if w > max_dimension:
                scale = max_dimension / w
                new_w = max_dimension
                new_h = int(h * scale)
            else:
                new_w, new_h = w, h
        else:
            if h > max_dimension:
                scale = max_dimension / h
                new_h = max_dimension
                new_w = int(w * scale)
            else:
                new_w, new_h = w, h
        
        # Resize with high-quality interpolation
        if new_w != w or new_h != h:
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            resized = image
        
        return resized
    
    def _find_document_contour_improved(self, gray: np.ndarray) -> Optional[np.ndarray]:
        """Improved document contour detection with better edge detection."""
        return self._find_document_contour(gray)
    
    def _find_document_by_brightness(self, gray: np.ndarray) -> Optional[np.ndarray]:
        """Find document by brightness - documents are usually brighter than background.
        This works well on textured light backgrounds (fabric, wood).
        Improved for extreme lighting conditions.
        """
        h, w = gray.shape
        total_area = h * w
        
        # Normalize brightness first for extreme lighting
        mean_brightness = np.mean(gray)
        std_brightness = np.std(gray)
        
        # If image is too bright or too dark, normalize
        normalized_gray = gray.copy()
        if mean_brightness > 200:  # Too bright
            normalized_gray = cv2.convertScaleAbs(gray, alpha=0.7, beta=-30)
        elif mean_brightness < 50:  # Too dark
            normalized_gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=30)
        
        # For very low contrast (white on white), return None to let edge detection handle it
        if std_brightness < 20 and mean_brightness > 200:
            return None  # Let other strategies handle it
        
        # Calculate local brightness variations
        blurred = cv2.GaussianBlur(normalized_gray, (15, 15), 0)
        
        # Try multiple threshold strategies
        strategies = [
            # Strategy 1: Otsu (works for most cases)
            (lambda img: cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1], "Otsu"),
            # Strategy 2: Adaptive threshold for low contrast
            (lambda img: cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2), "Adaptive"),
            # Strategy 3: Fixed threshold for high contrast
            (lambda img: cv2.threshold(img, 200, 255, cv2.THRESH_BINARY)[1] if np.mean(img) > 180 else None, "FixedHigh"),
            # Strategy 4: Mean-based threshold for low contrast
            (lambda img: cv2.threshold(img, int(np.mean(img) + 10), 255, cv2.THRESH_BINARY)[1] if np.std(img) < 30 else None, "MeanBased"),
        ]
        
        for strategy_func, strategy_name in strategies:
            try:
                bright_mask = strategy_func(blurred)
                if bright_mask is None:
                    continue
            except:
                continue
            
            # Invert if needed - documents might be darker than background
            mean_bright = np.mean(blurred[bright_mask > 128]) if np.any(bright_mask > 128) else 0
            mean_dark = np.mean(blurred[bright_mask < 128]) if np.any(bright_mask < 128) else 255
            
            if mean_dark > mean_bright and mean_dark > 0:
                # Document is darker, invert mask
                bright_mask = cv2.bitwise_not(bright_mask)
            
            # Morphological operations to clean up
            kernel = np.ones((7, 7), np.uint8)
            bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_CLOSE, kernel, iterations=5)
            bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_OPEN, kernel, iterations=3)
            
            # Find contours
            contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                contours = sorted(contours, key=cv2.contourArea, reverse=True)
                
                for contour in contours[:20]:  # Check more contours for 100% detection
                    peri = cv2.arcLength(contour, True)
                    if peri < 200:
                        continue
                    
                    epsilon = 0.02 * peri
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    if len(approx) >= 4:
                        if len(approx) > 4:
                            epsilon = 0.05 * peri
                            approx = cv2.approxPolyDP(contour, epsilon, True)
                        
                        if len(approx) == 4:
                            area = cv2.contourArea(approx)
                            coverage = area / total_area
                            
                            if 0.05 <= coverage <= 0.95:
                                rect = self._order_points(approx.reshape(4, 2))
                                width = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
                                height = np.sqrt(((rect[3][0] - rect[0][0]) ** 2) + ((rect[3][1] - rect[0][1]) ** 2))
                                aspect = max(width, height) / (min(width, height) + 1e-5)
                                
                                if 0.3 <= aspect <= 4.0:
                                    logger.info(f"Found document via brightness ({strategy_name}): coverage={coverage:.2f}, aspect={aspect:.2f}")
                                    return approx.reshape(4, 2)
        
        return None
    
    def _find_document_in_region(
        self,
        roi_gray: np.ndarray,
        roi_image: np.ndarray,
        doc_type_hint: Optional[str],
        offset_x: int,
        offset_y: int
    ) -> Optional[np.ndarray]:
        """Find document contour within a specific region (ROI).
        This is used when we have document specifications to narrow the search.
        """
        # Try template matching first
        try:
            from backend.app.scanner.template_matcher import DocumentTemplateMatcher
            matcher = DocumentTemplateMatcher()
            template_result = matcher.find_document_multi_scale(roi_image)
            if template_result:
                contour, confidence = template_result
                if confidence > 0.4:
                    # Adjust coordinates to full image
                    contour = contour.astype(np.float32)
                    contour[:, 0] += offset_x
                    contour[:, 1] += offset_y
                    logger.info(f"Found document in ROI via template matching: confidence={confidence:.2f}")
                    return contour.astype(np.int32)
        except Exception as e:
            logger.debug(f"Template matching in ROI failed: {e}")
        
        # Try brightness detection in ROI
        brightness_contour = self._find_document_by_brightness(roi_gray)
        if brightness_contour is not None:
            # Adjust coordinates to full image
            brightness_contour = brightness_contour.astype(np.float32)
            brightness_contour[:, 0] += offset_x
            brightness_contour[:, 1] += offset_y
            return brightness_contour.astype(np.int32)
        
        # Try edge detection in ROI
        edge_contour = self._find_document_contour(roi_gray)
        if edge_contour is not None:
            # Adjust coordinates to full image
            edge_contour = edge_contour.astype(np.float32)
            edge_contour[:, 0] += offset_x
            edge_contour[:, 1] += offset_y
            return edge_contour.astype(np.int32)
        
        return None
    
    def _find_document_by_color(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Find document by color difference - documents are usually brighter/whiter than background."""
        h, w = image.shape[:2]
        total_area = h * w
        
        # Convert to LAB for better color analysis
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Documents are usually brighter - find bright regions
        # Use Otsu to find optimal threshold
        _, bright_mask = cv2.threshold(l, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological operations to clean up
        kernel = np.ones((5, 5), np.uint8)
        bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            for contour in contours[:20]:  # Check more contours for 100% detection
                peri = cv2.arcLength(contour, True)
                if peri < 200:
                    continue
                
                epsilon = 0.02 * peri
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) >= 4:
                    if len(approx) > 4:
                        epsilon = 0.05 * peri
                        approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    if len(approx) == 4:
                        area = cv2.contourArea(approx)
                        coverage = area / total_area
                        
                        if 0.05 <= coverage <= 0.95:
                            rect = self._order_points(approx.reshape(4, 2))
                            width = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
                            height = np.sqrt(((rect[3][0] - rect[0][0]) ** 2) + ((rect[3][1] - rect[0][1]) ** 2))
                            aspect = max(width, height) / (min(width, height) + 1e-5)
                            
                            if 0.3 <= aspect <= 4.0:
                                logger.info(f"Found document via color detection: coverage={coverage:.2f}, aspect={aspect:.2f}")
                                return approx.reshape(4, 2)
        
        return None
    
    def _enhance_brightness_contrast_light(self, image: np.ndarray) -> np.ndarray:
        """Very light brightness/contrast enhancement - minimal processing."""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Very light CLAHE
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        enhanced = cv2.merge([l, a, b])
        result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        return result
    
    def _denoise_light(self, image: np.ndarray) -> np.ndarray:
        """Very light denoising - preserve detail."""
        denoised = cv2.fastNlMeansDenoisingColored(
            image, None,
            h=3,  # Very light
            hColor=3,
            templateWindowSize=7,
            searchWindowSize=21
        )
        return denoised
    
    def _remove_background_very_light(self, image: np.ndarray) -> np.ndarray:
        """Minimal background enhancement - almost no processing."""
        # Just return the image - no processing
        # Or very minimal if needed
        return image
    
    def _sharpen_very_light(self, image: np.ndarray) -> np.ndarray:
        """Very subtle sharpening - almost none."""
        # Skip sharpening for high-quality images
        return image
    
    def _enhance_smart(self, image: np.ndarray) -> np.ndarray:
        """Smart enhancement - improve readability without blur."""
        # Convert to LAB for better processing
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Light CLAHE for contrast - not too aggressive
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge back
        enhanced = cv2.merge([l, a, b])
        result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        return result
    
    def _denoise_very_light(self, image: np.ndarray) -> np.ndarray:
        """Very light denoising - only for low-quality images."""
        # Minimal denoising to preserve detail
        denoised = cv2.fastNlMeansDenoisingColored(
            image, None,
            h=3,  # Very light
            hColor=3,
            templateWindowSize=7,
            searchWindowSize=21
        )
        return denoised
    
    def _enhance_contrast_light(self, image: np.ndarray) -> np.ndarray:
        """Light contrast enhancement - minimal processing."""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Light CLAHE
        clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    def _sharpen_light(self, image: np.ndarray) -> np.ndarray:
        """Light sharpening - minimal."""
        gaussian = cv2.GaussianBlur(image, (0, 0), 1.0)
        sharpened = cv2.addWeighted(image, 1.15, gaussian, -0.15, 0)
        return sharpened
