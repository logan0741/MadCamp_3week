"""
Garment size scaling utilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import trimesh
from loguru import logger


class GarmentSizeScaler:
    """
    Scale template garment meshes based on measurement data.
    """

    REFERENCE_SIZES: Dict[str, Dict[str, float]] = {
        "top": {"length": 70, "shoulder": 45, "chest": 100, "sleeve": 60},
        "pants": {"length": 100, "waist": 80, "hip": 100, "inseam": 75},
        "dress": {"length": 90, "shoulder": 40, "bust": 88, "waist": 70},
        "skirt": {"length": 45, "waist": 70, "hip": 95},
    }

    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = template_dir or (Path(__file__).parent.parent / "templates")

    def load_template_mesh(self, garment_type: str) -> trimesh.Trimesh:
        """
        Load template mesh for garment type.
        """
        template_path = self.template_dir / f"{garment_type}.obj"
        if template_path.exists():
            mesh = trimesh.load_mesh(template_path, process=False)
            return self._ensure_trimesh(mesh)

        fallback = self._fallback_mesh_path(garment_type)
        if fallback and fallback.exists():
            logger.warning(f"Template not found, using fallback mesh: {fallback}")
            mesh = trimesh.load_mesh(fallback, process=False)
            return self._ensure_trimesh(mesh)

        logger.warning(f"Template not found for {garment_type}, using primitive box")
        mesh = trimesh.creation.box(extents=(0.5, 0.8, 0.3))
        return self._ensure_trimesh(mesh)

    def scale_mesh(
        self,
        template_mesh: trimesh.Trimesh,
        garment_type: str,
        target_cm: Dict[str, float],
    ) -> trimesh.Trimesh:
        """
        Apply non-uniform scaling based on size measurements.
        """
        if garment_type not in self.REFERENCE_SIZES:
            raise ValueError(f"Unknown garment_type: {garment_type}")

        ref = self.REFERENCE_SIZES[garment_type]
        scales = {k: target_cm.get(k, ref[k]) / ref[k] for k in ref}

        vertices = template_mesh.vertices.copy()
        center = template_mesh.centroid
        vertices = vertices - center

        if garment_type in {"top", "dress"}:
            vertices[:, 1] *= scales.get("length", 1.0)
            vertices[:, 0] *= scales.get("shoulder", 1.0)
            vertices[:, 2] *= scales.get("chest", scales.get("bust", 1.0))
        elif garment_type in {"pants", "skirt"}:
            vertices[:, 1] *= scales.get("length", 1.0)
            vertices[:, 0] *= scales.get("waist", 1.0)
            vertices[:, 2] *= scales.get("hip", 1.0)
        else:
            vertices[:, :] *= 1.0

        vertices = vertices + center

        scaled = template_mesh.copy()
        scaled.vertices = vertices
        return scaled

    def _fallback_mesh_path(self, garment_type: str) -> Path | None:
        snug_dir = Path(__file__).parent.parent / "3d" / "snug" / "assets" / "meshes"
        mapping = {
            "top": snug_dir / "tshirt.obj",
            "dress": snug_dir / "long_sleeve_top.obj",
            "pants": snug_dir / "pants.obj",
            "skirt": snug_dir / "shorts.obj",
        }
        return mapping.get(garment_type)

    def _ensure_trimesh(self, mesh: trimesh.Trimesh | trimesh.Scene) -> trimesh.Trimesh:
        if isinstance(mesh, trimesh.Scene):
            if not mesh.geometry:
                raise ValueError("Empty mesh scene")
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        return mesh
