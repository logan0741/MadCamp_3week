"""
Garment Simulation Module

Uses SNUG for neural garment simulation.
"""

from .snug_wrapper import SnugModel, simulate_garment
from .garment_types import GarmentType, AVAILABLE_GARMENTS
from .texture_processor import GarmentTextureProcessor

__all__ = [
    "SnugModel",
    "simulate_garment",
    "GarmentType",
    "AVAILABLE_GARMENTS",
    "GarmentTextureProcessor",
]
