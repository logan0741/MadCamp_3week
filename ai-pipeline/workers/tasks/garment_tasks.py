"""
Garment processing Celery tasks.
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
from PIL import Image
from loguru import logger
from celery import Task

from config import settings
from workers.celery_app import celery_app
from models.garment import GarmentTextureProcessor
from models.scaling import GarmentSizeScaler
from models.smplx import StandardMannequin
from models.export import export_dressed_mannequin


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


def get_product_sizes_sync(product_id: int) -> Dict[str, Dict[str, float]]:
    url = _backend_sizes_url(product_id)
    response = httpx.get(url, timeout=settings.backend_timeout_seconds)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and "sizes" in data:
        return data["sizes"]
    if isinstance(data, dict):
        return data
    return {}


# ============================================
# Custom Task Class with Progress
# ============================================

class GarmentTask(Task):
    """Custom task with progress tracking."""

    def update_progress(self, current: int, total: int, message: str = ""):
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current,
                "total": total,
                "progress": int((current / total) * 100),
                "message": message,
            },
        )


# ============================================
# Garment Async Task
# ============================================

@celery_app.task(
    bind=True,
    base=GarmentTask,
    name="workers.tasks.garment_tasks.process_garment_async",
    max_retries=2,
    default_retry_delay=30,
)
def process_garment_async(
    self,
    front_image_url: Optional[str] = None,
    back_image_url: Optional[str] = None,
    front_image_base64: Optional[str] = None,
    back_image_base64: Optional[str] = None,
    garment_type: str = "top",
    product_id: int = 0,
    size: Optional[str] = "M",
    height_cm: float = 170,
    weight_kg: float = 65,
    callback_url: Optional[str] = None,
) -> Dict:
    task_id = self.request.id
    start_time = time.time()

    garment_type = garment_type.strip().lower()
    if garment_type not in ALLOWED_GARMENT_TYPES:
        raise ValueError("Unsupported garment_type")

    try:
        self.update_progress(1, 5, "Loading images...")

        if front_image_url:
            front_img = load_image_from_url(front_image_url)
        elif front_image_base64:
            front_img = load_image_from_base64(front_image_base64)
        else:
            raise ValueError("Front image required")

        if back_image_url:
            back_img = load_image_from_url(back_image_url)
        elif back_image_base64:
            back_img = load_image_from_base64(back_image_base64)
        else:
            raise ValueError("Back image required")

        self.update_progress(2, 5, "Processing textures...")
        texture_processor = GarmentTextureProcessor()
        textures = texture_processor.process(front_img, back_img, garment_type)

        front_url = _save_image(textures["front_texture"], "textures", "front")
        back_url = _save_image(textures["back_texture"], "textures", "back")
        atlas_url = _save_image(textures["uv_atlas"], "textures", "atlas")

        self.update_progress(3, 5, "Scaling mesh...")
        try:
            sizes = get_product_sizes_sync(product_id)
        except Exception as e:
            logger.warning(f"Failed to fetch sizes from backend: {e}")
            sizes = {}

        target_cm = _select_size_measurements(sizes, size)

        scaler = GarmentSizeScaler()
        template_mesh = scaler.load_template_mesh(garment_type)
        scaled_mesh = scaler.scale_mesh(template_mesh, garment_type, target_cm)

        self.update_progress(4, 5, "Generating mannequin and exporting...")
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

        self.update_progress(5, 5, "Complete")
        processing_time = time.time() - start_time

        result = {
            "success": True,
            "task_id": task_id,
            "garment_glb_url": glb_url,
            "uv_atlas_url": atlas_url,
            "front_texture_url": front_url,
            "back_texture_url": back_url,
            "size_applied": size,
            "processing_time_seconds": round(processing_time, 3),
        }

        if callback_url:
            try:
                httpx.post(callback_url, json=result, timeout=10.0)
                logger.info(f"Webhook sent to {callback_url}")
            except Exception as e:
                logger.warning(f"Failed to send webhook: {e}")

        return result

    except Exception as e:
        logger.error(f"Garment task failed: {e}", exc_info=True)
        raise
