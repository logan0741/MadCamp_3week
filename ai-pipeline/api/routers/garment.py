"""
Garment processing router.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import base64
import time
import uuid
from io import BytesIO
from typing import Dict, Optional

import httpx
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from loguru import logger
from PIL import Image

from config import settings
from api.schemas.garment import (
    GarmentProcessRequest,
    GarmentProcessResponse,
    GarmentAsyncResponse,
    GarmentSizesResponse,
)
from models.garment import GarmentTextureProcessor
from models.scaling import GarmentSizeScaler
from models.smplx import StandardMannequin
from models.export import export_dressed_mannequin


router = APIRouter()

ALLOWED_GARMENT_TYPES = {"top", "pants", "dress", "skirt"}


# ============================================
# Helper Functions
# ============================================

def load_image_from_url(url: str) -> Image.Image:
    response = httpx.get(url, timeout=settings.backend_timeout_seconds)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))


def load_image_from_base64(base64_str: str) -> Image.Image:
    image_data = base64.b64decode(base64_str)
    return Image.open(BytesIO(image_data))


def _safe_filename(prefix: str, suffix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}{suffix}"


def _save_image(image: Image.Image, subdir: str, prefix: str) -> str:
    output_dir = settings.output_dir / "garment" / subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = _safe_filename(prefix, ".png")
    filepath = output_dir / filename
    image.save(filepath, format="PNG")

    return f"{settings.cdn_base_url}/outputs/garment/{subdir}/{filename}"


def _save_glb(path: Path) -> str:
    rel_path = path.relative_to(settings.output_dir)
    return f"{settings.cdn_base_url}/outputs/{rel_path.as_posix()}"


def _backend_sizes_url(product_id: int) -> str:
    base = settings.backend_base_url.rstrip("/")
    endpoint = settings.backend_size_endpoint.format(product_id=product_id)
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    return f"{base}{endpoint}"


def _select_size_measurements(
    sizes: Dict[str, Dict[str, float]],
    size_label: Optional[str],
) -> Dict[str, float]:
    if not sizes:
        return {}

    if size_label is None:
        return next(iter(sizes.values()))

    normalized = size_label.strip().upper()
    if normalized in sizes:
        return sizes[normalized]

    if size_label in sizes:
        return sizes[size_label]

    return next(iter(sizes.values()))


async def get_product_sizes(product_id: int) -> Dict[str, Dict[str, float]]:
    url = _backend_sizes_url(product_id)
    async with httpx.AsyncClient(timeout=settings.backend_timeout_seconds) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    if isinstance(data, dict) and "sizes" in data:
        return data["sizes"]
    if isinstance(data, dict):
        return data
    return {}


async def run_garment_pipeline(
    front_img: Image.Image,
    back_img: Image.Image,
    garment_type: str,
    product_id: int,
    size_label: Optional[str],
    height_cm: float,
    weight_kg: float,
) -> GarmentProcessResponse:
    garment_type = garment_type.strip().lower()
    if garment_type not in ALLOWED_GARMENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported garment_type")

    start_time = time.time()

    texture_processor = GarmentTextureProcessor()
    textures = texture_processor.process(front_img, back_img, garment_type)

    front_url = _save_image(textures["front_texture"], "textures", "front")
    back_url = _save_image(textures["back_texture"], "textures", "back")
    atlas_url = _save_image(textures["uv_atlas"], "textures", "atlas")

    try:
        sizes = await get_product_sizes(product_id)
    except Exception as e:
        logger.warning(f"Failed to fetch sizes from backend: {e}")
        sizes = {}

    target_cm = _select_size_measurements(sizes, size_label)

    scaler = GarmentSizeScaler()
    template_mesh = scaler.load_template_mesh(garment_type)
    scaled_mesh = scaler.scale_mesh(template_mesh, garment_type, target_cm)

    mannequin = StandardMannequin()
    mannequin_mesh = mannequin.get_mesh(height_cm=height_cm, weight_kg=weight_kg)

    output_dir = settings.output_dir / "garment" / "glb"
    output_dir.mkdir(parents=True, exist_ok=True)
    glb_filename = _safe_filename("garment", ".glb")
    glb_path = output_dir / glb_filename

    export_dressed_mannequin(
        mannequin_mesh=mannequin_mesh,
        garment_mesh=scaled_mesh,
        garment_texture=textures["uv_atlas"],
        output_path=glb_path,
    )

    glb_url = _save_glb(glb_path)

    processing_time = time.time() - start_time

    return GarmentProcessResponse(
        success=True,
        garment_glb_url=glb_url,
        uv_atlas_url=atlas_url,
        front_texture_url=front_url,
        back_texture_url=back_url,
        size_applied=size_label,
        processing_time_seconds=round(processing_time, 3),
    )


# ============================================
# Endpoints
# ============================================

@router.post("/process", response_model=GarmentProcessResponse)
async def process_garment_upload(
    front_image: UploadFile = File(..., description="Front image"),
    back_image: UploadFile = File(..., description="Back image"),
    garment_type: str = Form(...),
    product_id: int = Form(...),
    size: str = Form("M"),
    height_cm: float = Form(170),
    weight_kg: float = Form(65),
):
    try:
        front_img = Image.open(BytesIO(await front_image.read()))
        back_img = Image.open(BytesIO(await back_image.read()))

        return await run_garment_pipeline(
            front_img=front_img,
            back_img=back_img,
            garment_type=garment_type,
            product_id=product_id,
            size_label=size,
            height_cm=height_cm,
            weight_kg=weight_kg,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Garment processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-async", response_model=GarmentAsyncResponse)
async def process_garment_async(request: GarmentProcessRequest):
    try:
        from workers.tasks.garment_tasks import process_garment_async as task_fn

        task = task_fn.delay(
            front_image_url=request.front_image_url,
            back_image_url=request.back_image_url,
            front_image_base64=request.front_image_base64,
            back_image_base64=request.back_image_base64,
            garment_type=request.garment_type,
            product_id=request.product_id,
            size=request.size,
            height_cm=request.height_cm,
            weight_kg=request.weight_kg,
            callback_url=request.callback_url,
        )

        return GarmentAsyncResponse(
            task_id=task.id,
            status_url=f"/api/garment/task/{task.id}",
        )
    except Exception as e:
        logger.error(f"Failed to submit garment task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_garment_task_status(task_id: str):
    try:
        from celery.result import AsyncResult

        task_result = AsyncResult(task_id)
        response = {
            "task_id": task_id,
            "status": task_result.state,
        }

        if task_result.state == "PENDING":
            response["message"] = "Task is waiting in queue"
        elif task_result.state == "PROGRESS":
            info = task_result.info or {}
            response.update({
                "progress": info.get("progress", 0),
                "current": info.get("current", 0),
                "total": info.get("total", 0),
                "message": info.get("message", "Processing..."),
            })
        elif task_result.state == "SUCCESS":
            response["result"] = task_result.result
            response["message"] = "Task completed successfully"
        elif task_result.state == "FAILURE":
            response["error"] = str(task_result.info)
            response["message"] = "Task failed"
        else:
            response["message"] = f"Unknown state: {task_result.state}"

        return response
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sizes/{product_id}", response_model=GarmentSizesResponse)
async def get_sizes(product_id: int):
    try:
        sizes = await get_product_sizes(product_id)
        return GarmentSizesResponse(product_id=product_id, sizes=sizes)
    except Exception as e:
        logger.error(f"Failed to fetch sizes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
