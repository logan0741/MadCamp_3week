"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


# ============= Auth Schemas =============

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    height: Optional[float] = None
    weight: Optional[float] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


# ============= User Schemas =============

class UserStatus(BaseModel):
    id: int
    username: str
    is_avatar_created: bool
    height: Optional[float]
    weight: Optional[float]
    avatar_url: Optional[str]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    height: Optional[float] = None
    weight: Optional[float] = None


# ============= Product Schemas =============

class ProductTrackRequest(BaseModel):
    url: str = Field(..., description="Musinsa product URL")


class ProductResponse(BaseModel):
    id: int
    musinsa_id: str
    url: str
    title: Optional[str]
    brand: Optional[str]
    thumbnail_url: Optional[str]
    image_urls: List[str] = []  # All product images for carousel
    original_price: Optional[int] = None  # Price before discount
    is_garment_modeled: bool
    current_price: Optional[int] = None
    discount_rate: Optional[int] = None

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int


# ============= Price Log Schemas =============

class PriceLogResponse(BaseModel):
    id: int
    price: int
    discount_rate: Optional[int]
    captured_at: date

    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    product_id: int
    title: Optional[str]
    history: List[PriceLogResponse]
    min_price: Optional[int] = None  # Lowest price ever
    max_price: Optional[int] = None  # Highest price ever
    min_date: Optional[str] = None   # Date of lowest price
    max_date: Optional[str] = None   # Date of highest price


# ============= AI Task Schemas =============

class AITaskCreate(BaseModel):
    task_type: str = Field(..., pattern="^(AVATAR|GARMENT)$")
    product_id: Optional[int] = None


class AITaskResponse(BaseModel):
    id: str
    task_type: str
    status: str
    result_url: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Onboarding Schemas =============

class OnboardingUploadResponse(BaseModel):
    message: str
    task_id: str
    status: str
