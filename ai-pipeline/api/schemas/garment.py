"""
Garment processing API schemas.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict
from datetime import datetime


class GarmentProcessRequest(BaseModel):
    """Request for garment processing with front/back images."""

    front_image_url: Optional[str] = Field(None, description="URL to front image")
    back_image_url: Optional[str] = Field(None, description="URL to back image")

    front_image_base64: Optional[str] = Field(None, description="Base64 front image")
    back_image_base64: Optional[str] = Field(None, description="Base64 back image")

    garment_type: str = Field(..., description="Garment type (top, pants, dress, skirt)")
    product_id: int = Field(..., description="Product ID from backend DB")
    size: Optional[str] = Field(default="M", description="Size label (S/M/L)")

    height_cm: Optional[float] = Field(default=170, description="Mannequin height in cm")
    weight_kg: Optional[float] = Field(default=65, description="Mannequin weight in kg")

    callback_url: Optional[str] = Field(None, description="Webhook URL for async completion")

    @validator("front_image_url", "back_image_url")
    def validate_url(cls, v):
        if v is not None and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @validator("front_image_base64", "back_image_base64")
    def validate_base64(cls, v):
        if v is not None:
            import base64
            try:
                base64.b64decode(v)
            except Exception:
                raise ValueError("Invalid base64 encoding")
        return v


class GarmentProcessResponse(BaseModel):
    """Response for garment processing."""

    success: bool = Field(default=True, description="Request success status")
    garment_glb_url: str = Field(..., description="URL to GLB output")
    uv_atlas_url: str = Field(..., description="URL to UV atlas texture")
    front_texture_url: str = Field(..., description="URL to front texture")
    back_texture_url: str = Field(..., description="URL to back texture")
    size_applied: Optional[str] = Field(None, description="Size label applied")
    processing_time_seconds: float = Field(..., description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GarmentAsyncResponse(BaseModel):
    """Async task response."""

    task_id: str = Field(..., description="Celery task ID")
    status_url: str = Field(..., description="URL to check task status")


class GarmentSizesResponse(BaseModel):
    """Size lookup response from backend."""

    product_id: int = Field(..., description="Product ID")
    sizes: Dict[str, Dict[str, float]] = Field(..., description="Size measurements")
