"""
FastAPI Main Application Entry Point
Clean Architecture structure
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from core.config import settings
from core.database import engine, Base
from api.v1 import router as api_v1_router

# Create database tables
Base.metadata.create_all(bind=engine)

# Create upload directories
os.makedirs(settings.VIDEO_UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.AVATAR_UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.GARMENT_UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Musinsa Price Tracker & Virtual Try-On API",
    description="무신사 가격 추적 및 3D 가상 피팅 서비스 API",
    version="1.0.0"
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
