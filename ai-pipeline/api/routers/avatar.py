"""
Avatar Router

Endpoints for 3D avatar generation and garment simulation.
Uses SHAPY for body estimation and SNUG for garment simulation.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional, List
import time
import uuid
import base64
import json
import numpy as np
from io import BytesIO
from PIL import Image
from loguru import logger

from config import settings

router = APIRouter()


# ============================================
# Schemas
# ============================================

from pydantic import BaseModel, Field
from typing import Dict, Any


class BodyMeasurements(BaseModel):
    """Body measurements for avatar generation."""
    height: float = Field(..., description="Height in meters", ge=1.0, le=2.5)
    weight: Optional[float] = Field(None, description="Weight in kg", ge=30, le=200)
    chest: Optional[float] = Field(None, description="Chest circumference in cm", ge=60, le=150)
    waist: Optional[float] = Field(None, description="Waist circumference in cm", ge=50, le=130)
    hips: Optional[float] = Field(None, description="Hip circumference in cm", ge=60, le=150)
    gender: str = Field("neutral", description="Gender: male, female, or neutral")


class AvatarRequest(BaseModel):
    """Request for avatar generation."""
    # Option 1: Generate from image
    image_url: Optional[str] = Field(None, description="URL of person image")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image")

    # Option 2: Generate from measurements
    measurements: Optional[BodyMeasurements] = None

    # Output options
    output_format: str = Field("glb", description="Output format: obj, ply, or glb")
    include_texture: bool = Field(False, description="Include texture mapping")


class AvatarResponse(BaseModel):
    """Response for avatar generation."""
    success: bool
    avatar_id: str
    mesh_url: str
    betas: List[float]
    measurements: Dict[str, float]
    processing_time_seconds: float
    confidence: Optional[float] = None


class GarmentSimulationRequest(BaseModel):
    """Request for garment simulation."""
    avatar_id: str = Field(..., description="Avatar ID from previous generation")
    garment_type: str = Field(..., description="Garment type: tshirt, dress, pants, etc.")

    # Optional custom pose
    pose: Optional[List[float]] = Field(None, description="Body pose parameters (63 values)")

    # Animation
    animate: bool = Field(False, description="Generate animation sequence")
    animation_frames: int = Field(30, description="Number of animation frames")

    output_format: str = Field("glb", description="Output format: obj, ply, or glb")


class GarmentSimulationResponse(BaseModel):
    """Response for garment simulation."""
    success: bool
    garment_mesh_url: str
    combined_mesh_url: Optional[str] = None
    animation_url: Optional[str] = None
    processing_time_seconds: float


class CombinedAvatarRequest(BaseModel):
    """Request for combined avatar + garment generation."""
    # Image input
    person_image_url: Optional[str] = None
    person_image_base64: Optional[str] = None

    # Or measurements
    measurements: Optional[BodyMeasurements] = None

    # Garment
    garment_type: str = Field("tshirt", description="Type of garment")
    garment_image_url: Optional[str] = Field(None, description="Custom garment image URL")

    output_format: str = Field("glb", description="Output format")


class CombinedAvatarResponse(BaseModel):
    """Response for combined avatar + garment."""
    success: bool
    avatar_mesh_url: str
    garment_mesh_url: str
    combined_mesh_url: str
    betas: List[float]
    measurements: Dict[str, float]
    processing_time_seconds: float


# ============================================
# Helper Functions
# ============================================

def load_image(url: Optional[str] = None, base64_str: Optional[str] = None) -> Image.Image:
    """Load image from URL or base64."""
    if url:
        import httpx
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGB')
    elif base64_str:
        image_data = base64.b64decode(base64_str)
        return Image.open(BytesIO(image_data)).convert('RGB')
    else:
        raise ValueError("Must provide either url or base64_str")


def get_output_dir(subdir: str) -> Path:
    """Get output directory, creating if needed."""
    output_dir = settings.output_dir / subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_avatar_storage_path(avatar_id: str) -> Path:
    """Get storage path for avatar data."""
    storage_dir = settings.output_dir / "avatars" / "data"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir / f"{avatar_id}.json"


def save_avatar_data(avatar_id: str, data: dict):
    """Save avatar data for later use."""
    path = get_avatar_storage_path(avatar_id)
    with open(path, 'w') as f:
        # Convert numpy arrays to lists
        serializable_data = {}
        for k, v in data.items():
            if isinstance(v, np.ndarray):
                serializable_data[k] = v.tolist()
            else:
                serializable_data[k] = v
        json.dump(serializable_data, f)


def load_avatar_data(avatar_id: str) -> dict:
    """Load avatar data."""
    path = get_avatar_storage_path(avatar_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Avatar not found: {avatar_id}")
    with open(path, 'r') as f:
        return json.load(f)


# ============================================
# Endpoints
# ============================================

@router.post("/generate", response_model=AvatarResponse)
async def generate_avatar(request: AvatarRequest):
    """
    Generate 3D avatar from image or measurements.

    Uses SHAPY to estimate body shape parameters (betas) and
    SMPL-X to generate the 3D mesh.
    """
    start_time = time.time()
    avatar_id = str(uuid.uuid4())

    try:
        # Import models
        from models.avatar import ShapyModel, SMPLXModel

        if request.image_url or request.image_base64:
            # Generate from image
            logger.info(f"Generating avatar from image: {avatar_id}")

            image = load_image(request.image_url, request.image_base64)

            # Estimate body shape
            shapy = ShapyModel(device="cuda")
            estimation = shapy.estimate_from_image(image)

            betas = estimation['betas']
            measurements = estimation['measurements']
            confidence = estimation.get('confidence', 0.0)

        elif request.measurements:
            # Generate from measurements
            logger.info(f"Generating avatar from measurements: {avatar_id}")

            shapy = ShapyModel(device="cuda")
            estimation = shapy.estimate_from_measurements(
                height=request.measurements.height,
                weight=request.measurements.weight,
                chest=request.measurements.chest,
                waist=request.measurements.waist,
                hips=request.measurements.hips,
                gender=request.measurements.gender,
            )

            betas = estimation['betas']
            measurements = {
                'height': request.measurements.height,
                'weight': request.measurements.weight or 70.0,
                'chest': request.measurements.chest or 95.0,
                'waist': request.measurements.waist or 80.0,
                'hips': request.measurements.hips or 95.0,
            }
            confidence = 1.0  # Full confidence for direct measurements

        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide either image or measurements"
            )

        # Generate mesh
        gender = request.measurements.gender if request.measurements else "neutral"
        smplx = SMPLXModel(gender=gender, device="cuda")

        output_dir = get_output_dir("avatars")
        mesh_filename = f"avatar_{avatar_id}.{request.output_format}"
        mesh_path = output_dir / mesh_filename

        smplx.export_mesh(
            betas=np.array(betas),
            output_path=str(mesh_path),
            format=request.output_format
        )

        # Save avatar data for later garment simulation
        save_avatar_data(avatar_id, {
            'betas': betas,
            'gender': gender,
            'measurements': measurements,
        })

        mesh_url = f"{settings.cdn_base_url}/outputs/avatars/{mesh_filename}"

        processing_time = time.time() - start_time
        logger.success(f"Avatar generated in {processing_time:.2f}s: {avatar_id}")

        return AvatarResponse(
            success=True,
            avatar_id=avatar_id,
            mesh_url=mesh_url,
            betas=betas.tolist() if isinstance(betas, np.ndarray) else list(betas),
            measurements=measurements,
            processing_time_seconds=round(processing_time, 3),
            confidence=confidence,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/garment/simulate", response_model=GarmentSimulationResponse)
async def simulate_garment(request: GarmentSimulationRequest):
    """
    Simulate garment on an existing avatar.

    Uses SNUG for neural garment simulation.
    """
    start_time = time.time()

    try:
        # Load avatar data
        avatar_data = load_avatar_data(request.avatar_id)
        betas = np.array(avatar_data['betas'])
        gender = avatar_data.get('gender', 'neutral')

        logger.info(f"Simulating {request.garment_type} on avatar {request.avatar_id}")

        # Import models
        from models.avatar import SMPLXModel
        from models.garment import SnugModel

        # Generate body mesh
        smplx = SMPLXModel(gender=gender, device="cuda")
        pose = np.array(request.pose) if request.pose else None
        body_result = smplx.forward(betas=betas, body_pose=pose)
        body_vertices = body_result['vertices'][0]  # Remove batch dimension

        # Simulate garment
        snug = SnugModel(garment_type=request.garment_type)
        garment_result = snug.simulate(body_vertices, pose)

        # Save garment mesh
        output_dir = get_output_dir("garments")
        garment_id = str(uuid.uuid4())
        garment_filename = f"garment_{garment_id}.{request.output_format}"
        garment_path = output_dir / garment_filename

        snug.export_mesh(
            garment_result['vertices'],
            garment_result['faces'],
            str(garment_path),
            format=request.output_format
        )

        garment_url = f"{settings.cdn_base_url}/outputs/garments/{garment_filename}"

        # Optionally create combined mesh
        combined_url = None
        if request.output_format in ['glb', 'obj']:
            try:
                import trimesh

                body_mesh = trimesh.Trimesh(
                    vertices=body_vertices,
                    faces=body_result['faces']
                )
                garment_mesh = trimesh.Trimesh(
                    vertices=garment_result['vertices'],
                    faces=garment_result['faces']
                )

                # Combine meshes
                combined = trimesh.util.concatenate([body_mesh, garment_mesh])

                combined_filename = f"combined_{garment_id}.{request.output_format}"
                combined_path = output_dir / combined_filename
                combined.export(str(combined_path), file_type=request.output_format)

                combined_url = f"{settings.cdn_base_url}/outputs/garments/{combined_filename}"

            except Exception as e:
                logger.warning(f"Failed to create combined mesh: {e}")

        processing_time = time.time() - start_time
        logger.success(f"Garment simulated in {processing_time:.2f}s")

        return GarmentSimulationResponse(
            success=True,
            garment_mesh_url=garment_url,
            combined_mesh_url=combined_url,
            animation_url=None,  # TODO: Implement animation
            processing_time_seconds=round(processing_time, 3),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Garment simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/combined", response_model=CombinedAvatarResponse)
async def generate_avatar_with_garment(request: CombinedAvatarRequest):
    """
    Generate avatar with garment in one request.

    Combines SHAPY body estimation, SMPL-X mesh generation,
    and SNUG garment simulation.
    """
    start_time = time.time()

    try:
        # First generate avatar
        avatar_request = AvatarRequest(
            image_url=request.person_image_url,
            image_base64=request.person_image_base64,
            measurements=request.measurements,
            output_format=request.output_format,
        )

        avatar_response = await generate_avatar(avatar_request)

        if not avatar_response.success:
            raise HTTPException(status_code=500, detail="Avatar generation failed")

        # Then simulate garment
        garment_request = GarmentSimulationRequest(
            avatar_id=avatar_response.avatar_id,
            garment_type=request.garment_type,
            output_format=request.output_format,
        )

        garment_response = await simulate_garment(garment_request)

        if not garment_response.success:
            raise HTTPException(status_code=500, detail="Garment simulation failed")

        processing_time = time.time() - start_time
        logger.success(f"Combined avatar+garment generated in {processing_time:.2f}s")

        return CombinedAvatarResponse(
            success=True,
            avatar_mesh_url=avatar_response.mesh_url,
            garment_mesh_url=garment_response.garment_mesh_url,
            combined_mesh_url=garment_response.combined_mesh_url or garment_response.garment_mesh_url,
            betas=avatar_response.betas,
            measurements=avatar_response.measurements,
            processing_time_seconds=round(processing_time, 3),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Combined generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/garments/types")
async def list_garment_types():
    """List available garment types for simulation."""
    from models.garment.garment_types import AVAILABLE_GARMENTS

    return {
        "garments": [
            {
                "type": key,
                "name": config.name,
                "material_stiffness": config.material_stiffness,
            }
            for key, config in AVAILABLE_GARMENTS.items()
        ]
    }


@router.get("/{avatar_id}")
async def get_avatar(avatar_id: str):
    """Get avatar information by ID."""
    try:
        avatar_data = load_avatar_data(avatar_id)

        output_dir = get_output_dir("avatars")

        # Find mesh file
        mesh_files = list(output_dir.glob(f"avatar_{avatar_id}.*"))

        mesh_url = None
        if mesh_files:
            mesh_filename = mesh_files[0].name
            mesh_url = f"{settings.cdn_base_url}/outputs/avatars/{mesh_filename}"

        return {
            "avatar_id": avatar_id,
            "betas": avatar_data.get('betas'),
            "gender": avatar_data.get('gender'),
            "measurements": avatar_data.get('measurements'),
            "mesh_url": mesh_url,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{avatar_id}")
async def delete_avatar(avatar_id: str):
    """Delete avatar and associated files."""
    try:
        # Delete data file
        data_path = get_avatar_storage_path(avatar_id)
        if data_path.exists():
            data_path.unlink()

        # Delete mesh files
        output_dir = get_output_dir("avatars")
        for mesh_file in output_dir.glob(f"avatar_{avatar_id}.*"):
            mesh_file.unlink()

        logger.info(f"Deleted avatar: {avatar_id}")

        return {"success": True, "message": f"Avatar {avatar_id} deleted"}

    except Exception as e:
        logger.error(f"Failed to delete avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))
