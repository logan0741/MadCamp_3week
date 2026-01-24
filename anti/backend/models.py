"""
SQLAlchemy ORM Models for Musinsa Price Tracker
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, 
    ForeignKey, Date, DateTime, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database import Base


class User(Base):
    """User table: onboarding status and body information"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    is_avatar_created = Column(Boolean, default=False)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    avatar_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    interests = relationship("UserInterest", back_populates="user", cascade="all, delete-orphan")
    ai_tasks = relationship("AITask", back_populates="user", cascade="all, delete-orphan")


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
    is_garment_modeled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    interests = relationship("UserInterest", back_populates="product", cascade="all, delete-orphan")
    price_logs = relationship("PriceLog", back_populates="product", cascade="all, delete-orphan")
    ai_tasks = relationship("AITask", back_populates="product", cascade="all, delete-orphan")


class UserInterest(Base):
    """User-Product relationship table (M:N)"""
    __tablename__ = "user_interests"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="interests")
    product = relationship("Product", back_populates="interests")


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


class AITask(Base):
    """AI task status table: for managing VRAM worker tasks"""
    __tablename__ = "ai_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    task_type = Column(String(20), nullable=False)  # 'AVATAR' or 'GARMENT'
    status = Column(String(20), default='PENDING')  # PENDING, PROCESSING, COMPLETED, FAILED
    result_url = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="ai_tasks")
    product = relationship("Product", back_populates="ai_tasks")
