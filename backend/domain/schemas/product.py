from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class ProductTrackRequest(BaseModel):
    url: str

class ProductResponse(BaseModel):
    id: int
    musinsa_id: str
    url: str
    title: Optional[str] = None
    brand: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_urls: List[str] = []
    original_price: Optional[int] = None
    is_garment_modeled: bool = False
    current_price: Optional[int] = None
    discount_rate: Optional[int] = None

class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int

class PriceLogResponse(BaseModel):
    id: int
    price: int
    discount_rate: Optional[int]
    captured_at: date

class PriceHistoryResponse(BaseModel):
    product_id: int
    title: Optional[str]
    history: List[PriceLogResponse]
    min_price: Optional[int]
    max_price: Optional[int]
    min_date: Optional[str]
    max_date: Optional[str]
