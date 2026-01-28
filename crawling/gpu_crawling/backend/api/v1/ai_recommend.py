"""
AI Recommendation API - Called by CPU server for product recommendations
Provides color analysis and style-based recommendations using PCCS.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import httpx
from sqlalchemy.orm import Session

from services.color_analyzer import (
    analyze_image_colors,
    analyze_product_colors,
    find_complementary_colors,
    PCCSColor,
    ColorAnalysisResult,
)
from services.recommendation_service import extract_category_from_path
from core.config import settings
from core.database import get_db
from api.dependencies import get_current_user
from domain.entities import User, Product, UserInterest

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class ProductInput(BaseModel):
    """Product data sent from CPU server"""
    id: str
    title: Optional[str] = None
    brand: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_urls: Optional[List[str]] = []
    price: Optional[int] = None
    category: Optional[str] = None
    category_main: Optional[str] = None
    style_tags: Optional[List[str]] = []


class RecommendRequest(BaseModel):
    """Request for product recommendations"""
    product: ProductInput
    user_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tone_preference: Optional[str] = None  # 'warm', 'cool', 'neutral'
    preferred_palette: Optional[List[str]] = None  # List of hex colors
    limit: int = Field(default=6, ge=1, le=20)


class ColorAnalysis(BaseModel):
    """PCCS color analysis result"""
    dominant_hex: str
    pccs_hue: float
    pccs_value: float
    pccs_chroma: float
    pccs_tone: str
    color_palette: List[str]
    color_temperature: str  # warm/cool/neutral
    complementary_suggestions: List[Dict[str, Any]]


class RecommendedProduct(BaseModel):
    """A recommended product"""
    product_id: str
    score: float
    match_reasons: List[str]
    pccs_tone: Optional[str] = None


class RecommendResponse(BaseModel):
    """Response with recommendations and color analysis"""
    status: str
    color_analysis: Optional[ColorAnalysis] = None
    recommendations: List[RecommendedProduct]
    style_suggestions: List[str]
    message: Optional[str] = None


class ColorAnalyzeRequest(BaseModel):
    """Request for color analysis only"""
    image_url: str
    additional_urls: Optional[List[str]] = []


class ColorAnalyzeResponse(BaseModel):
    """Response with color analysis"""
    status: str
    analysis: Optional[ColorAnalysis] = None
    message: Optional[str] = None


class BatchColorRequest(BaseModel):
    """Batch color analysis request"""
    products: List[ProductInput]


class BatchColorResponse(BaseModel):
    """Batch color analysis response"""
    status: str
    results: List[Dict[str, Any]]
    processed: int
    failed: int


# ============================================
# Helper Functions
# ============================================

def color_result_to_analysis(result: ColorAnalysisResult) -> ColorAnalysis:
    """Convert ColorAnalysisResult to API response model"""
    primary = result.primary_color
    return ColorAnalysis(
        dominant_hex=result.dominant_hex,
        pccs_hue=primary.hue,
        pccs_value=primary.value,
        pccs_chroma=primary.chroma,
        pccs_tone=primary.tone,
        color_palette=result.color_palette,
        color_temperature=result.category_suggestion,
        complementary_suggestions=find_complementary_colors(primary)
    )


def generate_style_suggestions(
    color_analysis: Optional[ColorAnalysis],
    user_preferences: Dict[str, Any]
) -> List[str]:
    """Generate style suggestions based on color and preferences"""
    suggestions = []

    if not color_analysis:
        return ["색상 분석을 완료하면 더 정확한 추천을 받을 수 있습니다."]

    tone = color_analysis.pccs_tone
    temp = color_analysis.color_temperature

    # Tone-based suggestions
    tone_suggestions = {
        'v': "비비드 톤의 선명한 색상으로 포인트를 줘보세요.",
        'b': "브라이트 톤으로 밝고 화사한 느낌을 연출하세요.",
        's': "스트롱 톤으로 강렬하면서도 세련된 룩을 완성하세요.",
        'dp': "딥 톤의 깊이감 있는 색상으로 고급스러움을 더하세요.",
        'lt': "라이트 톤으로 부드럽고 상쾌한 분위기를 연출하세요.",
        'sf': "소프트 톤으로 자연스럽고 편안한 스타일링을 해보세요.",
        'd': "덜 톤의 차분한 색상으로 세련된 무드를 만들어보세요.",
        'dk': "다크 톤으로 시크하고 모던한 느낌을 줘보세요.",
        'p': "페일 톤의 은은한 파스텔로 청순한 룩을 연출하세요.",
        'W': "화이트 계열로 깔끔하고 미니멀한 스타일을 완성하세요.",
        'Bk': "블랙 계열로 모던하고 시크한 분위기를 연출하세요.",
        'Gy': "그레이 계열로 세련되고 차분한 코디를 해보세요.",
    }

    if tone in tone_suggestions:
        suggestions.append(tone_suggestions[tone])

    # Temperature-based suggestions
    if temp == 'warm':
        suggestions.append("따뜻한 톤의 색상이어서 같은 웜톤 제품과 잘 어울립니다.")
    elif temp == 'cool':
        suggestions.append("차가운 톤의 색상이어서 쿨톤 계열 제품과 매칭해보세요.")
    else:
        suggestions.append("뉴트럴 톤이어서 다양한 색상과 자유롭게 매칭 가능합니다.")

    # Complementary color suggestions
    suggestions.append("보색 또는 유사색 조합으로 스타일링하면 더욱 세련됩니다.")

    return suggestions


# ============================================
# API Endpoints
# ============================================

@router.get("/health")
async def health_check():
    """AI recommendation service health check"""
    return {
        "status": "healthy",
        "service": "ai-recommend",
        "features": ["color_analysis", "pccs_tone", "style_recommendation"]
    }


@router.post("/analyze-color", response_model=ColorAnalyzeResponse)
async def analyze_color(request: ColorAnalyzeRequest):
    """
    Analyze color from product image.

    Returns PCCS color analysis including:
    - Dominant color (hex)
    - PCCS coordinates (hue, value, chroma)
    - PCCS tone classification
    - Color palette
    - Color temperature (warm/cool/neutral)
    - Complementary color suggestions
    """
    try:
        result = await analyze_image_colors(request.image_url)

        if not result:
            # Try additional URLs if main fails
            for url in (request.additional_urls or [])[:3]:
                result = await analyze_image_colors(url)
                if result:
                    break

        if not result:
            return ColorAnalyzeResponse(
                status="failed",
                analysis=None,
                message="이미지에서 색상을 추출할 수 없습니다."
            )

        analysis = color_result_to_analysis(result)

        return ColorAnalyzeResponse(
            status="success",
            analysis=analysis,
            message=None
        )

    except Exception as e:
        logger.error(f"Color analysis failed: {e}")
        return ColorAnalyzeResponse(
            status="error",
            analysis=None,
            message=f"색상 분석 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/recommend", response_model=RecommendResponse)
async def get_recommendations(request: RecommendRequest):
    """
    Get product recommendations based on color analysis.

    This endpoint is called by the CPU server with product data.
    It analyzes the product's colors and returns:
    - Color analysis results
    - Style-based recommendations
    - Matching suggestions
    """
    product = request.product
    color_analysis = None

    # Analyze product colors if image available
    if product.thumbnail_url or product.image_urls:
        try:
            result = await analyze_product_colors(
                thumbnail_url=product.thumbnail_url or "",
                image_urls=product.image_urls or []
            )

            if result:
                color_analysis = ColorAnalysis(
                    dominant_hex=result['primary_color_hex'],
                    pccs_hue=result['pccs_hue'],
                    pccs_value=result['pccs_value'],
                    pccs_chroma=result['pccs_chroma'],
                    pccs_tone=result['pccs_tone'],
                    color_palette=result['color_palette'],
                    color_temperature=result['color_temperature'],
                    complementary_suggestions=result['complementary_suggestions']
                )
        except Exception as e:
            logger.warning(f"Color analysis failed for product {product.id}: {e}")

    # Generate style suggestions
    style_suggestions = generate_style_suggestions(
        color_analysis,
        request.user_preferences or {}
    )

    # Generate recommendations based on color analysis
    recommendations = []

    if color_analysis:
        # Create recommendation based on analyzed data
        match_reasons = []

        if color_analysis.pccs_tone:
            match_reasons.append(f"tone:{color_analysis.pccs_tone}")
        if color_analysis.color_temperature:
            match_reasons.append(f"temp:{color_analysis.color_temperature}")

        # Add the source product as a base recommendation
        recommendations.append(RecommendedProduct(
            product_id=product.id,
            score=1.0,
            match_reasons=match_reasons,
            pccs_tone=color_analysis.pccs_tone
        ))

    return RecommendResponse(
        status="success",
        color_analysis=color_analysis,
        recommendations=recommendations,
        style_suggestions=style_suggestions,
        message=None
    )


@router.post("/batch-analyze", response_model=BatchColorResponse)
async def batch_analyze_colors(request: BatchColorRequest):
    """
    Batch color analysis for multiple products.

    Used by CPU server to analyze colors for multiple products at once.
    """
    results = []
    processed = 0
    failed = 0

    for product in request.products:
        try:
            if not product.thumbnail_url and not product.image_urls:
                results.append({
                    "product_id": product.id,
                    "status": "skipped",
                    "reason": "no_image"
                })
                failed += 1
                continue

            result = await analyze_product_colors(
                thumbnail_url=product.thumbnail_url or "",
                image_urls=product.image_urls or []
            )

            if result:
                results.append({
                    "product_id": product.id,
                    "status": "success",
                    "color_data": result
                })
                processed += 1
            else:
                results.append({
                    "product_id": product.id,
                    "status": "failed",
                    "reason": "analysis_failed"
                })
                failed += 1

        except Exception as e:
            logger.error(f"Batch analysis failed for {product.id}: {e}")
            results.append({
                "product_id": product.id,
                "status": "error",
                "reason": str(e)
            })
            failed += 1

    return BatchColorResponse(
        status="success",
        results=results,
        processed=processed,
        failed=failed
    )


@router.post("/style-match")
async def find_style_matches(
    source_color_hex: str,
    target_tone: Optional[str] = None,
    match_type: str = "analogous"
):
    """
    Find matching colors based on color theory.

    Args:
        source_color_hex: Source color in hex format
        target_tone: Preferred PCCS tone (optional)
        match_type: Type of color match (complementary, analogous, triadic, same_tone)

    Returns:
        Color matching suggestions
    """
    from services.color_analyzer import hex_to_rgb, analyze_rgb_color

    try:
        r, g, b = hex_to_rgb(source_color_hex)
        source_color = analyze_rgb_color(r, g, b)
        suggestions = find_complementary_colors(source_color)

        # Filter by match type if specified
        if match_type != "all":
            suggestions = [s for s in suggestions if s['type'] == match_type]

        return {
            "status": "success",
            "source_color": {
                "hex": source_color.hex_color,
                "pccs_tone": source_color.tone,
                "hue": source_color.hue,
                "value": source_color.value,
                "chroma": source_color.chroma
            },
            "suggestions": suggestions
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid color: {str(e)}")


# ============================================
# Fashion Terrorist Feature
# ============================================

class InterestedProduct(BaseModel):
    """Product user is interested in"""
    product_id: str
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    pccs_tone: Optional[str] = None
    color_temperature: Optional[str] = None


class AnalyzeWithProductsRequest(BaseModel):
    """Request for user photo + products analysis"""
    user_photo_url: str
    interested_products: List[InterestedProduct]
    recommendation_count: int = Field(default=12, ge=1, le=24)


class SkinToneAnalysis(BaseModel):
    """User skin tone analysis result"""
    pccs_tone: str
    color_temperature: str
    season: str
    hex: str
    value: float
    chroma: float


class ProductRecommendation(BaseModel):
    """Recommended product with match info"""
    product_id: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    pccs_tone: Optional[str] = None
    match_score: float
    match_reason: str


class AnalyzeWithProductsResponse(BaseModel):
    """Response with Fashion Terrorist evaluation"""
    status: str  # "success" | "warning" | "error"
    user_skin_tone: Optional[SkinToneAnalysis] = None
    compatibility_score: float
    fashion_terrorist_flag: bool
    fashion_terrorist_reason: Optional[str] = None
    recommendations: List[ProductRecommendation]
    better_alternatives: Optional[List[ProductRecommendation]] = None
    style_advice: str


class GenerateRecommendationRequest(BaseModel):
    """Request for photo-based recommendations"""
    user_photo_url: str
    interested_product_ids: Optional[List[int]] = Field(default_factory=list)
    recommendation_count: int = Field(default=12, ge=1, le=24)


class RecommendationProductDetail(BaseModel):
    """Recommended product detail for frontend"""
    id: int
    musinsa_id: str
    url: str
    title: Optional[str] = None
    brand: Optional[str] = None
    thumbnail_url: Optional[str] = None
    original_price: Optional[int] = None
    category_main: Optional[str] = None
    pccs_tone: Optional[str] = None
    color_temperature: Optional[str] = None
    match_score: float
    match_reason: str


class GenerateRecommendationResponse(BaseModel):
    """Response for photo-based recommendations"""
    status: str  # "success" | "warning" | "error"
    user_skin_tone: Optional[SkinToneAnalysis] = None
    compatibility_score: float
    fashion_terrorist_flag: bool
    fashion_terrorist_reason: Optional[str] = None
    recommendations: List[RecommendationProductDetail]
    style_advice: str
    total: int


# Fashion Terrorist Logic
EXTREME_TONE_MISMATCH = {
    # (피부톤, 의류톤) -> 경고 메시지
    ("p", "v"): "페일 톤 피부에 비비드 톤은 과도한 대비를 만들어 피부가 창백해 보입니다",
    ("p", "dp"): "페일 톤 피부에 딥 톤은 얼굴이 칙칙해 보일 수 있습니다",
    ("ltg", "v"): "라이트 그레이시 톤에 비비드는 부조화를 일으킵니다",
    ("dkg", "p"): "다크 그레이시 톤에 페일 톤은 불균형한 대비입니다",
    ("dk", "p"): "다크 톤 피부에 페일 톤은 부자연스럽습니다",
    ("g", "v"): "그레이시 톤에 비비드는 과도한 대비로 어색합니다",
    ("sf", "v"): "소프트 톤 피부에 비비드는 얼굴이 묻힐 수 있습니다",
}

TEMP_CLASH_WARNINGS = {
    ("warm", "cool"): "웜톤 피부에 쿨톤 의류는 얼굴이 노랗게/칙칙해 보입니다",
    ("cool", "warm"): "쿨톤 피부에 웜톤 의류는 얼굴이 붉어 보입니다",
}

# 피부 시즌별 추천 톤
SEASON_RECOMMENDED_TONES = {
    "spring": ["b", "lt", "v", "s", "p"],       # 밝고 선명한 웜톤
    "summer": ["sf", "lt", "ltg", "p", "g"],    # 부드럽고 차분한 쿨톤
    "autumn": ["dp", "d", "s", "dkg", "dk"],    # 깊고 따뜻한 톤
    "winter": ["v", "dk", "Bk", "W", "s"],      # 선명하고 대비 있는 쿨톤
}


def determine_season(skin_temp: str, skin_value: float) -> str:
    """피부 색온도와 명도로 시즌 판별"""
    if skin_temp == "warm":
        return "spring" if skin_value >= 6.0 else "autumn"
    elif skin_temp == "cool":
        return "summer" if skin_value >= 6.0 else "winter"
    else:
        # neutral은 명도 기준
        return "summer" if skin_value >= 6.0 else "autumn"


def check_fashion_terrorist(
    skin_tone: str,
    skin_temp: str,
    products: List[InterestedProduct]
) -> tuple[bool, Optional[str], float]:
    """
    Fashion Terrorist 여부 판별

    Returns:
        (is_terrorist, reason, compatibility_score)
    """
    if not products:
        return False, None, 0.5

    mismatch_scores = []
    worst_reason = None

    for product in products:
        product_tone = product.pccs_tone or "g"
        product_temp = product.color_temperature or "neutral"

        # 톤 불일치 체크
        if (skin_tone, product_tone) in EXTREME_TONE_MISMATCH:
            worst_reason = EXTREME_TONE_MISMATCH[(skin_tone, product_tone)]
            mismatch_scores.append(0.2)
            continue

        # 색온도 충돌 체크
        if (skin_temp, product_temp) in TEMP_CLASH_WARNINGS:
            if worst_reason is None:
                worst_reason = TEMP_CLASH_WARNINGS[(skin_temp, product_temp)]
            mismatch_scores.append(0.3)
            continue

        # 일반 조화도 계산
        tone_harmony = calculate_tone_harmony(skin_tone, product_tone)
        temp_harmony = 1.0 if skin_temp == product_temp or "neutral" in [skin_temp, product_temp] else 0.5
        score = tone_harmony * 0.6 + temp_harmony * 0.4
        mismatch_scores.append(score)

    avg_score = sum(mismatch_scores) / len(mismatch_scores) if mismatch_scores else 0.5

    # Fashion Terrorist 판정: 점수 0.3 미만
    is_terrorist = avg_score < 0.3

    return is_terrorist, worst_reason if is_terrorist else None, avg_score


def calculate_tone_harmony(skin_tone: str, product_tone: str) -> float:
    """두 톤 간의 조화도 계산 (0.0 ~ 1.0)"""
    # 같은 톤
    if skin_tone == product_tone:
        return 1.0

    # 조화로운 톤 조합
    HARMONY_MAP = {
        "sf": ["sf", "lt", "g", "ltg", "p"],
        "lt": ["lt", "sf", "p", "b", "ltg"],
        "g": ["g", "sf", "ltg", "dkg", "d"],
        "ltg": ["ltg", "lt", "g", "p", "sf"],
        "dkg": ["dkg", "g", "dk", "d"],
        "p": ["p", "lt", "ltg", "sf"],
        "b": ["b", "lt", "v", "s"],
        "v": ["v", "b", "s", "dp"],
        "s": ["s", "v", "b", "dp"],
        "dp": ["dp", "s", "d", "dk"],
        "d": ["d", "dp", "dkg", "sf"],
        "dk": ["dk", "dkg", "dp", "d"],
    }

    harmonious = HARMONY_MAP.get(skin_tone, [])
    if product_tone in harmonious:
        return 0.8

    # 그 외
    return 0.5


def _normalize_category(product: Product) -> str:
    if product.category_main:
        return product.category_main
    category_main, _ = extract_category_from_path(product.category_path or "")
    return category_main


def _score_product_match(
    skin_tone: str,
    skin_temp: str,
    product: Product
) -> tuple[float, str]:
    product_tone = product.pccs_tone or "g"
    product_temp = product.color_temperature or "neutral"

    tone_score = calculate_tone_harmony(skin_tone, product_tone)
    temp_score = 1.0 if skin_temp == product_temp or "neutral" in [skin_temp, product_temp] else 0.5
    final_score = round(tone_score * 0.6 + temp_score * 0.4, 2)
    reason = f"피부톤 {skin_tone}에 {product_tone} 톤 조합"

    return final_score, reason


def _select_recommendations(
    db: Session,
    recommended_tones: List[str],
    limit: int,
    skin_tone: str,
    skin_temp: str,
) -> List[RecommendationProductDetail]:
    category_targets = {
        "상의": 4,
        "하의": 3,
        "아우터": 2,
        "신발": 2,
        "액세서리": 1,
    }

    candidates = (
        db.query(Product)
        .filter(
            Product.thumbnail_url.isnot(None),
            Product.pccs_tone.in_(recommended_tones),
        )
        .order_by(Product.created_at.desc())
        .limit(240)
        .all()
    )

    if not candidates:
        candidates = (
            db.query(Product)
            .filter(Product.thumbnail_url.isnot(None))
            .order_by(Product.created_at.desc())
            .limit(240)
            .all()
        )

    scored: Dict[int, tuple[float, str]] = {}
    for product in candidates:
        scored[product.id] = _score_product_match(skin_tone, skin_temp, product)

    bucketed: Dict[str, List[Product]] = {k: [] for k in category_targets.keys()}
    others: List[Product] = []

    for product in candidates:
        category = _normalize_category(product)
        if category in bucketed:
            bucketed[category].append(product)
        else:
            others.append(product)

    for category in bucketed.keys():
        bucketed[category].sort(key=lambda p: scored[p.id][0], reverse=True)
    others.sort(key=lambda p: scored[p.id][0], reverse=True)

    selected: List[RecommendationProductDetail] = []
    used_ids: set[int] = set()

    for category, count in category_targets.items():
        for product in bucketed[category][:count]:
            if product.id in used_ids:
                continue
            score, reason = scored[product.id]
            selected.append(
                RecommendationProductDetail(
                    id=product.id,
                    musinsa_id=product.musinsa_id,
                    url=product.url,
                    title=product.title,
                    brand=product.brand,
                    thumbnail_url=product.thumbnail_url,
                    original_price=product.original_price,
                    category_main=product.category_main,
                    pccs_tone=product.pccs_tone,
                    color_temperature=product.color_temperature,
                    match_score=score,
                    match_reason=reason,
                )
            )
            used_ids.add(product.id)
            if len(selected) >= limit:
                break
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        fallback_pool = others + [p for group in bucketed.values() for p in group]
        for product in fallback_pool:
            if len(selected) >= limit:
                break
            if product.id in used_ids:
                continue
            score, reason = scored[product.id]
            selected.append(
                RecommendationProductDetail(
                    id=product.id,
                    musinsa_id=product.musinsa_id,
                    url=product.url,
                    title=product.title,
                    brand=product.brand,
                    thumbnail_url=product.thumbnail_url,
                    original_price=product.original_price,
                    category_main=product.category_main,
                    pccs_tone=product.pccs_tone,
                    color_temperature=product.color_temperature,
                    match_score=score,
                    match_reason=reason,
                )
            )
            used_ids.add(product.id)

    return selected[:limit]


async def _request_gpu_analysis(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    base_url = settings.GPU_RECOMMEND_BASE_URL.strip()
    if not base_url:
        return None

    try:
        async with httpx.AsyncClient(timeout=settings.GPU_RECOMMEND_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/ai-recommend/analyze-with-products",
                json=payload,
            )
        if response.status_code >= 400:
            logger.warning("GPU analysis failed: %s", response.text)
            return None
        return response.json()
    except Exception as exc:
        logger.warning("GPU analysis request error: %s", exc)
        return None


def _parse_gpu_skin_tone(data: Dict[str, Any]) -> Optional[SkinToneAnalysis]:
    raw = data.get("user_skin_tone") or data.get("user_analysis", {}).get("skin_tone")
    if not raw:
        return None

    return SkinToneAnalysis(
        pccs_tone=raw.get("pccs_tone") or raw.get("tone") or "g",
        color_temperature=raw.get("color_temperature") or raw.get("temperature") or "neutral",
        season=_normalize_season(raw.get("season") or "summer"),
        hex=raw.get("hex") or "#000000",
        value=float(raw.get("value", 0.0)),
        chroma=float(raw.get("chroma", 0.0)),
    )


def _normalize_season(season: str) -> str:
    if not season:
        return "summer"
    lower = season.lower()
    if "spring" in lower:
        return "spring"
    if "summer" in lower:
        return "summer"
    if "autumn" in lower or "fall" in lower:
        return "autumn"
    if "winter" in lower:
        return "winter"
    return season


@router.post("/analyze-with-products", response_model=AnalyzeWithProductsResponse)
async def analyze_with_products(request: AnalyzeWithProductsRequest):
    """
    사용자 사진 + 관심 상품을 함께 분석하여 Fashion Terrorist 여부 판별

    - 사용자 피부톤 분석 (PCCS)
    - 관심 상품과의 조화도 계산
    - Fashion Terrorist 경고 플래그
    - 12개 추천 상품 반환
    """
    try:
        # 1. 사용자 피부톤 분석
        skin_result = await analyze_image_colors(request.user_photo_url)

        if not skin_result:
            return AnalyzeWithProductsResponse(
                status="error",
                user_skin_tone=None,
                compatibility_score=0.0,
                fashion_terrorist_flag=False,
                fashion_terrorist_reason="사진에서 피부톤을 분석할 수 없습니다",
                recommendations=[],
                style_advice="다른 사진으로 다시 시도해주세요."
            )

        skin_analysis = skin_result.primary_color
        skin_temp = skin_result.category_suggestion
        season = determine_season(skin_temp, skin_analysis.value)

        user_skin = SkinToneAnalysis(
            pccs_tone=skin_analysis.tone,
            color_temperature=skin_temp,
            season=season,
            hex=skin_analysis.hex_color,
            value=skin_analysis.value,
            chroma=skin_analysis.chroma
        )

        # 2. 관심 상품 색상 분석 (아직 분석 안된 경우)
        analyzed_products = []
        for product in request.interested_products:
            if product.pccs_tone and product.color_temperature:
                analyzed_products.append(product)
            elif product.thumbnail_url:
                prod_result = await analyze_image_colors(product.thumbnail_url)
                if prod_result:
                    product.pccs_tone = prod_result.primary_color.tone
                    product.color_temperature = prod_result.category_suggestion
                analyzed_products.append(product)

        # 3. Fashion Terrorist 체크
        is_terrorist, reason, compat_score = check_fashion_terrorist(
            skin_analysis.tone,
            skin_temp,
            analyzed_products
        )

        # 4. 추천 상품 생성
        recommendations = []
        recommended_tones = SEASON_RECOMMENDED_TONES.get(season, ["sf", "lt", "g"])

        for i, tone in enumerate(recommended_tones[:request.recommendation_count]):
            recommendations.append(ProductRecommendation(
                product_id=f"rec_{i+1}",
                title=f"{season} 시즌에 어울리는 {tone} 톤 아이템",
                thumbnail_url=None,
                pccs_tone=tone,
                match_score=0.9 - (i * 0.05),
                match_reason=f"{season} 타입에 추천되는 {tone} 톤"
            ))

        # 5. 스타일 조언 생성
        style_advice = generate_style_advice(season, skin_temp, is_terrorist)

        # 6. 대안 상품 (Fashion Terrorist인 경우)
        better_alternatives = None
        if is_terrorist:
            better_alternatives = [
                ProductRecommendation(
                    product_id="alt_1",
                    title=f"{season} 타입에 더 어울리는 대안",
                    pccs_tone=recommended_tones[0] if recommended_tones else "sf",
                    match_score=0.95,
                    match_reason="피부톤과 조화로운 색상"
                )
            ]

        return AnalyzeWithProductsResponse(
            status="warning" if is_terrorist else "success",
            user_skin_tone=user_skin,
            compatibility_score=round(compat_score, 2),
            fashion_terrorist_flag=is_terrorist,
            fashion_terrorist_reason=reason,
            recommendations=recommendations,
            better_alternatives=better_alternatives,
            style_advice=style_advice
        )

    except Exception as e:
        logger.error(f"Analyze with products failed: {e}")
        return AnalyzeWithProductsResponse(
            status="error",
            user_skin_tone=None,
            compatibility_score=0.0,
            fashion_terrorist_flag=False,
            fashion_terrorist_reason=str(e),
            recommendations=[],
            style_advice="분석 중 오류가 발생했습니다."
        )


@router.post("/generate", response_model=GenerateRecommendationResponse)
async def generate_recommendations(
    payload: GenerateRecommendationRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate photo-based recommendations with Fashion Terrorist check.

    - Analyze user skin tone (GPU preferred, fallback to local)
    - Evaluate mismatch with interested products
    - If Fashion Terrorist -> return warning
    - Otherwise return 12 recommended products from DB
    """
    # 1) Resolve interested products
    interested_products: List[InterestedProduct] = []
    product_ids = payload.interested_product_ids or []

    if not product_ids:
        interests = db.query(UserInterest).filter(UserInterest.user_id == current_user.id).all()
        product_ids = [interest.product_id for interest in interests]

    if product_ids:
        products = (
            db.query(Product)
            .join(UserInterest, UserInterest.product_id == Product.id)
            .filter(UserInterest.user_id == current_user.id, Product.id.in_(product_ids))
            .all()
        )
        for product in products:
            interested_products.append(
                InterestedProduct(
                    product_id=str(product.id),
                    thumbnail_url=product.thumbnail_url,
                    title=product.title,
                    pccs_tone=product.pccs_tone,
                    color_temperature=product.color_temperature,
                )
            )

    # 2) Try GPU analysis first
    user_photo_url = payload.user_photo_url
    if not user_photo_url.startswith("http"):
        base_url = str(http_request.base_url).rstrip("/")
        user_photo_url = f"{base_url}{user_photo_url}"

    gpu_payload = {
        "user_photo_url": user_photo_url,
        "interested_products": [p.dict() for p in interested_products],
        "recommendation_count": payload.recommendation_count,
    }

    gpu_result = await _request_gpu_analysis(gpu_payload)

    user_skin: Optional[SkinToneAnalysis] = None
    skin_tone = "g"
    skin_temp = "neutral"
    season = "summer"
    compat_score = 0.5
    is_terrorist = False
    reason: Optional[str] = None

    if gpu_result:
        user_skin = _parse_gpu_skin_tone(gpu_result)
        if user_skin:
            skin_tone = user_skin.pccs_tone
            skin_temp = user_skin.color_temperature
            season = user_skin.season
        compat_score = float(gpu_result.get("compatibility_score", compat_score))
        is_terrorist = bool(gpu_result.get("fashion_terrorist_flag", False))
        reason = gpu_result.get("fashion_terrorist_reason")

    if gpu_result and not user_skin:
        gpu_result = None

    # 3) Fallback to local analysis if GPU unavailable
    if not gpu_result:
        skin_result = await analyze_image_colors(user_photo_url)
        if not skin_result:
            return GenerateRecommendationResponse(
                status="error",
                user_skin_tone=None,
                compatibility_score=0.0,
                fashion_terrorist_flag=False,
                fashion_terrorist_reason="사진에서 피부톤을 분석할 수 없습니다",
                recommendations=[],
                style_advice="다른 사진으로 다시 시도해주세요.",
                total=0,
            )

        skin_analysis = skin_result.primary_color
        skin_temp = skin_result.category_suggestion
        season = determine_season(skin_temp, skin_analysis.value)
        skin_tone = skin_analysis.tone

        user_skin = SkinToneAnalysis(
            pccs_tone=skin_tone,
            color_temperature=skin_temp,
            season=season,
            hex=skin_analysis.hex_color,
            value=skin_analysis.value,
            chroma=skin_analysis.chroma,
        )

        # Analyze interested products if tone info missing
        analyzed_products: List[InterestedProduct] = []
        for product in interested_products:
            if product.pccs_tone and product.color_temperature:
                analyzed_products.append(product)
                continue
            if product.thumbnail_url:
                prod_result = await analyze_image_colors(product.thumbnail_url)
                if prod_result:
                    product.pccs_tone = prod_result.primary_color.tone
                    product.color_temperature = prod_result.category_suggestion
            analyzed_products.append(product)

        is_terrorist, reason, compat_score = check_fashion_terrorist(
            skin_tone,
            skin_temp,
            analyzed_products,
        )

    # 4) If Fashion Terrorist -> return warning
    if is_terrorist:
        return GenerateRecommendationResponse(
            status="warning",
            user_skin_tone=user_skin,
            compatibility_score=round(float(compat_score), 2),
            fashion_terrorist_flag=True,
            fashion_terrorist_reason=reason or "피부톤과 스타일이 맞지 않습니다",
            recommendations=[],
            style_advice=generate_style_advice(season, skin_temp, True),
            total=0,
        )

    # 5) Build recommendations from DB
    recommended_tones = SEASON_RECOMMENDED_TONES.get(season, ["sf", "lt", "g"])
    recommendations = _select_recommendations(
        db,
        recommended_tones=recommended_tones,
        limit=payload.recommendation_count,
        skin_tone=skin_tone,
        skin_temp=skin_temp,
    )

    if not recommendations:
        return GenerateRecommendationResponse(
            status="warning",
            user_skin_tone=user_skin,
            compatibility_score=round(float(compat_score), 2),
            fashion_terrorist_flag=True,
            fashion_terrorist_reason="추천 상품을 찾을 수 없습니다",
            recommendations=[],
            style_advice=generate_style_advice(season, skin_temp, True),
            total=0,
        )

    return GenerateRecommendationResponse(
        status="success",
        user_skin_tone=user_skin,
        compatibility_score=round(float(compat_score), 2),
        fashion_terrorist_flag=False,
        fashion_terrorist_reason=None,
        recommendations=recommendations,
        style_advice=generate_style_advice(season, skin_temp, False),
        total=len(recommendations),
    )


def generate_style_advice(season: str, skin_temp: str, is_terrorist: bool) -> str:
    """시즌과 상태에 따른 스타일 조언 생성"""
    season_advice = {
        "spring": "봄 웜톤으로 밝고 화사한 색상이 잘 어울립니다. 코랄, 피치, 밝은 오렌지 계열을 추천드려요.",
        "summer": "여름 쿨톤으로 부드럽고 차분한 색상이 잘 어울립니다. 라벤더, 로즈, 소프트 블루 계열을 추천드려요.",
        "autumn": "가을 웜톤으로 깊고 따뜻한 색상이 잘 어울립니다. 머스타드, 테라코타, 올리브 계열을 추천드려요.",
        "winter": "겨울 쿨톤으로 선명하고 대비 있는 색상이 잘 어울립니다. 버건디, 네이비, 블랙&화이트를 추천드려요."
    }

    base_advice = season_advice.get(season, "다양한 색상을 시도해보세요.")

    if is_terrorist:
        return f"⚠️ 현재 선택하신 상품은 피부톤과 맞지 않습니다. {base_advice}"

    return base_advice
