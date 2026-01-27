"""
MemeForty Phase 2: 3D Reconstruction Pipeline Master Integration

Combines all 5 steps into a unified 3D reconstruction pipeline.

Steps:
1. Multi-view Depth Fusion (Hunyuan3D-2mv)
2. SMPL-X Wrapping (Shrink-wrap)
3. Automatic Rigging
4. Smart Texture Baking
5. GLB Optimization

Hardware Constraints:
- 20GB VRAM limit
- Sequential inference with flush between modules
"""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass, field

import numpy as np
import torch
from PIL import Image
from loguru import logger


def flush_vram():
    """Flush VRAM cache to prevent OOM."""
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()


@dataclass
class Phase2Config:
    """Configuration for MemeForty Phase 2 3D Pipeline."""
    
    # Step 1: Depth Fusion
    depth_resolution: int = 512
    
    # Step 2: SMPL-X Wrapping
    height_cm: float = 170
    weight_kg: float = 65
    gender: str = "neutral"
    
    # Step 3: Rigging
    max_bone_influences: int = 4
    
    # Step 4: Texture
    atlas_size: tuple = (2048, 2048)
    material_type: str = "fabric"
    
    # Step 5: GLB
    target_faces: Optional[int] = 50000
    mobile_optimized: bool = True
    enable_lod: bool = True
    
    # Hardware
    device: str = "cuda"


@dataclass
class Phase2Result:
    """Result container for Phase 2 3D Pipeline."""
    
    # Step outputs
    raw_mesh: Any = None
    wrapped_mesh: Any = None
    rigged_data: Dict[str, Any] = field(default_factory=dict)
    texture_data: Dict[str, Any] = field(default_factory=dict)
    optimized_mesh: Any = None
    
    # Final outputs
    glb_path: Optional[str] = None
    
    # Quality metrics
    step_scores: Dict[str, float] = field(default_factory=dict)
    overall_quality: float = 0.0
    
    # Metadata
    processing_times: Dict[str, float] = field(default_factory=dict)


