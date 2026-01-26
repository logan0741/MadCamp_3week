"""
Unified Garment Reconstruction Pipeline

Orchestrates the complete flow from product images to GLB export:
1. Dual-view segmentation (Mission 2)
2. Size-accurate scaling (Mission 3)
3. Physics simulation (Mission 4)
4. GLB export with rigging (Mission 5)

Implements checkpoint support for session continuity.
"""

from __future__ import annotations

import gc
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import numpy as np
from PIL import Image
from loguru import logger

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

import trimesh


@dataclass
class PipelineCheckpoint:
    """Checkpoint state for pipeline continuity."""
    session_id: str
    stage: str
    timestamp: str
    completed_stages: list
    pending_stages: list
    intermediate_files: Dict[str, str]
    vram_status_mb: float
    error: Optional[str] = None


@dataclass
class ReconstructionResult:
    """Final result from garment reconstruction."""
    glb_path: str
    garment_type: str
    target_size: str
    measurements: Dict[str, float]
    verification_report: Dict[str, Any]
    processing_time_seconds: float
    checkpoints: list
    success: bool
    error: Optional[str] = None


class GarmentReconstructionPipeline:
    """
    End-to-end garment reconstruction pipeline with checkpointing.

    Stages:
        1. SEGMENTATION - Extract garment from front/back images
        2. SCALING - Apply size-accurate non-uniform scaling
        3. PHYSICS - SNUG simulation for realistic draping
        4. EXPORT - GLB with SMPL-X rigging and UV atlas
    """

    STAGES = ["SEGMENTATION", "SCALING", "PHYSICS", "EXPORT"]

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        checkpoint_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, dict], None]] = None,
        vram_limit_mb: float = 20480,  # 20GB
    ):
        self.output_dir = output_dir or Path("data/outputs/reconstruction")
        self.checkpoint_dir = checkpoint_dir or Path("data/checkpoints")
        self.progress_callback = progress_callback
        self.vram_limit_mb = vram_limit_mb

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self._checkpoints: list = []
        self._session_id: str = ""

    def _get_vram_mb(self) -> float:
        """Get current VRAM usage."""
        if HAS_TORCH and torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 * 1024)
        return 0.0

    def _clear_vram(self) -> None:
        """Clear VRAM cache."""
        if HAS_TORCH and torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()

    def _log_progress(self, message: str, data: Optional[dict] = None) -> None:
        """Log progress with callback."""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message, data or {})

    def _save_checkpoint(
        self,
        stage: str,
        completed: list,
        pending: list,
        files: Dict[str, str],
        error: Optional[str] = None,
    ) -> PipelineCheckpoint:
        """Save checkpoint state to disk."""
        checkpoint = PipelineCheckpoint(
            session_id=self._session_id,
            stage=stage,
            timestamp=datetime.now().isoformat(),
            completed_stages=completed,
            pending_stages=pending,
            intermediate_files=files,
            vram_status_mb=self._get_vram_mb(),
            error=error,
        )

        self._checkpoints.append(checkpoint)

        checkpoint_path = self.checkpoint_dir / f"{self._session_id}_{stage}.json"
        with open(checkpoint_path, "w") as f:
            json.dump(asdict(checkpoint), f, indent=2)

        self._log_progress(f"Checkpoint saved: {stage}", asdict(checkpoint))
        return checkpoint

    def load_checkpoint(self, session_id: str) -> Optional[PipelineCheckpoint]:
        """Load latest checkpoint for session."""
        checkpoints = sorted(self.checkpoint_dir.glob(f"{session_id}_*.json"))
        if not checkpoints:
            return None

        with open(checkpoints[-1]) as f:
            data = json.load(f)

        return PipelineCheckpoint(**data)

    def reconstruct(
        self,
        front_image: Image.Image,
        back_image: Image.Image,
        garment_type: str,
        target_size: str,
        measurements_cm: Dict[str, float],
        product_id: str = "unknown",
        resume_session: Optional[str] = None,
    ) -> ReconstructionResult:
        """
        Run full reconstruction pipeline.

        Args:
            front_image: Front view PIL Image
            back_image: Back view PIL Image
            garment_type: Type (top, dress, pants, skirt)
            target_size: Size label (S, M, L, etc.)
            measurements_cm: Dict with length, shoulder, chest, etc.
            product_id: Product identifier for outputs
            resume_session: Optional session ID to resume from

        Returns:
            ReconstructionResult with GLB path and verification
        """
        import time
        start_time = time.time()

        self._session_id = resume_session or f"{product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._checkpoints = []

        completed_stages = []
        pending_stages = list(self.STAGES)
        intermediate_files = {}

        # Check for resume
        if resume_session:
            checkpoint = self.load_checkpoint(resume_session)
            if checkpoint:
                completed_stages = checkpoint.completed_stages
                pending_stages = checkpoint.pending_stages
                intermediate_files = checkpoint.intermediate_files
                self._log_progress(f"Resuming from checkpoint: {checkpoint.stage}")

        try:
            # Stage 1: SEGMENTATION
            if "SEGMENTATION" in pending_stages:
                self._log_progress("Stage 1/4: Dual-view Segmentation")
                seg_result = self._run_segmentation(
                    front_image, back_image, garment_type, product_id
                )
                intermediate_files.update(seg_result)
                completed_stages.append("SEGMENTATION")
                pending_stages.remove("SEGMENTATION")
                self._save_checkpoint("SEGMENTATION", completed_stages, pending_stages, intermediate_files)
                self._clear_vram()

            # Stage 2: SCALING
            if "SCALING" in pending_stages:
                self._log_progress("Stage 2/4: Size-Accurate Scaling")
                scale_result = self._run_scaling(
                    garment_type, measurements_cm, product_id
                )
                intermediate_files.update(scale_result)
                completed_stages.append("SCALING")
                pending_stages.remove("SCALING")
                self._save_checkpoint("SCALING", completed_stages, pending_stages, intermediate_files)

            # Stage 3: PHYSICS
            if "PHYSICS" in pending_stages:
                self._log_progress("Stage 3/4: Physics Simulation")
                physics_result = self._run_physics(
                    intermediate_files.get("scaled_mesh_path"),
                    garment_type,
                    product_id,
                )
                intermediate_files.update(physics_result)
                completed_stages.append("PHYSICS")
                pending_stages.remove("PHYSICS")
                self._save_checkpoint("PHYSICS", completed_stages, pending_stages, intermediate_files)
                self._clear_vram()

            # Stage 4: EXPORT
            if "EXPORT" in pending_stages:
                self._log_progress("Stage 4/4: GLB Export")
                export_result = self._run_export(
                    intermediate_files,
                    garment_type,
                    product_id,
                )
                intermediate_files.update(export_result)
                completed_stages.append("EXPORT")
                pending_stages.remove("EXPORT")
                self._save_checkpoint("EXPORT", completed_stages, pending_stages, intermediate_files)

            processing_time = time.time() - start_time

            return ReconstructionResult(
                glb_path=intermediate_files.get("glb_path", ""),
                garment_type=garment_type,
                target_size=target_size,
                measurements=measurements_cm,
                verification_report=intermediate_files.get("verification", {}),
                processing_time_seconds=processing_time,
                checkpoints=[asdict(c) for c in self._checkpoints],
                success=True,
            )

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self._save_checkpoint("ERROR", completed_stages, pending_stages, intermediate_files, str(e))

            return ReconstructionResult(
                glb_path="",
                garment_type=garment_type,
                target_size=target_size,
                measurements=measurements_cm,
                verification_report={},
                processing_time_seconds=time.time() - start_time,
                checkpoints=[asdict(c) for c in self._checkpoints],
                success=False,
                error=str(e),
            )

    def _run_segmentation(
        self,
        front_image: Image.Image,
        back_image: Image.Image,
        garment_type: str,
        product_id: str,
    ) -> Dict[str, str]:
        """Execute segmentation stage."""
        from models.segmentation.dual_view_processor import DualViewSegmentationPipeline

        seg_dir = self.output_dir / product_id / "segmentation"
        pipeline = DualViewSegmentationPipeline(
            output_dir=seg_dir,
            progress_callback=self.progress_callback,
        )

        result = pipeline.process_dual_view(
            front_image=front_image,
            back_image=back_image,
            garment_type=garment_type,
            output_prefix=product_id,
        )

        return {
            "front_rgba_path": str(seg_dir / f"{product_id}_front.png"),
            "back_rgba_path": str(seg_dir / f"{product_id}_back.png"),
            "front_mask_path": str(seg_dir / f"{product_id}_front_mask.npy"),
            "back_mask_path": str(seg_dir / f"{product_id}_back_mask.npy"),
        }

    def _run_scaling(
        self,
        garment_type: str,
        measurements_cm: Dict[str, float],
        product_id: str,
    ) -> Dict[str, Any]:
        """Execute scaling stage with verification."""
        from models.scaling.size_scaler import GarmentSizeScaler

        scaler = GarmentSizeScaler()
        template = scaler.load_template_mesh(garment_type)
        scaled_mesh, verification = scaler.scale_mesh_with_verification(
            template, garment_type, measurements_cm
        )

        mesh_path = self.output_dir / product_id / f"{product_id}_scaled.obj"
        mesh_path.parent.mkdir(parents=True, exist_ok=True)
        scaled_mesh.export(str(mesh_path))

        return {
            "scaled_mesh_path": str(mesh_path),
            "verification": verification,
        }

    def _run_physics(
        self,
        mesh_path: str,
        garment_type: str,
        product_id: str,
    ) -> Dict[str, str]:
        """Execute physics simulation stage."""
        from models.garment.snug_wrapper import SnugModel

        # Load scaled mesh
        mesh = trimesh.load(mesh_path)
        vertices = np.array(mesh.vertices)

        # Create body approximation for simulation
        body_vertices = self._create_body_proxy(vertices)

        # Run SNUG simulation
        snug = SnugModel(garment_type=garment_type)
        result = snug.simulate(body_vertices)

        # Save simulated mesh
        physics_path = self.output_dir / product_id / f"{product_id}_physics.obj"
        simulated_mesh = trimesh.Trimesh(
            vertices=result["vertices"],
            faces=mesh.faces if hasattr(mesh, "faces") else result["faces"],
        )
        simulated_mesh.export(str(physics_path))

        return {
            "physics_mesh_path": str(physics_path),
            "stress_values": result.get("stress", []).tolist() if isinstance(result.get("stress"), np.ndarray) else [],
        }

    def _run_export(
        self,
        intermediate_files: Dict[str, str],
        garment_type: str,
        product_id: str,
    ) -> Dict[str, str]:
        """Execute GLB export stage."""
        from models.export.unity_exporter import export_dressed_mannequin
        from models.smplx.mannequin import generate_mannequin

        # Load physics mesh
        garment_mesh = trimesh.load(intermediate_files.get("physics_mesh_path", intermediate_files.get("scaled_mesh_path")))

        # Generate mannequin
        mannequin = generate_mannequin(height_cm=170, weight_kg=65)

        # Create texture from front/back RGBA
        texture = self._create_uv_atlas(
            intermediate_files.get("front_rgba_path"),
            intermediate_files.get("back_rgba_path"),
        )

        # Export GLB
        glb_path = self.output_dir / product_id / f"{product_id}.glb"
        export_dressed_mannequin(
            mannequin_mesh=mannequin,
            garment_mesh=garment_mesh,
            garment_texture=texture,
            output_path=glb_path,
        )

        return {
            "glb_path": str(glb_path),
        }

    def _create_body_proxy(self, garment_vertices: np.ndarray) -> np.ndarray:
        """Create body vertex proxy from garment bounds."""
        bounds = np.array([garment_vertices.min(axis=0), garment_vertices.max(axis=0)])
        center = bounds.mean(axis=0)

        # Create simple body proxy (cylinder approximation)
        n_points = 1000
        theta = np.linspace(0, 2 * np.pi, n_points)
        height = np.linspace(bounds[0, 1], bounds[1, 1], n_points)

        radius = (bounds[1, 0] - bounds[0, 0]) / 2 * 0.9  # Slightly smaller than garment

        x = center[0] + radius * np.cos(theta)
        y = height
        z = center[2] + radius * np.sin(theta)

        return np.column_stack([x, y, z])

    def _create_uv_atlas(
        self,
        front_path: Optional[str],
        back_path: Optional[str],
        atlas_size: tuple = (2048, 1024),
    ) -> Image.Image:
        """Create UV atlas from front/back images."""
        atlas = Image.new("RGBA", atlas_size, (200, 200, 200, 255))

        half_width = atlas_size[0] // 2

        if front_path and Path(front_path).exists():
            front = Image.open(front_path)
            front = front.resize((half_width, atlas_size[1]), Image.Resampling.LANCZOS)
            atlas.paste(front, (0, 0))

        if back_path and Path(back_path).exists():
            back = Image.open(back_path)
            back = back.resize((half_width, atlas_size[1]), Image.Resampling.LANCZOS)
            atlas.paste(back, (half_width, 0))

        return atlas


def reconstruct_garment(
    front_image: Image.Image,
    back_image: Image.Image,
    garment_type: str,
    target_size: str,
    measurements_cm: Dict[str, float],
    product_id: str = "garment",
    output_dir: Optional[Path] = None,
) -> ReconstructionResult:
    """Convenience function for garment reconstruction."""
    pipeline = GarmentReconstructionPipeline(output_dir=output_dir)
    return pipeline.reconstruct(
        front_image=front_image,
        back_image=back_image,
        garment_type=garment_type,
        target_size=target_size,
        measurements_cm=measurements_cm,
        product_id=product_id,
    )
