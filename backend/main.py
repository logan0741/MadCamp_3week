"""
FastAPI Main Application Entry Point
Clean Architecture structure with scheduled price tracking
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging

from core.config import settings
from infrastructure.persistence.database import engine, Base, get_db
from api.v1 import router as api_v1_router
from api.dependencies import get_current_user
from application.scheduler import price_scheduler
from domain.entities import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting Musinsa Price Tracker API")
    price_scheduler.start()
    yield
    # Shutdown
    logger.info("Shutting down...")
    price_scheduler.stop()


app = FastAPI(
    title="Musinsa Price Tracker & Virtual Try-On API",
    description="무신사 가격 추적 및 3D 가상 피팅 서비스 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Static files for uploads
import os
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include API v1 routers
# Note: keeping legacy routes without /api/v1 prefix for backward compatibility
app.include_router(api_v1_router)


@app.get("/")
async def root():
    return {
        "message": "Musinsa Price Tracker & Virtual Try-On API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# ============= Admin Endpoints for Price Updates =============

@app.post("/admin/update-prices")
async def trigger_price_update(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Manually trigger a price update for all products (requires authentication)"""
    background_tasks.add_task(price_scheduler.update_all_prices)
    return {
        "message": "가격 업데이트가 백그라운드에서 시작되었습니다.",
        "status": "started"
    }


@app.post("/admin/update-price/{product_id}")
async def trigger_single_price_update(
    product_id: int,
    current_user: User = Depends(get_current_user)
):
    """Manually update price for a single product (requires authentication)"""
    result = await price_scheduler.update_single_product(product_id)
    
    if result:
        return {
            "message": "가격이 업데이트되었습니다.",
            "data": result
        }
    else:
        raise HTTPException(
            status_code=400,
            detail="가격을 업데이트할 수 없습니다. 상품을 찾을 수 없거나 크롤링에 실패했습니다."
        )


@app.get("/admin/scheduler-status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user)
):
    """Get current scheduler status and next run times"""
    jobs = []
    for job in price_scheduler.scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None
        })
    
    return {
        "is_running": price_scheduler._is_running,
        "jobs": jobs
    }
