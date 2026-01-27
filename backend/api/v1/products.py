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
from services.ai_client import (
    ai_client,
    get_ai_recommendations,
    analyze_product_color,
    check_gpu_server_health
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


@router.get("/{product_id}/colors")
async def get_product_colors(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Get PCCS color analysis for a product.
    Calls GPU server AI API for color analysis.
    """
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.thumbnail_url:
        raise HTTPException(status_code=400, detail="Product has no images for analysis")

    try:
        # Call GPU server for color analysis
        color_data = await analyze_product_color(product.thumbnail_url)

        if color_data.get("status") == "error":
            return {
                "product_id": product_id,
                "error": color_data.get("message", "GPU server error"),
                "colors": None
            }

        return {
            "product_id": product_id,
            "pccs": color_data.get("pccs", {}),
            "primary_color": color_data.get("dominant_color"),
            "analysis": color_data
        }

    except Exception as exc:
        return {
            "product_id": product_id,
            "error": str(exc),
            "colors": None
        }


@router.get("/{product_id}/recommendations")
async def get_product_recommendations(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get style-matched product recommendations for outfit coordination.
    Calls GPU server AI API for recommendations based on style/color analysis.
    """
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        # Prepare product data for GPU server
        import json
        image_urls = []
        if product.image_urls:
            if isinstance(product.image_urls, str):
                try:
                    image_urls = json.loads(product.image_urls)
                except:
                    image_urls = []
            else:
                image_urls = product.image_urls
        
        product_data = {
            "id": product.musinsa_id,
            "title": product.title,
            "brand": product.brand,
            "thumbnail_url": product.thumbnail_url,
            "image_urls": image_urls,
            "price": product.original_price,
        }
        
        # Call GPU server for AI recommendations
        result = await get_ai_recommendations(product_data)
        
        if result.get("status") == "error":
            return {
                "product_id": product_id,
                "error": result.get("message", "GPU server error"),
                "recommendations": []
            }
        
        return {
            "product_id": product_id,
            "recommendations": result.get("recommendations", []),
            "color_analysis": result.get("color_analysis", {}),
            "status": "success"
        }
        
    except Exception as exc:
        return {
            "product_id": product_id,
            "error": str(exc),
            "recommendations": []
        }


@router.get("/gpu/health")
async def check_gpu_health():
    """Check GPU server AI API health status"""
    is_healthy = await check_gpu_server_health()
    return {
        "gpu_server": "healthy" if is_healthy else "unreachable",
        "url": "http://192.168.0.250:8000"
    }


@router.get("/{product_id}/ai-recommend")
async def get_ai_recommend(
    product_id: int,
    tone_preference: str = None,
    db: Session = Depends(get_db)
):
    """
    상품에 대한 AI 추천 조회 (GPU 서버 호출)
    - 색상 분석
    - 스타일 추천
    - 매칭 상품 제안
    """
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    try:
        import json
        image_urls = []
        if product.image_urls:
            if isinstance(product.image_urls, str):
                try:
                    image_urls = json.loads(product.image_urls)
                except:
                    image_urls = []
            else:
                image_urls = product.image_urls
        
        result = await ai_client.get_recommendation(
            product_id=str(product.id),
            title=product.title,
            thumbnail_url=product.thumbnail_url,
            image_urls=image_urls,
            brand=product.brand,
            price=product.original_price,
            tone_preference=tone_preference
        )
        
        return result
        
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "product_id": product_id
        }


@router.post("/{product_id}/analyze-color")
async def analyze_color_endpoint(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    상품 색상 분석 요청 (GPU 서버 호출)
    분석된 PCCS 색상 정보를 반환
    """
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    if not product.thumbnail_url:
        raise HTTPException(status_code=400, detail="상품 이미지가 없습니다.")
    
    try:
        import json
        image_urls = []
        if product.image_urls:
            if isinstance(product.image_urls, str):
                try:
                    image_urls = json.loads(product.image_urls)
                except:
                    image_urls = []
            else:
                image_urls = product.image_urls
        
        result = await ai_client.analyze_color(
            image_url=product.thumbnail_url,
            additional_urls=image_urls[:3]
        )
        
        return {
            "product_id": product_id,
            **result
        }
        
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "product_id": product_id
        }
