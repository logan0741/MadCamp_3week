"""
Garment texture processing using front/back images.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
from PIL import Image
from loguru import logger

from models.segmentation import FashnSegmenter


class GarmentTextureProcessor:
    """
    Build UV-ready textures from front/back garment images.
    """

    def __init__(self, atlas_size: Tuple[int, int] = (2048, 1024)) -> None:
        self.atlas_size = atlas_size
        self.panel_size = (atlas_size[0] // 2, atlas_size[1])
        try:
            self.segmenter = FashnSegmenter.get_instance()
        except Exception as e:
            logger.warning(f"FashnHumanParser unavailable, using fallback masks: {e}")
            self.segmenter = None

    def process(
        self,
        front_image: Image.Image,
        back_image: Image.Image,
        garment_type: str,
    ) -> Dict[str, Image.Image]:
        """
        Process front/back images and return textures.
        """
        front_garment = self._safe_extract(front_image, garment_type, side="front")
        back_garment = self._safe_extract(back_image, garment_type, side="back")

        uv_atlas = self._create_uv_atlas(front_garment, back_garment)

        return {
            "front_texture": front_garment,
            "back_texture": back_garment,
            "uv_atlas": uv_atlas,
        }

    def _safe_extract(self, image: Image.Image, garment_type: str, side: str) -> Image.Image:
        if self.segmenter is None:
            return self._fallback_rgba(image)
        try:
            return self.segmenter.extract_garment(image, garment_type)
        except Exception as e:
            logger.warning(f"Segmentation failed for {side} image: {e}")
            return self._fallback_rgba(image)

    def _fallback_rgba(self, image: Image.Image) -> Image.Image:
        """
        Fallback: convert to RGBA and remove white background.
        """
        rgb = image.convert("RGB")
        img_array = np.array(rgb)
        white_mask = np.all(img_array > 240, axis=2)
        alpha = np.where(white_mask, 0, 255).astype(np.uint8)

        rgba = Image.fromarray(img_array, mode="RGB").convert("RGBA")
        rgba.putalpha(Image.fromarray(alpha, mode="L"))
        return rgba

    def _create_uv_atlas(self, front: Image.Image, back: Image.Image) -> Image.Image:
        """
        Combine front and back into a single UV atlas.
        """
        atlas = Image.new("RGBA", self.atlas_size, (0, 0, 0, 0))

        front_resized = self._fit_square(front, self.panel_size)
        back_resized = self._fit_square(back, self.panel_size)

        atlas.paste(front_resized, (0, 0), front_resized)
        atlas.paste(back_resized, (self.panel_size[0], 0), back_resized)
        return atlas

    def _fit_square(self, image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """
        Resize image to fit target size with padding.
        """
        target_w, target_h = size
        img = image.convert("RGBA")
        img_w, img_h = img.size

        scale = min(target_w / img_w, target_h / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))

        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))

        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        canvas.paste(resized, (paste_x, paste_y), resized)
        return canvas
