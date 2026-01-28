"""
Personal Color Router - Analyze personal color from user image.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from core.database import get_db
from domain.entities import User
from services.personal_color import analyze_personal_color
from services.user_service import UserService


router = APIRouter()


@router.post("/analyze")
async def analyze_personal_color_endpoint(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Analyze personal color from a face image and update user profile."""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid image type.")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image.")

    result = analyze_personal_color(image_bytes)
    UserService.update_personal_color(db, current_user, result)

    return {
        "user_id": current_user.id,
        "personal_color": result,
    }

