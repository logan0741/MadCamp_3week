"""
Local GPU Analysis Server (port 8001)
Provides /ai-recommend endpoints for the backend without SSH tunneling.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from PIL import Image
from io import BytesIO

try:
    from crawling.gpu_crawling.backend.services.personal_color import (
        analyze_personal_color,
        get_recommended_palette,
    )
except Exception as exc:  # pragma: no cover - import guard for runtime
    raise RuntimeError(
        "Failed to import personal_color analyzer. "
        "Ensure the repo root is the working directory."
    ) from exc


class AnalyzeCustomRequest(BaseModel):
    image_url: str
    prompt: Optional[str] = None


class AnalyzeColorRequest(BaseModel):
    image_url: str
    additional_urls: Optional[List[str]] = None


class RecommendRequest(BaseModel):
    product: dict
    tone_preference: Optional[str] = None
    limit: int = 6


app = FastAPI(
    title="Local GPU Analysis Server",
    description="Local /ai-recommend endpoints for personal color analysis",
    version="0.1.0",
)


SEASON_LABELS = {
    "spring_warm": "봄 웜톤",
    "summer_cool": "여름 쿨톤",
    "autumn_warm": "가을 웜톤",
    "winter_cool": "겨울 쿨톤",
    "neutral": "뉴트럴",
}


def _opposite_tone(tone: Optional[str]) -> Optional[str]:
    if tone == "warm":
        return "cool"
    if tone == "cool":
        return "warm"
    return None


async def _download_image(url: str) -> bytes:
    timeout = httpx.Timeout(connect=5.0, read=20.0, write=20.0, pool=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch image: {resp.status_code}")
        return resp.content


def _average_hex(image_bytes: bytes) -> str:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image = image.resize((64, 64))
    pixels = list(image.getdata())
    r = sum(p[0] for p in pixels) / len(pixels)
    g = sum(p[1] for p in pixels) / len(pixels)
    b = sum(p[2] for p in pixels) / len(pixels)
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


@app.get("/ai-recommend/health")
async def health():
    return {
        "status": "healthy",
        "service": "ai-recommend",
        "features": ["analyze-custom", "analyze-color"],
    }


@app.post("/ai-recommend/analyze-custom")
async def analyze_custom(payload: AnalyzeCustomRequest):
    image_bytes = await _download_image(payload.image_url)
    analysis = analyze_personal_color(image_bytes)

    base_tone = analysis.get("base_tone")
    season = analysis.get("season") or "neutral"
    personal_color = SEASON_LABELS.get(season, SEASON_LABELS.get(base_tone, "퍼스널 컬러"))

    best_colors = analysis.get("recommended_palette") or []
    opposite = _opposite_tone(base_tone)
    worst_colors = get_recommended_palette(
        base_tone=opposite,
        season=None,
        tone_type=None,
    ) if opposite else []

    return {
        "user_analysis": {
            "personal_color": personal_color,
            "skin_tone_hex": analysis.get("skin_tone_hex") or _average_hex(image_bytes),
            "best_colors": best_colors,
            "worst_colors": worst_colors,
        },
        "fashion_terrorist_check": {
            "is_terrorist": False,
            "mismatch_score": 12,
            "warning_message": "",
        },
        "recommendations": [],
    }


@app.post("/ai-recommend/analyze-color")
async def analyze_color(payload: AnalyzeColorRequest):
    image_bytes = await _download_image(payload.image_url)
    dominant_hex = _average_hex(image_bytes)
    return {
        "status": "success",
        "dominant_color": dominant_hex,
        "pccs": {},
    }


@app.post("/ai-recommend/recommend")
async def recommend(_: RecommendRequest):
    return {
        "status": "success",
        "color_analysis": None,
        "recommendations": [],
        "style_suggestions": [],
    }
