"""
AI Models Package
Contains implementations for ECON, BCNet, IDM-VTON, 3DGS, SHAPY, and SNUG.
"""

from .vton import IDMVTON

# Lazy imports for 3D models (they have heavy dependencies)
def get_shapy_model():
    """Get SHAPY model for body shape estimation."""
    from .avatar import ShapyModel
    return ShapyModel

def get_smplx_model():
    """Get SMPL-X model for body mesh generation."""
    from .avatar import SMPLXModel
    return SMPLXModel

def get_snug_model():
    """Get SNUG model for garment simulation."""
    from .garment import SnugModel
    return SnugModel

__all__ = [
    "IDMVTON",
    "get_shapy_model",
    "get_smplx_model",
    "get_snug_model",
]
