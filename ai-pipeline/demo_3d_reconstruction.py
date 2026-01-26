#!/usr/bin/env python3
"""
Demo: 3D Garment Reconstruction from Real Images

This script demonstrates the full pipeline:
1. Dual-view segmentation (fashn-human-parser)
2. Size-accurate mesh scaling
3. Physics simulation (SNUG)
4. GLB export for Unity viewer

Output files are saved to: data/outputs/demo/
"""

import sys
from pathlib import Path
from datetime import datetime
import argparse
import shutil

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image
from loguru import logger
import numpy as np

# Configure logging
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")


def main(publish_to_frontend: bool = False):
    print("\n" + "="*60)
    print("  3D Garment Reconstruction Demo")
    print("="*60 + "\n")

    # Setup output directory (disposable test artifacts)
    date_tag = datetime.now().strftime("%Y%m%d")
    run_id = f"demo_{datetime.now().strftime('%H%M%S')}"
    output_dir = PROJECT_ROOT / "test_artifacts" / "github_samples" / date_tag / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load sample images
    print("[1/5] Loading sample images...")

    # Use SHAPY sample images (people in clothing)
    sample_images_dir = PROJECT_ROOT / "models" / "3d" / "shapy" / "samples" / "images"

    # Use img_00 as front view, img_01 as back view (simulating dual-view)
    front_image_path = sample_images_dir / "img_00.jpg"
    back_image_path = sample_images_dir / "img_01.jpg"

    if not front_image_path.exists():
        print(f"  ❌ Sample image not found: {front_image_path}")
        # Use SNUG demo image as fallback
        front_image_path = PROJECT_ROOT / "models" / "3d" / "snug" / "assets" / "images" / "demo.jpg"
        back_image_path = front_image_path  # Use same image for both views

    front_image = Image.open(front_image_path)
    back_image = Image.open(back_image_path)

    # Copy inputs into test artifacts for traceability
    inputs_dir = output_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    try:
        import shutil

        shutil.copy2(front_image_path, inputs_dir / front_image_path.name)
        if back_image_path != front_image_path:
            shutil.copy2(back_image_path, inputs_dir / back_image_path.name)
    except Exception:
        pass

    print(f"  ✓ Front image: {front_image_path.name} ({front_image.size})")
    print(f"  ✓ Back image: {back_image_path.name} ({back_image.size})")

    # Define Musinsa-style size measurements (Size M)
    measurements = {
        "length": 72,      # cm - 총장
        "shoulder": 48,    # cm - 어깨너비
        "chest": 108,      # cm - 가슴단면
        "sleeve": 62,      # cm - 소매길이
    }
    print(f"  ✓ Target measurements: {measurements}")

    # Step 2: Dual-view Segmentation
    print("\n[2/5] Running dual-view segmentation...")
    try:
        from models.segmentation.dual_view_processor import DualViewSegmentationPipeline

        seg_output_dir = output_dir / "segmentation"
        seg_pipeline = DualViewSegmentationPipeline(output_dir=seg_output_dir)

        seg_result = seg_pipeline.process_dual_view(
            front_image=front_image,
            back_image=back_image,
            garment_type="top",
            save_outputs=True,
            output_prefix=f"garment_{timestamp}",
        )

        print(f"  ✓ Front RGBA saved: {seg_output_dir}/garment_{timestamp}_front.png")
        print(f"  ✓ Back RGBA saved: {seg_output_dir}/garment_{timestamp}_back.png")
        print(f"  ✓ VRAM used: {seg_result.vram_after_mb:.1f} MB")

        front_rgba = seg_result.front_rgba
        back_rgba = seg_result.back_rgba

    except Exception as e:
        logger.warning(f"Segmentation failed: {e}, using original images as textures")
        front_rgba = front_image.convert("RGBA")
        back_rgba = back_image.convert("RGBA")

    # Step 3: Size-accurate Scaling
    print("\n[3/5] Scaling template mesh to measurements...")
    from models.scaling.size_scaler import GarmentSizeScaler

    scaler = GarmentSizeScaler()
    template = scaler.load_template_mesh("top")

    print(f"  ✓ Loaded template: {len(template.vertices)} vertices, {len(template.faces)} faces")

    scaled_mesh, verification = scaler.scale_mesh_with_verification(
        template, "top", measurements
    )

    print(f"  ✓ Scaled mesh: {len(scaled_mesh.vertices)} vertices")
    print(f"  ✓ Verification accuracy: {verification['overall_accuracy']:.1f}%")

    # Save scaled mesh
    scaled_mesh_path = output_dir / f"scaled_mesh_{timestamp}.obj"
    scaled_mesh.export(str(scaled_mesh_path))
    print(f"  ✓ Saved: {scaled_mesh_path}")

    # Step 4: Physics Simulation
    print("\n[4/5] Running physics simulation (SNUG)...")
    from models.garment.snug_wrapper import SnugModel

    snug = SnugModel(garment_type="tshirt", use_gpu=True)

    # Create body proxy from mesh
    bounds = scaled_mesh.bounds
    center = bounds.mean(axis=0)

    # Generate body vertices (cylinder approximation)
    n_points = len(scaled_mesh.vertices)
    height = np.linspace(bounds[0, 1], bounds[1, 1], n_points)
    theta = np.linspace(0, 2 * np.pi, n_points)
    radius = (bounds[1, 0] - bounds[0, 0]) / 2 * 0.85

    body_vertices = np.column_stack([
        center[0] + radius * np.cos(theta),
        height,
        center[2] + radius * np.sin(theta),
    ]).astype(np.float32)

    physics_result = snug.simulate(body_vertices)
    print(f"  ✓ Simulation complete: {len(physics_result['vertices'])} output vertices")

    # For GLB export, use scaled mesh (preserves topology)
    physics_mesh = scaled_mesh.copy()

    # Step 5: GLB Export
    print("\n[5/5] Exporting GLB for Unity viewer...")
    from models.export.unity_exporter import export_dressed_mannequin
    from models.smplx.mannequin import generate_mannequin

    # Generate mannequin
    mannequin = generate_mannequin(height_cm=175, weight_kg=70)
    print(f"  ✓ Generated mannequin: {len(mannequin.vertices)} vertices")

    # Create UV atlas from front/back images
    atlas_width, atlas_height = 2048, 1024
    atlas = Image.new("RGBA", (atlas_width, atlas_height), (200, 200, 200, 255))

    # Resize and paste front/back
    half_width = atlas_width // 2
    front_resized = front_rgba.resize((half_width, atlas_height), Image.Resampling.LANCZOS)
    back_resized = back_rgba.resize((half_width, atlas_height), Image.Resampling.LANCZOS)

    atlas.paste(front_resized, (0, 0))
    atlas.paste(back_resized, (half_width, 0))

    # Save atlas
    atlas_path = output_dir / f"uv_atlas_{timestamp}.png"
    atlas.save(atlas_path)
    print(f"  ✓ UV Atlas saved: {atlas_path}")

    # Export GLB
    glb_path = output_dir / f"garment_3d_{timestamp}.glb"
    export_dressed_mannequin(
        mannequin_mesh=mannequin,
        garment_mesh=physics_mesh,
        garment_texture=atlas,
        output_path=glb_path,
    )

    glb_size = glb_path.stat().st_size / 1024
    print(f"  ✓ GLB exported: {glb_path} ({glb_size:.1f} KB)")

    # Summary
    print("\n" + "="*60)
    print("  ✅ 3D Reconstruction Complete!")
    print("="*60)
    print(f"\n📁 Output files saved to: {output_dir}/")
    print(f"   - Segmented images: segmentation/garment_{timestamp}_*.png")
    print(f"   - Scaled mesh: scaled_mesh_{timestamp}.obj")
    print(f"   - UV Atlas: uv_atlas_{timestamp}.png")
    print(f"   - 3D Model: garment_3d_{timestamp}.glb")
    print(f"\n🌐 To view the GLB file:")
    print(f"   1. Open https://gltf-viewer.donmccurdy.com/")
    print(f"   2. Drag and drop: {glb_path}")
    print(f"\n   Or copy to frontend:")
    print(f"   cp {glb_path} /home/MadCamp/MadCamp_3week/frontend/public/models/")

    if publish_to_frontend:
        frontend_dir = PROJECT_ROOT.parent / "frontend" / "public" / "test_artifacts" / "github_samples" / date_tag / run_id
        frontend_dir.mkdir(parents=True, exist_ok=True)
        for item in output_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, frontend_dir / item.name)
        # copy segmentation outputs if exist
        seg_dir = output_dir / "segmentation"
        if seg_dir.exists():
            target_seg = frontend_dir / "segmentation"
            target_seg.mkdir(parents=True, exist_ok=True)
            for item in seg_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, target_seg / item.name)

    return str(glb_path)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="3D Garment Reconstruction Demo")
        parser.add_argument("--publish-to-frontend", action="store_true")
        args = parser.parse_args()
        result = main(publish_to_frontend=args.publish_to_frontend)
        print(f"\n✅ Success! GLB file: {result}\n")
    except Exception as e:
        logger.exception(f"Demo failed: {e}")
        sys.exit(1)
