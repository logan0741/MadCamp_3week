"""
SMPL-X Body Model Wrapper

Provides interface for creating 3D body meshes from parameters.
"""

import os
import numpy as np
from typing import Dict, Optional, Tuple, Any
from pathlib import Path

# Model paths
SMPLX_MODEL_DIR = os.environ.get(
    "SMPLX_MODEL_DIR",
    str(Path(__file__).parent.parent / "3d" / "shapy" / "data" / "body_models" / "smplx")
)

class SMPLXModel:
    """SMPL-X parametric body model wrapper."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        gender: str = "neutral",
        num_betas: int = 10,
        use_pca: bool = True,
        num_pca_comps: int = 12,
        device: str = "cuda"
    ):
        """
        Initialize SMPL-X model.

        Args:
            model_path: Path to SMPL-X model files
            gender: 'male', 'female', or 'neutral'
            num_betas: Number of body shape parameters
            use_pca: Whether to use PCA for hand pose
            num_pca_comps: Number of PCA components for hands
            device: 'cuda' or 'cpu'
        """
        self.model_path = model_path or SMPLX_MODEL_DIR
        self.gender = gender
        self.num_betas = num_betas
        self.use_pca = use_pca
        self.num_pca_comps = num_pca_comps
        self.device = device
        self._model = None

    def _load_model(self):
        """Lazy load SMPL-X model."""
        if self._model is not None:
            return

        try:
            import smplx
            import torch

            self._model = smplx.create(
                model_path=self.model_path,
                model_type='smplx',
                gender=self.gender,
                num_betas=self.num_betas,
                use_pca=self.use_pca,
                num_pca_comps=self.num_pca_comps,
            ).to(self.device)

        except ImportError:
            raise RuntimeError("smplx package not installed. Run: pip install smplx")
        except Exception as e:
            raise RuntimeError(f"Failed to load SMPL-X model: {e}")

    def forward(
        self,
        betas: Optional[np.ndarray] = None,
        body_pose: Optional[np.ndarray] = None,
        global_orient: Optional[np.ndarray] = None,
        transl: Optional[np.ndarray] = None,
        expression: Optional[np.ndarray] = None,
        jaw_pose: Optional[np.ndarray] = None,
        left_hand_pose: Optional[np.ndarray] = None,
        right_hand_pose: Optional[np.ndarray] = None,
        return_verts: bool = True,
    ) -> Dict[str, Any]:
        """
        Run SMPL-X forward pass.

        Args:
            betas: Body shape parameters (batch_size, num_betas)
            body_pose: Body pose parameters (batch_size, 63)
            global_orient: Global orientation (batch_size, 3)
            transl: Translation (batch_size, 3)
            expression: Face expression (batch_size, 10)
            jaw_pose: Jaw pose (batch_size, 3)
            left_hand_pose: Left hand pose
            right_hand_pose: Right hand pose
            return_verts: Whether to return vertices

        Returns:
            Dictionary with vertices, joints, faces, etc.
        """
        import torch

        self._load_model()

        # Convert numpy to torch tensors
        def to_tensor(x, default_shape):
            if x is None:
                x = np.zeros(default_shape)
            return torch.tensor(x, dtype=torch.float32, device=self.device)

        batch_size = 1
        if betas is not None:
            batch_size = betas.shape[0] if len(betas.shape) > 1 else 1

        params = {
            'betas': to_tensor(betas, (batch_size, self.num_betas)),
            'body_pose': to_tensor(body_pose, (batch_size, 63)),
            'global_orient': to_tensor(global_orient, (batch_size, 3)),
            'transl': to_tensor(transl, (batch_size, 3)),
            'return_verts': return_verts,
        }

        if expression is not None:
            params['expression'] = to_tensor(expression, (batch_size, 10))
        if jaw_pose is not None:
            params['jaw_pose'] = to_tensor(jaw_pose, (batch_size, 3))
        if left_hand_pose is not None:
            params['left_hand_pose'] = to_tensor(left_hand_pose, (batch_size, self.num_pca_comps))
        if right_hand_pose is not None:
            params['right_hand_pose'] = to_tensor(right_hand_pose, (batch_size, self.num_pca_comps))

        with torch.no_grad():
            output = self._model(**params)

        result = {
            'vertices': output.vertices.cpu().numpy(),
            'joints': output.joints.cpu().numpy(),
            'faces': self._model.faces,
        }

        if hasattr(output, 'full_pose'):
            result['full_pose'] = output.full_pose.cpu().numpy()

        return result

    def get_mesh(
        self,
        betas: np.ndarray,
        pose: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get mesh vertices and faces from shape parameters.

        Args:
            betas: Shape parameters
            pose: Optional body pose

        Returns:
            Tuple of (vertices, faces)
        """
        result = self.forward(betas=betas, body_pose=pose)
        return result['vertices'], result['faces']

    def export_mesh(
        self,
        betas: np.ndarray,
        output_path: str,
        pose: Optional[np.ndarray] = None,
        format: str = "obj"
    ) -> str:
        """
        Export mesh to file.

        Args:
            betas: Shape parameters
            output_path: Path to save mesh
            pose: Optional body pose
            format: Export format ('obj', 'ply', 'glb')

        Returns:
            Path to saved file
        """
        import trimesh

        vertices, faces = self.get_mesh(betas, pose)

        # Handle batch dimension
        if len(vertices.shape) == 3:
            vertices = vertices[0]

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

        if format == "obj":
            mesh.export(output_path, file_type='obj')
        elif format == "ply":
            mesh.export(output_path, file_type='ply')
        elif format == "glb":
            mesh.export(output_path, file_type='glb')
        else:
            raise ValueError(f"Unsupported format: {format}")

        return output_path


def create_body_mesh(
    betas: np.ndarray,
    gender: str = "neutral",
    pose: Optional[np.ndarray] = None,
    output_path: Optional[str] = None,
    device: str = "cuda"
) -> Dict[str, Any]:
    """
    Convenience function to create body mesh from parameters.

    Args:
        betas: Body shape parameters
        gender: 'male', 'female', or 'neutral'
        pose: Optional body pose parameters
        output_path: If provided, export mesh to this path
        device: 'cuda' or 'cpu'

    Returns:
        Dictionary with vertices, faces, and optional file path
    """
    model = SMPLXModel(gender=gender, device=device)
    vertices, faces = model.get_mesh(betas, pose)

    result = {
        'vertices': vertices,
        'faces': faces,
    }

    if output_path:
        model.export_mesh(betas, output_path, pose)
        result['mesh_path'] = output_path

    return result
