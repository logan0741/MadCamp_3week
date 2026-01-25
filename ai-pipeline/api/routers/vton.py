"""
VTON Router
Endpoints for virtual try-on functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
import time
import uuid
import base64
from io import BytesIO
from PIL import Image
from loguru import logger

from config import settings
from api.schemas.vton import (
    VTONRequest,
    VTONResponse,
    VTONBatchRequest,
    VTONBatchResponse,
)
from models.vton.idm_vton import get_vton_model
from models.vton import VTONPreprocessor, VTONPostprocessor


router = APIRouter()

# Initialize preprocessor and postprocessor
preprocessor = VTONPreprocessor(
    target_size=(settings.vton_image_size, settings.vton_image_size)
)
postprocessor = VTONPostprocessor()


# ============================================
# Helper Functions
# ============================================

def load_image_from_url(url: str) -> Image.Image:
    """Download image from URL."""
    import httpx

    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()

    return Image.open(BytesIO(response.content))


def load_image_from_base64(base64_str: str) -> Image.Image:
    """Decode base64 image."""
    image_data = base64.b64decode(base64_str)
    return Image.open(BytesIO(image_data))


def save_result_image(image: Image.Image, prefix: str = "vton") -> str:
    """
    Save result image to output directory.

    Args:
        image: PIL Image
        prefix: Filename prefix

    Returns:
        URL to saved image
    """
    # Create output directory if needed
    output_dir = settings.output_dir / "vton"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    filename = f"{prefix}_{uuid.uuid4()}.png"
    filepath = output_dir / filename

    # Save image
    image.save(filepath, format="PNG", quality=95)

    # Return URL
    url = f"{settings.cdn_base_url}/outputs/vton/{filename}"
    return url


# ============================================
# Endpoints
# ============================================

@router.post("/try-on", response_model=VTONResponse)
async def virtual_try_on(request: VTONRequest):
    """
    Perform virtual try-on inference.

    This endpoint runs synchronously and returns the result immediately.
    For long-running requests, use the async endpoint instead.
    """
    start_time = time.time()

    try:
        # Load person image
        if request.person_image_url:
            person_img = load_image_from_url(request.person_image_url)
        elif request.person_image_base64:
            person_img = load_image_from_base64(request.person_image_base64)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either person_image_url or person_image_base64 must be provided"
            )

        # Load garment image
        if request.garment_image_url:
            garment_img = load_image_from_url(request.garment_image_url)
        elif request.garment_image_base64:
            garment_img = load_image_from_base64(request.garment_image_base64)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either garment_image_url or garment_image_base64 must be provided"
            )

        # Preprocess images
        logger.info("Preprocessing images...")
        person_preprocessed = preprocessor.process_person_image(person_img)
        garment_preprocessed = preprocessor.process_garment_image(garment_img)

        # Run VTON inference
        logger.info("Running VTON inference...")
        vton_model = get_vton_model()

        output_img = vton_model(
            person_image=person_preprocessed,
            garment_image=garment_preprocessed,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            seed=request.seed,
        )

        # Post-process if enabled
        if request.enhance_output:
            logger.info("Post-processing output...")
            output_img = postprocessor.process(
                output_img,
                original_person_image=person_preprocessed if request.restore_face else None,
            )

        # Save result
        result_url = save_result_image(output_img)

        # Get VRAM stats
        vram_stats = vton_model.get_vram_usage()

        processing_time = time.time() - start_time

        logger.success(f"VTON completed in {processing_time:.2f}s")

        return VTONResponse(
            success=True,
            result_url=result_url,
            processing_time_seconds=round(processing_time, 3),
            vram_allocated_mb=vram_stats.get("allocated_mb"),
        )

    except Exception as e:
        logger.error(f"VTON failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/try-on/upload", response_model=VTONResponse)
async def virtual_try_on_upload(
    person_image: UploadFile = File(..., description="Person image file"),
    garment_image: UploadFile = File(..., description="Garment image file"),
    num_inference_steps: int = 50,
    guidance_scale: float = 7.5,
    seed: Optional[int] = None,
    enhance_output: bool = True,
    restore_face: bool = True,
):
    """
    Virtual try-on with file upload.

    Upload images directly instead of providing URLs.
    """
    start_time = time.time()

    try:
        # Load images from upload
        person_img = Image.open(BytesIO(await person_image.read()))
        garment_img = Image.open(BytesIO(await garment_image.read()))

        # Validate formats
        if person_img.format not in ["JPEG", "PNG"]:
            raise HTTPException(status_code=400, detail="Person image must be JPEG or PNG")
        if garment_img.format not in ["JPEG", "PNG"]:
            raise HTTPException(status_code=400, detail="Garment image must be JPEG or PNG")

        # Preprocess
        person_preprocessed = preprocessor.process_person_image(person_img)
        garment_preprocessed = preprocessor.process_garment_image(garment_img)

        # Run VTON
        vton_model = get_vton_model()
        output_img = vton_model(
            person_image=person_preprocessed,
            garment_image=garment_preprocessed,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )

        # Post-process
        if enhance_output:
            output_img = postprocessor.process(
                output_img,
                original_person_image=person_preprocessed if restore_face else None,
            )

        # Save result
        result_url = save_result_image(output_img)

        # VRAM stats
        vram_stats = vton_model.get_vram_usage()

        processing_time = time.time() - start_time

        return VTONResponse(
            success=True,
            result_url=result_url,
            processing_time_seconds=round(processing_time, 3),
            vram_allocated_mb=vram_stats.get("allocated_mb"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VTON upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/try-on/batch", response_model=VTONBatchResponse)
async def virtual_try_on_batch(request: VTONBatchRequest):
    """
    Batch virtual try-on.

    Process multiple try-on requests sequentially.
    For large batches, use the async endpoint instead.
    """
    start_time = time.time()

    results = []

    for idx, req in enumerate(request.requests):
        logger.info(f"Processing batch item {idx + 1}/{len(request.requests)}")

        try:
            # Process single request
            result = await virtual_try_on(req)
            results.append(result)

        except Exception as e:
            logger.error(f"Batch item {idx + 1} failed: {e}")
            # Continue with other items
            results.append(
                VTONResponse(
                    success=False,
                    result_url="",
                    processing_time_seconds=0.0,
                )
            )

    total_time = time.time() - start_time

    return VTONBatchResponse(
        success=True,
        results=results,
        total_processing_time_seconds=round(total_time, 3),
    )


@router.get("/model/status")
async def model_status():
    """Get VTON model status and VRAM usage."""
    vton_model = get_vton_model()

    return {
        "model_loaded": vton_model.is_loaded,
        "model_id": vton_model.model_id,
        "device": vton_model.device,
        "vram_stats": vton_model.get_vram_usage(),
        "estimated_inference_time_seconds": vton_model.estimate_inference_time(
            settings.vton_num_inference_steps
        ),
    }


@router.post("/model/reload")
async def reload_model():
    """Reload VTON model (useful after CUDA out of memory errors)."""
    try:
        vton_model = get_vton_model()
        vton_model.unload_model()
        vton_model.load_model()

        return {"success": True, "message": "Model reloaded successfully"}

    except Exception as e:
        logger.error(f"Model reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Async Endpoints (Celery-based)
# ============================================

@router.post("/try-on/async")
async def virtual_try_on_async(request: VTONRequest):
    """
    Asynchronous virtual try-on.

    Submit a task and get task_id immediately.
    Check status at /tasks/{task_id}
    """
    try:
        # Import Celery task
        from workers.tasks.vton_tasks import process_vton_async

        # Submit task to Celery
        task = process_vton_async.delay(
            person_image_url=request.person_image_url,
            garment_image_url=request.garment_image_url,
            person_image_base64=request.person_image_base64,
            garment_image_base64=request.garment_image_base64,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            seed=request.seed,
            enhance_output=request.enhance_output,
            restore_face=request.restore_face,
        )

        logger.info(f"Submitted async VTON task: {task.id}")

        return {
            "success": True,
            "task_id": task.id,
            "status_url": f"/api/vton/tasks/{task.id}",
            "message": "Task submitted successfully",
        }

    except Exception as e:
        logger.error(f"Failed to submit async task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/try-on/batch-async")
async def virtual_try_on_batch_async(request: VTONBatchRequest):
    """
    Asynchronous batch virtual try-on.

    Submit batch task and get task_id immediately.
    """
    try:
        from workers.tasks.vton_tasks import process_vton_batch_async

        # Convert pydantic models to dicts
        requests_data = [req.dict() for req in request.requests]

        # Submit batch task
        task = process_vton_batch_async.delay(requests=requests_data)

        logger.info(f"Submitted async batch VTON task: {task.id} ({len(requests_data)} items)")

        return {
            "success": True,
            "task_id": task.id,
            "status_url": f"/api/vton/tasks/{task.id}",
            "batch_size": len(requests_data),
            "message": "Batch task submitted successfully",
        }

    except Exception as e:
        logger.error(f"Failed to submit batch async task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Get status of async VTON task.

    Returns:
        - PENDING: Task waiting in queue
        - PROGRESS: Task is running (includes progress percentage)
        - SUCCESS: Task completed successfully
        - FAILURE: Task failed
    """
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
            # Get progress info
            info = task_result.info or {}
            response["progress"] = info.get("progress", 0)
            response["current"] = info.get("current", 0)
            response["total"] = info.get("total", 0)
            response["message"] = info.get("message", "Processing...")

        elif task_result.state == "SUCCESS":
            # Get result data
            result = task_result.result
            response["result"] = result
            response["message"] = "Task completed successfully"

        elif task_result.state == "FAILURE":
            # Get error info
            response["error"] = str(task_result.info)
            response["message"] = "Task failed"

        else:
            response["message"] = f"Unknown state: {task_result.state}"

        return response

    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running or pending task.
    """
    try:
        from celery.result import AsyncResult

        task_result = AsyncResult(task_id)

        if task_result.state in ["PENDING", "PROGRESS"]:
            task_result.revoke(terminate=True)
            logger.info(f"Cancelled task: {task_id}")

            return {
                "success": True,
                "task_id": task_id,
                "message": "Task cancelled successfully",
            }
        else:
            return {
                "success": False,
                "task_id": task_id,
                "status": task_result.state,
                "message": f"Cannot cancel task in state: {task_result.state}",
            }

    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(status_code=500, detail=str(e))
