"""
FastAPI Main Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from database import engine, Base
from routers import auth, user, onboarding, products, ai

# Create database tables
Base.metadata.create_all(bind=engine)

# Create upload directories
os.makedirs("uploads/videos", exist_ok=True)
os.makedirs("uploads/avatars", exist_ok=True)
os.makedirs("uploads/garments", exist_ok=True)

app = FastAPI(
    title="Musinsa Price Tracker & Virtual Try-On API",
    description="무신사 가격 추적 및 3D 가상 피팅 서비스 API",
    version="1.0.0"
)

# CORS configuration for local development
# Must use specific origins (not wildcard) when credentials are needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Static files for uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(ai.router, prefix="/ai", tags=["AI Tasks"])


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
