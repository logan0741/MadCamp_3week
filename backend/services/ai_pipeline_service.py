"""
AI Pipeline integration service.
"""
from __future__ import annotations

import json
from typing import Dict, Optional, Tuple

import httpx

from core.config import settings
from domain.entities import Product


def select_front_back_images(product: Product) -> Tuple[Optional[str], Optional[str]]:
    """
    Pick front/back image URLs from product data.
    """
    urls = []
    if product.image_urls:
        try:
            urls = json.loads(product.image_urls)
        except Exception:
            urls = []

    if not urls and product.thumbnail_url:
        urls = [product.thumbnail_url]

    front = urls[0] if urls else None
    back = urls[1] if len(urls) > 1 else front
    return front, back


async def submit_garment_task(
    front_url: str,
    back_url: str,
    garment_type: str,
    product_id: int,
    size: str = "M",
    height_cm: float = 170,
    weight_kg: float = 65,
    callback_url: Optional[str] = None,
) -> Dict:
    """
    Submit garment generation to AI pipeline.
    """
    payload = {
        "front_image_url": front_url,
        "back_image_url": back_url,
        "garment_type": garment_type,
        "product_id": product_id,
        "size": size,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "callback_url": callback_url,
    }

    url = f"{settings.AI_PIPELINE_BASE_URL.rstrip('/')}/api/garment/process-async"

    async with httpx.AsyncClient(timeout=settings.AI_PIPELINE_TIMEOUT_SECONDS) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def fetch_garment_task(task_id: str) -> Dict:
    """
    Fetch task status from AI pipeline.
    """
    url = f"{settings.AI_PIPELINE_BASE_URL.rstrip('/')}/api/garment/task/{task_id}"
    async with httpx.AsyncClient(timeout=settings.AI_PIPELINE_TIMEOUT_SECONDS) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def map_ai_pipeline_status(status: str) -> str:
    """
    Map AI pipeline task status to backend task status.
    """
    if status in ("PENDING",):
        return "PENDING"
    if status in ("PROGRESS",):
        return "PROCESSING"
    if status in ("SUCCESS",):
        return "COMPLETED"
    if status in ("FAILURE",):
        return "FAILED"
    return "PROCESSING"
