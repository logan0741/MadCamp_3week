from fastapi import APIRouter
from api.v1 import products

router = APIRouter()

router.include_router(products.router, prefix="/products", tags=["Products"])
