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
        if update_data.height is not None:
            user.height = update_data.height
        if update_data.weight is not None:
            user.weight = update_data.weight
        
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def mark_avatar_created(db: Session, user: User, avatar_url: str) -> User:
        """Mark user's avatar as created"""
        user.is_avatar_created = True
        user.avatar_url = avatar_url
        db.commit()
        db.refresh(user)
        return user
