from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
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
        "features": ["color_analysis", "pccs_tone", "style_recommendation", "custom_analysis"]
    }

@router.post("/analyze-custom", response_model=AIAnalysisResult)
async def analyze_custom(request: AnalyzeCustomRequest):
    """
    Mock/Stub implementation of Custom Analysis.
    In a real scenario, this would call an LLM (OpenAI/Anthropic/Gemini)
    or a local Grid model to process the image and prompt.
    """
    logger.info(f"Analyzing Image: {request.image_url}")
    logger.info(f"Generic Prompt: {request.prompt[:50]}...")
    
    # Simulate processing delay
    await asyncio.sleep(2)
    
    # Mock Logic: Randomly decide Personal Color and Terrorist Status
    # for demonstration purposes.
    
    personal_colors = ["Spring Warm", "Summer Cool", "Autumn Warm", "Winter Cool"]
    selected_tone = random.choice(personal_colors)
    
    is_terrorist = random.random() < 0.3  # 30% chance of being a terrorist in simulation
    
    recommendations = []
    if not is_terrorist:
        # Generate 12 mock items (Cream style)
        categories = ["Top", "Bottom", "Outer", "Shoes"]
        brands = ["Musinsa Standard", "Nike", "Adidas", "Covernat", "Thisisneverthat"]
        
        for i in range(12):
            cat = categories[i % 4]
            rec = RecommendationItem(
                category=cat,
                brand=random.choice(brands),
                product_name=f"{cat} Item {i+1}",
                musinsa_id=f"1000{i}",
                url=f"https://www.musinsa.com/app/goods/1000{i}",
                color="Black" if i % 2 == 0 else "White",
                reason=f"Matches your {selected_tone} tone."
            )
            recommendations.append(rec)
    
    result = AIAnalysisResult(
        user_analysis=UserAnalysis(
            personal_color=selected_tone,
            skin_tone_hex="#F5CBA7",
            best_colors=["#FF0000", "#00FF00"],
            worst_colors=["#0000FF", "#FFFF00"]
        ),
        fashion_terrorist_check=FashionTerroristCheck(
            is_terrorist=is_terrorist,
            mismatch_score=85 if is_terrorist else 10,
            warning_message="색상 조합이 너무 난해합니다! 톤온톤 매칭을 시도해보세요." if is_terrorist else "좋은 스타일입니다."
        ),
        recommendations=recommendations,
        status="success" if not is_terrorist else "fashion_terrorist" # Optional status override
    )
    
    # Check if prompt requested "success" status explicitly despite terrorist?
    # Keeping it simple for now.
    
    return result

# Note: Other endpoints (recommend, analyze-color) can be added here if needed to fully verify the GPU server interface.
