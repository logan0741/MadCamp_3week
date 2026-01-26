"""
Auth Schemas - Authentication related Pydantic models
"""
from pydantic import BaseModel, Field
from typing import Optional


class UserCreate(BaseModel):
    """Schema for user registration"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded token data"""
    username: Optional[str] = None
