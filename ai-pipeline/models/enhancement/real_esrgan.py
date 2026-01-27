"""
Real-ESRGAN Image Enhancement Module for MemeForty Phase 1.

Step 1: Image Enhancement (Base Layer)
- Real-ESRGAN v1.4 for upscaling
- Rembg for background removal
- Minimum 1024px on shortest side
"""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
import torch
from PIL import Image
from loguru import logger


def flush_vram():
    """Flush VRAM cache to prevent OOM."""
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()


class RealESRGANEnhancer:
    """
    Real-ESRGAN v1.4 wrapper for image upscaling and enhancement.
    
    Provides textural restoration focused upscaling with VRAM management.
    Expected VRAM: ~4GB
    """
    
    _instance: Optional["RealESRGANEnhancer"] = None
    
    @classmethod
    def get_instance(cls) -> "RealESRGANEnhancer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(
        self,
        model_name: str = "RealESRGAN_x4plus",
        device: str = "cuda",
        half_precision: bool = True,
        min_size: int = 1024,
    ):
        """
        Initialize Real-ESRGAN enhancer.
        
        Args:
            model_name: Model variant to use
            device: Device for inference (cuda/cpu)
            half_precision: Use FP16 for reduced VRAM
            min_size: Minimum size for shortest side
        """
        self.model_name = model_name
        self.device = device
        self.half_precision = half_precision
        self.min_size = min_size
        self.upsampler = None
        self._loaded = False
        
        logger.info(f"RealESRGANEnhancer initialized (model={model_name}, min_size={min_size})")
    
    def load_model(self) -> None:
        """Load Real-ESRGAN model into VRAM."""
        if self._loaded:
            return
            
        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
        except ImportError as e:
            raise RuntimeError(
                "Real-ESRGAN dependencies required. Install with:\n"
                "pip install realesrgan basicsr"
            ) from e
        
        # RealESRGAN_x4plus model architecture
        model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=4,
        )
        
        self.upsampler = RealESRGANer(
            scale=4,
            model_path=None,  # Will download automatically
            dni_weight=None,
            model=model,
            tile=0,  # No tiling for small images
            tile_pad=10,
            pre_pad=0,
            half=self.half_precision,
            device=self.device,
        )
        
        self._loaded = True
        logger.info("Real-ESRGAN model loaded")
    
    def unload_model(self) -> None:
        """Unload model from VRAM."""
        if self.upsampler is not None:
            del self.upsampler
            self.upsampler = None
        self._loaded = False
        flush_vram()
        logger.info("Real-ESRGAN model unloaded")
    
    def _calculate_scale(self, image: Image.Image) -> int:
        """Calculate required scale factor to meet minimum size."""
        w, h = image.size
        min_dim = min(w, h)
        
        if min_dim >= self.min_size:
            return 1  # No upscaling needed
        
        # Calculate scale to reach min_size
        scale = self.min_size / min_dim
        
        # Real-ESRGAN uses 4x, so we may need multiple passes
        if scale <= 2:
            return 2
        elif scale <= 4:
            return 4
        else:
            return 4  # Max single pass, may need resize after
    
    def enhance(
        self,
        image: Union[str, Path, Image.Image],
        outscale: Optional[int] = None,
    ) -> Image.Image:
        """
        Enhance and upscale image.
        
        Args:
            image: Input image (path or PIL Image)
            outscale: Output scale factor (auto-calculated if None)
            
        Returns:
            Enhanced PIL Image with min 1024px shortest side
        """
        if not self._loaded:
            self.load_model()
        
        # Load image
        if isinstance(image, (str, Path)):
            img = Image.open(image).convert("RGB")
        else:
            img = image.convert("RGB")
        
        # Calculate scale if not provided
        if outscale is None:
            outscale = self._calculate_scale(img)
        
        if outscale == 1:
            logger.info("Image already meets minimum size, skipping upscale")
            return img
        
        # Convert to numpy for Real-ESRGAN
        img_np = np.array(img)
        
        # Run enhancement
        with torch.cuda.amp.autocast():
            output, _ = self.upsampler.enhance(img_np, outscale=outscale)
        
        result = Image.fromarray(output)
        
        # Ensure minimum size is met
        w, h = result.size
        if min(w, h) < self.min_size:
            # Resize to meet minimum
            if w < h:
                new_w = self.min_size
                new_h = int(h * (self.min_size / w))
            else:
                new_h = self.min_size
                new_w = int(w * (self.min_size / h))
            result = result.resize((new_w, new_h), Image.LANCZOS)
        
        logger.info(f"Enhanced: {img.size} -> {result.size}")
        return result
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded


