"""
AI Router - Virtual try-on and garment modeling
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User, Product, AITask
from schemas import AITaskResponse, AITaskCreate
from routers.auth import get_current_user

router = APIRouter()


async def process_garment_generation(task_id: str, product_id: int, db_url: str):
    """
    Background task to process garment 3D model generation.
    For 8GB GPU, this would use a lighter model or placeholder.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        task = db.query(AITask).filter(AITask.id == task_id).first()
        if task:
            task.status = "PROCESSING"
            db.commit()
        
        # TODO: Actual BCNet processing
        import asyncio
        await asyncio.sleep(3)  # Simulate processing
        
        if task:
            task.status = "COMPLETED"
            task.result_url = f"/uploads/garments/{product_id}/garment.glb"
            db.commit()
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            product.is_garment_modeled = True
            db.commit()
            
    except Exception as e:
        if task:
            task.status = "FAILED"
            task.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/fit/{product_id}", response_model=AITaskResponse)
async def request_garment_fitting(
    product_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request 3D garment modeling for a specific product (on-demand)"""
    
    # Check if user has avatar created
    if not current_user.is_avatar_created:
        raise HTTPException(
            status_code=400,
            detail="아바타를 먼저 생성해주세요. 온보딩을 완료해주세요."
        )
    
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    # Check if garment is already modeled
    if product.is_garment_modeled:
        # Return existing result
        existing_task = db.query(AITask).filter(
            AITask.product_id == product_id,
            AITask.task_type == "GARMENT",
            AITask.status == "COMPLETED"
        ).first()
        
        if existing_task:
            return existing_task
    
    # Check for pending/processing task
    existing_task = db.query(AITask).filter(
        AITask.product_id == product_id,
        AITask.task_type == "GARMENT",
        AITask.status.in_(["PENDING", "PROCESSING"])
    ).first()
    
    if existing_task:
        return existing_task
    
    # Create new task
    task = AITask(
        user_id=current_user.id,
        product_id=product_id,
        task_type="GARMENT",
        status="PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create output directory
    import os
    garment_dir = os.path.join("uploads/garments", str(product_id))
    os.makedirs(garment_dir, exist_ok=True)
    
    # Start background processing
    background_tasks.add_task(
        process_garment_generation,
        task.id,
        product_id,
        "sqlite:///./musinsa_tracker.db"
    )
    
    return task


@router.get("/tasks", response_model=List[AITaskResponse])
async def get_user_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all AI tasks for the current user"""
    
    tasks = db.query(AITask).filter(
        AITask.user_id == current_user.id
    ).order_by(AITask.created_at.desc()).all()
    
    return tasks


@router.get("/task/{task_id}", response_model=AITaskResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific AI task status"""
    
    task = db.query(AITask).filter(
        AITask.id == task_id,
        AITask.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task
