"""
SMPL-X Wrapping Module for MemeForty Phase 2.

Step 2: SMPL-X-based Mesh Wrapping
- Template Fitting: Place SMPL-X inside generated mesh
- Shrink-wrap Algorithm: Vacuum-pack SMPL-X to mesh surface
- Standardizes all avatars to same vertex count for animation reuse
"""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Optional, Tuple, Union, Dict, Any, List

import numpy as np
import torch
from loguru import logger

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False


def flush_vram():
    """Flush VRAM cache to prevent OOM."""
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()


class ShrinkWrapAlgorithm:
    """
    Shrink-wrap algorithm implementation.
    
    Projects template mesh vertices onto target mesh surface
    like vacuum packaging.
    """
    
    def __init__(self, iterations: int = 10, smooth_factor: float = 0.3):
        """
        Initialize shrink-wrap algorithm.
        
        Args:
            iterations: Number of shrink-wrap iterations
            smooth_factor: Laplacian smoothing factor between iterations
        """
        self.iterations = iterations
        self.smooth_factor = smooth_factor
    
    def project_to_surface(
        self,
        source_vertices: np.ndarray,
        target_mesh: "trimesh.Trimesh",
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Project source vertices to closest points on target surface.
        
        Args:
            source_vertices: (N, 3) vertices to project
            target_mesh: Target mesh to project onto
            
        Returns:
            Tuple of (projected_vertices, distances)
        """
        # Find closest points on target mesh
        closest_points, distances, face_ids = target_mesh.nearest.on_surface(source_vertices)
        
        return closest_points, distances
    
    def laplacian_smooth(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        factor: float = 0.5,
    ) -> np.ndarray:
        """
        Apply Laplacian smoothing to vertices.
        
        Args:
            vertices: (N, 3) vertex positions
            faces: (F, 3) face indices
            factor: Smoothing factor (0-1)
            
        Returns:
            Smoothed vertices
        """
        from scipy.sparse import lil_matrix
        
        n_verts = len(vertices)
        
        # Build adjacency matrix
        adj = lil_matrix((n_verts, n_verts))
        for face in faces:
            for i in range(3):
                adj[face[i], face[(i + 1) % 3]] = 1
                adj[face[(i + 1) % 3], face[i]] = 1
        
        adj = adj.tocsr()
        
        # Compute Laplacian
        smoothed = vertices.copy()
        for i in range(n_verts):
            neighbors = adj[i].nonzero()[1]
            if len(neighbors) > 0:
                neighbor_mean = vertices[neighbors].mean(axis=0)
                smoothed[i] = vertices[i] * (1 - factor) + neighbor_mean * factor
        
        return smoothed
    
    def wrap(
        self,
        template_mesh: "trimesh.Trimesh",
        target_mesh: "trimesh.Trimesh",
        preserve_boundary: bool = True,
    ) -> "trimesh.Trimesh":
        """
        Perform shrink-wrap operation.
        
        Args:
            template_mesh: Source template to deform (e.g., SMPL-X)
            target_mesh: Target mesh to wrap onto
            preserve_boundary: Keep boundary vertices fixed
            
        Returns:
            Wrapped mesh with template topology and target shape
        """
        vertices = template_mesh.vertices.copy()
        faces = template_mesh.faces.copy()
        
        # Identify boundary vertices if needed
        boundary_mask = np.zeros(len(vertices), dtype=bool)
        if preserve_boundary:
            edges = template_mesh.edges_unique
            edge_counts = np.bincount(edges.flatten(), minlength=len(vertices))
            boundary_mask = edge_counts < 6  # Simplified boundary detection
        
        logger.info(f"Starting shrink-wrap: {self.iterations} iterations")
        
        for iteration in range(self.iterations):
            # Project to target surface
            projected, distances = self.project_to_surface(vertices, target_mesh)
            
            # Blend with projection (stronger as iterations progress)
            blend = (iteration + 1) / self.iterations
            vertices = vertices * (1 - blend * 0.5) + projected * (blend * 0.5)
            
            # Preserve boundary
            if preserve_boundary:
                vertices[boundary_mask] = template_mesh.vertices[boundary_mask]
            
            # Apply smoothing
            vertices = self.laplacian_smooth(vertices, faces, self.smooth_factor)
            
            avg_dist = np.mean(distances)
            logger.debug(f"Iteration {iteration + 1}: avg_distance={avg_dist:.4f}")
        
        # Final projection
        vertices, _ = self.project_to_surface(vertices, target_mesh)
        
        result = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        logger.info(f"Shrink-wrap complete: {len(result.vertices)} vertices")
        
        return result


class SMPLXWrapper:
    """
    SMPL-X based mesh wrapping for avatar standardization.
    
    Converts arbitrary AI-generated meshes to standard SMPL-X topology,
    enabling animation reuse across all avatars.
    """
    
    _instance: Optional["SMPLXWrapper"] = None
    
    @classmethod
    def get_instance(cls) -> "SMPLXWrapper":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(
        self,
        device: str = "cuda",
        gender: str = "neutral",
    ):
        """
        Initialize SMPL-X wrapper.
        
        Args:
            device: Device for SMPL-X inference
            gender: Body gender (neutral, male, female)
        """
        self.device = device
        self.gender = gender
        self._smplx_model = None
        self._loaded = False
        
        self.shrink_wrap = ShrinkWrapAlgorithm(iterations=10, smooth_factor=0.3)
        
        logger.info(f"SMPLXWrapper initialized (gender={gender})")
    
    def load_model(self) -> None:
        """Load SMPL-X model."""
        if self._loaded:
            return
        
        try:
            import smplx
            from config import settings
            
            model_path = settings.smplx_model_path or settings.model_weights_dir / "smplx"
            
            self._smplx_model = smplx.create(
                model_path=str(model_path),
                model_type="smplx",
                gender=self.gender,
                num_betas=10,
            ).to(self.device)
            
            self._loaded = True
            logger.info("SMPL-X model loaded")
        except Exception as e:
            logger.warning(f"SMPL-X loading failed: {e}, using fallback")
            self._loaded = True  # Mark as loaded to use fallback
    
    def unload_model(self) -> None:
        """Unload model from VRAM."""
        if self._smplx_model is not None:
            del self._smplx_model
            self._smplx_model = None
        self._loaded = False
        SMPLXWrapper._instance = None
        flush_vram()
    
    def get_template_mesh(
        self,
        height_cm: float = 170,
        weight_kg: float = 65,
        pose: Optional[np.ndarray] = None,
    ) -> "trimesh.Trimesh":
        """
        Generate SMPL-X template mesh.
        
        Args:
            height_cm: Target height in centimeters
            weight_kg: Target weight in kilograms
            pose: Optional body pose parameters
            
        Returns:
            SMPL-X mesh at specified body shape
        """
        if not self._loaded:
            self.load_model()
        
        if self._smplx_model is None:
            # Fallback to capsule
            return self._create_fallback_template(height_cm)
        
        # Compute shape betas from height/weight
        betas = self._height_weight_to_betas(height_cm, weight_kg)
        
        body_pose = torch.zeros([1, 63], dtype=torch.float32, device=self.device)
        if pose is not None:
            body_pose = torch.tensor(pose, device=self.device).reshape(1, 63)
        
        with torch.no_grad():
            output = self._smplx_model(
                betas=torch.tensor(betas, device=self.device),
                body_pose=body_pose,
                return_verts=True,
            )
        
        vertices = output.vertices[0].detach().cpu().numpy()
        
        # Scale to target height
        scale = height_cm / 170.0
        vertices = vertices * scale
        
        return trimesh.Trimesh(
            vertices=vertices,
            faces=self._smplx_model.faces,
            process=False
        )
    
    def _height_weight_to_betas(self, height_cm: float, weight_kg: float) -> np.ndarray:
        """Convert height/weight to SMPL-X betas."""
        betas = np.zeros((1, 10), dtype=np.float32)
        height_delta = (height_cm - 170.0) / 10.0
        weight_delta = (weight_kg - 65.0) / 10.0
        betas[0, 0] = np.clip(height_delta * 0.1, -2.0, 2.0)
        betas[0, 1] = np.clip(weight_delta * 0.1, -2.0, 2.0)
        return betas
    
    def _create_fallback_template(self, height_cm: float) -> "trimesh.Trimesh":
        """Create fallback template mesh."""
        height_m = max(height_cm / 100.0, 1.0)
        
        # Create humanoid shape from primitives
        # Torso
        torso = trimesh.creation.cylinder(
            radius=0.15 * height_m,
            height=0.4 * height_m,
            sections=32
        )
        torso.apply_translation([0, 0.3 * height_m, 0])
        
        # Head
        head = trimesh.creation.uv_sphere(radius=0.1 * height_m, count=[16, 16])
        head.apply_translation([0, 0.6 * height_m, 0])
        
        # Combine
        mesh = trimesh.util.concatenate([torso, head])
        return mesh
    
    def align_template_to_target(
        self,
        template: "trimesh.Trimesh",
        target: "trimesh.Trimesh",
    ) -> "trimesh.Trimesh":
        """
        Align template mesh to target mesh center and scale.
        
        Args:
            template: Template mesh to align
            target: Target mesh to align to
            
        Returns:
            Aligned template mesh
        """
        # Get bounding boxes
        template_bounds = template.bounds
        target_bounds = target.bounds
        
        # Compute centers
        template_center = (template_bounds[0] + template_bounds[1]) / 2
        target_center = (target_bounds[0] + target_bounds[1]) / 2
        
        # Compute scale (match bounding box size)
        template_size = template_bounds[1] - template_bounds[0]
        target_size = target_bounds[1] - target_bounds[0]
        
        scale = np.min(target_size / (template_size + 1e-8))
        scale = np.clip(scale, 0.5, 2.0)  # Limit scale range
        
        # Create transformation
        aligned = template.copy()
        aligned.vertices = (aligned.vertices - template_center) * scale + target_center
        
        logger.debug(f"Template aligned: scale={scale:.3f}")
        return aligned
    
    def wrap(
        self,
        target_mesh: "trimesh.Trimesh",
        height_cm: float = 170,
        weight_kg: float = 65,
    ) -> Dict[str, Any]:
        """
        Wrap SMPL-X template onto target mesh.
        
        Args:
            target_mesh: AI-generated mesh to wrap
            height_cm: Target body height
            weight_kg: Target body weight
            
        Returns:
            Dict with 'wrapped_mesh', 'template', 'quality_score'
        """
        result = {}
        
        logger.info("[Step 2.1] Generating SMPL-X template...")
        template = self.get_template_mesh(height_cm, weight_kg)
        result["template"] = template
        
        logger.info("[Step 2.2] Aligning template to target...")
        aligned_template = self.align_template_to_target(template, target_mesh)
        
        logger.info("[Step 2.3] Performing shrink-wrap...")
        wrapped = self.shrink_wrap.wrap(aligned_template, target_mesh)
        result["wrapped_mesh"] = wrapped
        
        # Calculate quality
        result["quality_score"] = self._calculate_quality(wrapped, target_mesh)
        result["vertex_count"] = len(wrapped.vertices)
        result["face_count"] = len(wrapped.faces)
        
        logger.info(f"Wrapping complete: {result['vertex_count']} vertices, quality={result['quality_score']:.1f}/10")
        return result
    
    def _calculate_quality(self, wrapped, target) -> float:
        """Calculate wrapping quality score."""
        score = 5.0
        
        # Check if mesh is valid
        if wrapped is not None and len(wrapped.vertices) > 100:
            score += 2.0
        
        # Check surface coverage
        try:
            _, distances, _ = target.nearest.on_surface(wrapped.vertices)
            avg_distance = np.mean(distances)
            if avg_distance < 0.1:
                score += 2.0
            elif avg_distance < 0.2:
                score += 1.0
        except:
            pass
        
        # Check mesh quality
        if wrapped is not None and not wrapped.is_empty:
            score += 1.0
        
        return min(10.0, score)


def wrap_mesh_to_smplx(
    mesh: "trimesh.Trimesh",
    height_cm: float = 170,
    weight_kg: float = 65,
) -> "trimesh.Trimesh":
    """
    Convenience function to wrap mesh to SMPL-X.
    
    Args:
        mesh: Input mesh
        height_cm: Target height
        weight_kg: Target weight
        
    Returns:
        Wrapped mesh with SMPL-X topology
    """
    wrapper = SMPLXWrapper.get_instance()
    result = wrapper.wrap(mesh, height_cm, weight_kg)
    return result["wrapped_mesh"]