class MemeForty3DPipeline:
    """
    MemeForty Phase 2: Complete 3D Reconstruction Pipeline.
    
    Orchestrates all 5 steps with proper VRAM management.
    
    Usage:
        pipeline = MemeForty3DPipeline()
        result = pipeline.process(
            front_image="fitted_front.jpg",
            back_image="fitted_back.jpg",
        )
    """
    
    def __init__(self, config: Optional[Phase2Config] = None):
        """
        Initialize Phase 2 pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or Phase2Config()
        logger.info("MemeForty3DPipeline initialized")
    
    def process(
        self,
        front_image: Union[str, Path, Image.Image],
        back_image: Union[str, Path, Image.Image],
        parsing_map: Optional[np.ndarray] = None,
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Phase2Result:
        """
        Run complete 3D reconstruction pipeline.
        
        Args:
            front_image: Front fitted image from Phase 1
            back_image: Back fitted image from Phase 1
            parsing_map: Optional parsing map for mask guidance
            output_dir: Output directory for files
            
        Returns:
            Phase2Result with all outputs
        """
        import time
        
        result = Phase2Result()
        
        if output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("=" * 60)
        logger.info("MemeForty Phase 2: Starting 3D Pipeline")
        logger.info("=" * 60)
        
        # ============================================
        # Step 1: Multi-view Depth Fusion
        # ============================================
        logger.info("[Step 1/5] Multi-view Depth Fusion (Hunyuan3D)")
        start_time = time.time()
        
        try:
            step1_result = self._step1_depth_fusion(front_image, back_image, parsing_map)
            result.raw_mesh = step1_result.get("mesh")
            result.step_scores["step1"] = step1_result.get("quality_score", 7.0)
        except Exception as e:
            logger.error(f"Step 1 failed: {e}")
            result.step_scores["step1"] = 0.0
        
        result.processing_times["step1"] = time.time() - start_time
        self._unload_step1()
        
        if result.raw_mesh is None:
            logger.error("Cannot proceed without raw mesh")
            return result
        
        # ============================================
        # Step 2: SMPL-X Wrapping
        # ============================================
        logger.info("[Step 2/5] SMPL-X Wrapping")
        start_time = time.time()
        
        try:
            step2_result = self._step2_smplx_wrap(result.raw_mesh)
            result.wrapped_mesh = step2_result.get("wrapped_mesh")
            result.step_scores["step2"] = step2_result.get("quality_score", 7.0)
        except Exception as e:
            logger.error(f"Step 2 failed: {e}")
            result.step_scores["step2"] = 0.0
            result.wrapped_mesh = result.raw_mesh  # Fallback
        
        result.processing_times["step2"] = time.time() - start_time
        self._unload_step2()
        
        # ============================================
        # Step 3: Automatic Rigging
        # ============================================
        logger.info("[Step 3/5] Automatic Rigging")
        start_time = time.time()
        
        try:
            step3_result = self._step3_rigging(result.wrapped_mesh)
            result.rigged_data = step3_result
            result.step_scores["step3"] = step3_result.get("quality_score", 7.0)
        except Exception as e:
            logger.error(f"Step 3 failed: {e}")
            result.step_scores["step3"] = 0.0
        
        result.processing_times["step3"] = time.time() - start_time
        
        # ============================================
        # Step 4: Texture Baking
        # ============================================
        logger.info("[Step 4/5] Texture Baking")
        start_time = time.time()
        
        try:
            step4_result = self._step4_texture(front_image, back_image)
            result.texture_data = step4_result
            result.step_scores["step4"] = step4_result.get("quality_score", 7.0)
        except Exception as e:
            logger.error(f"Step 4 failed: {e}")
            result.step_scores["step4"] = 0.0
        
        result.processing_times["step4"] = time.time() - start_time
        
        # ============================================
        # Step 5: GLB Optimization & Export
        # ============================================
        logger.info("[Step 5/5] GLB Optimization")
        start_time = time.time()
        
        try:
            step5_result = self._step5_optimize(
                result.wrapped_mesh,
                result.texture_data.get("atlas"),
                output_dir,
            )
            result.optimized_mesh = step5_result.get("mesh")
            result.glb_path = step5_result.get("glb_path")
            result.step_scores["step5"] = step5_result.get("quality_score", 7.0)
        except Exception as e:
            logger.error(f"Step 5 failed: {e}")
            result.step_scores["step5"] = 0.0
        
        result.processing_times["step5"] = time.time() - start_time
        
        # ============================================
        # Final Summary
        # ============================================
        total_time = sum(result.processing_times.values())
        valid_scores = list(result.step_scores.values())
        result.overall_quality = np.mean(valid_scores) if valid_scores else 0.0
        
        logger.info("=" * 60)
        logger.info("MemeForty Phase 2: Pipeline Complete")
        logger.info(f"Overall Quality: {result.overall_quality:.1f}/10")
        logger.info(f"Total Time: {total_time:.2f}s")
        if result.glb_path:
            logger.info(f"GLB Output: {result.glb_path}")
        logger.info("=" * 60)
        
        flush_vram()
        return result
    
    # ========================================
    # Step 1: Depth Fusion
    # ========================================
    def _step1_depth_fusion(self, front, back, parsing_map) -> dict:
        from models.3d.depth import DepthFusionPipeline
        
        pipeline = DepthFusionPipeline(
            resolution=self.config.depth_resolution,
            device=self.config.device,
        )
        return pipeline.process(front, back, parsing_map)
    
    def _unload_step1(self):
        flush_vram()
    
    # ========================================
    # Step 2: SMPL-X Wrapping
    # ========================================
    def _step2_smplx_wrap(self, mesh) -> dict:
        from models.smplx import SMPLXWrapper
        
        wrapper = SMPLXWrapper.get_instance()
        return wrapper.wrap(
            mesh,
            height_cm=self.config.height_cm,
            weight_kg=self.config.weight_kg,
        )
    
    def _unload_step2(self):
        from models.smplx import SMPLXWrapper
        if SMPLXWrapper._instance:
            SMPLXWrapper._instance.unload_model()
        flush_vram()
    
    # ========================================
    # Step 3: Rigging
    # ========================================
    def _step3_rigging(self, mesh) -> dict:
        from models.rigging import RiggingPipeline
        
        pipeline = RiggingPipeline(max_influences=self.config.max_bone_influences)
        return pipeline.process(mesh, height_cm=self.config.height_cm)
    
    # ========================================
    # Step 4: Texture Baking
    # ========================================
    def _step4_texture(self, front, back) -> dict:
        from models.texture import SmartTextureBaker
        
        baker = SmartTextureBaker(
            atlas_size=self.config.atlas_size,
            material_type=self.config.material_type,
        )
        return baker.bake(front, back)
    
    # ========================================
    # Step 5: GLB Optimization
    # ========================================
    def _step5_optimize(self, mesh, texture, output_dir) -> dict:
        from models.export import GLBOptimizer, MobileOptimizer
        
        if self.config.mobile_optimized:
            optimizer = MobileOptimizer()
            result = optimizer.optimize_for_mobile(mesh)
        else:
            optimizer = GLBOptimizer(
                target_faces=self.config.target_faces,
                enable_lod=self.config.enable_lod,
            )
            result = optimizer.optimize(mesh)
        
        # Export GLB
        if output_dir is not None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            glb_path = Path(output_dir) / f"model_{timestamp}.glb"
            
            if self.config.mobile_optimized:
                result["glb_path"] = optimizer.optimizer.export_glb(result, glb_path)
            else:
                result["glb_path"] = optimizer.export_glb(result, glb_path)
        
        return result


# Convenience function
def run_phase2_pipeline(
    front_image: Union[str, Path, Image.Image],
    back_image: Union[str, Path, Image.Image],
    output_dir: Optional[Union[str, Path]] = None,
    **config_kwargs,
) -> Phase2Result:
    """
    Run Phase 2 3D pipeline with default settings.
    
    Args:
        front_image: Front fitted image
        back_image: Back fitted image
        output_dir: Output directory
        **config_kwargs: Override config parameters
        
    Returns:
        Phase2Result
    """
    config = Phase2Config(**config_kwargs)
    pipeline = MemeForty3DPipeline(config)
    return pipeline.process(front_image, back_image, output_dir=output_dir)


def connect_phase1_to_phase2(
    phase1_result,
    output_dir: Optional[Union[str, Path]] = None,
) -> Phase2Result:
    """
    Connect Phase 1 output to Phase 2 input.
    
    Args:
        phase1_result: Result from MemeForty2DPipeline
        output_dir: Output directory
        
    Returns:
        Phase2Result
    """
    front = phase1_result.color_corrected_front or phase1_result.vton_front
    back = phase1_result.color_corrected_back or phase1_result.vton_back
    
    if front is None:
        raise ValueError("Phase 1 result missing front view")
    
    return run_phase2_pipeline(front, back, output_dir=output_dir)
