"""
User Schemas - User related Pydantic models
"""
from pydantic import BaseModel
from typing import Optional


class UserStatus(BaseModel):
    """Schema for user status response"""
    id: int
    username: str

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for user profile update"""
    pass
