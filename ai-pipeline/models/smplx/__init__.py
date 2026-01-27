"""
SMPL-X mannequin and wrapping utilities.
"""

from .mannequin import StandardMannequin, generate_mannequin
from .smplx_wrapper import (
    SMPLXWrapper,
    ShrinkWrapAlgorithm,
    wrap_mesh_to_smplx,
    flush_vram,
)

__all__ = [
    "StandardMannequin",
    "generate_mannequin",
    "SMPLXWrapper",
    "ShrinkWrapAlgorithm",
    "wrap_mesh_to_smplx",
    "flush_vram",
]
