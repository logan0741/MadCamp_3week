"""
Onboarding Router - Video upload and avatar generation
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
import os
import uuid
import aiofiles

from database import get_db
from models import User, AITask
from schemas import OnboardingUploadResponse, AITaskResponse
from routers.auth import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads/videos"


async def process_avatar_generation(task_id: str, video_path: str, user_id: int, db_url: str):
    """
    Background task to process avatar generation.
    In production, this would call ECON + SMPL-X + 3DGS pipeline.
    For 8GB GPU, we'll use a simplified placeholder.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Update task status to processing
        task = db.query(AITask).filter(AITask.id == task_id).first()
        if task:
            task.status = "PROCESSING"
            db.commit()
        
        # TODO: Actual AI processing would go here
        # For now, simulate processing time and create a placeholder
        import asyncio
        await asyncio.sleep(5)  # Simulate processing
        
        # Update task and user with result
        if task:
            task.status = "COMPLETED"
            task.result_url = f"/uploads/avatars/{user_id}/avatar.glb"
            db.commit()
        
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_avatar_created = True
            user.avatar_url = f"/uploads/avatars/{user_id}/avatar.glb"
            db.commit()
            
    except Exception as e:
        if task:
            task.status = "FAILED"
            task.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=OnboardingUploadResponse)
async def upload_onboarding_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload onboarding video for avatar generation"""
    
    # Validate file type
    allowed_types = ["video/mp4", "video/webm", "video/quicktime"]
    if video.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {allowed_types}"
        )
    
    # Create user upload directory
    user_upload_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)
    
    # Generate unique filename
    file_ext = os.path.splitext(video.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(user_upload_dir, unique_filename)
    
    # Save uploaded file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await video.read()
        await f.write(content)
    
    # Create AI task
    task = AITask(
        user_id=current_user.id,
        task_type="AVATAR",
        status="PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create avatar output directory
    avatar_dir = os.path.join("uploads/avatars", str(current_user.id))
    os.makedirs(avatar_dir, exist_ok=True)
    
    # Add background task for processing
    # Note: For actual async processing in production, use Celery
    background_tasks.add_task(
        process_avatar_generation,
        task.id,
        file_path,
        current_user.id,
        "sqlite:///./musinsa_tracker.db"
    )
    
    return OnboardingUploadResponse(
        message="비디오가 업로드되었습니다. 아바타 생성이 시작됩니다.",
        task_id=task.id,
        status=task.status
    )


@router.get("/task/{task_id}", response_model=AITaskResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get onboarding task status"""
    task = db.query(AITask).filter(
        AITask.id == task_id,
        AITask.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task
