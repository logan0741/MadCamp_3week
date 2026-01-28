"""
Domain Entities - SQLAlchemy ORM Models
"""
from domain.entities.user import User, UserInterest
from domain.entities.product import Product, PriceLog
from domain.entities.fitting import FittingResult

__all__ = [
    "User",
    "UserInterest",
    "Product",
    "PriceLog",
    "FittingResult",
]
