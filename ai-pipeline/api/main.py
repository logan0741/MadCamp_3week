"""
AI Pipeline FastAPI Application
Provides REST API for virtual try-on and 3D avatar generation.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger
import time

from config import settings, print_config_summary
from api.routers import avatar, garment


# ============================================
# Lifespan Context Manager
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events.

    Startup:
    - Load AI models into VRAM
    - Initialize connections (Redis, database)

    Shutdown:
    - Unload models
    - Close connections
    """
    # Startup
    logger.info("=" * 50)
    logger.info("AI Pipeline API Starting...")
    logger.info("=" * 50)

    # Print configuration
    print_config_summary()

    # Pre-load VTON model if enabled (always-on)
    if settings.enable_vton:
        logger.info("Pre-loading IDM-VTON model...")
        try:
            from models import IDMVTON
            vton_model = IDMVTON()
            vton_model.load_model()
            logger.success("IDM-VTON model loaded and ready")
        except Exception as e:
            logger.error(f"Failed to load VTON model: {e}")

    # TODO: Initialize other models as needed
    # ECON, BCNet, 3DGS are loaded on-demand via Celery

    logger.success("AI Pipeline API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down AI Pipeline API...")

    # Unload models
    try:
        from models.vton.idm_vton import get_vton_model
        vton = get_vton_model()
        vton.unload_model()
    except Exception as e:
        logger.warning(f"Error during model cleanup: {e}")

    logger.success("AI Pipeline API shut down complete")


# ============================================
# FastAPI App Instance
# ============================================
app = FastAPI(
    title="Musinsa AI Pipeline",
    description="AI-powered virtual try-on and 3D avatar generation",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================
# Middleware
# ============================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    start_time = time.time()

    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Log response time
    process_time = time.time() - start_time
    logger.info(f"Completed in {process_time:.3f}s - Status: {response.status_code}")

    # Add custom header
    response.headers["X-Process-Time"] = str(process_time)

    return response


# ============================================
# Exception Handlers
# ============================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug_mode else "An error occurred",
        },
    )


# ============================================
# Static Files
# ============================================
# Serve output files (avatars, garments, try-on results)
app.mount(
    "/outputs",
    StaticFiles(directory=str(settings.output_dir)),
    name="outputs"
)


# ============================================
# Routes
# ============================================

@app.get("/")
async def root():
    """Root endpoint - API status."""
    return {
        "service": "Musinsa AI Pipeline",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.environment,
        "features": {
            "vton": settings.enable_vton,
            "econ": settings.enable_econ,
            "bcnet": settings.enable_bcnet,
            "3dgs": settings.enable_3dgs,
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer."""
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        cuda_devices = torch.cuda.device_count() if cuda_available else 0
        return {
            "status": "healthy",
            "cuda_available": cuda_available,
            "cuda_devices": cuda_devices,
        }
    except Exception:
        return {
            "status": "healthy",
            "cuda_available": False,
            "cuda_devices": 0,
            "warning": "torch not installed",
        }


@app.get("/vram-status")
async def vram_status():
    """Get VRAM usage statistics."""
    import torch

    if not torch.cuda.is_available():
        return {"error": "CUDA not available"}

    devices = []
    for i in range(torch.cuda.device_count()):
        allocated = torch.cuda.memory_allocated(i) / 1024**3  # GB
        reserved = torch.cuda.memory_reserved(i) / 1024**3
        total = torch.cuda.get_device_properties(i).total_memory / 1024**3

        devices.append({
            "device_id": i,
            "name": torch.cuda.get_device_name(i),
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "total_gb": round(total, 2),
            "utilization_percent": round((allocated / total) * 100, 2),
        })

    return {
        "total_devices": len(devices),
        "devices": devices,
    }


# ============================================
# Include Routers
# ============================================
if settings.enable_vton:
    from api.routers import vton

    app.include_router(
        vton.router,
        prefix="/api/vton",
        tags=["Virtual Try-On"],
    )
else:
    logger.warning("VTON disabled: skipping /api/vton routes")

app.include_router(
    avatar.router,
    prefix="/api/avatar",
    tags=["3D Avatar"],
)

app.include_router(
    garment.router,
    prefix="/api/garment",
    tags=["Garment Pipeline"],
)


# ============================================
# Entry Point
# ============================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=settings.api_workers if not settings.api_reload else 1,
        log_level=settings.log_level.lower(),
    )
