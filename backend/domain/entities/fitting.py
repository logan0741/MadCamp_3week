"""
Fitting Entity - Virtual Try-on results
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.persistence.database import Base


class FittingResult(Base):
    """Fitting result table: Stores generated VTON images"""
    __tablename__ = "fitting_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    fitting_image_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="fittings")
    product = relationship("Product", backref="fittings")
