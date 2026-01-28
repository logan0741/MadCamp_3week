"""
Products Router - Product tracking and price history
Thin controller layer - delegates to ProductService
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from core.database import get_db
from domain.entities import Product
from domain.schemas import (
    ProductTrackRequest, ProductResponse, ProductListResponse,
    PriceHistoryResponse
)
from services.product_service import ProductService
from services.scraper import scrape_musinsa_product
from services.size_scraper import (
    get_cached_sizes,
    save_cached_sizes,
    scrape_musinsa_sizes,
)

router = APIRouter()


@router.post("/track", response_model=ProductResponse)
async def track_product(
    request: ProductTrackRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a Musinsa product URL for price tracking"""
    
    try:
        musinsa_id = ProductService.extract_musinsa_id(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # For OneLink URLs, we need to scrape first to get the real product ID
    is_onelink = musinsa_id.startswith('onelink_')
    product_info = None
    
    if is_onelink:
        try:
            product_info = await scrape_musinsa_product(request.url, musinsa_id)
            if product_info.get("product_id") and not product_info["product_id"].startswith('onelink_'):
                musinsa_id = product_info["product_id"]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not resolve share link: {str(e)}")
    
    # Check if product already exists
    product = ProductService.get_product_by_musinsa_id(db, musinsa_id)
    
    if not product:
        # Scrape product information if not already done
        if not product_info:
            try:
                product_info = await scrape_musinsa_product(request.url, musinsa_id)
            except Exception:
                product_info = {
                    "title": f"상품 {musinsa_id}",
                    "brand": None,
                    "thumbnail_url": None,
                    "image_urls": [],
                    "price": None,
                    "original_price": None,
                    "discount_rate": None
                }
        
        # Create new product
        product = ProductService.create_product(db, musinsa_id, request.url, product_info)
        
        # Add initial price log if price was scraped
        if product_info.get("price"):
            ProductService.add_price_log(
                db, product.id,
                product_info["price"],
                product_info.get("discount_rate")
            )
    
    # Get latest price and build response
    latest_price = ProductService.get_latest_price(db, product.id)
    return ProductService.build_product_response(product, latest_price)


@router.get("/{product_id}/history", response_model=PriceHistoryResponse)
async def get_price_history(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get price history for a product"""
    return ProductService.get_price_history(db, product_id)


@router.get("/{product_id}/sizes")
async def get_product_sizes(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Get size measurements for a product.
    """
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cached = get_cached_sizes(product_id)
    if cached and cached.sizes:
        return {
            "product_id": product_id,
            "sizes": cached.sizes,
            "source": cached.source,
            "updated_at": cached.updated_at,
        }

    try:
        result = await scrape_musinsa_sizes(
            product_id=product.musinsa_id,
            product_url=product.url,
            use_playwright=False,
        )
        if result.sizes:
            save_cached_sizes(product_id, result)
        return {
            "product_id": product_id,
            "sizes": result.sizes,
            "source": result.source,
            "updated_at": result.updated_at,
        }
    except Exception as exc:
        return {
            "product_id": product_id,
            "sizes": {},
            "error": str(exc),
        }
