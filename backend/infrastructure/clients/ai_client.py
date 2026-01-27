"""
AI Client - GPU 서버 AI API 호출 클라이언트
GPU 서버(192.168.0.250:8000)의 AI 추천 API를 호출
"""
import httpx
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# AI API Server (Remote)
GPU_API_URL = "http://172.10.5.42:8000"
GPU_API_TIMEOUT = 30.0


class AIClient:
    """GPU 서버 AI API 클라이언트"""

    def __init__(self, base_url: str = GPU_API_URL, timeout: float = GPU_API_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout

    async def health_check(self) -> Dict:
        """AI 서비스 상태 확인"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/ai-recommend/health")
                return response.json()
            except Exception as e:
                logger.error(f"AI health check failed: {e}")
                return {"status": "unavailable", "error": str(e)}

    async def get_recommendation(
        self,
        product_id: str,
        title: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        price: Optional[int] = None,
        tone_preference: Optional[str] = None,
        limit: int = 6
    ) -> Dict:
        """
        상품 추천 요청

        Args:
            product_id: 상품 ID
            title: 상품명
            thumbnail_url: 썸네일 이미지 URL
            image_urls: 추가 이미지 URL 리스트
            brand: 브랜드
            category: 카테고리
            price: 가격
            tone_preference: 톤 선호도 ('warm', 'cool', 'neutral')
            limit: 추천 개수

        Returns:
            추천 결과 (색상 분석 + 스타일 제안)
        """
        payload = {
            "product": {
                "id": product_id,
                "title": title,
                "thumbnail_url": thumbnail_url,
                "image_urls": image_urls or [],
                "brand": brand,
                "category": category,
                "price": price
            },
            "tone_preference": tone_preference,
            "limit": limit
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/ai-recommend/recommend",
                    json=payload
                )
                return response.json()
            except Exception as e:
                logger.error(f"AI recommendation failed: {e}")
                return {"status": "error", "message": str(e)}

    async def analyze_color(
        self,
        image_url: str,
        additional_urls: Optional[List[str]] = None
    ) -> Dict:
        """
        이미지 색상 분석

        Args:
            image_url: 분석할 이미지 URL
            additional_urls: 추가 이미지 URL (메인 실패시 사용)

        Returns:
            PCCS 색상 분석 결과
        """
        payload = {
            "image_url": image_url,
            "additional_urls": additional_urls or []
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/ai-recommend/analyze-color",
                    json=payload
                )
                return response.json()
            except Exception as e:
                logger.error(f"Color analysis failed: {e}")
                return {"status": "error", "message": str(e)}

    async def batch_analyze_colors(self, products: List[Dict]) -> Dict:
        """
        배치 색상 분석

        Args:
            products: 상품 리스트 [{"id": "...", "thumbnail_url": "...", ...}, ...]

        Returns:
            배치 분석 결과
        """
        payload = {"products": products}

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/ai-recommend/batch-analyze",
                    json=payload
                )
                return response.json()
            except Exception as e:
                logger.error(f"Batch analysis failed: {e}")
                return {"status": "error", "message": str(e)}

    async def analyze_custom(self, image_url: str, prompt: str) -> Dict:
        """
        사용자 정의 프롬프트로 분석 요청 (패션 테러리스트 판별 등)
        
        Args:
            image_url: 분석할 이미지 URL
            prompt: GPU LLM에 전달할 시스템 프롬프트
            
        Returns:
            분석 결과 JSON
        """
        payload = {
            "image_url": image_url,
            "prompt": prompt
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:  # 긴 타임아웃
            try:
                # Assuming the GPU server has a generic endpoint for this
                # If not, this might need to be adjusted to whatever the GPU server supports
                response = await client.post(
                    f"{self.base_url}/ai-recommend/analyze-custom",
                    json=payload
                )
                return response.json()
            except Exception as e:
                logger.error(f"Custom analysis failed: {e}")
                return {"status": "error", "message": str(e)}


# 싱글톤 인스턴스
ai_client = AIClient()


# 편의 함수들 (기존 호환)
async def get_ai_recommendations(
    product_data: Dict,
    user_preferences: Optional[Dict] = None,
    limit: int = 6
) -> Dict:
    """상품 데이터로 추천 받기 (기존 API 호환)"""
    return await ai_client.get_recommendation(
        product_id=str(product_data.get("id", "")),
        title=product_data.get("title"),
        thumbnail_url=product_data.get("thumbnail_url"),
        image_urls=product_data.get("image_urls", []),
        brand=product_data.get("brand"),
        category=product_data.get("category"),
        price=product_data.get("price"),
        tone_preference=user_preferences.get("tone") if user_preferences else None,
        limit=limit
    )


async def analyze_product_color(image_url: str, additional_urls: List[str] = None) -> Dict:
    """상품 이미지 색상 분석"""
    return await ai_client.analyze_color(image_url, additional_urls)


async def check_gpu_server_health() -> bool:
    """GPU 서버 상태 확인"""
    result = await ai_client.health_check()
    return result.get("status") == "healthy"


async def analyze_custom_prompt(image_url: str, prompt: str) -> Dict:
    """커스텀 프롬프트 분석 요청"""
    return await ai_client.analyze_custom(image_url, prompt)
