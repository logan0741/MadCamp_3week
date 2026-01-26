"""
User Entity - User and UserInterest models
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class User(Base):
    """User table: onboarding status and body information"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    is_avatar_created = Column(Boolean, default=False)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    gender = Column(String(10), nullable=True)
    avatar_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    interests = relationship("UserInterest", back_populates="user", cascade="all, delete-orphan")
    ai_tasks = relationship("AITask", back_populates="user", cascade="all, delete-orphan")


class UserInterest(Base):
    """User-Product relationship table (M:N)"""
    __tablename__ = "user_interests"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="interests")
    product = relationship("Product", back_populates="interests")
