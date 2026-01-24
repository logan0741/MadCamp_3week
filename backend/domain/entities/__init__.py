"""
Domain Entities - SQLAlchemy ORM Models
"""
from domain.entities.user import User, UserInterest
from domain.entities.product import Product, PriceLog
from domain.entities.ai_task import AITask

__all__ = [
    "User",
    "UserInterest",
    "Product",
    "PriceLog",
    "AITask",
]
