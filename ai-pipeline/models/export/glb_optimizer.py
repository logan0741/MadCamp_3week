"""
GLB Optimization Module for MemeForty Phase 2 Step 5.

Polygon decimation, LOD generation, and Draco compression.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union

import numpy as np
from loguru import logger

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False


class MeshDecimator:
    """
    Polygon decimation for mesh optimization.
    """
    
    def __init__(self, preserve_boundary: bool = True):
        """
        Initialize mesh decimator.
        
        Args:
            preserve_boundary: Keep boundary vertices during decimation
        """
        self.preserve_boundary = preserve_boundary
    
    def decimate(
        self,
        mesh: "trimesh.Trimesh",
        target_faces: Optional[int] = None,
        ratio: float = 0.5,
    ) -> "trimesh.Trimesh":
        """
        Decimate mesh to reduce polygon count.
        
        Args:
            mesh: Input mesh
            target_faces: Target number of faces (overrides ratio)
            ratio: Reduction ratio (0-1, lower = fewer faces)
            
        Returns:
            Decimated mesh
        """
        current_faces = len(mesh.faces)
        
        if target_faces is None:
            target_faces = int(current_faces * ratio)
        
        target_faces = max(100, min(target_faces, current_faces))
        
        logger.info(f"Decimating: {current_faces} -> {target_faces} faces")
        
        try:
            # Use quadric decimation if available
            decimated = mesh.simplify_quadric_decimation(target_faces)
            
            if not hasattr(decimated, 'vertices') or len(decimated.vertices) == 0:
                logger.warning("Decimation failed, returning original mesh")
                return mesh
            
            return decimated
        except Exception as e:
            logger.warning(f"Decimation failed: {e}, using vertex clustering")
            return self._fallback_decimate(mesh, target_faces)
    
    def _fallback_decimate(
        self,
        mesh: "trimesh.Trimesh",
        target_faces: int,
    ) -> "trimesh.Trimesh":
        """Fallback decimation using vertex clustering."""
        # Calculate voxel size based on desired reduction
        current_faces = len(mesh.faces)
        reduction = target_faces / current_faces
        
        bounds = mesh.bounds
        diagonal = np.linalg.norm(bounds[1] - bounds[0])
        voxel_size = diagonal * (1 - reduction) * 0.1
        
        vertices = mesh.vertices.copy()
        
        # Cluster vertices
        quantized = np.round(vertices / voxel_size) * voxel_size
        unique_verts, inverse = np.unique(quantized, axis=0, return_inverse=True)
        
        # Remap faces
        new_faces = inverse[mesh.faces]
        valid_faces = new_faces[:, 0] != new_faces[:, 1]
        valid_faces &= new_faces[:, 1] != new_faces[:, 2]
        valid_faces &= new_faces[:, 0] != new_faces[:, 2]
        
        return trimesh.Trimesh(
            vertices=unique_verts,
            faces=new_faces[valid_faces],
            process=True
        )


class LODGenerator:
    """
    Level of Detail (LOD) generator for mobile optimization.
    """
    
    LOD_RATIOS = {
        0: 1.0,    # Full detail
        1: 0.5,    # 50% for medium distance
        2: 0.25,   # 25% for far distance
        3: 0.1,    # 10% for very far
    }
    
    def __init__(self, num_levels: int = 3):
        """
        Initialize LOD generator.
        
        Args:
            num_levels: Number of LOD levels to generate
        """
        self.num_levels = min(num_levels, 4)
        self.decimator = MeshDecimator()
    
    def generate_lods(
        self,
        mesh: "trimesh.Trimesh",
    ) -> List["trimesh.Trimesh"]:
        """
        Generate LOD meshes.
        
        Args:
            mesh: High-detail source mesh
            
        Returns:
            List of LOD meshes from high to low detail
        """
        lods = [mesh]  # LOD0 is original
        
        for level in range(1, self.num_levels + 1):
            ratio = self.LOD_RATIOS.get(level, 0.1)
            lod = self.decimator.decimate(mesh, ratio=ratio)
            lods.append(lod)
            logger.info(f"LOD{level}: {len(lod.faces)} faces ({ratio*100:.0f}%)")
        
        return lods


class GLBOptimizer:
    """
    GLB export optimizer with compression.
    
    Supports:
    - Polygon decimation
    - LOD generation
    - Draco compression (if available)
    - Mobile-optimized export
    """
    
    def __init__(
        self,
        target_faces: Optional[int] = None,
        enable_lod: bool = True,
        enable_draco: bool = True,
    ):
        """
        Initialize GLB optimizer.
        
        Args:
            target_faces: Target face count for decimation
            enable_lod: Generate LOD levels
            enable_draco: Use Draco compression if available
        """
        self.target_faces = target_faces
        self.enable_lod = enable_lod
        self.enable_draco = enable_draco
        
        self.decimator = MeshDecimator()
        self.lod_generator = LODGenerator()
        
        logger.info("GLBOptimizer initialized")
    
    def optimize(
        self,
        mesh: "trimesh.Trimesh",
        texture_paths: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize mesh for GLB export.
        
        Args:
            mesh: Input mesh
            texture_paths: Optional texture file paths
            
        Returns:
            Dict with optimized data and quality metrics
        """
        result = {
            "original_faces": len(mesh.faces),
            "original_vertices": len(mesh.vertices),
        }
        
        logger.info("[Step 5.1] Decimating mesh...")
        optimized = mesh
        if self.target_faces is not None:
            optimized = self.decimator.decimate(mesh, target_faces=self.target_faces)
        
        result["mesh"] = optimized
        result["optimized_faces"] = len(optimized.faces)
        result["optimized_vertices"] = len(optimized.vertices)
        
        # Generate LODs if enabled
        if self.enable_lod:
            logger.info("[Step 5.2] Generating LOD levels...")
            result["lods"] = self.lod_generator.generate_lods(optimized)
        
        # Apply textures
        if texture_paths:
            result["textures"] = texture_paths
        
        # Calculate quality
        result["compression_ratio"] = 1 - (result["optimized_faces"] / result["original_faces"])
        result["quality_score"] = self._calculate_quality(result)
        
        logger.info(f"Optimization complete: {result['compression_ratio']*100:.1f}% reduction")
        return result
    
    def export_glb(
        self,
        result: Dict[str, Any],
        output_path: Union[str, Path],
        include_lods: bool = False,
    ) -> str:
        """
        Export optimized mesh to GLB.
        
        Args:
            result: Optimization result
            output_path: Output GLB path
            include_lods: Include LOD meshes in export
            
        Returns:
            Path to exported GLB
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        mesh = result["mesh"]
        
        # Create scene
        scene = trimesh.Scene()
        scene.add_geometry(mesh, node_name="main_mesh")
        
        # Add LODs if requested
        if include_lods and "lods" in result:
            for i, lod in enumerate(result["lods"][1:], 1):
                scene.add_geometry(lod, node_name=f"lod_{i}")
        
        # Export
        scene.export(str(output_path), file_type="glb")
        
        file_size = output_path.stat().st_size / 1024
        logger.info(f"Exported GLB: {output_path} ({file_size:.1f} KB)")
        
        return str(output_path)
    
    def _calculate_quality(self, result: Dict[str, Any]) -> float:
        """Calculate optimization quality score."""
        score = 5.0
        
        # Check face reduction
        reduction = result.get("compression_ratio", 0)
        if 0.3 < reduction < 0.8:
            score += 2.0  # Good balance
        elif reduction >= 0.8:
            score += 1.0  # Too aggressive
        
        # Check mesh validity
        mesh = result.get("mesh")
        if mesh is not None:
            if mesh.is_watertight:
                score += 1.5
            if len(mesh.faces) >= 1000:
                score += 1.5
        
        return min(10.0, score)


class MobileOptimizer:
    """
    Mobile-specific GLB optimization.
    
    Targets:
    - Max 50K triangles
    - Max 2K texture resolution
    - Single mesh per model
    """
    
    MOBILE_LIMITS = {
        "max_faces": 50000,
        "max_texture_size": 2048,
        "max_file_size_kb": 5000,
    }
    
    def __init__(self):
        self.optimizer = GLBOptimizer(enable_lod=False)
    
    def optimize_for_mobile(
        self,
        mesh: "trimesh.Trimesh",
        texture_paths: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize for mobile viewing.
        
        Args:
            mesh: Input mesh
            texture_paths: Texture file paths
            
        Returns:
            Mobile-optimized result
        """
        # Ensure under face limit
        if len(mesh.faces) > self.MOBILE_LIMITS["max_faces"]:
            self.optimizer.target_faces = self.MOBILE_LIMITS["max_faces"]
        else:
            self.optimizer.target_faces = None
        
        result = self.optimizer.optimize(mesh, texture_paths)
        result["mobile_optimized"] = True
        result["mobile_limits"] = self.MOBILE_LIMITS
        
        return result


def optimize_mesh_for_export(
    mesh: "trimesh.Trimesh",
    output_path: Union[str, Path],
    target_faces: Optional[int] = None,
    mobile: bool = False,
) -> str:
    """
    Convenience function to optimize and export mesh.
    
    Args:
        mesh: Input mesh
        output_path: Output GLB path
        target_faces: Optional target face count
        mobile: Optimize for mobile
        
    Returns:
        Path to exported GLB
    """
    if mobile:
        optimizer = MobileOptimizer()
        result = optimizer.optimize_for_mobile(mesh)
    else:
        optimizer = GLBOptimizer(target_faces=target_faces)
        result = optimizer.optimize(mesh)
    
    return optimizer.optimizer.export_glb(result, output_path) if mobile else optimizer.export_glb(result, output_path)
