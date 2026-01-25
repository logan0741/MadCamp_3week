"""
VTON Celery Tasks
Asynchronous virtual try-on tasks.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
import uuid
from typing import Optional, Dict
from PIL import Image
from io import BytesIO
import httpx
import base64

from loguru import logger
from celery import Task

from workers.celery_app import celery_app
from workers.vram_manager import VRAMContext
from models.vton.idm_vton import get_vton_model
from models.vton import VTONPreprocessor, VTONPostprocessor
from config import settings


# Initialize processors
preprocessor = VTONPreprocessor(
    target_size=(settings.vton_image_size, settings.vton_image_size)
)
postprocessor = VTONPostprocessor()


# ============================================
# Helper Functions
# ============================================

def load_image_from_url(url: str) -> Image.Image:
    """Download image from URL."""
    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))


def load_image_from_base64(base64_str: str) -> Image.Image:
    """Decode base64 image."""
    image_data = base64.b64decode(base64_str)
    return Image.open(BytesIO(image_data))


def save_result_image(image: Image.Image, task_id: str) -> str:
    """
    Save result image to output directory.

    Args:
        image: PIL Image
        task_id: Task identifier

    Returns:
        URL to saved image
    """
    # Create output directory
    output_dir = settings.output_dir / "vton" / "async"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    filename = f"result_{task_id}.png"
    filepath = output_dir / filename

    # Save image
    image.save(filepath, format="PNG", quality=95)

    # Return URL
    url = f"{settings.cdn_base_url}/outputs/vton/async/{filename}"
    return url


# ============================================
# Custom Task Class with Progress
# ============================================

class VTONTask(Task):
    """Custom Celery task with progress tracking."""

    def update_progress(self, current: int, total: int, message: str = ""):
        """Update task progress."""
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current,
                "total": total,
                "progress": int((current / total) * 100),
                "message": message,
            }
        )


# ============================================
# VTON Async Tasks
# ============================================

@celery_app.task(
    bind=True,
    base=VTONTask,
    name="workers.tasks.vton_tasks.process_vton_async",
    max_retries=3,
    default_retry_delay=60,
)
def process_vton_async(
    self,
    person_image_url: Optional[str] = None,
    garment_image_url: Optional[str] = None,
    person_image_base64: Optional[str] = None,
    garment_image_base64: Optional[str] = None,
    num_inference_steps: int = 50,
    guidance_scale: float = 7.5,
    seed: Optional[int] = None,
    enhance_output: bool = True,
    restore_face: bool = True,
    callback_url: Optional[str] = None,
) -> Dict:
    """
    Asynchronous virtual try-on task.

    Args:
        person_image_url: URL to person image
        garment_image_url: URL to garment image
        person_image_base64: Base64 encoded person image
        garment_image_base64: Base64 encoded garment image
        num_inference_steps: Number of diffusion steps
        guidance_scale: CFG scale
        seed: Random seed
        enhance_output: Apply post-processing
        restore_face: Restore original face
        callback_url: Webhook URL for completion notification

    Returns:
        Dictionary with result URL and metadata
    """
    task_id = self.request.id
    start_time = time.time()

    logger.info(f"Starting VTON task {task_id}")

    try:
        # Update progress: Loading images
        self.update_progress(1, 5, "Loading images...")

        # Load person image
        if person_image_url:
            person_img = load_image_from_url(person_image_url)
        elif person_image_base64:
            person_img = load_image_from_base64(person_image_base64)
        else:
            raise ValueError("Either person_image_url or person_image_base64 required")

        # Load garment image
        if garment_image_url:
            garment_img = load_image_from_url(garment_image_url)
        elif garment_image_base64:
            garment_img = load_image_from_base64(garment_image_base64)
        else:
            raise ValueError("Either garment_image_url or garment_image_base64 required")

        # Update progress: Preprocessing
        self.update_progress(2, 5, "Preprocessing images...")

        person_preprocessed = preprocessor.process_person_image(person_img)
        garment_preprocessed = preprocessor.process_garment_image(garment_img)

        # Update progress: Running inference
        self.update_progress(3, 5, "Running VTON inference...")

        # Use VRAM context manager
        with VRAMContext(task_id, "VTON", device_id=0):
            vton_model = get_vton_model()

            output_img = vton_model(
                person_image=person_preprocessed,
                garment_image=garment_preprocessed,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                seed=seed,
            )

        # Update progress: Post-processing
        self.update_progress(4, 5, "Enhancing output...")

        if enhance_output:
            output_img = postprocessor.process(
                output_img,
                original_person_image=person_preprocessed if restore_face else None,
            )

        # Save result
        result_url = save_result_image(output_img, task_id)

        # Update progress: Complete
        self.update_progress(5, 5, "Complete")

        processing_time = time.time() - start_time

        result = {
            "success": True,
            "task_id": task_id,
            "result_url": result_url,
            "processing_time_seconds": round(processing_time, 3),
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
        }

        # Send webhook callback if provided
        if callback_url:
            try:
                httpx.post(callback_url, json=result, timeout=10.0)
                logger.info(f"Webhook sent to {callback_url}")
            except Exception as e:
                logger.warning(f"Failed to send webhook: {e}")

        logger.success(f"VTON task {task_id} completed in {processing_time:.2f}s")

        return result

    except Exception as exc:
        logger.error(f"VTON task {task_id} failed: {exc}", exc_info=True)

        # Retry on certain errors
        if isinstance(exc, (httpx.HTTPError, ConnectionError)):
            raise self.retry(exc=exc)

        # Return error result
        return {
            "success": False,
            "task_id": task_id,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }


@celery_app.task(
    bind=True,
    name="workers.tasks.vton_tasks.process_vton_batch_async",
    max_retries=1,
)
def process_vton_batch_async(
    self,
    requests: list[dict],
    callback_url: Optional[str] = None,
) -> Dict:
    """
    Batch virtual try-on task.

    Args:
        requests: List of VTON request dictionaries
        callback_url: Webhook URL for completion notification

    Returns:
        Dictionary with batch results
    """
    task_id = self.request.id
    start_time = time.time()

    logger.info(f"Starting batch VTON task {task_id} with {len(requests)} items")

    results = []
    failed_count = 0

    for idx, request_params in enumerate(requests):
        logger.info(f"Processing batch item {idx + 1}/{len(requests)}")

        try:
            # Process individual request (synchronous within task)
            result = process_vton_async(
                person_image_url=request_params.get("person_image_url"),
                garment_image_url=request_params.get("garment_image_url"),
                person_image_base64=request_params.get("person_image_base64"),
                garment_image_base64=request_params.get("garment_image_base64"),
                num_inference_steps=request_params.get("num_inference_steps", 50),
                guidance_scale=request_params.get("guidance_scale", 7.5),
                seed=request_params.get("seed"),
                enhance_output=request_params.get("enhance_output", True),
                restore_face=request_params.get("restore_face", True),
            )

            results.append(result)

            if not result.get("success"):
                failed_count += 1

        except Exception as e:
            logger.error(f"Batch item {idx + 1} failed: {e}")
            results.append({
                "success": False,
                "error": str(e),
                "item_index": idx,
            })
            failed_count += 1

    total_time = time.time() - start_time

    batch_result = {
        "success": failed_count == 0,
        "task_id": task_id,
        "total_items": len(requests),
        "successful_items": len(requests) - failed_count,
        "failed_items": failed_count,
        "results": results,
        "total_processing_time_seconds": round(total_time, 3),
    }

    # Send webhook callback
    if callback_url:
        try:
            httpx.post(callback_url, json=batch_result, timeout=10.0)
        except Exception as e:
            logger.warning(f"Failed to send webhook: {e}")

    logger.success(
        f"Batch VTON task {task_id} completed: "
        f"{len(requests) - failed_count}/{len(requests)} successful"
    )

    return batch_result


# ============================================
# Utility Tasks
# ============================================

@celery_app.task(name="workers.tasks.vton_tasks.cleanup_old_results")
def cleanup_old_results(max_age_hours: int = 24):
    """
    Clean up old result files.

    Args:
        max_age_hours: Maximum age in hours before deletion
    """
    import time
    from pathlib import Path

    output_dir = settings.output_dir / "vton" / "async"

    if not output_dir.exists():
        return {"deleted": 0, "message": "Output directory does not exist"}

    deleted_count = 0
    cutoff_time = time.time() - (max_age_hours * 3600)

    for file_path in output_dir.glob("*.png"):
        if file_path.stat().st_mtime < cutoff_time:
            file_path.unlink()
            deleted_count += 1

    logger.info(f"Cleaned up {deleted_count} old result files")

    return {
        "deleted": deleted_count,
        "cutoff_hours": max_age_hours,
    }
