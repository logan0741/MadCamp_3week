"""
Garment size scaling utilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np
import trimesh
from loguru import logger


class GarmentSizeScaler:
    """
    Scale template garment meshes based on measurement data.
    """

    REFERENCE_SIZES: Dict[str, Dict[str, float]] = {
        "top": {"length": 70, "shoulder": 45, "chest": 100, "sleeve": 60},
        "pants": {"length": 100, "waist": 80, "hip": 100, "inseam": 75},
        "dress": {"length": 90, "shoulder": 40, "bust": 88, "waist": 70},
        "skirt": {"length": 45, "waist": 70, "hip": 95},
    }

    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = template_dir or (Path(__file__).parent.parent / "templates")

    def load_template_mesh(self, garment_type: str) -> trimesh.Trimesh:
        """
        Load template mesh for garment type.
        """
        template_path = self.template_dir / f"{garment_type}.obj"
        if template_path.exists():
            mesh = trimesh.load_mesh(template_path, process=False)
            return self._ensure_trimesh(mesh)

        fallback = self._fallback_mesh_path(garment_type)
        if fallback and fallback.exists():
            logger.warning(f"Template not found, using fallback mesh: {fallback}")
            mesh = trimesh.load_mesh(fallback, process=False)
            return self._ensure_trimesh(mesh)

        logger.warning(f"Template not found for {garment_type}, using primitive box")
        mesh = trimesh.creation.box(extents=(0.5, 0.8, 0.3))
        return self._ensure_trimesh(mesh)

    def scale_mesh(
        self,
        template_mesh: trimesh.Trimesh,
        garment_type: str,
        target_cm: Dict[str, float],
    ) -> trimesh.Trimesh:
        """
        Apply non-uniform scaling based on size measurements.
        """
        if garment_type not in self.REFERENCE_SIZES:
            raise ValueError(f"Unknown garment_type: {garment_type}")

        ref = self.REFERENCE_SIZES[garment_type]
        scales = {k: target_cm.get(k, ref[k]) / ref[k] for k in ref}

        vertices = template_mesh.vertices.copy()
        center = template_mesh.centroid
        vertices = vertices - center

        if garment_type in {"top", "dress"}:
            vertices[:, 1] *= scales.get("length", 1.0)
            vertices[:, 0] *= scales.get("shoulder", 1.0)
            vertices[:, 2] *= scales.get("chest", scales.get("bust", 1.0))
        elif garment_type in {"pants", "skirt"}:
            vertices[:, 1] *= scales.get("length", 1.0)
            vertices[:, 0] *= scales.get("waist", 1.0)
            vertices[:, 2] *= scales.get("hip", 1.0)
        else:
            vertices[:, :] *= 1.0

        vertices = vertices + center

        scaled = template_mesh.copy()
        scaled.vertices = vertices
        return scaled

    def _fallback_mesh_path(self, garment_type: str) -> Path | None:
        snug_dir = Path(__file__).parent.parent / "3d" / "snug" / "assets" / "meshes"
        mapping = {
            "top": snug_dir / "tshirt.obj",
            "dress": snug_dir / "long_sleeve_top.obj",
            "pants": snug_dir / "pants.obj",
            "skirt": snug_dir / "shorts.obj",
        }
        return mapping.get(garment_type)

    def _ensure_trimesh(self, mesh: trimesh.Trimesh | trimesh.Scene) -> trimesh.Trimesh:
        if isinstance(mesh, trimesh.Scene):
            if not mesh.geometry:
                raise ValueError("Empty mesh scene")
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        return mesh

    def get_mesh_measurements(self, mesh: trimesh.Trimesh) -> Dict[str, float]:
        """
        Extract actual measurements from mesh bounding box.

        Returns dimensions in cm (assuming mesh units are meters, scaled by 100).
        """
        bounds = mesh.bounds
        extents = bounds[1] - bounds[0]

        # Assuming Y is vertical (length), X is width, Z is depth
        return {
            "length_cm": float(extents[1] * 100),
            "width_cm": float(extents[0] * 100),
            "depth_cm": float(extents[2] * 100),
            "bounding_box": extents.tolist(),
        }

    def verify_mesh_dimensions(
        self,
        scaled_mesh: trimesh.Trimesh,
        garment_type: str,
        target_cm: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Verify scaled mesh dimensions against input measurements.

        Returns fact-check report with accuracy metrics.
        """
        actual = self.get_mesh_measurements(scaled_mesh)
        ref = self.REFERENCE_SIZES.get(garment_type, {})

        verification = {
            "garment_type": garment_type,
            "target_measurements": target_cm,
            "actual_mesh_dimensions": actual,
            "reference_sizes": ref,
            "verification_results": {},
            "overall_accuracy": 0.0,
            "passed": False,
        }

        # Map mesh dimensions to measurement types
        dimension_mapping = {
            "length": "length_cm",
            "shoulder": "width_cm",
            "chest": "depth_cm",
            "bust": "depth_cm",
            "waist": "width_cm",
            "hip": "depth_cm",
        }

        accuracies = []
        for measurement, target_value in target_cm.items():
            mesh_dim = dimension_mapping.get(measurement)
            if mesh_dim and mesh_dim in actual:
                actual_value = actual[mesh_dim]
                # Calculate scale-adjusted accuracy
                ref_value = ref.get(measurement, target_value)
                expected_scale = target_value / ref_value if ref_value else 1.0

                # Compare ratios rather than absolute values
                accuracy = min(target_value, actual_value) / max(target_value, actual_value) * 100
                accuracies.append(accuracy)

                verification["verification_results"][measurement] = {
                    "target_cm": target_value,
                    "reference_cm": ref_value,
                    "expected_scale": expected_scale,
                    "accuracy_percent": round(accuracy, 2),
                }

        if accuracies:
            verification["overall_accuracy"] = round(sum(accuracies) / len(accuracies), 2)
            verification["passed"] = verification["overall_accuracy"] >= 85.0

        return verification

    def scale_mesh_with_verification(
        self,
        template_mesh: trimesh.Trimesh,
        garment_type: str,
        target_cm: Dict[str, float],
    ) -> tuple[trimesh.Trimesh, Dict[str, Any]]:
        """
        Scale mesh and return verification report.

        Returns:
            Tuple of (scaled_mesh, verification_report)
        """
        scaled = self.scale_mesh(template_mesh, garment_type, target_cm)
        verification = self.verify_mesh_dimensions(scaled, garment_type, target_cm)

        if not verification["passed"]:
            logger.warning(
                f"Mesh verification failed: {verification['overall_accuracy']:.1f}% accuracy "
                f"(target: 85%)"
            )
        else:
            logger.info(
                f"Mesh verification passed: {verification['overall_accuracy']:.1f}% accuracy"
            )

        return scaled, verification
