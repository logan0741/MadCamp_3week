"""
Dual-view segmentation pipeline for front/back garment processing.

Implements VRAM-aware processing with checkpoint support.
"""

from __future__ import annotations

import gc
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

import numpy as np
from PIL import Image
from loguru import logger

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from .fashn_parser import FashnSegmenter, apply_mask_with_alpha


@dataclass
class SegmentationResult:
    """Result from dual-view segmentation."""
    front_mask: np.ndarray
    back_mask: np.ndarray
    front_rgba: Image.Image
    back_rgba: Image.Image
    garment_type: str
    timestamp: str
    vram_before_mb: float
    vram_after_mb: float


class DualViewSegmentationPipeline:
    """
    Process front and back garment images with VRAM management.

    Implements torch.cuda.empty_cache() between processing stages
    to prevent OOM errors on 20GB VRAM systems.
    """

    VRAM_BUDGET_MB = 4096  # 4GB allocated for segmentation

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, dict], None]] = None,
    ):
        self.output_dir = output_dir or Path("data/outputs/segmentation")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = progress_callback
        self._segmenter: Optional[FashnSegmenter] = None

    @property
    def segmenter(self) -> FashnSegmenter:
        """Lazy-load segmenter to control VRAM allocation timing."""
        if self._segmenter is None:
            self._log_progress("Loading FashnHumanParser model...")
            self._segmenter = FashnSegmenter.get_instance()
        return self._segmenter

    def _get_vram_mb(self) -> float:
        """Get current VRAM usage in MB."""
        if HAS_TORCH and torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 * 1024)
        return 0.0

    def _clear_vram(self) -> None:
        """Clear VRAM cache between processing stages."""
        if HAS_TORCH and torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
            logger.debug(f"VRAM cleared. Current usage: {self._get_vram_mb():.1f} MB")

    def _log_progress(self, message: str, data: Optional[dict] = None) -> None:
        """Log progress with optional callback."""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message, data or {})

    def process_dual_view(
        self,
        front_image: Image.Image,
        back_image: Image.Image,
        garment_type: str = "top",
        save_outputs: bool = True,
        output_prefix: str = "garment",
    ) -> SegmentationResult:
        """
        Process front and back images with VRAM-aware staging.

        Args:
            front_image: PIL Image of garment front view
            back_image: PIL Image of garment back view
            garment_type: Type of garment (top, dress, pants, skirt)
            save_outputs: Whether to save alpha-masked PNGs
            output_prefix: Prefix for output filenames

        Returns:
            SegmentationResult with masks and RGBA images
        """
        timestamp = datetime.now().isoformat()
        vram_before = self._get_vram_mb()

        self._log_progress(
            f"Starting dual-view segmentation for {garment_type}",
            {"vram_mb": vram_before, "garment_type": garment_type}
        )

        # Stage 1: Process front image
        self._log_progress("Processing front image...")
        front_masks = self.segmenter.segment(front_image)
        front_mask = front_masks.get(garment_type, front_masks.get("torso", np.zeros_like(list(front_masks.values())[0])))
        front_rgba = apply_mask_with_alpha(front_image, front_mask)

        # Clear VRAM between stages
        self._clear_vram()

        # Stage 2: Process back image
        self._log_progress("Processing back image...")
        back_masks = self.segmenter.segment(back_image)
        back_mask = back_masks.get(garment_type, back_masks.get("torso", np.zeros_like(list(back_masks.values())[0])))
        back_rgba = apply_mask_with_alpha(back_image, back_mask)

        # Clear VRAM after processing
        self._clear_vram()

        vram_after = self._get_vram_mb()

        # Save outputs if requested
        if save_outputs:
            front_path = self.output_dir / f"{output_prefix}_front.png"
            back_path = self.output_dir / f"{output_prefix}_back.png"
            front_mask_path = self.output_dir / f"{output_prefix}_front_mask.npy"
            back_mask_path = self.output_dir / f"{output_prefix}_back_mask.npy"

            front_rgba.save(front_path)
            back_rgba.save(back_path)
            np.save(front_mask_path, front_mask)
            np.save(back_mask_path, back_mask)

            self._log_progress(
                f"Saved outputs to {self.output_dir}",
                {
                    "front_png": str(front_path),
                    "back_png": str(back_path),
                    "front_mask": str(front_mask_path),
                    "back_mask": str(back_mask_path),
                }
            )

        result = SegmentationResult(
            front_mask=front_mask,
            back_mask=back_mask,
            front_rgba=front_rgba,
            back_rgba=back_rgba,
            garment_type=garment_type,
            timestamp=timestamp,
            vram_before_mb=vram_before,
            vram_after_mb=vram_after,
        )

        self._log_progress(
            f"Dual-view segmentation complete",
            {
                "garment_type": garment_type,
                "vram_before_mb": vram_before,
                "vram_after_mb": vram_after,
                "timestamp": timestamp,
            }
        )

        return result

    def process_from_urls(
        self,
        front_url: str,
        back_url: str,
        garment_type: str = "top",
        output_prefix: str = "garment",
    ) -> SegmentationResult:
        """
        Process images from URLs with automatic download.
        """
        import requests
        from io import BytesIO

        self._log_progress(f"Downloading front image from {front_url}")
        front_resp = requests.get(front_url, timeout=30)
        front_resp.raise_for_status()
        front_image = Image.open(BytesIO(front_resp.content))

        self._log_progress(f"Downloading back image from {back_url}")
        back_resp = requests.get(back_url, timeout=30)
        back_resp.raise_for_status()
        back_image = Image.open(BytesIO(back_resp.content))

        return self.process_dual_view(
            front_image=front_image,
            back_image=back_image,
            garment_type=garment_type,
            output_prefix=output_prefix,
        )


def get_dual_view_pipeline(
    output_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[[str, dict], None]] = None,
) -> DualViewSegmentationPipeline:
    """Factory function for creating pipeline instances."""
    return DualViewSegmentationPipeline(
        output_dir=output_dir,
        progress_callback=progress_callback,
    )
