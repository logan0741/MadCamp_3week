"""
User Router - User status and profile management
Thin controller layer - delegates to UserService
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from domain.entities import User
from domain.schemas import UserStatus, UserUpdate
from api.dependencies import get_current_user
from services.user_service import UserService

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
    return UserService.update_profile(db, current_user, update_data)
