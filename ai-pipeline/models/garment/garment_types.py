"""
Garment type definitions and configurations.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path

SNUG_DIR = Path(__file__).parent.parent / "3d" / "snug"
GARMENT_ASSETS_DIR = SNUG_DIR / "assets"


class GarmentType(Enum):
    """Available garment types in SNUG."""
    TSHIRT = "tshirt"
    TANK = "tank"
    DRESS = "dress"
    SKIRT = "skirt"
    PANTS = "pants"
    SHORTS = "shorts"


@dataclass
class GarmentConfig:
    """Configuration for a garment type."""
    name: str
    type: GarmentType
    mesh_path: Optional[str] = None
    material_stiffness: float = 1.0
    material_density: float = 0.3
    thickness: float = 0.001  # meters


# Available garments with their configurations
AVAILABLE_GARMENTS: Dict[str, GarmentConfig] = {
    "tshirt": GarmentConfig(
        name="T-Shirt",
        type=GarmentType.TSHIRT,
        mesh_path=str(GARMENT_ASSETS_DIR / "garments" / "tshirt.obj"),
        material_stiffness=1.0,
        material_density=0.3,
    ),
    "tank": GarmentConfig(
        name="Tank Top",
        type=GarmentType.TANK,
        mesh_path=str(GARMENT_ASSETS_DIR / "garments" / "tank.obj"),
        material_stiffness=0.8,
        material_density=0.25,
    ),
    "dress": GarmentConfig(
        name="Dress",
        type=GarmentType.DRESS,
        mesh_path=str(GARMENT_ASSETS_DIR / "garments" / "dress.obj"),
        material_stiffness=0.7,
        material_density=0.28,
    ),
    "skirt": GarmentConfig(
        name="Skirt",
        type=GarmentType.SKIRT,
        mesh_path=str(GARMENT_ASSETS_DIR / "garments" / "skirt.obj"),
        material_stiffness=0.6,
        material_density=0.25,
    ),
    "pants": GarmentConfig(
        name="Pants",
        type=GarmentType.PANTS,
        mesh_path=str(GARMENT_ASSETS_DIR / "garments" / "pants.obj"),
        material_stiffness=1.2,
        material_density=0.35,
    ),
    "shorts": GarmentConfig(
        name="Shorts",
        type=GarmentType.SHORTS,
        mesh_path=str(GARMENT_ASSETS_DIR / "garments" / "shorts.obj"),
        material_stiffness=1.1,
        material_density=0.32,
    ),
}


def get_garment_config(garment_type: str) -> GarmentConfig:
    """Get garment configuration by type name."""
    if garment_type not in AVAILABLE_GARMENTS:
        raise ValueError(
            f"Unknown garment type: {garment_type}. "
            f"Available: {list(AVAILABLE_GARMENTS.keys())}"
        )
    return AVAILABLE_GARMENTS[garment_type]


def list_available_garments() -> List[str]:
    """List all available garment types."""
    return list(AVAILABLE_GARMENTS.keys())