class BackgroundRemover:
    """
    Rembg wrapper for background removal.
    
    Uses isnet-general-use model for best general performance.
    """
    
    _instance: Optional["BackgroundRemover"] = None
    
    @classmethod
    def get_instance(cls) -> "BackgroundRemover":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self, model_name: str = "isnet-general-use"):
        """
        Initialize background remover.
        
        Args:
            model_name: Rembg model to use
        """
        self.model_name = model_name
        self._session = None
        logger.info(f"BackgroundRemover initialized (model={model_name})")
    
    def _get_session(self):
        """Lazy load rembg session."""
        if self._session is None:
            try:
                from rembg import new_session
            except ImportError as e:
                raise RuntimeError(
                    "rembg required. Install with: pip install rembg[gpu]"
                ) from e
            self._session = new_session(self.model_name)
        return self._session
    
    def remove_background(
        self,
        image: Union[str, Path, Image.Image],
        return_mask: bool = False,
    ) -> Union[Image.Image, Tuple[Image.Image, Image.Image]]:
        """
        Remove background from image.
        
        Args:
            image: Input image
            return_mask: Also return the mask
            
        Returns:
            RGBA image with transparent background (and mask if requested)
        """
        try:
            from rembg import remove
        except ImportError as e:
            raise RuntimeError(
                "rembg required. Install with: pip install rembg[gpu]"
            ) from e
        
        # Load image
        if isinstance(image, (str, Path)):
            img = Image.open(image).convert("RGB")
        else:
            img = image.convert("RGB")
        
        # Remove background
        result = remove(img, session=self._get_session())
        
        if return_mask:
            # Extract alpha channel as mask
            if result.mode == "RGBA":
                mask = result.split()[3]
            else:
                mask = Image.new("L", result.size, 255)
            return result, mask
        
        return result
    
    def unload(self) -> None:
        """Unload session to free memory."""
        if self._session is not None:
            del self._session
            self._session = None
        flush_vram()


class ImageEnhancementPipeline:
    """
    Step 1 Pipeline: Image Enhancement (Base Layer)
    
    Combines Real-ESRGAN upscaling with Rembg background removal.
    """
    
    def __init__(self, min_size: int = 1024):
        """
        Initialize enhancement pipeline.
        
        Args:
            min_size: Minimum size for shortest side
        """
        self.min_size = min_size
        self.enhancer = RealESRGANEnhancer(min_size=min_size)
        self.bg_remover = BackgroundRemover()
        logger.info("ImageEnhancementPipeline initialized")
    
    def process(
        self,
        image: Union[str, Path, Image.Image],
        remove_background: bool = True,
        upscale: bool = True,
    ) -> dict:
        """
        Process image through enhancement pipeline.
        
        Args:
            image: Input image
            remove_background: Whether to remove background
            upscale: Whether to upscale image
            
        Returns:
            Dict with 'enhanced', 'mask' (if bg removed), 'original_size', 'final_size'
        """
        # Load image
        if isinstance(image, (str, Path)):
            img = Image.open(image).convert("RGB")
        else:
            img = image.convert("RGB")
        
        original_size = img.size
        result = {"original_size": original_size}
        
        # Step 1a: Upscale
        if upscale:
            img = self.enhancer.enhance(img)
        
        # Step 1b: Remove background
        if remove_background:
            img, mask = self.bg_remover.remove_background(img, return_mask=True)
            result["mask"] = mask
        
        result["enhanced"] = img
        result["final_size"] = img.size
        
        logger.info(f"Enhancement complete: {original_size} -> {img.size}")
        return result
    
    def unload_all(self) -> None:
        """Unload all models to free VRAM."""
        self.enhancer.unload_model()
        self.bg_remover.unload()
        flush_vram()
        logger.info("All enhancement models unloaded")


# Quality assessment helper
def assess_quality(image: Image.Image) -> dict:
    """
    Assess image quality for 3D reconstruction suitability.
    
    Returns dict with quality metrics.
    """
    w, h = image.size
    min_dim = min(w, h)
    
    # Calculate sharpness using Laplacian variance
    from PIL import ImageFilter
    gray = image.convert("L")
    laplacian = gray.filter(ImageFilter.FIND_EDGES)
    sharpness = np.array(laplacian).var()
    
    return {
        "width": w,
        "height": h,
        "min_dimension": min_dim,
        "meets_1024_requirement": min_dim >= 1024,
        "sharpness_score": float(sharpness),
        "quality_rating": min(10, max(1, int(sharpness / 100))),
    }
