"""
AITask Entity - AI task status model
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from core.database import Base


class AITask(Base):
    """AI task status table: for managing VRAM worker tasks"""
    __tablename__ = "ai_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    task_type = Column(String(20), nullable=False)  # 'AVATAR' or 'GARMENT'
    status = Column(String(20), default='PENDING')  # PENDING, PROCESSING, COMPLETED, FAILED
    external_task_id = Column(String(64), nullable=True)
    result_url = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="ai_tasks")
    product = relationship("Product", back_populates="ai_tasks")
