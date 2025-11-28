"""
Template-based document detection.
Uses template matching to find documents on images.
"""

from __future__ import annotations

import logging
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import pickle

logger = logging.getLogger(__name__)


class DocumentTemplateMatcher:
    """Match documents using templates."""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        # Try multiple possible paths for templates
        possible_paths = [
            templates_dir,
            Path("/app/templates"),  # Extracted templates directory
            Path("/opt/HostFlow/samples"),  # Original samples (fallback)
            Path(__file__).parent.parent.parent / "samples",
        ]
        
        self.templates_dir = None
        for path in possible_paths:
            if path and Path(path).exists():
                self.templates_dir = Path(path)
                break
        
        self.templates: Dict[str, List[np.ndarray]] = {}
        self.template_info: Dict[str, Dict] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load document templates from templates directory or samples."""
        if not self.templates_dir or not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return
        
        # First, try to load from extracted templates index
        index_path = self.templates_dir / "templates_index.pkl"
        if index_path.exists():
            try:
                import pickle
                with open(index_path, 'rb') as f:
                    templates_index = pickle.load(f)
                
                for doc_type, template_list in templates_index.items():
                    for template_info in template_list:
                        template_path = Path(template_info["path"])
                        if template_path.exists():
                            template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                            if template is not None:
                                if doc_type not in self.templates:
                                    self.templates[doc_type] = []
                                    self.template_info[doc_type] = {
                                        "aspect_ratios": [],
                                        "sizes": []
                                    }
                                self.templates[doc_type].append(template)
                                self.template_info[doc_type]["aspect_ratios"].append(template_info["aspect"])
                                self.template_info[doc_type]["sizes"].append(template_info["size"])
                                logger.debug(f"Loaded template: {template_path.name} as {doc_type}")
                
                logger.info(f"Loaded {sum(len(templates) for templates in self.templates.values())} templates from index")
                return
            except Exception as e:
                logger.warning(f"Failed to load template index: {e}")
        
        # Fallback: load directly from directory
        template_files = list(self.templates_dir.rglob("*.jpg")) + \
                        list(self.templates_dir.rglob("*.jpeg")) + \
                        list(self.templates_dir.rglob("*.png"))
        
        for template_path in template_files[:20]:  # Limit to first 20
            try:
                # Extract document type from path
                doc_type = self._infer_document_type(template_path)
                
                # Load template
                template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                if template is None:
                    continue
                
                # Normalize template
                template_normalized = self._normalize_template(template)
                
                if doc_type not in self.templates:
                    self.templates[doc_type] = []
                    self.template_info[doc_type] = {
                        "aspect_ratios": [],
                        "sizes": []
                    }
                
                self.templates[doc_type].append(template_normalized)
                
                # Store template info
                h, w = template_normalized.shape
                aspect = w / h if h > 0 else 1.0
                self.template_info[doc_type]["aspect_ratios"].append(aspect)
                self.template_info[doc_type]["sizes"].append((w, h))
                
                logger.debug(f"Loaded template: {template_path.name} as {doc_type}")
                
            except Exception as e:
                logger.warning(f"Failed to load template {template_path}: {e}")
        
        logger.info(f"Loaded {sum(len(templates) for templates in self.templates.values())} templates")
    
    def _infer_document_type(self, path: Path) -> str:
        """Infer document type from file path."""
        path_str = str(path).lower()
        
        if "passport" in path_str or "paszport" in path_str:
            return "passport"
        elif "licence" in path_str or "prawo jazdy" in path_str or "pj" in path_str:
            return "driver_license"
        elif "op" in path_str or "dowod" in path_str or "identity" in path_str:
            return "id_card"
        elif "karta pobytu" in path_str or "kp" in path_str:
            return "residence_card"
        elif "tacho" in path_str:
            return "tachograph_card"
        elif "adr" in path_str:
            return "adr_card"
        elif "decyzja" in path_str or "decision" in path_str:
            return "decision"
        else:
            return "unknown"
    
    def _normalize_template(self, template: np.ndarray) -> np.ndarray:
        """Normalize template to standard size for matching."""
        # Resize to standard size (maintain aspect ratio)
        # Use a reasonable size for template matching
        max_dimension = 400
        h, w = template.shape
        
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
        
        if new_w != w or new_h != h:
            template = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return template
    
    def find_document(
        self,
        image: np.ndarray,
        doc_type_hint: Optional[str] = None
    ) -> Optional[Tuple[np.ndarray, float]]:
        """
        Find document in image using template matching.
        
        Returns:
            Tuple of (contour, confidence) or None if not found
        """
        if not self.templates:
            return None
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Resize image for faster matching (if too large)
        h, w = gray.shape
        scale = 1.0
        if w > 1500 or h > 1500:
            scale = 1500.0 / max(w, h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized_gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            resized_gray = gray
        
        best_match = None
        best_confidence = 0.0
        
        # Try matching with templates
        doc_types_to_try = [doc_type_hint] if doc_type_hint and doc_type_hint in self.templates else list(self.templates.keys())
        
        for doc_type in doc_types_to_try:
            if doc_type not in self.templates:
                continue
            
            for template in self.templates[doc_type]:
                # Template matching
                result = cv2.matchTemplate(resized_gray, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_confidence:
                    best_confidence = max_val
                    
                    # Get template dimensions
                    t_h, t_w = template.shape
                    
                    # Calculate bounding box
                    top_left = max_loc
                    bottom_right = (top_left[0] + t_w, top_left[1] + t_h)
                    
                    # Scale back to original size
                    if scale < 1.0:
                        top_left = (int(top_left[0] / scale), int(top_left[1] / scale))
                        bottom_right = (int(bottom_right[0] / scale), int(bottom_right[1] / scale))
                    
                    # Create contour from bounding box
                    contour = np.array([
                        [top_left[0], top_left[1]],
                        [bottom_right[0], top_left[1]],
                        [bottom_right[0], bottom_right[1]],
                        [top_left[0], bottom_right[1]]
                    ], dtype=np.float32)
                    
                    best_match = contour
        
        # Only return if confidence is high enough
        if best_match is not None and best_confidence > 0.5:
            logger.info(f"Found document via template matching: confidence={best_confidence:.2f}")
            return best_match, best_confidence
        
        return None
    
    def find_document_multi_scale(
        self,
        image: np.ndarray,
        doc_type_hint: Optional[str] = None
    ) -> Optional[Tuple[np.ndarray, float]]:
        """
        Find document using multi-scale template matching.
        More robust but slower.
        """
        if not self.templates:
            return None
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        best_match = None
        best_confidence = 0.0
        
        doc_types_to_try = [doc_type_hint] if doc_type_hint and doc_type_hint in self.templates else list(self.templates.keys())
        
        for doc_type in doc_types_to_try:
            if doc_type not in self.templates:
                continue
            
            for template in self.templates[doc_type]:
                # Try multiple scales
                scales = [0.5, 0.75, 1.0, 1.25, 1.5]
                
                for scale in scales:
                    # Resize template
                    t_h, t_w = template.shape
                    scaled_w = int(t_w * scale)
                    scaled_h = int(t_h * scale)
                    
                    if scaled_w > gray.shape[1] or scaled_h > gray.shape[0]:
                        continue
                    
                    scaled_template = cv2.resize(template, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
                    
                    # Template matching
                    result = cv2.matchTemplate(gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(result)
                    
                    if max_val > best_confidence:
                        best_confidence = max_val
                        
                        # Calculate bounding box
                        top_left = max_loc
                        bottom_right = (top_left[0] + scaled_w, top_left[1] + scaled_h)
                        
                        # Create contour
                        contour = np.array([
                            [top_left[0], top_left[1]],
                            [bottom_right[0], top_left[1]],
                            [bottom_right[0], bottom_right[1]],
                            [top_left[0], bottom_right[1]]
                        ], dtype=np.float32)
                        
                        best_match = contour
        
        if best_match is not None and best_confidence > 0.4:  # Lower threshold for multi-scale
            logger.info(f"Found document via multi-scale template matching: confidence={best_confidence:.2f}")
            return best_match, best_confidence
        
        return None

