"""
Product Service - Product management business logic
"""
from typing import List, Optional, Tuple
import re
import json

from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException

from domain.entities import User, Product, UserInterest, PriceLog
from domain.schemas import ProductResponse, PriceLogResponse, PriceHistoryResponse


class ProductService:
    """Service for product operations"""
    
    @staticmethod
    def extract_musinsa_id(url: str) -> str:
        """Extract product ID from Musinsa URL or return placeholder for OneLink URLs"""
        
        # Handle OneLink URLs - these will be resolved by the scraper
        if 'onelink.me' in url or 'musinsa.app.link' in url:
            match = re.search(r'/([A-Za-z0-9]+)/?$', url)
            if match:
                return f"onelink_{match.group(1)}"
            return f"onelink_{hash(url) % 1000000}"
        
        # Handle various Musinsa URL formats
        patterns = [
            r'musinsa\.com/app/goods/(\d+)',
            r'musinsa\.com/goods/(\d+)',
            r'musinsa\.com/products/(\d+)',
            r'store\.musinsa\.com/app/goods/(\d+)',
            r'goods/(\d+)',
            r'products/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError("Could not extract product ID from URL. Use a Musinsa product URL or share link.")
    
    @staticmethod
    def get_product_by_musinsa_id(db: Session, musinsa_id: str) -> Optional[Product]:
        """Get product by Musinsa ID"""
        return db.query(Product).filter(Product.musinsa_id == musinsa_id).first()
    
    @staticmethod
    def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        return db.query(Product).filter(Product.id == product_id).first()
    
    @staticmethod
    def create_product(db: Session, musinsa_id: str, url: str, product_info: dict) -> Product:
        """Create a new product"""
        product = Product(
            musinsa_id=musinsa_id,
            url=url,
            title=product_info.get("title"),
            brand=product_info.get("brand"),
            thumbnail_url=product_info.get("thumbnail_url"),
            image_urls=json.dumps(product_info.get("image_urls", [])),
            original_price=product_info.get("original_price")
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    
    @staticmethod
    def add_price_log(db: Session, product_id: int, price: int, discount_rate: Optional[int] = None) -> PriceLog:
        """Add or update price log for today (Upsert)"""
        from datetime import datetime
        from sqlalchemy import func
        
        today = datetime.now().date()
        
        # Check for existing log today to ensure 1 log per day
        existing_log = db.query(PriceLog).filter(
            PriceLog.product_id == product_id,
            func.date(PriceLog.captured_at) == today
        ).first()
        
        if existing_log:
            existing_log.price = price
            existing_log.discount_rate = discount_rate
            db.commit()
            db.refresh(existing_log)
            return existing_log
        
        price_log = PriceLog(
            product_id=product_id,
            price=price,
            discount_rate=discount_rate
        )
        db.add(price_log)
        db.commit()
        db.refresh(price_log)
        return price_log
    
    @staticmethod
    def get_latest_price(db: Session, product_id: int) -> Optional[PriceLog]:
        """Get the latest price log for a product"""
        return db.query(PriceLog).filter(
            PriceLog.product_id == product_id
        ).order_by(desc(PriceLog.captured_at)).first()
    
    @staticmethod
    def check_user_interest(db: Session, user_id: int, product_id: int) -> bool:
        """Check if user has this product in interests"""
        existing = db.query(UserInterest).filter(
            UserInterest.user_id == user_id,
            UserInterest.product_id == product_id
        ).first()
        return existing is not None
    
    @staticmethod
    def add_to_interests(db: Session, user_id: int, product_id: int) -> UserInterest:
        """Add product to user's interests"""
        interest = UserInterest(
            user_id=user_id,
            product_id=product_id
        )
        db.add(interest)
        db.commit()
        return interest
    
    @staticmethod
    def remove_from_interests(db: Session, user_id: int, product_id: int) -> bool:
        """Remove product from user's interests"""
        interest = db.query(UserInterest).filter(
            UserInterest.user_id == user_id,
            UserInterest.product_id == product_id
        ).first()
        
        if not interest:
            return False
        
        db.delete(interest)
        db.commit()
        return True
    
    @staticmethod
    def get_user_products(db: Session, user_id: int) -> List[Tuple[Product, Optional[PriceLog]]]:
        """Get all products in user's interest list with latest prices"""
        interests = db.query(UserInterest).filter(
            UserInterest.user_id == user_id
        ).all()
        
        result = []
        for interest in interests:
            product = interest.product
            latest_price = db.query(PriceLog).filter(
                PriceLog.product_id == product.id
            ).order_by(desc(PriceLog.captured_at)).first()
            result.append((product, latest_price))
        
        return result
    
    @staticmethod
    def build_product_response(product: Product, latest_price: Optional[PriceLog]) -> ProductResponse:
        """Build a ProductResponse from product and price log"""
        # Parse image_urls from JSON
        image_urls = []
        if product.image_urls:
            try:
                image_urls = json.loads(product.image_urls)
            except:
                pass
        
        return ProductResponse(
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
    
    @staticmethod
    def get_price_history(db: Session, product_id: int) -> PriceHistoryResponse:
        """Get price history for a product"""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
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
