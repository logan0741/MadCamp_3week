"""
Backend API Proxy Example
백엔드에서 AI API를 프록시하는 예시 코드

메인 백엔드 (/root/MadCamp_3week/backend/) 에 추가할 코드
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import httpx
import asyncio

# 기존 백엔드 imports
from database import get_db
from models import User, Product, AITask
from schemas import VTONRequest, VTONResponse

# AI API Configuration
AI_API_BASE_URL = "http://localhost:8001"  # AI 파이프라인 서버
AI_API_TIMEOUT = 60.0  # 타임아웃 (초)


# ============================================
# Router
# ============================================

router = APIRouter(prefix="/ai", tags=["AI Virtual Try-On"])


# ============================================
# Synchronous Virtual Try-On
# ============================================

@router.post("/vton/try-on")
async def virtual_try_on_proxy(
    request: VTONRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    가상 피팅 프록시 엔드포인트

    사용자 인증 후 AI API 호출하고 결과를 DB에 저장
    """
    try:
        # AI API 호출
        async with httpx.AsyncClient(timeout=AI_API_TIMEOUT) as client:
            response = await client.post(
                f"{AI_API_BASE_URL}/api/vton/try-on",
                json=request.dict(),
            )
            response.raise_for_status()

            ai_result = response.json()

        # 결과를 DB에 저장 (선택적)
        # task = AITask(
        #     user_id=current_user.id,
        #     task_type="VTON",
        #     status="COMPLETED",
        #     result_url=ai_result["result_url"],
        # )
        # db.add(task)
        # db.commit()

        return ai_result

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI API 호출 실패: {str(e)}"
        )


# ============================================
# Asynchronous Virtual Try-On (with Database)
# ============================================

@router.post("/vton/try-on-async")
async def virtual_try_on_async_proxy(
    request: VTONRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    비동기 가상 피팅 프록시

    1. AI API에 비동기 작업 제출
    2. DB에 태스크 레코드 생성 (PENDING 상태)
    3. 태스크 ID 반환
    4. 백그라운드에서 폴링하여 완료 시 DB 업데이트
    """
    try:
        # AI API에 비동기 작업 제출
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AI_API_BASE_URL}/api/vton/try-on/async",
                json=request.dict(),
            )
            response.raise_for_status()

            task_info = response.json()

        # DB에 태스크 레코드 생성
        db_task = AITask(
            user_id=current_user.id,
            task_type="VTON",
            celery_task_id=task_info["task_id"],
            status="PENDING",
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)

        # 백그라운드에서 상태 업데이트 시작
        asyncio.create_task(
            poll_task_status(db_task.id, task_info["task_id"])
        )

        return {
            "success": True,
            "task_id": db_task.id,
            "celery_task_id": task_info["task_id"],
            "status": "PENDING",
            "message": "가상 피팅 작업이 시작되었습니다.",
        }

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI API 호출 실패: {str(e)}"
        )


async def poll_task_status(db_task_id: int, celery_task_id: str):
    """
    백그라운드에서 AI 작업 상태를 폴링하고 DB 업데이트
    """
    from database import SessionLocal

    db = SessionLocal()

    try:
        while True:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{AI_API_BASE_URL}/api/vton/tasks/{celery_task_id}"
                )
                status_info = response.json()

            # DB 업데이트
            db_task = db.query(AITask).filter(AITask.id == db_task_id).first()

            if status_info["status"] == "SUCCESS":
                db_task.status = "COMPLETED"
                db_task.result_url = status_info["result"]["result_url"]
                db.commit()
                break

            elif status_info["status"] == "FAILURE":
                db_task.status = "FAILED"
                db_task.error_message = status_info.get("error", "Unknown error")
                db.commit()
                break

            elif status_info["status"] == "PROGRESS":
                # 진행 상태만 업데이트 (완료 대기)
                db_task.status = "PROCESSING"
                db.commit()

            # 1초 대기 후 재시도
            await asyncio.sleep(1)

    finally:
        db.close()


# ============================================
# Get Task Status
# ============================================

@router.get("/vton/tasks/{task_id}")
async def get_task_status(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    작업 상태 조회
    """
    task = db.query(AITask).filter(
        AITask.id == task_id,
        AITask.user_id == current_user.id  # 본인 작업만 조회 가능
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    return {
        "task_id": task.id,
        "status": task.status,
        "result_url": task.result_url,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


# ============================================
# File Upload Endpoint
# ============================================

@router.post("/vton/upload")
async def virtual_try_on_upload(
    person_image: UploadFile = File(...),
    garment_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    파일 업로드 방식 가상 피팅

    1. 클라이언트로부터 이미지 파일 수신
    2. AI API로 전달 (multipart/form-data)
    3. 결과 반환
    """
    try:
        # 파일 읽기
        person_content = await person_image.read()
        garment_content = await garment_image.read()

        # AI API 호출 (multipart)
        async with httpx.AsyncClient(timeout=AI_API_TIMEOUT) as client:
            files = {
                "person_image": (person_image.filename, person_content, person_image.content_type),
                "garment_image": (garment_image.filename, garment_content, garment_image.content_type),
            }

            response = await client.post(
                f"{AI_API_BASE_URL}/api/vton/try-on/upload",
                files=files,
                data={
                    "num_inference_steps": 50,
                    "guidance_scale": 7.5,
                    "enhance_output": True,
                    "restore_face": True,
                }
            )
            response.raise_for_status()

            return response.json()

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI API 호출 실패: {str(e)}"
        )


# ============================================
# Webhook Callback (for async tasks)
# ============================================

@router.post("/vton/webhook")
async def vton_webhook_callback(
    result: dict,
    db: Session = Depends(get_db),
):
    """
    AI 서버에서 작업 완료 시 호출하는 웹훅

    AI API에서 비동기 작업 제출 시 callback_url 파라미터로
    이 엔드포인트 URL을 전달하면 완료 시 자동 호출됨
    """
    task_id = result.get("task_id")

    # DB에서 태스크 찾기
    db_task = db.query(AITask).filter(
        AITask.celery_task_id == task_id
    ).first()

    if db_task:
        if result.get("success"):
            db_task.status = "COMPLETED"
            db_task.result_url = result.get("result_url")
        else:
            db_task.status = "FAILED"
            db_task.error_message = result.get("error", "Unknown error")

        db.commit()

        # 사용자에게 알림 전송 (선택적)
        # send_notification_to_user(db_task.user_id, "가상 피팅 완료!")

    return {"success": True}


# ============================================
# Database Model Example
# ============================================

"""
# models.py에 추가할 테이블

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base

class AITask(Base):
    __tablename__ = "ai_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_type = Column(String(50))  # "VTON", "AVATAR", "GARMENT"
    celery_task_id = Column(String(255), unique=True)  # Celery 태스크 ID
    status = Column(String(50), default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    result_url = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
"""


# ============================================
# Environment Variables (.env)
# ============================================

"""
# .env 파일에 추가

AI_API_BASE_URL=http://localhost:8001
AI_API_TIMEOUT=60.0
AI_WEBHOOK_URL=https://yourdomain.com/api/ai/vton/webhook
"""


# ============================================
# Usage in main.py
# ============================================

"""
# main.py에 라우터 추가

from routers import ai_proxy

app.include_router(ai_proxy.router, prefix="/api")
"""
