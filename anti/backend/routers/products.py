"""
Products Router - Product tracking and price history
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
import re

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
    """Extract product ID from Musinsa URL"""
    # Handle various Musinsa URL formats
    patterns = [
        r'musinsa\.com/app/goods/(\d+)',
        r'musinsa\.com/goods/(\d+)',
        r'store\.musinsa\.com/app/goods/(\d+)',
        r'goods/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError("Could not extract product ID from URL")


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
    
    # Check if product already exists
    product = db.query(Product).filter(Product.musinsa_id == musinsa_id).first()
    
    if not product:
        # Scrape product information
        try:
            product_info = await scrape_musinsa_product(request.url, musinsa_id)
        except Exception as e:
            # If scraping fails, create with minimal info
            product_info = {
                "title": f"상품 {musinsa_id}",
                "brand": None,
                "thumbnail_url": None,
                "price": None,
                "discount_rate": None
            }
        
        # Create new product
        product = Product(
            musinsa_id=musinsa_id,
            url=request.url,
            title=product_info.get("title"),
            brand=product_info.get("brand"),
            thumbnail_url=product_info.get("thumbnail_url")
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
    
    response = ProductResponse(
        id=product.id,
        musinsa_id=product.musinsa_id,
        url=product.url,
        title=product.title,
        brand=product.brand,
        thumbnail_url=product.thumbnail_url,
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
        
        products.append(ProductResponse(
            id=product.id,
            musinsa_id=product.musinsa_id,
            url=product.url,
            title=product.title,
            brand=product.brand,
            thumbnail_url=product.thumbnail_url,
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
    
    return PriceHistoryResponse(
        product_id=product_id,
        title=product.title,
        history=history
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
