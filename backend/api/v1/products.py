"""
Products Router - Product tracking and price history
Thin controller layer - delegates to ProductService
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from core.database import get_db
from domain.entities import User
from domain.schemas import (
    ProductTrackRequest, ProductResponse, ProductListResponse,
    PriceHistoryResponse
)
from api.dependencies import get_current_user
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
    current_user: User = Depends(get_current_user),
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
    
    # Add to user's interests if not already there
    if not ProductService.check_user_interest(db, current_user.id, product.id):
        ProductService.add_to_interests(db, current_user.id, product.id)
    
    # Get latest price and build response
    latest_price = ProductService.get_latest_price(db, product.id)
    return ProductService.build_product_response(product, latest_price)


@router.get("", response_model=ProductListResponse)
async def get_user_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all products in user's interest list"""
    products_with_prices = ProductService.get_user_products(db, current_user.id)
    
    products = [
        ProductService.build_product_response(product, latest_price)
        for product, latest_price in products_with_prices
    ]
    
    return ProductListResponse(products=products, total=len(products))


@router.get("/{product_id}/history", response_model=PriceHistoryResponse)
async def get_price_history(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get price history for a product"""
    return ProductService.get_price_history(db, product_id)


@router.delete("/{product_id}")
async def remove_product_from_interests(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a product from user's interest list"""
    success = ProductService.remove_from_interests(db, current_user.id, product_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Product not in your interest list")
    
    return {"message": "Product removed from interest list"}


@router.get("/{product_id}/sizes")
async def get_product_sizes(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Get size measurements for a product.

    NOTE: 현재 DB에 사이즈 테이블이 없어 빈 값 반환.
    팀원 크롤링 데이터 연동 시 이 부분을 교체하세요.
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
