"""
User Router - User status and profile management
Thin controller layer - delegates to UserService
"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
import shutil
import os
import uuid

from core.database import get_db
from domain.entities import User
from domain.schemas import UserStatus, UserUpdate
from api.dependencies import get_current_user
from services.user_service import UserService

router = APIRouter()


@router.get("/status", response_model=UserStatus)
async def get_user_status(current_user: User = Depends(get_current_user)):
    """Get current user status including avatar creation status"""
    return current_user


@router.put("/profile", response_model=UserStatus)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    return UserService.update_profile(db, current_user, update_data)


@router.post("/interests/{product_id}")
async def add_interest(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add product to interest list"""
    try:
        UserService.add_interest(db, current_user, product_id)
        return {"status": "success", "message": "Product added to interests"}
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/interests")
async def get_interests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's interest list"""
    interests = UserService.get_interests(db, current_user)
    # Extract products from UserInterest objects
    products = [i.product for i in interests if i.product]
    
    # Simple list return for now, frontend expectations might vary
    return {
        "total": len(products),
        "products": products
    }


@router.delete("/interests/{product_id}")
async def remove_interest(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    UserService.remove_interest(db, current_user, product_id)
    return {"status": "success", "message": "Product removed from interests"}


@router.get("/photos")
async def get_user_photos(
    photo_type: str = "model",
    current_user: User = Depends(get_current_user)
):
    """List uploaded user photos by type (model or daily)"""
    import os
    
    upload_dir = "uploads/users"
    
    if not os.path.exists(upload_dir):
        return {"photos": []}
        
    try:
        # Filter files by username and type in filename
        # Pattern: {username}_{type}_*.ext
        prefix = f"{current_user.username}_{photo_type}_"
        photos = [
            f for f in os.listdir(upload_dir) 
            if os.path.isfile(os.path.join(upload_dir, f)) and 
            f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and
            f.startswith(prefix)
        ]
        
        # Sort by modification time (newest first)
        photos.sort(key=lambda x: os.path.getmtime(os.path.join(upload_dir, x)), reverse=True)

        return {
            "photos": [
                {
                    "filename": f,
                    "url": f"/api/uploads/users/{f}"
                }
                for f in photos
            ]
        }
    except Exception as e:
        return {"error": str(e), "photos": []}


@router.post("/photos")
async def upload_photo(
    file: UploadFile = File(...),
    photo_type: str = "model",
    current_user: User = Depends(get_current_user)
):
    """Upload user photo with type specification"""
    upload_dir = "uploads/users"
    os.makedirs(upload_dir, exist_ok=True)

    # For 'model' type, delete existing photos of that type
    if photo_type == "model":
        try:
            prefix = f"{current_user.username}_model_"
            for f in os.listdir(upload_dir):
                if f.startswith(prefix):
                    os.remove(os.path.join(upload_dir, f))
        except Exception as e:
            print(f"Error deleting old model photos: {e}")

    # Generate safe filename: {username}_{type}_{uuid}.{ext}
    ext = os.path.splitext(file.filename)[1]
    filename = f"{current_user.username}_{photo_type}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "status": "success",
            "filename": filename,
            "url": f"/api/uploads/users/{filename}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/ai/analyze")
async def analyze_photo(
    request: dict,  # {"filename": "..."}
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Selected photo analysis with "Fashion Terrorist" check
    1. Load Prompt
    2. Call GPU (analyze_custom)
    3. If valid, crawl/track products asynchronously (or sync if fast enough)
    """
    from services.ai_client import analyze_custom_prompt
    import os
    
    filename = request.get("filename")
    if not filename:
        return {"status": "error", "message": "Filename required"}
        
    # 1. Load Prompt
    prompt_path = os.path.join(os.path.dirname(__file__), "../../core/prompts/recommendation.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_text = f.read()
    except FileNotFoundError:
        return {"status": "error", "message": "Prompt file not found"}
        
    # 2. Construct Image URL (Accessible by GPU server)
    # Host IP is 192.168.0.77 based on check
    image_url = f"http://192.168.0.77:8000/uploads/users/{filename}"
    
    # 3. Call GPU
    result = await analyze_custom_prompt(image_url, prompt_text)
    
    if result.get("status") == "error":
        return result
        
    # 4. Check Fashion Terrorist
    terrorist_check = result.get("fashion_terrorist_check", {})
    if terrorist_check.get("is_terrorist"):
        return {
            "status": "fashion_terrorist",
            "message": terrorist_check.get("warning_message", "패션 테러리스트 경고!"),
            "data": result
        }
        
    # 5. Process Recommendations (Crawl & Save)
    # Import here to avoid circular deps
    from services.product_service import ProductService
    import logging
    logger = logging.getLogger(__name__)

    recommendations = result.get("recommendations", [])
    processed_recs = []
    
    # Process synchronously for MVP (limit 12 items, approx 30-60s)
    # Ideally should be BackgroundTasks, but user wants immediate feedback?
    # Let's do it sync for now, if timeout is issue, we switch to background.
    for item in recommendations:
        musinsa_id = item.get("musinsa_id")
        url = item.get("url")
        
        # Extract ID from URL if ID is missing but URL exists
        if not musinsa_id and url:
            import re
            match = re.search(r'/products/(\d+)', url)
            if match:
                musinsa_id = match.group(1)
        
        if musinsa_id:
            try:
                # Track/Crawl product
                product = ProductService.track_product(db, musinsa_id)
                if product:
                    # Return product details so frontend can add to interest later
                    # We do NOT add to interest automatically here.
                    processed_recs.append(product)
            except Exception as e:
                logger.error(f"Failed to track recommended item {musinsa_id}: {e}")
                
    return {
        "status": "success",
        "data": result,
        "processed_count": len(processed_recs)
    }
