"""
Rigging Module for MemeForty Phase 2 Step 3.
"""

from .skeleton import (
    Bone,
    Skeleton,
    SMPLX_BONE_HIERARCHY,
    create_smplx_skeleton,
    fit_skeleton_to_mesh,
)
from .auto_rigger import (
    AutoRigger,
    RiggingPipeline,
)

__all__ = [
    "Bone",
    "Skeleton",
    "SMPLX_BONE_HIERARCHY",
    "create_smplx_skeleton",
    "fit_skeleton_to_mesh",
    "AutoRigger",
    "RiggingPipeline",
]
