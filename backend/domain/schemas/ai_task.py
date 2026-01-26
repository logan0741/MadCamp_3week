"""
AI Task Schemas - AI task related Pydantic models
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AITaskCreate(BaseModel):
    """Schema for AI task creation"""
    task_type: str = Field(..., pattern="^(AVATAR|GARMENT)$")
    product_id: Optional[int] = None


class AITaskResponse(BaseModel):
    """Schema for AI task response"""
    id: str
    task_type: str
    status: str
    external_task_id: Optional[str] = None
    result_url: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OnboardingUploadResponse(BaseModel):
    """Schema for onboarding upload response"""
    message: str
    task_id: str
    status: str
