"""
Garment Simulation Module

Uses SNUG for neural garment simulation.
"""

from .snug_wrapper import SnugModel, simulate_garment
from .garment_types import GarmentType, AVAILABLE_GARMENTS

__all__ = [
    "SnugModel",
    "simulate_garment",
    "GarmentType",
    "AVAILABLE_GARMENTS",
]
