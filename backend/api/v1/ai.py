"""
AI Router - Virtual try-on and garment modeling
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from domain.entities import User, Product, AITask
from domain.schemas import AITaskResponse
from api.dependencies import get_current_user
from services.ai_pipeline_service import (
    select_front_back_images,
    submit_garment_task,
    fetch_garment_task,
    map_ai_pipeline_status,
)

router = APIRouter()


@router.post("/fit/{product_id}", response_model=AITaskResponse)
async def request_garment_fitting(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request 3D garment modeling for a specific product (on-demand)"""
    
    if not current_user.is_avatar_created:
        raise HTTPException(
            status_code=400,
            detail="아바타를 먼저 생성해주세요. 온보딩을 완료해주세요."
        )
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    if product.is_garment_modeled:
        existing_task = db.query(AITask).filter(
            AITask.product_id == product_id,
            AITask.task_type == "GARMENT",
            AITask.status == "COMPLETED"
        ).first()
        
        if existing_task:
            return existing_task
    
    existing_task = db.query(AITask).filter(
        AITask.product_id == product_id,
        AITask.task_type == "GARMENT",
        AITask.status.in_(["PENDING", "PROCESSING"])
    ).first()
    
    if existing_task:
        return existing_task
    
    task = AITask(
        user_id=current_user.id,
        product_id=product_id,
        task_type="GARMENT",
        status="PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    front_url, back_url = select_front_back_images(product)
    if not front_url or not back_url:
        raise HTTPException(status_code=400, detail="상품 이미지가 부족합니다.")

    try:
        response = await submit_garment_task(
            front_url=front_url,
            back_url=back_url,
            garment_type="top",
            product_id=product_id,
            size="M",
            height_cm=170,
            weight_kg=65,
        )

        task.external_task_id = response.get("task_id")
        task.status = "PROCESSING"
        db.commit()
        db.refresh(task)

    except Exception as e:
        task.status = "FAILED"
        task.error_message = str(e)
        db.commit()
        db.refresh(task)

        raise HTTPException(status_code=502, detail=f"AI 파이프라인 요청 실패: {e}")

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

    if task.external_task_id and task.status not in ["COMPLETED", "FAILED"]:
        try:
            pipeline_status = await fetch_garment_task(task.external_task_id)
            mapped_status = map_ai_pipeline_status(pipeline_status.get("status", ""))

            task.status = mapped_status

            if mapped_status == "COMPLETED":
                result = pipeline_status.get("result", {}) or {}
                task.result_url = result.get("garment_glb_url")
                task.error_message = None

                product = db.query(Product).filter(Product.id == task.product_id).first()
                if product:
                    product.is_garment_modeled = True

            elif mapped_status == "FAILED":
                task.error_message = pipeline_status.get("error") or "AI pipeline failed"

            db.commit()
            db.refresh(task)
        except Exception:
            # Keep existing task status if pipeline check fails
            db.rollback()

    return task
