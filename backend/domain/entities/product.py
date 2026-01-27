"""
Product Entity - Product and PriceLog models
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Date, DateTime, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.persistence.database import Base


class Product(Base):
    """Product table: Musinsa product information"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    musinsa_id = Column(String(20), unique=True, nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(String(255), nullable=True)
    brand = Column(String(100), nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    image_urls = Column(Text, nullable=True)  # JSON array of image URLs for carousel
    original_price = Column(Integer, nullable=True)  # Price before discount
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # AI Analysis Fields
    is_garment_modeled = Column(Boolean, default=False)
    
    # Color Analysis
    pccs_hue = Column(String(20), nullable=True)
    pccs_value = Column(String(20), nullable=True)
    pccs_chroma = Column(String(20), nullable=True)
    pccs_tone = Column(String(20), nullable=True)
    primary_color_hex = Column(String(20), nullable=True)
    color_temperature = Column(String(20), nullable=True)

    # Relationships
    interests = relationship("UserInterest", back_populates="product", cascade="all, delete-orphan")
    price_logs = relationship("PriceLog", back_populates="product", cascade="all, delete-orphan")


class PriceLog(Base):
    """Price history table: time-series data for charts"""
    __tablename__ = "price_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    price = Column(Integer, nullable=False)
    discount_rate = Column(Integer, nullable=True)
    captured_at = Column(Date, server_default=func.current_date())

    # Unique constraint for product + date combination
    __table_args__ = (
        UniqueConstraint('product_id', 'captured_at', name='uq_product_date'),
    )

    # Relationships
    product = relationship("Product", back_populates="price_logs")
