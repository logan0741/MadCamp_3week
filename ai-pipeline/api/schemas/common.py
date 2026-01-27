"""
Common API Schemas
Shared request/response models.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "ValidationError",
                "message": "Invalid image format. Expected JPEG or PNG.",
                "timestamp": "2026-01-24T12:00:00Z",
            }
        }


class SuccessResponse(BaseModel):
    """Standard success response."""

    success: bool = Field(default=True, description="Always true for success")
    data: Any = Field(..., description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"result": "Operation completed"},
                "timestamp": "2026-01-24T12:00:00Z",
            }
        }


class TaskStatus(BaseModel):
    """Async task status."""

    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(..., description="Task status: PENDING, PROCESSING, SUCCESS, FAILURE")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage")
    result_url: Optional[str] = Field(None, description="Result URL when completed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Task creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc123-def456",
                "status": "PROCESSING",
                "progress": 65,
                "result_url": None,
                "error_message": None,
                "created_at": "2026-01-24T12:00:00Z",
                "updated_at": "2026-01-24T12:05:00Z",
            }
        }
