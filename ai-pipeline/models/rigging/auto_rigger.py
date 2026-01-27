"""
Automatic Rigging Module for MemeForty Phase 2 Step 3.

Implements automatic bone weight calculation and rigging.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import numpy as np
from loguru import logger

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

from .skeleton import Skeleton, Bone, create_smplx_skeleton, fit_skeleton_to_mesh


class AutoRigger:
    """
    Automatic rigging for SMPL-X wrapped meshes.
    
    Calculates bone weights based on vertex proximity to skeleton.
    """
    
    def __init__(
        self,
        max_influences: int = 4,
        weight_falloff: float = 2.0,
    ):
        """
        Initialize auto rigger.
        
        Args:
            max_influences: Maximum bones per vertex
            weight_falloff: Distance falloff exponent for weights
        """
        self.max_influences = max_influences
        self.weight_falloff = weight_falloff
        
        logger.info(f"AutoRigger initialized (max_influences={max_influences})")
    
    def calculate_bone_weights(
        self,
        vertices: np.ndarray,
        skeleton: Skeleton,
    ) -> Dict[str, np.ndarray]:
        """
        Calculate bone weights for each vertex.
        
        Uses heat diffusion-like algorithm based on distance to bone axis.
        
        Args:
            vertices: (N, 3) mesh vertices
            skeleton: Fitted skeleton
            
        Returns:
            Dict mapping bone names to (N,) weight arrays
        """
        n_verts = len(vertices)
        bone_names = list(skeleton.bones.keys())
        n_bones = len(bone_names)
        
        # Calculate distance from each vertex to each bone
        distances = np.zeros((n_verts, n_bones))
        
        for i, bone_name in enumerate(bone_names):
            bone = skeleton.bones[bone_name]
            distances[:, i] = self._distance_to_bone(vertices, bone)
        
        # Convert distances to weights using inverse distance
        # Closer = higher weight
        weights = 1.0 / (distances + 1e-6) ** self.weight_falloff
        
        # Limit to max_influences per vertex
        if self.max_influences < n_bones:
            for v in range(n_verts):
                sorted_indices = np.argsort(weights[v])[::-1]
                mask = np.zeros(n_bones, dtype=bool)
                mask[sorted_indices[:self.max_influences]] = True
                weights[v, ~mask] = 0
        
        # Normalize weights per vertex
        weight_sums = weights.sum(axis=1, keepdims=True)
        weights = weights / (weight_sums + 1e-8)
        
        # Convert to dict
        weight_dict = {}
        for i, bone_name in enumerate(bone_names):
            weight_dict[bone_name] = weights[:, i]
        
        return weight_dict
    
    def _distance_to_bone(
        self,
        vertices: np.ndarray,
        bone: Bone,
    ) -> np.ndarray:
        """
        Calculate distance from vertices to bone axis.
        
        Args:
            vertices: (N, 3) vertices
            bone: Bone to calculate distance to
            
        Returns:
            (N,) array of distances
        """
        head = bone.head
        tail = bone.tail
        
        # Vector from head to tail
        bone_vec = tail - head
        bone_length = np.linalg.norm(bone_vec)
        
        if bone_length < 1e-8:
            return np.linalg.norm(vertices - head, axis=1)
        
        bone_dir = bone_vec / bone_length
        
        # Vector from head to each vertex
        to_vertex = vertices - head
        
        # Project onto bone axis
        t = np.dot(to_vertex, bone_dir)
        t = np.clip(t, 0, bone_length)
        
        # Closest point on bone
        closest = head + t[:, np.newaxis] * bone_dir
        
        # Distance to closest point
        distances = np.linalg.norm(vertices - closest, axis=1)
        
        return distances
    
    def rig_mesh(
        self,
        mesh: "trimesh.Trimesh",
        skeleton: Optional[Skeleton] = None,
        height_cm: float = 170,
    ) -> Dict[str, Any]:
        """
        Automatically rig a mesh.
        
        Args:
            mesh: Input mesh to rig
            skeleton: Optional skeleton (created if not provided)
            height_cm: Height for skeleton creation
            
        Returns:
            Dict with 'skeleton', 'weights', 'rigged_mesh', 'quality_score'
        """
        result = {}
        
        logger.info("[Step 3.1] Creating skeleton...")
        if skeleton is None:
            skeleton = create_smplx_skeleton(height_scale=height_cm / 170)
        
        logger.info("[Step 3.2] Fitting skeleton to mesh...")
        fitted_skeleton = fit_skeleton_to_mesh(skeleton, mesh.vertices)
        result["skeleton"] = fitted_skeleton
        
        logger.info("[Step 3.3] Calculating bone weights...")
        weights = self.calculate_bone_weights(mesh.vertices, fitted_skeleton)
        result["weights"] = weights
        
        # Create rigged mesh representation
        result["rigged_mesh"] = self._create_rigged_mesh(mesh, fitted_skeleton, weights)
        
        # Quality score
        result["quality_score"] = self._calculate_quality(weights)
        result["bone_count"] = fitted_skeleton.bone_count
        
        logger.info(f"Rigging complete: {result['bone_count']} bones, quality={result['quality_score']:.1f}/10")
        return result
    
    def _create_rigged_mesh(
        self,
        mesh: "trimesh.Trimesh",
        skeleton: Skeleton,
        weights: Dict[str, np.ndarray],
    ) -> Dict[str, Any]:
        """Create rigged mesh data structure for export."""
        return {
            "vertices": mesh.vertices.copy(),
            "faces": mesh.faces.copy(),
            "skeleton": skeleton,
            "bone_weights": weights,
            "vertex_count": len(mesh.vertices),
            "face_count": len(mesh.faces),
        }
    
    def _calculate_quality(self, weights: Dict[str, np.ndarray]) -> float:
        """Calculate rigging quality score."""
        score = 5.0
        
        # Check weight coverage
        total_weights = np.zeros(len(list(weights.values())[0]))
        for w in weights.values():
            total_weights += w
        
        coverage = np.mean(total_weights > 0.01)
        if coverage > 0.95:
            score += 3.0
        elif coverage > 0.8:
            score += 2.0
        elif coverage > 0.5:
            score += 1.0
        
        # Check weight smoothness
        weight_matrix = np.stack(list(weights.values()), axis=1)
        max_weights = weight_matrix.max(axis=1)
        smoothness = 1 - np.std(max_weights)
        score += smoothness * 2
        
        return min(10.0, max(0.0, score))
    
    def export_weights_for_unity(
        self,
        weights: Dict[str, np.ndarray],
        output_path: Path,
    ) -> None:
        """
        Export bone weights in Unity-compatible format.
        
        Args:
            weights: Bone weight dictionary
            output_path: Path to save JSON
        """
        import json
        
        n_verts = len(list(weights.values())[0])
        bone_names = list(weights.keys())
        
        unity_weights = []
        for v in range(n_verts):
            vertex_weights = []
            for bone in bone_names:
                if weights[bone][v] > 0.01:
                    vertex_weights.append({
                        "bone": bone,
                        "weight": float(weights[bone][v])
                    })
            # Sort by weight descending
            vertex_weights.sort(key=lambda x: x["weight"], reverse=True)
            # Limit to 4
            vertex_weights = vertex_weights[:4]
            unity_weights.append(vertex_weights)
        
        with open(output_path, "w") as f:
            json.dump({
                "bones": bone_names,
                "weights": unity_weights
            }, f, indent=2)
        
        logger.info(f"Exported weights to {output_path}")


class RiggingPipeline:
    """
    Step 3 Pipeline: Automatic Rigging
    
    Combines skeleton creation and weight calculation.
    """
    
    def __init__(self, max_influences: int = 4):
        self.rigger = AutoRigger(max_influences=max_influences)
    
    def process(
        self,
        mesh: "trimesh.Trimesh",
        height_cm: float = 170,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Process mesh through rigging pipeline.
        
        Args:
            mesh: Input mesh
            height_cm: Target height
            output_dir: Optional output directory
            
        Returns:
            Rigging result dict
        """
        result = self.rigger.rig_mesh(mesh, height_cm=height_cm)
        
        if output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Export weights
            weights_path = output_dir / "bone_weights.json"
            self.rigger.export_weights_for_unity(result["weights"], weights_path)
            result["weights_path"] = str(weights_path)
        
        return result
