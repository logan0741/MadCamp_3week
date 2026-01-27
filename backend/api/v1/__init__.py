"""
API v1 package - Version 1 of REST API
"""
from fastapi import APIRouter

from api.v1 import auth, user, products

router = APIRouter()

# Include all v1 routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(user.router, prefix="/user", tags=["User"])
router.include_router(products.router, prefix="/products", tags=["Products"])
from api.v1 import ai_recommend
router.include_router(ai_recommend.router, prefix="/ai-recommend", tags=["AI Recommend"])
