"""
Domain Entities - SQLAlchemy ORM Models
"""
from domain.entities.user import User, UserInterest, UserPhoto
from domain.entities.product import Product, PriceLog
from domain.entities.fitting import FittingResult

__all__ = [
    "User",
    "UserInterest",
    "UserPhoto",
    "Product",
    "PriceLog",
    "FittingResult",
]
