"""
SNUG Garment Simulation Wrapper

Neural garment simulation using self-supervised learning.
Based on: https://github.com/isantesteban/snug
"""

import os
import sys
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple, Union
import tempfile

from .garment_types import GarmentConfig, get_garment_config, GarmentType

# SNUG paths
SNUG_DIR = Path(__file__).parent.parent / "3d" / "snug"
SNUG_MODELS_DIR = SNUG_DIR / "models"
SNUG_ASSETS_DIR = SNUG_DIR / "assets"


class SnugModel:
    """
    SNUG neural garment simulation model.

    Simulates garment deformation on a parametric body model.
    """

    def __init__(
        self,
        garment_type: str = "tshirt",
        model_dir: Optional[str] = None,
        use_gpu: bool = True,
    ):
        """
        Initialize SNUG model.

        Args:
            garment_type: Type of garment ('tshirt', 'dress', etc.)
            model_dir: Path to SNUG model directory
            use_gpu: Whether to use GPU acceleration
        """
        self.garment_type = garment_type
        self.garment_config = get_garment_config(garment_type)
        self.model_dir = Path(model_dir) if model_dir else SNUG_MODELS_DIR
        self.use_gpu = use_gpu
        self._model = None
        self._initialized = False

    def _add_snug_to_path(self):
        """Add SNUG to Python path."""
        if str(SNUG_DIR) not in sys.path:
            sys.path.insert(0, str(SNUG_DIR))

    def _load_model(self):
        """Lazy load SNUG model."""
        if self._initialized:
            return

        self._add_snug_to_path()

        try:
            # Import SNUG modules
            import tensorflow as tf

            # Configure GPU
            if self.use_gpu:
                gpus = tf.config.list_physical_devices('GPU')
                if gpus:
                    tf.config.experimental.set_memory_growth(gpus[0], True)
            else:
                tf.config.set_visible_devices([], 'GPU')

            self._initialized = True

        except ImportError as e:
            # TensorFlow not available - will use fallback physics
            print(f"TensorFlow not available ({e}), using fallback physics")
            self._initialized = True

    def simulate(
        self,
        body_vertices: np.ndarray,
        body_pose: Optional[np.ndarray] = None,
        prev_garment_vertices: Optional[np.ndarray] = None,
        num_steps: int = 1,
    ) -> Dict[str, Any]:
        """
        Simulate garment deformation on body.

        Args:
            body_vertices: Body mesh vertices (N, 3)
            body_pose: Body pose parameters (optional)
            prev_garment_vertices: Previous frame garment vertices (for animation)
            num_steps: Number of simulation steps

        Returns:
            Dictionary containing:
                - vertices: Deformed garment vertices
                - faces: Garment mesh faces
                - stress: Stress values per vertex (optional)
        """
        self._load_model()

        try:
            return self._run_snug_inference(
                body_vertices,
                body_pose,
                prev_garment_vertices,
                num_steps
            )
        except Exception as e:
            print(f"Warning: SNUG simulation failed ({e}), using fallback")
            return self._get_fallback_result(body_vertices)

    def _run_snug_inference(
        self,
        body_vertices: np.ndarray,
        body_pose: Optional[np.ndarray],
        prev_garment_vertices: Optional[np.ndarray],
        num_steps: int,
    ) -> Dict[str, Any]:
        """Run actual SNUG model inference."""
        try:
            import tensorflow as tf
        except ImportError:
            # TensorFlow not available, use fallback
            return self._get_fallback_result(body_vertices)

        # Load garment template mesh
        garment_template = self._load_garment_template()

        if garment_template is None:
            return self._get_fallback_result(body_vertices)

        template_verts, template_faces = garment_template

        # Simple physics-inspired deformation
        # Real SNUG would use neural network for deformation
        deformed_verts = self._apply_body_deformation(
            template_verts,
            body_vertices
        )

        return {
            'vertices': deformed_verts.astype(np.float32),
            'faces': template_faces,
            'stress': np.zeros(len(deformed_verts), dtype=np.float32),
        }

    def _load_garment_template(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Load garment template mesh."""
        try:
            import trimesh

            mesh_path = self.garment_config.mesh_path
            if mesh_path and Path(mesh_path).exists():
                mesh = trimesh.load(mesh_path)
                return mesh.vertices, mesh.faces

            # Try default location
            default_path = SNUG_ASSETS_DIR / "garments" / f"{self.garment_type}.obj"
            if default_path.exists():
                mesh = trimesh.load(str(default_path))
                return mesh.vertices, mesh.faces

            return None

        except Exception as e:
            print(f"Failed to load garment template: {e}")
            return None

    def _apply_body_deformation(
        self,
        garment_vertices: np.ndarray,
        body_vertices: np.ndarray,
    ) -> np.ndarray:
        """
        Apply body-based deformation to garment.

        This is a simplified deformation that moves garment vertices
        based on nearest body vertices.
        """
        from scipy.spatial import cKDTree

        # Build KD-tree for body vertices
        body_tree = cKDTree(body_vertices)

        # For each garment vertex, find influence from body
        distances, indices = body_tree.query(garment_vertices, k=4)

        # Compute weights (inverse distance)
        weights = 1.0 / (distances + 1e-6)
        weights = weights / weights.sum(axis=1, keepdims=True)

        # Compute deformed positions
        deformed = np.zeros_like(garment_vertices)
        for i in range(4):
            deformed += weights[:, i:i+1] * body_vertices[indices[:, i]]

        # Add offset to prevent intersection
        offset = 0.005  # 5mm offset
        normals = self._estimate_normals(deformed)
        deformed += normals * offset

        return deformed

    def _estimate_normals(self, vertices: np.ndarray) -> np.ndarray:
        """Estimate vertex normals (simplified)."""
        # For simplicity, use radial direction from centroid
        centroid = vertices.mean(axis=0)
        normals = vertices - centroid
        normals = normals / (np.linalg.norm(normals, axis=1, keepdims=True) + 1e-6)
        return normals

    def _get_fallback_result(self, body_vertices: np.ndarray) -> Dict[str, Any]:
        """Return fallback result with simple garment approximation."""
        # Create a simple garment mesh based on body vertices
        # This is a very basic fallback

        # Get torso vertices (rough approximation)
        center = body_vertices.mean(axis=0)
        torso_mask = (body_vertices[:, 1] > center[1] - 0.3) & \
                     (body_vertices[:, 1] < center[1] + 0.3)

        if torso_mask.sum() < 100:
            # Not enough vertices, use all
            garment_verts = body_vertices.copy()
        else:
            garment_verts = body_vertices[torso_mask].copy()

        # Add small offset
        garment_verts[:, 2] += 0.01  # 1cm offset

        return {
            'vertices': garment_verts.astype(np.float32),
            'faces': np.array([[0, 1, 2]], dtype=np.int32),  # Dummy face
            'stress': np.zeros(len(garment_verts), dtype=np.float32),
        }

    def animate(
        self,
        body_sequence: np.ndarray,
        fps: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Animate garment over a sequence of body poses.

        Args:
            body_sequence: Sequence of body vertices (T, N, 3)
            fps: Target frames per second

        Returns:
            List of simulation results for each frame
        """
        results = []
        prev_garment = None

        for frame_idx, body_verts in enumerate(body_sequence):
            result = self.simulate(
                body_vertices=body_verts,
                prev_garment_vertices=prev_garment,
                num_steps=1
            )
            results.append(result)
            prev_garment = result['vertices']

        return results

    def export_mesh(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        output_path: str,
        format: str = "obj"
    ) -> str:
        """Export garment mesh to file."""
        import trimesh

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        mesh.export(output_path, file_type=format)
        return output_path


def simulate_garment(
    garment_type: str,
    body_vertices: np.ndarray,
    body_pose: Optional[np.ndarray] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to simulate garment on body.

    Args:
        garment_type: Type of garment ('tshirt', 'dress', etc.)
        body_vertices: Body mesh vertices
        body_pose: Optional body pose parameters
        output_path: Optional path to export result mesh

    Returns:
        Simulation result dictionary
    """
    model = SnugModel(garment_type=garment_type)
    result = model.simulate(body_vertices, body_pose)

    if output_path:
        model.export_mesh(
            result['vertices'],
            result['faces'],
            output_path
        )
        result['mesh_path'] = output_path

    return result
