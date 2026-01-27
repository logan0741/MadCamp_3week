"""
Domain Entities - SQLAlchemy ORM Models
"""
from domain.entities.user import User, UserInterest
from domain.entities.product import Product, PriceLog

__all__ = [
    "User",
    "UserInterest",
    "Product",
    "PriceLog",
]
