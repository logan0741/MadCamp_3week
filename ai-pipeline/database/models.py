"""
Database Models for AI Pipeline
Stores AI task results, file paths, and performance metrics.
"""

from datetime import datetime
from typing import Optional, List
import json

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, 
    Boolean, ForeignKey, Index, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AITaskResult(Base):
    """
    Stores results and metadata for AI processing tasks.
    """
    __tablename__ = "ai_task_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), unique=True, nullable=False, index=True)  # Celery task ID
    
    # Task metadata
    task_type = Column(String(50), nullable=False)  # vton, 3d_reconstruction, segmentation, etc.
    status = Column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    priority = Column(Integer, default=0)
    
    # Input parameters (JSON)
    input_params = Column(Text)  # JSON serialized input
    
    # Output file paths
    output_json_path = Column(String(500))
    output_image_paths = Column(Text)  # JSON array of paths
    output_glb_path = Column(String(500))
    output_obj_path = Column(String(500))
    
    # Performance metrics
    vram_peak_mb = Column(Integer)
    processing_time_sec = Column(Float)
    gpu_device = Column(String(20))
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_task_status_created', 'status', 'created_at'),
        Index('ix_task_type_status', 'task_type', 'status'),
    )
    
    def set_image_paths(self, paths: List[str]):
        """Set output image paths from list."""
        self.output_image_paths = json.dumps(paths)
    
    def get_image_paths(self) -> List[str]:
        """Get output image paths as list."""
        if self.output_image_paths:
            return json.loads(self.output_image_paths)
        return []
    
    def set_input_params(self, params: dict):
        """Set input parameters from dict."""
        self.input_params = json.dumps(params)
    
    def get_input_params(self) -> dict:
        """Get input parameters as dict."""
        if self.input_params:
            return json.loads(self.input_params)
        return {}


class MusinsaProduct(Base):
    """
    Stores Musinsa product metadata and generated assets.
    """
    __tablename__ = "musinsa_products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(50), unique=True, nullable=False, index=True)  # Musinsa product ID
    
    # Basic info
    name = Column(String(255), nullable=False)
    brand = Column(String(100))
    category = Column(String(50))  # 상의, 하의, 아우터, 원피스 등
    subcategory = Column(String(50))  # 티셔츠, 청바지, 코트 등
    
    # Pricing
    original_price = Column(Integer)
    sale_price = Column(Integer)
    discount_rate = Column(Integer)
    
    # PCCS color information
    pccs_hue = Column(Float)  # 0-360
    pccs_value = Column(Float)  # 0-10
    pccs_chroma = Column(Float)  # 0-14
    pccs_tone = Column(String(10))  # v, b, s, dp, lt, sf, d, dk, p, ltg, g, dkg
    primary_color_hex = Column(String(7))  # #RRGGBB
    
    # Size information (JSON)
    sizes_json = Column(Text)  # {"S": {"length": 70, "shoulder": 45, ...}, "M": {...}}
    available_sizes = Column(String(100))  # "S,M,L,XL"
    
    # Generated asset paths
    front_image_path = Column(String(500))
    back_image_path = Column(String(500))
    glb_path = Column(String(500))
    thumbnail_path = Column(String(500))
    
    # External URLs
    product_url = Column(String(500))
    image_url = Column(String(500))
    
    # Vector embedding for similarity search
    embedding_vector = Column(Text)  # JSON array of floats
    
    # Status
    is_active = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('ix_product_category_brand', 'category', 'brand'),
        Index('ix_product_pccs_tone', 'pccs_tone'),
    )
    
    def set_sizes(self, sizes: dict):
        """Set sizes from dict."""
        self.sizes_json = json.dumps(sizes, ensure_ascii=False)
    
    def get_sizes(self) -> dict:
        """Get sizes as dict."""
        if self.sizes_json:
            return json.loads(self.sizes_json)
        return {}
    
    def get_size(self, size_name: str) -> Optional[dict]:
        """Get specific size measurements."""
        sizes = self.get_sizes()
        return sizes.get(size_name)


class UserProfile(Base):
    """
    Stores user body measurements and color preferences.
    """
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), unique=True, nullable=False, index=True)
    
    # Body measurements (cm)
    height = Column(Float)
    weight = Column(Float)
    shoulder_width = Column(Float)
    chest = Column(Float)
    waist = Column(Float)
    hip = Column(Float)
    arm_length = Column(Float)
    leg_length = Column(Float)
    
    # Personal Color Analysis (PCA)
    pca_season = Column(String(20))  # spring_warm, summer_cool, autumn_warm, winter_cool
    pca_type = Column(String(20))  # bright, muted, light, deep
    skin_tone_hex = Column(String(7))
    
    # PCCS preferences
    preferred_tones = Column(String(100))  # Comma-separated: "v,b,lt"
    preferred_hue_range = Column(String(50))  # "0-60,300-360" for warm colors
    
    # Generated avatar
    avatar_glb_path = Column(String(500))
    avatar_thumbnail_path = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())


class RecommendationLog(Base):
    """
    Logs product recommendations for analytics and improvement.
    """
    __tablename__ = "recommendation_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), index=True)
    session_id = Column(String(36), index=True)
    
    # Query info
    query_type = Column(String(50))  # text_search, color_match, style_similar
    query_text = Column(Text)
    
    # Results (JSON array of product IDs with scores)
    recommendations_json = Column(Text)
    
    # Scoring breakdown
    text_similarity_score = Column(Float)
    pccs_distance_score = Column(Float)
    combined_score = Column(Float)
    
    # User interaction
    clicked_product_id = Column(String(50))
    purchased_product_id = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    def set_recommendations(self, recs: List[dict]):
        """Set recommendations from list of {product_id, score} dicts."""
        self.recommendations_json = json.dumps(recs)
    
    def get_recommendations(self) -> List[dict]:
        """Get recommendations as list."""
        if self.recommendations_json:
            return json.loads(self.recommendations_json)
        return []
