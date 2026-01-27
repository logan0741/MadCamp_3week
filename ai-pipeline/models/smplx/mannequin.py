"""
Standard SMPL-X mannequin generator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import trimesh
from loguru import logger

from config import settings


class StandardMannequin:
    """
    Generate a neutral SMPL-X mannequin scaled by height and weight.
    """

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        gender: str = "neutral",
        device: str = "cuda",
    ) -> None:
        self.model_path = Path(model_path) if model_path else self._default_model_path()
        self.gender = gender
        self.device = self._resolve_device(device)
        self.model = None

    def _resolve_device(self, device: str) -> str:
        if device != "cuda":
            return device
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return device

    def _default_model_path(self) -> Path:
        if settings.smplx_model_path:
            path = Path(settings.smplx_model_path)
            return path if path.is_dir() else path.parent
        return settings.model_weights_dir / "smplx"

    def _load_model(self) -> None:
        if self.model is not None:
            return
        try:
            import smplx
            import torch

            self.model = smplx.create(
                model_path=str(self.model_path),
                model_type="smplx",
                gender=self.gender,
                num_betas=10,
            ).to(self.device)

            logger.info(f"SMPL-X model loaded from {self.model_path}")
        except Exception as exc:
            raise RuntimeError(f"Failed to load SMPL-X model: {exc}") from exc

    def _height_weight_to_betas(self, height_cm: float, weight_kg: float) -> np.ndarray:
        """
        Simple heuristic mapping to SMPL-X betas.
        """
        betas = np.zeros((1, 10), dtype=np.float32)
        height_delta = (height_cm - 170.0) / 10.0
        weight_delta = (weight_kg - 65.0) / 10.0

        betas[0, 0] = np.clip(height_delta * 0.1, -2.0, 2.0)
        betas[0, 1] = np.clip(weight_delta * 0.1, -2.0, 2.0)
        return betas

    def _fallback_mesh(self, height_cm: float) -> trimesh.Trimesh:
        """
        Fallback mannequin when SMPL-X weights are unavailable.
        """
        height_m = max(height_cm / 100.0, 1.0)
        radius = max(height_m * 0.12, 0.15)
        mesh = trimesh.creation.capsule(radius=radius, height=height_m * 0.8)
        # Align capsule to Y axis
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        return mesh

    def get_mesh(self, height_cm: float = 170, weight_kg: float = 65) -> trimesh.Trimesh:
        """
        Create a SMPL-X mesh scaled to the target height.
        """
        try:
            self._load_model()
        except Exception as exc:
            logger.warning(f"SMPL-X unavailable, using fallback mannequin: {exc}")
            return self._fallback_mesh(height_cm)

        import torch

        betas = self._height_weight_to_betas(height_cm, weight_kg)
        body_pose = torch.zeros([1, 63], dtype=torch.float32, device=self.device)

        with torch.no_grad():
            output = self.model(
                betas=torch.tensor(betas, device=self.device),
                body_pose=body_pose,
                return_verts=True,
            )

        vertices = output.vertices[0].detach().cpu().numpy()
        scale = height_cm / 170.0
        vertices = vertices * scale

        return trimesh.Trimesh(vertices=vertices, faces=self.model.faces, process=False)


# Global singleton instance
_mannequin_instance: StandardMannequin | None = None


def generate_mannequin(
    height_cm: float = 170,
    weight_kg: float = 65,
    gender: str = "neutral",
) -> trimesh.Trimesh:
    """
    Convenience function to generate a mannequin mesh.

    Args:
        height_cm: Target height in centimeters
        weight_kg: Target weight in kilograms
        gender: Body gender (neutral, male, female)

    Returns:
        trimesh.Trimesh of the mannequin body
    """
    global _mannequin_instance
    if _mannequin_instance is None or _mannequin_instance.gender != gender:
        _mannequin_instance = StandardMannequin(gender=gender)
    return _mannequin_instance.get_mesh(height_cm, weight_kg)
