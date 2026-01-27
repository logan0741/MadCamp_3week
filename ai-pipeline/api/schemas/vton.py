"""
VTON API Schemas
Request/response models for virtual try-on endpoints.
"""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, List
from datetime import datetime


class VTONRequest(BaseModel):
    """Single virtual try-on request."""

    person_image_url: Optional[str] = Field(None, description="URL to person image")
    garment_image_url: Optional[str] = Field(None, description="URL to garment image")

    # Alternative: base64 encoded images
    person_image_base64: Optional[str] = Field(None, description="Base64 encoded person image")
    garment_image_base64: Optional[str] = Field(None, description="Base64 encoded garment image")

    # Inference parameters
    num_inference_steps: int = Field(
        default=50,
        ge=10,
        le=100,
        description="Number of diffusion steps (higher = better quality, slower)"
    )
    guidance_scale: float = Field(
        default=7.5,
        ge=1.0,
        le=20.0,
        description="Classifier-free guidance scale"
    )
    seed: Optional[int] = Field(None, ge=0, description="Random seed for reproducibility")

    # Post-processing options
    enhance_output: bool = Field(default=True, description="Apply post-processing enhancement")
    restore_face: bool = Field(default=True, description="Restore original face")

    @validator("person_image_url", "garment_image_url")
    def validate_url(cls, v):
        """Validate URL format."""
        if v is not None and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @validator("person_image_base64", "garment_image_base64")
    def validate_base64(cls, v):
        """Validate base64 format."""
        if v is not None:
            import base64
            try:
                base64.b64decode(v)
            except Exception:
                raise ValueError("Invalid base64 encoding")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "person_image_url": "https://example.com/person.jpg",
                "garment_image_url": "https://example.com/garment.jpg",
                "num_inference_steps": 50,
                "guidance_scale": 7.5,
                "seed": 42,
                "enhance_output": True,
                "restore_face": True,
            }
        }


class VTONResponse(BaseModel):
    """Virtual try-on response."""

    success: bool = Field(default=True, description="Request success status")
    result_url: str = Field(..., description="URL to result image")
    processing_time_seconds: float = Field(..., description="Processing time in seconds")

    # Optional: Include VRAM stats for monitoring
    vram_allocated_mb: Optional[float] = Field(None, description="VRAM used (MB)")

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "result_url": "http://localhost:8001/outputs/vton/result_abc123.png",
                "processing_time_seconds": 2.35,
                "vram_allocated_mb": 8192.5,
                "timestamp": "2026-01-24T12:00:00Z",
            }
        }


class VTONBatchRequest(BaseModel):
    """Batch virtual try-on request."""

    requests: List[VTONRequest] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of try-on requests (max 10)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "requests": [
                    {
                        "person_image_url": "https://example.com/person1.jpg",
                        "garment_image_url": "https://example.com/garment1.jpg",
                    },
                    {
                        "person_image_url": "https://example.com/person2.jpg",
                        "garment_image_url": "https://example.com/garment2.jpg",
                    },
                ]
            }
        }


class VTONBatchResponse(BaseModel):
    """Batch virtual try-on response."""

    success: bool = Field(default=True, description="Batch success status")
    results: List[VTONResponse] = Field(..., description="List of individual results")
    total_processing_time_seconds: float = Field(..., description="Total time for all requests")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "results": [
                    {
                        "success": True,
                        "result_url": "http://localhost:8001/outputs/vton/result_1.png",
                        "processing_time_seconds": 2.1,
                        "timestamp": "2026-01-24T12:00:00Z",
                    },
                    {
                        "success": True,
                        "result_url": "http://localhost:8001/outputs/vton/result_2.png",
                        "processing_time_seconds": 2.3,
                        "timestamp": "2026-01-24T12:00:01Z",
                    },
                ],
                "total_processing_time_seconds": 4.4,
            }
        }


class VTONAsyncRequest(BaseModel):
    """Async virtual try-on request (via Celery)."""

    person_image_url: str = Field(..., description="URL to person image")
    garment_image_url: str = Field(..., description="URL to garment image")
    callback_url: Optional[str] = Field(None, description="Webhook URL for completion notification")

    class Config:
        json_schema_extra = {
            "example": {
                "person_image_url": "https://example.com/person.jpg",
                "garment_image_url": "https://example.com/garment.jpg",
                "callback_url": "https://backend.example.com/webhooks/vton-complete",
            }
        }


class VTONAsyncResponse(BaseModel):
    """Async virtual try-on task response."""

    task_id: str = Field(..., description="Celery task ID")
    status_url: str = Field(..., description="URL to check task status")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc123-def456-ghi789",
                "status_url": "http://localhost:8001/api/vton/tasks/abc123-def456-ghi789",
            }
        }
