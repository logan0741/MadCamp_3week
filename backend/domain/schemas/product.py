"""
Product Schemas - Product and Price related Pydantic models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class ProductTrackRequest(BaseModel):
    """Schema for product tracking request"""
    url: str = Field(..., description="Musinsa product URL")


class ProductResponse(BaseModel):
    """Schema for product response"""
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
    """Schema for product list response"""
    products: List[ProductResponse]
    total: int


class PriceLogResponse(BaseModel):
    """Schema for price log response"""
    id: int
    price: int
    discount_rate: Optional[int]
    captured_at: date

    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    """Schema for price history response"""
    product_id: int
    title: Optional[str]
    history: List[PriceLogResponse]
    min_price: Optional[int] = None  # Lowest price ever
    max_price: Optional[int] = None  # Highest price ever
    min_date: Optional[str] = None   # Date of lowest price
    max_date: Optional[str] = None   # Date of highest price
