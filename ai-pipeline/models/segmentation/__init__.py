"""
Segmentation models for garment and body parsing.
"""

from .fashn_parser import FashnSegmenter, apply_mask_with_alpha
from .dual_view_processor import (
    DualViewSegmentationPipeline,
    SegmentationResult,
    get_dual_view_pipeline,
)

__all__ = [
    "FashnSegmenter",
    "apply_mask_with_alpha",
    "DualViewSegmentationPipeline",
    "SegmentationResult",
    "get_dual_view_pipeline",
]
