"""
Fashn Human Parser wrapper for clothing segmentation.
"""

from __future__ import annotations

from typing import Dict

import numpy as np
from PIL import Image
from loguru import logger


class FashnSegmenter:
    """
    Singleton wrapper around FashnHumanParser.

    Provides category masks for clothing items.
    """

    _instance: "FashnSegmenter" | None = None

    @classmethod
    def get_instance(cls) -> "FashnSegmenter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        try:
            from fashn_human_parser import FashnHumanParser, LABELS_TO_IDS
        except Exception as exc:
            raise RuntimeError(
                "fashn-human-parser is required. Install with: pip install fashn-human-parser"
            ) from exc

        self.parser = FashnHumanParser()
        self.labels = LABELS_TO_IDS
        logger.info("FashnHumanParser initialized")

    def _predict(self, image: Image.Image) -> np.ndarray:
        try:
            return self.parser.predict(image)
        except Exception:
            return self.parser.predict(np.array(image))

    def segment(self, image: Image.Image) -> Dict[str, np.ndarray]:
        """
        Segment image and return category masks.

        Returns dict with keys: top, dress, pants, skirt, torso.
        """
        if not isinstance(image, Image.Image):
            raise TypeError("image must be a PIL.Image")

        rgb = image.convert("RGB")
        seg = self._predict(rgb)
        seg = np.asarray(seg)
        if seg.ndim == 3:
            seg = np.squeeze(seg)

        return {
            "top": seg == self.labels.get("top"),
            "dress": seg == self.labels.get("dress"),
            "pants": seg == self.labels.get("pants"),
            "skirt": seg == self.labels.get("skirt"),
            "torso": seg == self.labels.get("torso"),
        }

    def extract_garment(self, image: Image.Image, garment_type: str) -> Image.Image:
        """
        Extract garment pixels with transparent background.
        """
        masks = self.segment(image)
        if garment_type not in masks:
            raise ValueError(f"Unknown garment_type: {garment_type}")

        mask = masks[garment_type]
        return apply_mask_with_alpha(image, mask)


def apply_mask_with_alpha(image: Image.Image, mask: np.ndarray) -> Image.Image:
    """
    Apply a binary mask and return RGBA image with transparent background.
    """
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a PIL.Image")

    rgba = image.convert("RGBA")
    if mask.dtype != np.uint8:
        alpha = (mask.astype(np.uint8) * 255)
    else:
        alpha = mask
        if alpha.max() <= 1:
            alpha = alpha * 255

    alpha_img = Image.fromarray(alpha, mode="L")
    rgba.putalpha(alpha_img)
    return rgba
