"""
Products Router - Product tracking and price history
Thin controller layer - delegates to ProductService
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from infrastructure.persistence.database import get_db
from domain.entities import User, FittingResult
from domain.schemas import (
    ProductTrackRequest, ProductResponse, ProductListResponse,
    PriceHistoryResponse
)
from api.dependencies import get_current_user
from application.product_service import ProductService
from infrastructure.clients.scraper import scrape_musinsa_product
from infrastructure.clients.size_scraper import (
    get_cached_sizes,
    save_cached_sizes,
    scrape_musinsa_sizes,
)
from infrastructure.clients.ai_client import (
    ai_client,
    get_ai_recommendations,
    analyze_product_color,
    check_gpu_server_health
)
from services.vton_client import generate_try_on_image
import uuid
import os
import logging

logger = logging.getLogger(__name__)

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
            "message": str(exc),
            "product_id": product_id
        }


@router.post("/{product_id}/fitting")
async def create_virtual_fitting(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Virtual Try-On (VTON) image.
    1. Uses the user's latest 'model' photo.
    2. Uses the product's thumbnail.
    3. Calls 'Nano Banana Pro' (Gemini) API.
    4. Saves result and returns it.
    """
    logger.info(f" [VTON] Starting virtual fitting request - User: {current_user.username}, Product: {product_id}")
    
    # 1. Get Product
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        logger.error(f" [VTON] Product {product_id} not found")
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.thumbnail_url:
        logger.error(f" [VTON] Product {product_id} has no thumbnail URL")
        raise HTTPException(status_code=400, detail="Product has no image")

    # 2. Get User's Model Photo
    upload_dir = "uploads/users"
    user_photo_path = None
    
    if os.path.exists(upload_dir):
        prefix = f"{current_user.username}_model_"
        photos = [
            f for f in os.listdir(upload_dir)
            if os.path.isfile(os.path.join(upload_dir, f)) and 
            f.startswith(prefix)
        ]
        # Sort by mtime (newest first)
        photos.sort(key=lambda x: os.path.getmtime(os.path.join(upload_dir, x)), reverse=True)
        
        if photos:
            user_photo_path = os.path.join(upload_dir, photos[0])
            logger.info(f" [VTON] Using user model photo: {user_photo_path}")
        else:
            logger.warning(f" [VTON] No model photos found with prefix {prefix} in {upload_dir}")
    else:
        logger.warning(f" [VTON] Upload directory {upload_dir} does not exist")

    if not user_photo_path:
        logger.error(f" [VTON] No model photo found for user {current_user.username}")
        raise HTTPException(status_code=400, detail="No model photo found. Please upload a photo in My Page.")

    # 3. Check existing fitting result
    existing_fitting = db.query(FittingResult).filter(
        FittingResult.user_id == current_user.id,
        FittingResult.product_id == product_id
    ).order_by(FittingResult.created_at.desc()).first()

    if existing_fitting:
         logger.info(f" [VTON] Found existing fitting record: {existing_fitting.fitting_image_url}")
         # Check if file still exists
         if existing_fitting.fitting_image_url.startswith("/"):
             local_path = existing_fitting.fitting_image_url.lstrip("/")
             if os.path.exists(local_path):
                 logger.info(f" [VTON] Returning existing fitting file: {local_path}")
                 return {
                     "status": "success",
                     "image_url": existing_fitting.fitting_image_url,
                     "message": "Retrieved existing fitting"
                 }
             else:
                 logger.warning(f" [VTON] Existing fitting file {local_path} not found on disk, will regenerate")

    # 4. Generate New Fitting
    logger.info(f" [VTON] Generating new VTON image for user {current_user.username}")
    fitting_dir = "uploads/fittings"
    os.makedirs(fitting_dir, exist_ok=True)
    
    filename = f"fitting_{current_user.id}_{product_id}_{uuid.uuid4().hex[:8]}.png"
    output_path = os.path.join(fitting_dir, filename)
    
    success = await generate_try_on_image(
        user_image_path=user_photo_path,
        product_image_url=product.thumbnail_url,
        output_path=output_path
    )
    
    if not success:
        logger.error(f" [VTON] VTON generation failed for user {current_user.username}")
        raise HTTPException(status_code=500, detail="VTON generation failed. Please try again later.")
        
    logger.info(f" [VTON] Successfully generated VTON image: {output_path}")

    # 5. Save to DB
    image_url = f"/api/uploads/fittings/{filename}"
    
    new_fitting = FittingResult(
        user_id=current_user.id,
        product_id=product_id,
        fitting_image_url=image_url
    )
    db.add(new_fitting)
    db.commit()
    db.refresh(new_fitting)
    
    logger.info(f" [VTON] Saved fitting result to DB for product {product_id}")
    
    return {
        "status": "success",
        "image_url": image_url,
        "message": "Generated new fitting"
    }
