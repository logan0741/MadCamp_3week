"""
Domain Schemas - Pydantic models for API validation
"""
from domain.schemas.auth import UserCreate, UserLogin, Token, TokenData
from domain.schemas.user import UserStatus, UserUpdate
from domain.schemas.product import (
    ProductTrackRequest,
    ProductResponse,
    ProductListResponse,
    PriceLogResponse,
    PriceHistoryResponse,
)
from domain.schemas.ai_task import AITaskCreate, AITaskResponse, OnboardingUploadResponse

__all__ = [
    # Auth
    "UserCreate",
    "UserLogin",
    "Token",
    "TokenData",
    # User
    "UserStatus",
    "UserUpdate",
    # Product
    "ProductTrackRequest",
    "ProductResponse",
    "ProductListResponse",
    "PriceLogResponse",
    "PriceHistoryResponse",
    # AI Task
    "AITaskCreate",
    "AITaskResponse",
    "OnboardingUploadResponse",
]
