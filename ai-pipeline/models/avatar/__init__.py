"""
3D Avatar Generation Module

Uses SHAPY for body shape estimation from images
and SMPL-X for parametric body model.
"""

from .shapy_wrapper import ShapyModel, estimate_body_shape
from .smplx_wrapper import SMPLXModel, create_body_mesh

__all__ = [
    "ShapyModel",
    "estimate_body_shape",
    "SMPLXModel",
    "create_body_mesh",
]
