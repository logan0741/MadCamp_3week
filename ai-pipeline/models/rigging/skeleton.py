"""
Skeleton Module for MemeForty Phase 2 Step 3.

Defines standard skeleton structure for rigging.
Unity-compatible bone naming and hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger


@dataclass
class Bone:
    """Single bone definition."""
    name: str
    parent: Optional[str] = None
    head: np.ndarray = field(default_factory=lambda: np.zeros(3))
    tail: np.ndarray = field(default_factory=lambda: np.zeros(3))
    roll: float = 0.0
    
    @property
    def length(self) -> float:
        return np.linalg.norm(self.tail - self.head)
    
    @property
    def direction(self) -> np.ndarray:
        vec = self.tail - self.head
        length = np.linalg.norm(vec)
        return vec / length if length > 1e-8 else np.array([0, 1, 0])


@dataclass
class Skeleton:
    """Complete skeleton definition."""
    bones: Dict[str, Bone] = field(default_factory=dict)
    root_bone: str = "Hips"
    
    def add_bone(self, bone: Bone) -> None:
        self.bones[bone.name] = bone
    
    def get_bone(self, name: str) -> Optional[Bone]:
        return self.bones.get(name)
    
    def get_children(self, bone_name: str) -> List[str]:
        return [
            name for name, bone in self.bones.items()
            if bone.parent == bone_name
        ]
    
    def get_bone_chain(self, end_bone: str) -> List[str]:
        """Get bone chain from root to end_bone."""
        chain = []
        current = end_bone
        while current is not None:
            chain.append(current)
            bone = self.bones.get(current)
            current = bone.parent if bone else None
        return list(reversed(chain))
    
    @property
    def bone_count(self) -> int:
        return len(self.bones)


# Standard SMPL-X compatible skeleton for Unity
SMPLX_BONE_HIERARCHY = {
    # Root
    "Hips": None,
    
    # Spine
    "Spine": "Hips",
    "Spine1": "Spine",
    "Spine2": "Spine1",
    "Neck": "Spine2",
    "Head": "Neck",
    
    # Left Arm
    "LeftShoulder": "Spine2",
    "LeftArm": "LeftShoulder",
    "LeftForeArm": "LeftArm",
    "LeftHand": "LeftForeArm",
    
    # Right Arm
    "RightShoulder": "Spine2",
    "RightArm": "RightShoulder",
    "RightForeArm": "RightArm",
    "RightHand": "RightForeArm",
    
    # Left Leg
    "LeftUpLeg": "Hips",
    "LeftLeg": "LeftUpLeg",
    "LeftFoot": "LeftLeg",
    "LeftToeBase": "LeftFoot",
    
    # Right Leg
    "RightUpLeg": "Hips",
    "RightLeg": "RightUpLeg",
    "RightFoot": "RightLeg",
    "RightToeBase": "RightFoot",
}


# Default bone positions (T-pose, height=1.7m)
SMPLX_BONE_POSITIONS = {
    "Hips": ([0, 0.95, 0], [0, 1.0, 0]),
    "Spine": ([0, 1.0, 0], [0, 1.1, 0]),
    "Spine1": ([0, 1.1, 0], [0, 1.2, 0]),
    "Spine2": ([0, 1.2, 0], [0, 1.35, 0]),
    "Neck": ([0, 1.35, 0], [0, 1.45, 0]),
    "Head": ([0, 1.45, 0], [0, 1.7, 0]),
    
    "LeftShoulder": ([0, 1.35, 0], [0.1, 1.35, 0]),
    "LeftArm": ([0.1, 1.35, 0], [0.35, 1.35, 0]),
    "LeftForeArm": ([0.35, 1.35, 0], [0.6, 1.35, 0]),
    "LeftHand": ([0.6, 1.35, 0], [0.75, 1.35, 0]),
    
    "RightShoulder": ([0, 1.35, 0], [-0.1, 1.35, 0]),
    "RightArm": ([-0.1, 1.35, 0], [-0.35, 1.35, 0]),
    "RightForeArm": ([-0.35, 1.35, 0], [-0.6, 1.35, 0]),
    "RightHand": ([-0.6, 1.35, 0], [-0.75, 1.35, 0]),
    
    "LeftUpLeg": ([0.1, 0.95, 0], [0.1, 0.5, 0]),
    "LeftLeg": ([0.1, 0.5, 0], [0.1, 0.1, 0]),
    "LeftFoot": ([0.1, 0.1, 0], [0.1, 0.05, 0.1]),
    "LeftToeBase": ([0.1, 0.05, 0.1], [0.1, 0.02, 0.2]),
    
    "RightUpLeg": ([-0.1, 0.95, 0], [-0.1, 0.5, 0]),
    "RightLeg": ([-0.1, 0.5, 0], [-0.1, 0.1, 0]),
    "RightFoot": ([-0.1, 0.1, 0], [-0.1, 0.05, 0.1]),
    "RightToeBase": ([-0.1, 0.05, 0.1], [-0.1, 0.02, 0.2]),
}


def create_smplx_skeleton(height_scale: float = 1.0) -> Skeleton:
    """
    Create standard SMPL-X compatible skeleton.
    
    Args:
        height_scale: Scale factor for height (1.0 = 1.7m person)
        
    Returns:
        Skeleton with all bones
    """
    skeleton = Skeleton()
    
    for bone_name, parent in SMPLX_BONE_HIERARCHY.items():
        if bone_name in SMPLX_BONE_POSITIONS:
            head, tail = SMPLX_BONE_POSITIONS[bone_name]
            bone = Bone(
                name=bone_name,
                parent=parent,
                head=np.array(head) * height_scale,
                tail=np.array(tail) * height_scale,
            )
        else:
            bone = Bone(name=bone_name, parent=parent)
        
        skeleton.add_bone(bone)
    
    logger.info(f"Created skeleton: {skeleton.bone_count} bones")
    return skeleton


def fit_skeleton_to_mesh(
    skeleton: Skeleton,
    mesh_vertices: np.ndarray,
) -> Skeleton:
    """
    Fit skeleton to mesh bounding box.
    
    Args:
        skeleton: Input skeleton
        mesh_vertices: (N, 3) mesh vertices
        
    Returns:
        Fitted skeleton
    """
    # Get mesh bounds
    min_bounds = mesh_vertices.min(axis=0)
    max_bounds = mesh_vertices.max(axis=0)
    mesh_height = max_bounds[1] - min_bounds[1]
    mesh_center = (min_bounds + max_bounds) / 2
    
    # Default skeleton height is 1.7m
    scale = mesh_height / 1.7
    
    # Create scaled skeleton
    fitted = Skeleton()
    
    for name, bone in skeleton.bones.items():
        new_bone = Bone(
            name=bone.name,
            parent=bone.parent,
            head=bone.head * scale + np.array([mesh_center[0], min_bounds[1], mesh_center[2]]),
            tail=bone.tail * scale + np.array([mesh_center[0], min_bounds[1], mesh_center[2]]),
            roll=bone.roll,
        )
        fitted.add_bone(new_bone)
    
    logger.info(f"Skeleton fitted: scale={scale:.3f}")
    return fitted
