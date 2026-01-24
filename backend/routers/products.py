"""
Products Router - Product tracking and price history
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
import re
import json

from database import get_db
from models import User, Product, UserInterest, PriceLog
from schemas import (
    ProductTrackRequest, ProductResponse, ProductListResponse,
    PriceHistoryResponse, PriceLogResponse
)
from routers.auth import get_current_user
from services.scraper import scrape_musinsa_product

router = APIRouter()


def extract_musinsa_id(url: str) -> str:
    """Extract product ID from Musinsa URL or return placeholder for OneLink URLs"""
    
    # Handle OneLink URLs - these will be resolved by the scraper
    if 'onelink.me' in url or 'musinsa.app.link' in url:
        # Extract a temporary ID from the OneLink path
        match = re.search(r'/([A-Za-z0-9]+)/?$', url)
        if match:
            return f"onelink_{match.group(1)}"
        return f"onelink_{hash(url) % 1000000}"
    
    # Handle various Musinsa URL formats
    patterns = [
        r'musinsa\.com/app/goods/(\d+)',
        r'musinsa\.com/goods/(\d+)',
        r'musinsa\.com/products/(\d+)',  # New format
        r'store\.musinsa\.com/app/goods/(\d+)',
        r'goods/(\d+)',
        r'products/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError("Could not extract product ID from URL. Use a Musinsa product URL or share link.")


@router.post("/track", response_model=ProductResponse)
async def track_product(
    request: ProductTrackRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a Musinsa product URL for price tracking"""
    
    try:
        musinsa_id = extract_musinsa_id(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # For OneLink URLs, we need to scrape first to get the real product ID
    is_onelink = musinsa_id.startswith('onelink_')
    
    if is_onelink:
        # Scrape first to resolve OneLink and get real product info
        try:
            product_info = await scrape_musinsa_product(request.url, musinsa_id)
            # Use the real product ID from scraper if available
            if product_info.get("product_id") and not product_info["product_id"].startswith('onelink_'):
                musinsa_id = product_info["product_id"]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not resolve share link: {str(e)}")
    
    # Check if product already exists (with resolved ID)
    product = db.query(Product).filter(Product.musinsa_id == musinsa_id).first()
    
    if not product:
        # Scrape product information (if not already done for OneLink)
        if not is_onelink:
            try:
                product_info = await scrape_musinsa_product(request.url, musinsa_id)
            except Exception as e:
                # If scraping fails, create with minimal info
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
        product = Product(
            musinsa_id=musinsa_id,
            url=request.url,
            title=product_info.get("title"),
            brand=product_info.get("brand"),
            thumbnail_url=product_info.get("thumbnail_url"),
            image_urls=json.dumps(product_info.get("image_urls", [])),
            original_price=product_info.get("original_price")
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        
        # Add initial price log if price was scraped
        if product_info.get("price"):
            price_log = PriceLog(
                product_id=product.id,
                price=product_info["price"],
                discount_rate=product_info.get("discount_rate")
            )
            db.add(price_log)
            db.commit()
    
    # Check if user already has this product in interests
    existing_interest = db.query(UserInterest).filter(
        UserInterest.user_id == current_user.id,
        UserInterest.product_id == product.id
    ).first()
    
    if not existing_interest:
        # Add to user's interests
        interest = UserInterest(
            user_id=current_user.id,
            product_id=product.id
        )
        db.add(interest)
        db.commit()
    
    # Get latest price
    latest_price = db.query(PriceLog).filter(
        PriceLog.product_id == product.id
    ).order_by(desc(PriceLog.captured_at)).first()
    
    # Parse image_urls from JSON
    image_urls = []
    if product.image_urls:
        try:
            image_urls = json.loads(product.image_urls)
        except:
            pass
    
    response = ProductResponse(
        id=product.id,
        musinsa_id=product.musinsa_id,
        url=product.url,
        title=product.title,
        brand=product.brand,
        thumbnail_url=product.thumbnail_url,
        image_urls=image_urls,
        original_price=product.original_price,
        is_garment_modeled=product.is_garment_modeled,
        current_price=latest_price.price if latest_price else None,
        discount_rate=latest_price.discount_rate if latest_price else None
    )
    
    return response


@router.get("", response_model=ProductListResponse)
async def get_user_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all products in user's interest list"""
    
    interests = db.query(UserInterest).filter(
        UserInterest.user_id == current_user.id
    ).all()
    
    products = []
    for interest in interests:
        product = interest.product
        
        # Get latest price
        latest_price = db.query(PriceLog).filter(
            PriceLog.product_id == product.id
        ).order_by(desc(PriceLog.captured_at)).first()
        
        # Parse image_urls from JSON
        image_urls = []
        if product.image_urls:
            try:
                image_urls = json.loads(product.image_urls)
            except:
                pass
        
        products.append(ProductResponse(
            id=product.id,
            musinsa_id=product.musinsa_id,
            url=product.url,
            title=product.title,
            brand=product.brand,
            thumbnail_url=product.thumbnail_url,
            image_urls=image_urls,
            original_price=product.original_price,
            is_garment_modeled=product.is_garment_modeled,
            current_price=latest_price.price if latest_price else None,
            discount_rate=latest_price.discount_rate if latest_price else None
        ))
    
    return ProductListResponse(products=products, total=len(products))


@router.get("/{product_id}/history", response_model=PriceHistoryResponse)
async def get_price_history(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get price history for a product"""
    
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get price logs
    price_logs = db.query(PriceLog).filter(
        PriceLog.product_id == product_id
    ).order_by(PriceLog.captured_at).all()
    
    history = [
        PriceLogResponse(
            id=log.id,
            price=log.price,
            discount_rate=log.discount_rate,
            captured_at=log.captured_at
        )
        for log in price_logs
    ]
    
    # Calculate min/max prices and their dates
    min_price = None
    max_price = None
    min_date = None
    max_date = None
    
    if price_logs:
        min_log = min(price_logs, key=lambda x: x.price)
        max_log = max(price_logs, key=lambda x: x.price)
        min_price = min_log.price
        max_price = max_log.price
        min_date = str(min_log.captured_at)
        max_date = str(max_log.captured_at)
    
    return PriceHistoryResponse(
        product_id=product_id,
        title=product.title,
        history=history,
        min_price=min_price,
        max_price=max_price,
        min_date=min_date,
        max_date=max_date
    )


@router.delete("/{product_id}")
async def remove_product_from_interests(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a product from user's interest list"""
    
    interest = db.query(UserInterest).filter(
        UserInterest.user_id == current_user.id,
        UserInterest.product_id == product_id
    ).first()
    
    if not interest:
        raise HTTPException(status_code=404, detail="Product not in your interest list")
    
    db.delete(interest)
    db.commit()
    
    return {"message": "Product removed from interest list"}
