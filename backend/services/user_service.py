"""
User Service - User management business logic
"""
from sqlalchemy.orm import Session

from domain.entities import User
from domain.schemas import UserUpdate


class UserService:
    """Service for user operations"""
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def update_profile(db: Session, user: User, update_data: UserUpdate) -> User:
        """Update user profile"""
        # height/weight removed
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def mark_avatar_created(db: Session, user: User, avatar_url: str) -> User:
        """Mark user's avatar as created"""
        # is_avatar_created removed from User model, skipping
        return user

    @staticmethod
    def add_interest(db: Session, user: User, product_id: int) -> User:
        """Add product to user's interest list"""
        from domain.entities import UserInterest, Product
        
        # Check if product exists
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        # Check if already exists
        existing = db.query(UserInterest).filter(
            UserInterest.user_id == user.id,
            UserInterest.product_id == product_id
        ).first()
        
        if not existing:
            interest = UserInterest(user_id=user.id, product_id=product_id)
            db.add(interest)
            db.commit()
            
        return user

    @staticmethod
    def get_interests(db: Session, user: User) -> list:
        """Get user's interested products"""
        return user.interests

    @staticmethod
    def remove_interest(db: Session, user: User, product_id: int) -> User:
        """Remove product from user's interest list"""
        from domain.entities import UserInterest
        
        db.query(UserInterest).filter(
            UserInterest.user_id == user.id,
            UserInterest.product_id == product_id
        ).delete()
        
        db.commit()
        return user
