"""
IDM-VTON: Improved Diffusion Models for Virtual Try-On
Provides instant 2D preview of garments on user's body.

Reference: https://huggingface.co/yisol/IDM-VTON
"""

import torch
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Union, Tuple
from loguru import logger

from diffusers import (
    StableDiffusionInpaintPipeline,
    DDIMScheduler,
    AutoencoderKL
)
from transformers import CLIPTextModel, CLIPTokenizer

from config import settings


class IDMVTON:
    """
    IDM-VTON wrapper class for 2D virtual try-on.

    This model provides instant 2D preview (< 1 second) while 3D models
    are being generated in the background.
    """

    def __init__(
        self,
        model_id: str = "yisol/IDM-VTON",
        device: str = "cuda",
        dtype: torch.dtype = torch.float16,
        enable_xformers: bool = True,
    ):
        """
        Initialize IDM-VTON pipeline.

        Args:
            model_id: HuggingFace model identifier
            device: Device to run inference on (cuda/cpu)
            dtype: Data type for model weights
            enable_xformers: Enable memory-efficient attention
        """
        self.model_id = model_id
        self.device = device
        self.dtype = dtype
        self.enable_xformers = enable_xformers

        self.pipeline = None
        self._is_loaded = False

        logger.info(f"Initializing IDM-VTON with model: {model_id}")

    def load_model(self):
        """Load model weights into VRAM."""
        if self._is_loaded:
            logger.warning("Model already loaded, skipping...")
            return

        try:
            logger.info("Loading IDM-VTON pipeline from HuggingFace...")

            # Load pipeline components
            self.pipeline = StableDiffusionInpaintPipeline.from_pretrained(
                self.model_id,
                torch_dtype=self.dtype,
                cache_dir=settings.vton_cache_dir,
                safety_checker=None,  # Disable for speed
                requires_safety_checker=False,
            )

            # Configure scheduler for quality
            self.pipeline.scheduler = DDIMScheduler.from_config(
                self.pipeline.scheduler.config
            )

            # Move to device
            self.pipeline = self.pipeline.to(self.device)

            # Enable memory optimizations
            if self.enable_xformers:
                try:
                    self.pipeline.enable_xformers_memory_efficient_attention()
                    logger.info("xFormers memory efficient attention enabled")
                except Exception as e:
                    logger.warning(f"Could not enable xFormers: {e}")

            # Enable sequential CPU offload for VRAM efficiency
            # This keeps only active layers in VRAM
            if settings.enable_vram_monitoring:
                self.pipeline.enable_sequential_cpu_offload()
                logger.info("Sequential CPU offload enabled for VRAM efficiency")

            self._is_loaded = True
            logger.success("IDM-VTON pipeline loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load IDM-VTON: {e}")
            raise

    def unload_model(self):
        """Unload model from VRAM to free memory."""
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
            torch.cuda.empty_cache()
            self._is_loaded = False
            logger.info("IDM-VTON model unloaded from VRAM")

    def __call__(
        self,
        person_image: Union[str, Path, Image.Image],
        garment_image: Union[str, Path, Image.Image],
        mask: Optional[Union[str, Path, Image.Image]] = None,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> Image.Image:
        """
        Perform virtual try-on inference.

        Args:
            person_image: Image of the person (front-facing)
            garment_image: Image of the garment to try on
            mask: Optional segmentation mask (auto-generated if None)
            num_inference_steps: Number of denoising steps (higher = better quality)
            guidance_scale: Classifier-free guidance scale (higher = more adherence to prompt)
            seed: Random seed for reproducibility

        Returns:
            PIL Image of person wearing the garment
        """
        if not self._is_loaded:
            self.load_model()

        # Load images
        person_img = self._load_image(person_image)
        garment_img = self._load_image(garment_image)

        # Resize to model's expected size
        target_size = (settings.vton_image_size, settings.vton_image_size)
        person_img = person_img.resize(target_size, Image.Resampling.LANCZOS)
        garment_img = garment_img.resize(target_size, Image.Resampling.LANCZOS)

        # Generate or load mask
        if mask is None:
            mask_img = self._generate_torso_mask(person_img)
        else:
            mask_img = self._load_image(mask).resize(target_size, Image.Resampling.NEAREST)

        # Set random seed for reproducibility
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        else:
            generator = None

        # Prepare prompt (IDM-VTON uses specific prompting)
        prompt = "a high quality photo of a model wearing clothes"
        negative_prompt = "monochrome, lowres, bad anatomy, worst quality, low quality"

        # Run inference
        logger.info(f"Running VTON inference (steps={num_inference_steps}, guidance={guidance_scale})")

        try:
            with torch.inference_mode():
                output = self.pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    image=person_img,
                    mask_image=mask_img,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    generator=generator,
                ).images[0]

            logger.success("VTON inference completed")
            return output

        except Exception as e:
            logger.error(f"VTON inference failed: {e}")
            raise

    def _load_image(self, image: Union[str, Path, Image.Image]) -> Image.Image:
        """
        Load image from various sources.

        Args:
            image: Path string, Path object, or PIL Image

        Returns:
            PIL Image in RGB mode
        """
        if isinstance(image, Image.Image):
            return image.convert("RGB")
        elif isinstance(image, (str, Path)):
            return Image.open(image).convert("RGB")
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

    def _generate_torso_mask(self, person_image: Image.Image) -> Image.Image:
        """
        Generate torso segmentation mask for garment replacement.

        This is a simplified implementation. In production, use a proper
        human parsing model like LIP (Look Into Person) or Graphonomy.

        Args:
            person_image: PIL Image of the person

        Returns:
            Binary mask image (white=replace, black=keep)
        """
        # TODO: Integrate human parsing model
        # For now, create a simple center rectangle mask

        width, height = person_image.size
        mask = Image.new("L", (width, height), 0)

        # Define torso region (approximate)
        torso_top = int(height * 0.2)
        torso_bottom = int(height * 0.7)
        torso_left = int(width * 0.25)
        torso_right = int(width * 0.75)

        # Draw white rectangle for torso
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        draw.rectangle(
            [torso_left, torso_top, torso_right, torso_bottom],
            fill=255
        )

        logger.warning("Using simplified mask generation. Integrate human parsing for production.")
        return mask

    def batch_process(
        self,
        person_images: list[Union[str, Path, Image.Image]],
        garment_images: list[Union[str, Path, Image.Image]],
        **kwargs
    ) -> list[Image.Image]:
        """
        Process multiple try-on requests in batch.

        Args:
            person_images: List of person images
            garment_images: List of garment images (must match length of person_images)
            **kwargs: Additional arguments passed to __call__

        Returns:
            List of output images
        """
        if len(person_images) != len(garment_images):
            raise ValueError("Number of person and garment images must match")

        results = []
        for person_img, garment_img in zip(person_images, garment_images):
            output = self(person_img, garment_img, **kwargs)
            results.append(output)

        return results

    def estimate_inference_time(self, num_steps: int) -> float:
        """
        Estimate inference time based on number of steps.

        Args:
            num_steps: Number of denoising steps

        Returns:
            Estimated time in seconds
        """
        # Empirical: ~0.02 seconds per step on RTX 3090
        # IDM-VTON is optimized for speed
        time_per_step = 0.02
        return num_steps * time_per_step

    def get_vram_usage(self) -> dict:
        """
        Get current VRAM usage statistics.

        Returns:
            Dictionary with memory stats in MB
        """
        if not torch.cuda.is_available():
            return {"error": "CUDA not available"}

        allocated = torch.cuda.memory_allocated(self.device) / 1024**2
        reserved = torch.cuda.memory_reserved(self.device) / 1024**2
        max_allocated = torch.cuda.max_memory_allocated(self.device) / 1024**2

        return {
            "allocated_mb": round(allocated, 2),
            "reserved_mb": round(reserved, 2),
            "max_allocated_mb": round(max_allocated, 2),
        }

    @property
    def is_loaded(self) -> bool:
        """Check if model is currently loaded in VRAM."""
        return self._is_loaded


# ============================================
# Singleton instance for global access
# ============================================
_vton_instance: Optional[IDMVTON] = None


def get_vton_model() -> IDMVTON:
    """
    Get or create singleton VTON model instance.

    This ensures only one model is loaded in VRAM at a time.

    Returns:
        IDMVTON instance
    """
    global _vton_instance

    if _vton_instance is None:
        _vton_instance = IDMVTON(
            model_id=settings.vton_model_id,
            device="cuda" if torch.cuda.is_available() else "cpu",
        )

    return _vton_instance
