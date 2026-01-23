"""
User Router - User status and profile management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserStatus, UserUpdate
from routers.auth import get_current_user

router = APIRouter()


@router.get("/status", response_model=UserStatus)
async def get_user_status(current_user: User = Depends(get_current_user)):
    """Get current user status including avatar creation status"""
    return current_user


@router.put("/profile", response_model=UserStatus)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile (height, weight)"""
    if update_data.height is not None:
        current_user.height = update_data.height
    if update_data.weight is not None:
        current_user.weight = update_data.weight
    
    db.commit()
    db.refresh(current_user)
    
    return current_user
