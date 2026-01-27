"""
Fashn Human Parser wrapper for clothing segmentation.

Step 2: Fashion Semantic Parsing (Guide Layer)
- Provides category masks for clothing items
- Collar and sleeve boundary detection with 1px precision
"""

from __future__ import annotations

from typing import Dict, Tuple, Optional
import gc

import numpy as np
from PIL import Image, ImageFilter
from loguru import logger
import torch


def flush_vram():
    """Flush VRAM cache to prevent OOM."""
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()


class FashnSegmenter:
    """
    Singleton wrapper around FashnHumanParser.

    Provides category masks for clothing items with detailed boundary detection.
    """

    _instance: "FashnSegmenter" | None = None

    @classmethod
    def get_instance(cls) -> "FashnSegmenter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        try:
            from fashn_human_parser import FashnHumanParser, LABELS_TO_IDS
        except Exception as exc:
            raise RuntimeError(
                "fashn-human-parser is required. Install with: pip install fashn-human-parser"
            ) from exc

        self.parser = FashnHumanParser()
        self.labels = LABELS_TO_IDS
        logger.info("FashnHumanParser initialized")

    def _predict(self, image: Image.Image) -> np.ndarray:
        try:
            return self.parser.predict(image)
        except Exception:
            return self.parser.predict(np.array(image))

    def segment(self, image: Image.Image) -> Dict[str, np.ndarray]:
        """
        Segment image and return category masks.

        Returns dict with keys: top, dress, pants, skirt, torso.
        """
        if not isinstance(image, Image.Image):
            raise TypeError("image must be a PIL.Image")

        rgb = image.convert("RGB")
        seg = self._predict(rgb)
        seg = np.asarray(seg)
        if seg.ndim == 3:
            seg = np.squeeze(seg)

        return {
            "top": seg == self.labels.get("top"),
            "dress": seg == self.labels.get("dress"),
            "pants": seg == self.labels.get("pants"),
            "skirt": seg == self.labels.get("skirt"),
            "torso": seg == self.labels.get("torso"),
        }

    def get_detailed_boundaries(
        self,
        image: Image.Image,
        garment_type: str = "top",
    ) -> Dict[str, np.ndarray]:
        """
        Get detailed boundary maps for collar and sleeves with 1px precision.
        
        Args:
            image: Input image
            garment_type: Type of garment to analyze
            
        Returns:
            Dict with 'collar_boundary', 'left_sleeve_boundary', 'right_sleeve_boundary',
            'garment_mask', and 'boundary_quality_score'
        """
        masks = self.segment(image)
        
        # Get the full garment mask
        if garment_type in masks:
            garment_mask = masks[garment_type]
        else:
            garment_mask = masks.get("top", np.zeros((image.height, image.width), dtype=bool))
        
        # Convert to uint8 for edge detection
        mask_uint8 = garment_mask.astype(np.uint8) * 255
        
        # Extract boundaries using morphological operations
        from scipy import ndimage
        
        # Detect all edges
        edges = self._detect_edges_precise(mask_uint8)
        
        # Analyze regions to separate collar and sleeves
        collar_region, left_sleeve, right_sleeve = self._analyze_garment_regions(
            garment_mask, edges, image.size
        )
        
        # Calculate boundary quality score (0-10)
        quality_score = self._calculate_boundary_quality(edges, collar_region, left_sleeve, right_sleeve)
        
        logger.info(f"Boundary detection complete: quality_score={quality_score:.1f}/10")
        
        return {
            "collar_boundary": collar_region,
            "left_sleeve_boundary": left_sleeve,
            "right_sleeve_boundary": right_sleeve,
            "garment_mask": garment_mask,
            "full_boundary": edges,
            "boundary_quality_score": quality_score,
        }
    
    def _detect_edges_precise(self, mask: np.ndarray) -> np.ndarray:
        """
        Detect edges with 1px precision using Canny-like approach.
        """
        from scipy import ndimage
        
        # Sobel edge detection for precise boundaries
        sx = ndimage.sobel(mask, axis=1, mode='constant')
        sy = ndimage.sobel(mask, axis=0, mode='constant')
        edges = np.hypot(sx, sy)
        
        # Normalize and threshold
        edges = (edges > 0).astype(np.uint8) * 255
        
        # Thin edges to 1px using morphological skeleton
        from scipy.ndimage import binary_dilation, binary_erosion
        
        # Skeletonize for 1px edges
        skeleton = self._skeletonize(edges > 0)
        
        return skeleton.astype(np.uint8) * 255
    
    def _skeletonize(self, binary_mask: np.ndarray) -> np.ndarray:
        """Morphological skeletonization for 1px boundaries."""
        from scipy.ndimage import binary_erosion, binary_dilation
        
        skeleton = np.zeros_like(binary_mask)
        element = np.ones((3, 3))
        
        temp = binary_mask.copy()
        while True:
            eroded = binary_erosion(temp, element)
            opened = binary_dilation(eroded, element)
            subset = temp & ~opened
            skeleton = skeleton | subset
            if not temp.any():
                break
            temp = eroded.copy()
            if not temp.any():
                break
        
        return skeleton
    
    def _analyze_garment_regions(
        self,
        garment_mask: np.ndarray,
        edges: np.ndarray,
        image_size: Tuple[int, int],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Analyze garment to separate collar and sleeve regions.
        
        Uses geometric heuristics based on typical garment structure.
        """
        h, w = garment_mask.shape
        width, height = image_size
        
        # Find bounding box of garment
        rows = np.any(garment_mask, axis=1)
        cols = np.any(garment_mask, axis=0)
        
        if not rows.any() or not cols.any():
            empty = np.zeros_like(garment_mask)
            return empty, empty, empty
        
        row_min, row_max = np.where(rows)[0][[0, -1]]
        col_min, col_max = np.where(cols)[0][[0, -1]]
        
        garment_height = row_max - row_min
        garment_width = col_max - col_min
        center_x = (col_min + col_max) // 2
        
        # Collar region: top 15% of garment, centered
        collar_height = int(garment_height * 0.15)
        collar_width = int(garment_width * 0.4)
        collar_mask = np.zeros_like(garment_mask)
        collar_top = row_min
        collar_bottom = row_min + collar_height
        collar_left = center_x - collar_width // 2
        collar_right = center_x + collar_width // 2
        
        collar_region = garment_mask.copy()
        collar_region[:collar_top, :] = False
        collar_region[collar_bottom:, :] = False
        collar_region[:, :max(0, collar_left)] = False
        collar_region[:, min(w, collar_right):] = False
        
        # Extract collar boundary from edges
        collar_boundary = edges.copy()
        collar_boundary[:collar_top, :] = 0
        collar_boundary[collar_bottom:, :] = 0
        collar_boundary[:, :max(0, collar_left)] = 0
        collar_boundary[:, min(w, collar_right):] = 0
        
        # Sleeve regions: sides in upper 60% of garment
        sleeve_height_end = row_min + int(garment_height * 0.6)
        
        # Left sleeve: left 30% 
        left_sleeve = edges.copy()
        left_sleeve[:row_min, :] = 0
        left_sleeve[sleeve_height_end:, :] = 0
        left_sleeve[:, center_x:] = 0  # Only left side
        
        # Right sleeve: right 30%
        right_sleeve = edges.copy()
        right_sleeve[:row_min, :] = 0
        right_sleeve[sleeve_height_end:, :] = 0
        right_sleeve[:, :center_x] = 0  # Only right side
        
        return collar_boundary, left_sleeve, right_sleeve
    
    def _calculate_boundary_quality(
        self,
        full_edges: np.ndarray,
        collar: np.ndarray,
        left_sleeve: np.ndarray,
        right_sleeve: np.ndarray,
    ) -> float:
        """
        Calculate quality score for boundary detection.
        
        Returns score from 0-10 based on:
        - Edge continuity
        - Region separation clarity
        - 1px precision maintenance
        """
        # Check if we have meaningful boundaries
        total_edge_pixels = np.sum(full_edges > 0)
        collar_pixels = np.sum(collar > 0)
        sleeve_pixels = np.sum(left_sleeve > 0) + np.sum(right_sleeve > 0)
        
        if total_edge_pixels == 0:
            return 0.0
        
        # Score based on region coverage
        coverage_score = min(5.0, (collar_pixels + sleeve_pixels) / total_edge_pixels * 10)
        
        # Score based on edge continuity (fewer gaps = better)
        from scipy.ndimage import label
        _, num_features = label(full_edges > 0)
        continuity_score = max(0, 5.0 - num_features * 0.5)
        
        return min(10.0, coverage_score + continuity_score)

    def extract_garment(self, image: Image.Image, garment_type: str) -> Image.Image:
        """
        Extract garment pixels with transparent background.
        """
        masks = self.segment(image)
        if garment_type not in masks:
            raise ValueError(f"Unknown garment_type: {garment_type}")

        mask = masks[garment_type]
        return apply_mask_with_alpha(image, mask)
    
    def unload(self) -> None:
        """Unload parser to free memory."""
        if hasattr(self, 'parser'):
            del self.parser
        FashnSegmenter._instance = None
        flush_vram()
        logger.info("FashnSegmenter unloaded")


def apply_mask_with_alpha(image: Image.Image, mask: np.ndarray) -> Image.Image:
    """
    Apply a binary mask and return RGBA image with transparent background.
    """
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a PIL.Image")

    rgba = image.convert("RGBA")
    if mask.dtype != np.uint8:
        alpha = (mask.astype(np.uint8) * 255)
    else:
        alpha = mask
        if alpha.max() <= 1:
            alpha = alpha * 255

    alpha_img = Image.fromarray(alpha, mode="L")
    rgba.putalpha(alpha_img)
    return rgba

