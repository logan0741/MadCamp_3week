"""
Export dressed mannequin to GLB for Unity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
import trimesh
from PIL import Image
from loguru import logger


def export_dressed_mannequin(
    mannequin_mesh: trimesh.Trimesh,
    garment_mesh: trimesh.Trimesh,
    garment_texture: Image.Image,
    output_path: Union[str, Path],
) -> str:
    """
    Export mannequin + garment as GLB for Unity.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scene = trimesh.Scene()

    _apply_mannequin_material(mannequin_mesh)
    scene.add_geometry(mannequin_mesh, node_name="mannequin")

    textured_garment = _apply_texture(garment_mesh, garment_texture)
    scene.add_geometry(textured_garment, node_name="garment")

    scene.export(str(output_path), file_type="glb")
    logger.info(f"Exported GLB to {output_path}")

    return str(output_path)


def _apply_mannequin_material(mesh: trimesh.Trimesh) -> None:
    """
    Apply a neutral gray material to mannequin.
    """
    color = np.array([200, 200, 200, 255], dtype=np.uint8)
    if mesh.visual is None or not hasattr(mesh.visual, "vertex_colors"):
        mesh.visual = trimesh.visual.ColorVisuals(
            mesh, vertex_colors=np.tile(color, (len(mesh.vertices), 1))
        )
    else:
        mesh.visual.vertex_colors = np.tile(color, (len(mesh.vertices), 1))


def _apply_texture(mesh: trimesh.Trimesh, texture: Image.Image) -> trimesh.Trimesh:
    """
    Attach a texture image to the mesh, ensuring UVs exist.
    """
    uv = None
    if mesh.visual is not None and hasattr(mesh.visual, "uv"):
        uv = mesh.visual.uv

    if uv is None or len(uv) == 0:
        uv = _generate_planar_uv(mesh)

    mesh.visual = trimesh.visual.TextureVisuals(uv=uv, image=texture)
    return mesh


def _generate_planar_uv(mesh: trimesh.Trimesh) -> np.ndarray:
    """
    Generate simple planar UVs based on X/Z bounds.
    """
    vertices = mesh.vertices
    min_x, min_z = np.min(vertices[:, [0, 2]], axis=0)
    max_x, max_z = np.max(vertices[:, [0, 2]], axis=0)

    span_x = max(max_x - min_x, 1e-6)
    span_z = max(max_z - min_z, 1e-6)

    u = (vertices[:, 0] - min_x) / span_x
    v = (vertices[:, 2] - min_z) / span_z

    return np.column_stack((u, v))
