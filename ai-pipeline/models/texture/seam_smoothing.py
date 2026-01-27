"""
Seam Smoothing Module for MemeForty Phase 2-B.

Seamless texture blending without Blender dependency.
Uses OpenCV for bilinear blending and inpainting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Union

import numpy as np
from PIL import Image
from loguru import logger

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class SeamDetector:
    """
    Detects seam regions between front and back projections.
    """
    
    def __init__(self, seam_width: int = 64):
        """
        Initialize seam detector.
        
        Args:
            seam_width: Width of the blending region in pixels
        """
        self.seam_width = seam_width
    
    def detect_seam_regions(
        self,
        front_mask: np.ndarray,
        back_mask: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect left and right seam regions.
        
        Args:
            front_mask: Binary mask for front projection
            back_mask: Binary mask for back projection
            
        Returns:
            (left_seam, right_seam) binary masks
        """
        h, w = front_mask.shape[:2]
        
        # Front covers center, back covers sides
        # Seams are at the left and right edges where they meet
        
        left_seam = np.zeros((h, w), dtype=np.uint8)
        right_seam = np.zeros((h, w), dtype=np.uint8)
        
        # Left seam region (roughly at UV x = 0.25)
        left_center = int(w * 0.25)
        left_seam[:, max(0, left_center - self.seam_width//2):left_center + self.seam_width//2] = 255
        
        # Right seam region (roughly at UV x = 0.75)
        right_center = int(w * 0.75)
        right_seam[:, max(0, right_center - self.seam_width//2):right_center + self.seam_width//2] = 255
        
        return left_seam, right_seam
    
    def get_blend_weights(
        self,
        width: int,
        seam_center: int,
    ) -> np.ndarray:
        """
        Generate linear blend weights for seam region.
        
        Args:
            width: Total width
            seam_center: X position of seam center
            
        Returns:
            (W,) array of blend weights [0, 1]
        """
        weights = np.zeros(width, dtype=np.float32)
        
        start = max(0, seam_center - self.seam_width // 2)
        end = min(width, seam_center + self.seam_width // 2)
        
        if end > start:
            weights[start:end] = np.linspace(0, 1, end - start)
        
        return weights


class BilinearBlender:
    """
    Bilinear blending for seamless texture transitions.
    """
    
    def __init__(self, blend_width: int = 64):
        """
        Initialize bilinear blender.
        
        Args:
            blend_width: Width of the blending region
        """
        self.blend_width = blend_width
    
    def blend_textures(
        self,
        front_texture: np.ndarray,
        back_texture: np.ndarray,
        blend_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Blend front and back textures at seam regions.
        
        Args:
            front_texture: Front projection texture (H, W, 3)
            back_texture: Back projection texture (H, W, 3)
            blend_mask: Optional custom blend mask
            
        Returns:
            Blended texture (H, W, 3)
        """
        h, w = front_texture.shape[:2]
        
        if blend_mask is None:
            # Create default side-seam blend mask
            blend_mask = self._create_seam_mask(h, w)
        
        # Ensure float for blending
        front = front_texture.astype(np.float32)
        back = back_texture.astype(np.float32)
        mask = blend_mask.astype(np.float32)
        
        if len(mask.shape) == 2:
            mask = mask[:, :, np.newaxis]
        
        # Bilinear blend: result = front * (1 - mask) + back * mask
        result = front * (1 - mask) + back * mask
        
        return result.astype(np.uint8)
    
    def _create_seam_mask(self, h: int, w: int) -> np.ndarray:
        """Create default seam blend mask."""
        mask = np.zeros((h, w), dtype=np.float32)
        
        # Texture is laid out as: [Back Left | Front | Back Right]
        # Seams at 1/3 and 2/3 of width
        
        left_seam = int(w * 0.33)
        right_seam = int(w * 0.67)
        
        # Left transition (0->1)
        for x in range(max(0, left_seam - self.blend_width//2), 
                       min(w, left_seam + self.blend_width//2)):
            t = (x - (left_seam - self.blend_width//2)) / self.blend_width
            mask[:, x] = t
        
        # Center is front (mask = 0)
        mask[:, left_seam + self.blend_width//2:right_seam - self.blend_width//2] = 0
        
        # Right transition (0->1)
        for x in range(max(0, right_seam - self.blend_width//2),
                       min(w, right_seam + self.blend_width//2)):
            t = (x - (right_seam - self.blend_width//2)) / self.blend_width
            mask[:, x] = t
        
        # Far right is back (mask = 1)
        mask[:, right_seam + self.blend_width//2:] = 1
        mask[:, :max(0, left_seam - self.blend_width//2)] = 1
        
        return mask


class InpaintingFiller:
    """
    Fills blind spots using OpenCV inpainting.
    """
    
    def __init__(self, inpaint_radius: int = 5):
        """
        Initialize inpainting filler.
        
        Args:
            inpaint_radius: Radius for inpainting algorithm
        """
        self.inpaint_radius = inpaint_radius
    
    def fill_blind_spots(
        self,
        texture: np.ndarray,
        blind_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Fill blind spots (armpits, crotch, etc.) using inpainting.
        
        Args:
            texture: Input texture with potential blind spots
            blind_mask: Binary mask of blind spots (255 = blind)
            
        Returns:
            Texture with blind spots filled
        """
        if blind_mask is None:
            blind_mask = self._detect_blind_spots(texture)
        
        if not np.any(blind_mask):
            return texture
        
        # Use Telea inpainting algorithm
        result = cv2.inpaint(
            texture, 
            blind_mask.astype(np.uint8),
            self.inpaint_radius,
            cv2.INPAINT_TELEA
        )
        
        logger.info(f"Filled {np.sum(blind_mask > 0)} blind spot pixels")
        return result
    
    def _detect_blind_spots(self, texture: np.ndarray) -> np.ndarray:
        """Detect blind spots as very dark or uniform regions."""
        # Consider nearly black pixels as blind spots
        gray = cv2.cvtColor(texture, cv2.COLOR_RGB2GRAY)
        blind_mask = (gray < 10).astype(np.uint8) * 255
        
        # Clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        blind_mask = cv2.morphologyEx(blind_mask, cv2.MORPH_OPEN, kernel)
        blind_mask = cv2.morphologyEx(blind_mask, cv2.MORPH_CLOSE, kernel)
        
        return blind_mask


class SeamSmoothingPipeline:
    """
    Complete seam smoothing pipeline for Phase 2-B.
    
    Combines:
    - Seam detection
    - Bilinear blending
    - Blind spot inpainting
    """
    
    def __init__(
        self,
        blend_width: int = 64,
        inpaint_radius: int = 5,
    ):
        """
        Initialize seam smoothing pipeline.
        
        Args:
            blend_width: Width of blend region
            inpaint_radius: Radius for inpainting
        """
        self.detector = SeamDetector(seam_width=blend_width)
        self.blender = BilinearBlender(blend_width=blend_width)
        self.filler = InpaintingFiller(inpaint_radius=inpaint_radius)
        
        logger.info(f"SeamSmoothingPipeline initialized (blend={blend_width}px)")
    
    def process(
        self,
        front_image: Union[str, Path, Image.Image],
        back_image: Union[str, Path, Image.Image],
        output_size: Tuple[int, int] = (2048, 2048),
    ) -> Dict[str, Any]:
        """
        Process front and back images into seamless texture.
        
        Args:
            front_image: Front projection image
            back_image: Back projection image  
            output_size: Output texture size
            
        Returns:
            Dict with 'texture', 'quality_score'
        """
        result = {}
        
        # Load images
        if isinstance(front_image, (str, Path)):
            front = np.array(Image.open(front_image).convert("RGB"))
        else:
            front = np.array(front_image.convert("RGB"))
        
        if isinstance(back_image, (str, Path)):
            back = np.array(Image.open(back_image).convert("RGB"))
        else:
            back = np.array(back_image.convert("RGB"))
        
        logger.info("[Step 1] Resizing inputs...")
        front = cv2.resize(front, output_size)
        back = cv2.resize(back, output_size)
        
        logger.info("[Step 2] Creating texture atlas...")
        atlas = self._create_atlas(front, back, output_size)
        
        logger.info("[Step 3] Bilinear blending at seams...")
        blended = self.blender.blend_textures(front, back)
        
        # Use blended version for the seam regions
        atlas = self._apply_seam_blending(atlas, blended)
        
        logger.info("[Step 4] Inpainting blind spots...")
        atlas = self.filler.fill_blind_spots(atlas)
        
        result["texture"] = atlas
        result["quality_score"] = self._calculate_quality(atlas)
        
        logger.info(f"Seam smoothing complete: quality={result['quality_score']:.1f}/10")
        return result
    
    def _create_atlas(
        self,
        front: np.ndarray,
        back: np.ndarray,
        size: Tuple[int, int],
    ) -> np.ndarray:
        """Create texture atlas from front and back."""
        w, h = size
        atlas = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Layout: [Back Left Quarter | Front Half | Back Right Quarter]
        quarter = w // 4
        half = w // 2
        
        # Back left (flipped horizontally)
        back_left = cv2.flip(back[:, half:], 1)
        atlas[:, :quarter] = cv2.resize(back_left, (quarter, h))
        
        # Front center
        atlas[:, quarter:quarter + half] = cv2.resize(front, (half, h))
        
        # Back right
        back_right = back[:, :half]
        atlas[:, quarter + half:] = cv2.resize(back_right, (quarter, h))
        
        return atlas
    
    def _apply_seam_blending(
        self,
        atlas: np.ndarray,
        blended: np.ndarray,
    ) -> np.ndarray:
        """Apply blended texture at seam regions."""
        h, w = atlas.shape[:2]
        result = atlas.copy()
        
        # Apply blending at the transition zones
        quarter = w // 4
        blend_w = self.blender.blend_width
        
        # Left seam
        left_start = max(0, quarter - blend_w)
        left_end = min(w, quarter + blend_w)
        result[:, left_start:left_end] = cv2.resize(
            blended[:, :blend_w * 2], (left_end - left_start, h)
        )
        
        # Right seam
        right_center = quarter + w // 2
        right_start = max(0, right_center - blend_w)
        right_end = min(w, right_center + blend_w)
        result[:, right_start:right_end] = cv2.resize(
            blended[:, -blend_w * 2:], (right_end - right_start, h)
        )
        
        return result
    
    def _calculate_quality(self, texture: np.ndarray) -> float:
        """Calculate texture quality score."""
        score = 5.0
        
        # Check for remaining black spots
        gray = cv2.cvtColor(texture, cv2.COLOR_RGB2GRAY)
        black_ratio = np.sum(gray < 10) / gray.size
        if black_ratio < 0.01:
            score += 2.0
        elif black_ratio < 0.05:
            score += 1.0
        
        # Check for seam visibility (edge detection at seam locations)
        w = texture.shape[1]
        quarter = w // 4
        
        left_region = texture[:, quarter - 20:quarter + 20]
        left_edges = cv2.Canny(left_region, 50, 150)
        left_edge_ratio = np.sum(left_edges > 0) / left_edges.size
        
        if left_edge_ratio < 0.1:
            score += 1.5
        
        # Check color consistency
        mean_colors = [
            texture[:, :w//3].mean(axis=(0, 1)),
            texture[:, w//3:2*w//3].mean(axis=(0, 1)),
            texture[:, 2*w//3:].mean(axis=(0, 1)),
        ]
        color_variance = np.std([np.mean(c) for c in mean_colors])
        if color_variance < 20:
            score += 1.5
        
        return min(10.0, score)
    
    def save_texture(
        self,
        result: Dict[str, Any],
        output_path: Union[str, Path],
    ) -> str:
        """Save texture to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        Image.fromarray(result["texture"]).save(output_path)
        logger.info(f"Saved seamless texture to {output_path}")
        
        return str(output_path)


# Convenience function
def smooth_texture_seams(
    front_image: Union[str, Path, Image.Image],
    back_image: Union[str, Path, Image.Image],
    output_path: Optional[Union[str, Path]] = None,
    blend_width: int = 64,
) -> Dict[str, Any]:
    """
    Convenience function for seam smoothing.
    
    Args:
        front_image: Front projection
        back_image: Back projection
        output_path: Optional output file path
        blend_width: Blend region width
        
    Returns:
        Processing result dict
    """
    pipeline = SeamSmoothingPipeline(blend_width=blend_width)
    result = pipeline.process(front_image, back_image)
    
    if output_path:
        pipeline.save_texture(result, output_path)
        result["output_path"] = str(output_path)
    
    return result
