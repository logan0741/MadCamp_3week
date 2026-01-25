"""
Auth Service - Authentication business logic
"""
from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from domain.entities import User
from domain.schemas import UserCreate, Token
from core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


class AuthService:
    """Service for authentication operations"""
    
    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        """Register a new user"""
        # Check if username already exists
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Create new user
        new_user = User(
            username=user_data.username,
            password_hash=get_password_hash(user_data.password),
            height=user_data.height,
            weight=user_data.weight,
            is_avatar_created=False
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate user and return user if valid"""
        user = db.query(User).filter(User.username == username).first()
        
        if not user or not verify_password(password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    def create_user_token(user: User) -> Token:
        """Create access token for user"""
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return Token(access_token=access_token, token_type="bearer")
