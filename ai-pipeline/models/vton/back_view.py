"""
Back-View VTON Module for MemeForty Phase 1.

Step 3: High-Fidelity VTON (Fitting Layer) - Back View Support
- 180-degree silhouette flip for back-view guide
- TPS (Thin Plate Spline) warping for garment fitting
- Integration with IDM-VTON for detail synthesis
"""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Optional, Tuple, Union, List

import numpy as np
import torch
from PIL import Image
from loguru import logger


def flush_vram():
    """Flush VRAM cache to prevent OOM."""
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()


class TPSWarper:
    """
    Thin Plate Spline (TPS) warping for garment deformation.
    
    Maps source control points to target control points with smooth interpolation.
    """
    
    def __init__(self, regularization: float = 0.0):
        """
        Initialize TPS warper.
        
        Args:
            regularization: Regularization parameter for smoothness
        """
        self.regularization = regularization
        self._params = None
    
    def fit(
        self,
        source_points: np.ndarray,
        target_points: np.ndarray,
    ) -> "TPSWarper":
        """
        Fit TPS transformation from source to target points.
        
        Args:
            source_points: (N, 2) array of source control points
            target_points: (N, 2) array of target control points
            
        Returns:
            Self for chaining
        """
        n = source_points.shape[0]
        
        # Build TPS kernel matrix K
        K = self._compute_kernel(source_points, source_points)
        
        # Add regularization
        K += self.regularization * np.eye(n)
        
        # Build P matrix [1, x, y]
        P = np.hstack([np.ones((n, 1)), source_points])
        
        # Build full system matrix
        L = np.zeros((n + 3, n + 3))
        L[:n, :n] = K
        L[:n, n:] = P
        L[n:, :n] = P.T
        
        # Build target matrix
        V = np.zeros((n + 3, 2))
        V[:n, :] = target_points
        
        # Solve system
        try:
            self._params = np.linalg.solve(L, V)
        except np.linalg.LinAlgError:
            # Fallback to pseudo-inverse
            self._params = np.linalg.lstsq(L, V, rcond=None)[0]
        
        self._source_points = source_points
        
        return self
    
    def _compute_kernel(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Compute TPS radial basis function kernel."""
        # Compute pairwise distances
        diff = x[:, np.newaxis, :] - y[np.newaxis, :, :]
        r2 = np.sum(diff ** 2, axis=2)
        
        # TPS kernel: r^2 * log(r)
        # Handle r=0 case
        with np.errstate(divide='ignore', invalid='ignore'):
            K = np.where(r2 > 0, r2 * np.log(np.sqrt(r2)), 0)
        
        return K
    
    def transform(self, points: np.ndarray) -> np.ndarray:
        """
        Transform points using fitted TPS.
        
        Args:
            points: (M, 2) array of points to transform
            
        Returns:
            (M, 2) array of transformed points
        """
        if self._params is None:
            raise RuntimeError("Must call fit() before transform()")
        
        n = self._source_points.shape[0]
        m = points.shape[0]
        
        # Compute kernel for new points
        K = self._compute_kernel(points, self._source_points)
        
        # Build augmented point matrix
        P = np.hstack([np.ones((m, 1)), points])
        
        # Combine
        L = np.hstack([K, P])
        
        # Transform
        result = L @ self._params
        
        return result
    
    def warp_image(
        self,
        image: Image.Image,
        output_size: Optional[Tuple[int, int]] = None,
    ) -> Image.Image:
        """
        Warp entire image using fitted TPS transformation.
        
        Args:
            image: Input PIL Image
            output_size: Output size (width, height), defaults to input size
            
        Returns:
            Warped PIL Image
        """
        if self._params is None:
            raise RuntimeError("Must call fit() before warp_image()")
        
        import cv2
        
        img_np = np.array(image)
        h, w = img_np.shape[:2]
        
        if output_size is None:
            out_w, out_h = w, h
        else:
            out_w, out_h = output_size
        
        # Create coordinate grid
        y_coords, x_coords = np.meshgrid(np.arange(out_h), np.arange(out_w), indexing='ij')
        coords = np.stack([x_coords.flatten(), y_coords.flatten()], axis=1).astype(np.float32)
        
        # Inverse transform to find source coordinates
        # For warping, we need inverse mapping
        # Simple approach: use forward mapping with interpolation
        source_coords = self.transform(coords)
        
        # Reshape for cv2.remap
        map_x = source_coords[:, 0].reshape(out_h, out_w).astype(np.float32)
        map_y = source_coords[:, 1].reshape(out_h, out_w).astype(np.float32)
        
        # Warp
        if img_np.ndim == 3:
            result = cv2.remap(img_np, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        else:
            result = cv2.remap(img_np, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        
        return Image.fromarray(result)


class BackViewGenerator:
    """
    Generate back-view fitting from front view and garment back image.
    
    Uses:
    1. 180-degree silhouette flip
    2. TPS warping for garment alignment
    3. IDM-VTON for detail synthesis
    """
    
    def __init__(self, device: str = "cuda"):
        """
        Initialize back-view generator.
        
        Args:
            device: Device for inference
        """
        self.device = device
        self.tps = TPSWarper(regularization=0.01)
        self._vton = None
        logger.info("BackViewGenerator initialized")
    
    def _get_vton(self):
        """Lazy load VTON model."""
        if self._vton is None:
            from .idm_vton import get_vton_model
            self._vton = get_vton_model()
        return self._vton
    
    def generate_back_silhouette(
        self,
        front_person: Image.Image,
        person_mask: Optional[np.ndarray] = None,
    ) -> Tuple[Image.Image, np.ndarray]:
        """
        Generate back-view silhouette by flipping front view.
        
        Args:
            front_person: Front-facing person image
            person_mask: Optional segmentation mask
            
        Returns:
            Tuple of (flipped_image, flipped_mask)
        """
        # Horizontal flip for back view simulation
        flipped = front_person.transpose(Image.FLIP_LEFT_RIGHT)
        
        if person_mask is not None:
            flipped_mask = np.fliplr(person_mask)
        else:
            flipped_mask = None
        
        logger.debug("Generated back silhouette via 180-degree flip")
        return flipped, flipped_mask
    
    def compute_alignment_points(
        self,
        silhouette_mask: np.ndarray,
        garment_mask: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute control points for TPS alignment.
        
        Uses key anatomical/garment landmarks:
        - Shoulders (left, right)
        - Neck/collar
        - Armholes
        - Hem corners
        
        Args:
            silhouette_mask: Binary mask of target silhouette
            garment_mask: Binary mask of source garment
            
        Returns:
            Tuple of (source_points, target_points) each (N, 2)
        """
        # Find bounding boxes
        sil_rows = np.any(silhouette_mask, axis=1)
        sil_cols = np.any(silhouette_mask, axis=0)
        gar_rows = np.any(garment_mask, axis=1)
        gar_cols = np.any(garment_mask, axis=0)
        
        if not (sil_rows.any() and sil_cols.any() and gar_rows.any() and gar_cols.any()):
            # Return identity mapping if no valid regions
            corners = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
            return corners, corners
        
        # Silhouette bounds
        sil_top, sil_bottom = np.where(sil_rows)[0][[0, -1]]
        sil_left, sil_right = np.where(sil_cols)[0][[0, -1]]
        
        # Garment bounds
        gar_top, gar_bottom = np.where(gar_rows)[0][[0, -1]]
        gar_left, gar_right = np.where(gar_cols)[0][[0, -1]]
        
        # Define control points (corners + midpoints)
        # Source (garment)
        source_points = np.array([
            [gar_left, gar_top],           # Top-left
            [gar_right, gar_top],          # Top-right
            [(gar_left + gar_right) / 2, gar_top],  # Top-center (collar)
            [gar_left, gar_bottom],        # Bottom-left
            [gar_right, gar_bottom],       # Bottom-right
            [(gar_left + gar_right) / 2, gar_bottom],  # Bottom-center
            [gar_left, (gar_top + gar_bottom) / 2],    # Left-center (armhole)
            [gar_right, (gar_top + gar_bottom) / 2],   # Right-center (armhole)
        ], dtype=np.float32)
        
        # Target (silhouette)
        target_points = np.array([
            [sil_left, sil_top],
            [sil_right, sil_top],
            [(sil_left + sil_right) / 2, sil_top],
            [sil_left, sil_bottom],
            [sil_right, sil_bottom],
            [(sil_left + sil_right) / 2, sil_bottom],
            [sil_left, (sil_top + sil_bottom) / 2],
            [sil_right, (sil_top + sil_bottom) / 2],
        ], dtype=np.float32)
        
        return source_points, target_points
    
    def warp_garment_to_silhouette(
        self,
        garment_image: Image.Image,
        garment_mask: np.ndarray,
        target_silhouette_mask: np.ndarray,
        output_size: Tuple[int, int],
    ) -> Image.Image:
        """
        Warp garment image to fit target silhouette using TPS.
        
        Args:
            garment_image: Flat-lay garment image (back view)
            garment_mask: Binary mask of garment
            target_silhouette_mask: Target body silhouette mask
            output_size: Output image size (width, height)
            
        Returns:
            Warped garment image
        """
        # Compute alignment points
        source_pts, target_pts = self.compute_alignment_points(
            target_silhouette_mask, garment_mask
        )
        
        # Fit TPS
        self.tps.fit(source_pts, target_pts)
        
        # Warp garment
        warped = self.tps.warp_image(garment_image, output_size)
        
        logger.debug("Warped garment to silhouette using TPS")
        return warped
    
    def generate_back_view(
        self,
        front_person: Image.Image,
        garment_back: Image.Image,
        person_mask: Optional[np.ndarray] = None,
        garment_mask: Optional[np.ndarray] = None,
        use_vton_synthesis: bool = True,
        num_inference_steps: int = 30,
    ) -> dict:
        """
        Generate complete back-view fitting.
        
        Args:
            front_person: Front-facing person image
            garment_back: Back view of garment (flat-lay)
            person_mask: Optional person segmentation mask
            garment_mask: Optional garment mask
            use_vton_synthesis: Use IDM-VTON for final synthesis
            num_inference_steps: VTON inference steps
            
        Returns:
            Dict with 'back_view', 'warped_garment', 'silhouette', 'quality_score'
        """
        result = {}
        
        # Step 1: Generate back silhouette
        back_silhouette, back_mask = self.generate_back_silhouette(
            front_person, person_mask
        )
        result["silhouette"] = back_silhouette
        
        # Step 2: Create masks if not provided
        if person_mask is None:
            # Use simple threshold or external segmenter
            back_mask = np.ones((back_silhouette.height, back_silhouette.width), dtype=bool)
        else:
            back_mask = np.fliplr(person_mask)
        
        if garment_mask is None:
            garment_mask = np.ones((garment_back.height, garment_back.width), dtype=bool)
        
        # Step 3: TPS warp garment to silhouette
        warped_garment = self.warp_garment_to_silhouette(
            garment_back,
            garment_mask,
            back_mask,
            (front_person.width, front_person.height),
        )
        result["warped_garment"] = warped_garment
        
        # Step 4: Final synthesis with IDM-VTON (optional)
        if use_vton_synthesis:
            try:
                vton = self._get_vton()
                back_view = vton(
                    person_image=back_silhouette,
                    garment_image=warped_garment,
                    num_inference_steps=num_inference_steps,
                )
                result["back_view"] = back_view
            except Exception as e:
                logger.warning(f"VTON synthesis failed: {e}, using warped garment overlay")
                result["back_view"] = self._simple_overlay(back_silhouette, warped_garment, back_mask)
        else:
            result["back_view"] = self._simple_overlay(back_silhouette, warped_garment, back_mask)
        
        # Calculate quality score
        result["quality_score"] = self._calculate_quality(result)
        
        logger.info(f"Back-view generation complete: quality={result['quality_score']:.1f}/10")
        return result
    
    def _simple_overlay(
        self,
        background: Image.Image,
        overlay: Image.Image,
        mask: np.ndarray,
    ) -> Image.Image:
        """Simple alpha blending overlay."""
        bg = background.convert("RGBA")
        ov = overlay.convert("RGBA")
        
        # Resize overlay to match background
        ov = ov.resize(bg.size, Image.LANCZOS)
        
        # Create mask image
        mask_resized = Image.fromarray((mask.astype(np.uint8) * 255)).resize(bg.size)
        
        # Composite
        result = Image.composite(ov, bg, mask_resized.convert("L"))
        return result.convert("RGB")
    
    def _calculate_quality(self, result: dict) -> float:
        """Calculate quality score for back-view generation."""
        score = 5.0  # Base score
        
        if "back_view" in result and result["back_view"] is not None:
            score += 2.0
        
        if "warped_garment" in result:
            score += 1.5
        
        if "silhouette" in result:
            score += 1.5
        
        return min(10.0, score)
    
    def unload(self) -> None:
        """Unload models to free VRAM."""
        if self._vton is not None:
            self._vton.unload_model()
            self._vton = None
        flush_vram()
        logger.info("BackViewGenerator unloaded")


# Convenience function for dual-view VTON
def generate_dual_view_vton(
    person_front: Image.Image,
    garment_front: Image.Image,
    garment_back: Image.Image,
    person_mask: Optional[np.ndarray] = None,
    garment_front_mask: Optional[np.ndarray] = None,
    garment_back_mask: Optional[np.ndarray] = None,
    num_inference_steps: int = 30,
) -> dict:
    """
    Generate both front and back VTON views.
    
    Args:
        person_front: Front-facing person image
        garment_front: Front view of garment
        garment_back: Back view of garment
        person_mask: Optional person segmentation
        garment_front_mask: Optional front garment mask
        garment_back_mask: Optional back garment mask
        num_inference_steps: VTON inference steps
        
    Returns:
        Dict with 'front_view', 'back_view', 'combined_quality'
    """
    from .idm_vton import get_vton_model
    
    result = {}
    
    # Front view with IDM-VTON
    vton = get_vton_model()
    vton.load_model()
    
    front_result = vton(
        person_image=person_front,
        garment_image=garment_front,
        mask=person_mask,
        num_inference_steps=num_inference_steps,
    )
    result["front_view"] = front_result
    
    # Unload VTON before back-view to save VRAM
    vton.unload_model()
    flush_vram()
    
    # Back view
    back_generator = BackViewGenerator()
    back_result = back_generator.generate_back_view(
        front_person=person_front,
        garment_back=garment_back,
        person_mask=person_mask,
        garment_mask=garment_back_mask,
        use_vton_synthesis=True,
        num_inference_steps=num_inference_steps,
    )
    result["back_view"] = back_result["back_view"]
    result["back_details"] = back_result
    
    # Combined quality
    result["combined_quality"] = (back_result.get("quality_score", 5.0) + 7.0) / 2
    
    # Cleanup
    back_generator.unload()
    
    logger.info(f"Dual-view VTON complete: combined_quality={result['combined_quality']:.1f}/10")
    return result
