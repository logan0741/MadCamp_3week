"""
User Schemas - User related Pydantic models
"""
from pydantic import BaseModel
from typing import Optional


class UserStatus(BaseModel):
    """Schema for user status response"""
    id: int
    username: str
    is_avatar_created: bool
    height: Optional[float]
    weight: Optional[float]
    avatar_url: Optional[str]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for user profile update"""
    height: Optional[float] = None
    weight: Optional[float] = None
