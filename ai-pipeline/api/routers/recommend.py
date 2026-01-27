from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import asyncio
import random

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Schemas ---

class AnalyzeCustomRequest(BaseModel):
    image_url: str
    prompt: Optional[str] = None

class RecommendationItem(BaseModel):
    category: str
    brand: str
    product_name: str
    musinsa_id: Optional[str] = None
    url: Optional[str] = None
    color: str
    reason: str

class UserAnalysis(BaseModel):
    personal_color: str
    skin_tone_hex: str
    best_colors: List[str]
    worst_colors: List[str]

class FashionTerroristCheck(BaseModel):
    is_terrorist: bool
    mismatch_score: int
    warning_message: str

class AIAnalysisResult(BaseModel):
    user_analysis: UserAnalysis
    fashion_terrorist_check: FashionTerroristCheck
    recommendations: List[RecommendationItem]
    status: str = "success"

# --- Endpoints ---

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-recommend",
        "features": ["color_analysis", "style_recommendation", "custom_analysis"]
    }

@router.post("/analyze-custom", response_model=AIAnalysisResult)
async def analyze_custom(request: AnalyzeCustomRequest):
    """
    Analyzes user image for personal color and style compatibility.
    This runs on the GPU server.
    """
    logger.info(f"GPU Analysis Request: {request.image_url}")
    
    # Simulate GPU inference time
    await asyncio.sleep(1)
    
    # Logic: In real implementation, this would load the image and run the VLM (e.g. LLaVA, CogVLM).
    # For now, we simulate the output structure required by the backend.
    
    personal_colors = ["Spring Warm", "Summer Cool", "Autumn Warm", "Winter Cool"]
    selected_tone = random.choice(personal_colors)
    
    # Fashion Terrorist Logic (Random or based on some heuristic)
    is_terrorist = random.random() < 0.2
    
    recommendations = []
    if not is_terrorist:
        categories = ["Top", "Bottom", "Outer", "Shoes"]
        brands = ["Musinsa Standard", "Nike", "Adidas", "Covernat", "Fallett"]
        
        for i in range(12):
            cat = categories[i % 4]
            # Mocking IDs that likely exist or are just placeholders
            rec = RecommendationItem(
                category=cat,
                brand=random.choice(brands),
                product_name=f"Trendy {cat} {i+1}",
                musinsa_id=f"2000{i}",  # Mock ID
                url=f"https://www.musinsa.com/app/goods/2000{i}",
                color="Black",
                reason=f"Perfect for {selected_tone}"
            )
            recommendations.append(rec)
            
    result = AIAnalysisResult(
        user_analysis=UserAnalysis(
            personal_color=selected_tone,
            skin_tone_hex="#E0AC69",
            best_colors=["#FF0000"],
            worst_colors=["#00FF00"]
        ),
        fashion_terrorist_check=FashionTerroristCheck(
            is_terrorist=is_terrorist,
            mismatch_score=90 if is_terrorist else 5,
            warning_message="색상 매치가 아쉽습니다. 톤온톤 스타일링을 추천합니다." if is_terrorist else "훌륭합니다."
        ),
        recommendations=recommendations,
        status="success" if not is_terrorist else "fashion_terrorist"
    )
    
    return result
