# CPU 서버 AI 연동 작업 프롬프트

## 📍 현재 상황

너는 **CPU 서버 (172.10.5.40)** 에서 작업 중이야.
GPU 서버 (192.168.0.250)에서 AI 추천 API가 준비 완료되었어.
이제 CPU 서버에서 GPU API를 호출하는 클라이언트를 구현해야 해.

---

## 🔐 서버 정보

| 서버 | IP | 역할 |
|------|-----|------|
| CPU 서버 (현재) | 172.10.5.40 | 크롤링, 메인 Backend |
| GPU 서버 | 192.168.0.250 | AI 추천 API |

---

## ✅ GPU 서버에서 완료된 작업

1. **AI 추천 API 생성 완료**
   - 엔드포인트: `http://192.168.0.250:8000/ai-recommend/...`
   - 색상 분석 (PCCS)
   - 스타일 추천
   - 배치 처리 지원

2. **테스트 완료**
   - CPU → GPU API 호출 테스트 통과
   - 상태 확인: `/tmp/gpu_status.txt`

---

## 🎯 네가 해야 할 작업

### 1. AI 클라이언트 서비스 생성

`/home/gunhee/MadCamp_3week/backend/services/ai_client.py` 생성:

```python
"""
AI Client - GPU 서버 AI API 호출 클라이언트
"""
import httpx
import logging
from typing import Dict, List, Optional, Any
from core.config import settings

logger = logging.getLogger(__name__)

# GPU 서버 AI API URL
GPU_API_URL = "http://192.168.0.250:8000"


class AIClient:
    """GPU 서버 AI API 클라이언트"""

    def __init__(self, base_url: str = GPU_API_URL, timeout: float = 30.0):
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


# 싱글톤 인스턴스
ai_client = AIClient()


# 편의 함수들
async def get_product_recommendation(product_data: Dict) -> Dict:
    """상품 데이터로 추천 받기"""
    return await ai_client.get_recommendation(
        product_id=str(product_data.get("id", "")),
        title=product_data.get("title"),
        thumbnail_url=product_data.get("thumbnail_url"),
        image_urls=product_data.get("image_urls", []),
        brand=product_data.get("brand"),
        category=product_data.get("category_main"),
        price=product_data.get("original_price")
    )


async def analyze_product_color(thumbnail_url: str, image_urls: List[str] = None) -> Dict:
    """상품 이미지 색상 분석"""
    return await ai_client.analyze_color(thumbnail_url, image_urls)
```

### 2. 상품 API에 추천 기능 추가

`/home/gunhee/MadCamp_3week/backend/api/v1/products.py`에 추가:

```python
from services.ai_client import ai_client, get_product_recommendation

@router.get("/{product_id}/ai-recommend")
async def get_ai_recommendations(
    product_id: int,
    tone_preference: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """상품에 대한 AI 추천 조회"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    # GPU 서버 AI API 호출
    result = await ai_client.get_recommendation(
        product_id=str(product.id),
        title=product.title,
        thumbnail_url=product.thumbnail_url,
        image_urls=json.loads(product.image_urls) if product.image_urls else [],
        brand=product.brand,
        category=product.category_main,
        price=product.original_price,
        tone_preference=tone_preference
    )

    return result


@router.post("/{product_id}/analyze-color")
async def analyze_product_color_endpoint(
    product_id: int,
    db: Session = Depends(get_db)
):
    """상품 색상 분석 요청"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    if not product.thumbnail_url:
        raise HTTPException(status_code=400, detail="상품 이미지가 없습니다.")

    image_urls = json.loads(product.image_urls) if product.image_urls else []

    result = await ai_client.analyze_color(
        image_url=product.thumbnail_url,
        additional_urls=image_urls[:3]
    )

    # 분석 결과를 DB에 저장
    if result.get("status") == "success" and result.get("analysis"):
        analysis = result["analysis"]
        product.pccs_hue = analysis.get("pccs_hue")
        product.pccs_value = analysis.get("pccs_value")
        product.pccs_chroma = analysis.get("pccs_chroma")
        product.pccs_tone = analysis.get("pccs_tone")
        product.primary_color_hex = analysis.get("dominant_hex")
        product.color_temperature = analysis.get("color_temperature")
        db.commit()

    return result
```

### 3. 크롤링 시 자동 색상 분석 연동 (선택)

`/home/gunhee/MadCamp_3week/backend/services/scraper.py`에서 크롤링 후 색상 분석 호출:

```python
from services.ai_client import analyze_product_color

async def enrich_product_with_ai(product_data: dict) -> dict:
    """크롤링된 상품에 AI 색상 분석 추가"""
    if product_data.get("thumbnail_url"):
        color_result = await analyze_product_color(
            product_data["thumbnail_url"],
            product_data.get("image_urls", [])
        )

        if color_result.get("status") == "success":
            analysis = color_result.get("analysis", {})
            product_data.update({
                "pccs_hue": analysis.get("pccs_hue"),
                "pccs_value": analysis.get("pccs_value"),
                "pccs_chroma": analysis.get("pccs_chroma"),
                "pccs_tone": analysis.get("pccs_tone"),
                "primary_color_hex": analysis.get("dominant_hex"),
                "color_temperature": analysis.get("color_temperature"),
            })

    return product_data
```

---

## 📡 GPU 서버 API 스펙

### 엔드포인트

| Endpoint | Method | 설명 |
|----------|--------|------|
| `/ai-recommend/health` | GET | 서비스 상태 |
| `/ai-recommend/recommend` | POST | 상품 추천 |
| `/ai-recommend/analyze-color` | POST | 색상 분석 |
| `/ai-recommend/batch-analyze` | POST | 배치 색상 분석 |
| `/ai-recommend/style-match` | POST | 스타일 매칭 |

### 추천 요청 예시

```bash
curl -X POST http://192.168.0.250:8000/ai-recommend/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "product": {
      "id": "12345",
      "title": "무신사 스탠다드 오버핏 티셔츠",
      "thumbnail_url": "https://image.msscdn.net/...",
      "image_urls": ["url1", "url2"],
      "brand": "무신사 스탠다드",
      "category": "상의",
      "price": 29900
    },
    "tone_preference": "warm",
    "limit": 6
  }'
```

### 추천 응답 예시

```json
{
  "status": "success",
  "color_analysis": {
    "dominant_hex": "#2F4F4F",
    "pccs_hue": 180.0,
    "pccs_value": 3.5,
    "pccs_chroma": 2.1,
    "pccs_tone": "dkg",
    "color_palette": ["#2F4F4F", "#3C5A5A", "#4A6666"],
    "color_temperature": "cool",
    "complementary_suggestions": [
      {"type": "complementary", "description": "보색 (강렬한 대비)"},
      {"type": "analogous", "description": "유사색 (자연스러운 조화)"}
    ]
  },
  "recommendations": [
    {
      "product_id": "12345",
      "score": 1.0,
      "match_reasons": ["tone:dkg", "temp:cool"],
      "pccs_tone": "dkg"
    }
  ],
  "style_suggestions": [
    "다크 그레이시 톤으로 시크하고 모던한 느낌을 줘보세요.",
    "차가운 톤의 색상이어서 쿨톤 계열 제품과 매칭해보세요."
  ],
  "message": null
}
```

---

## 🧪 테스트 방법

### 1. GPU 서버 연결 테스트
```bash
curl http://192.168.0.250:8000/ai-recommend/health
```

### 2. 추천 API 테스트
```bash
curl -X POST http://192.168.0.250:8000/ai-recommend/recommend \
  -H "Content-Type: application/json" \
  -d '{"product": {"id": "test", "title": "테스트"}}'
```

### 3. 색상 분석 테스트 (실제 무신사 이미지로)
```bash
curl -X POST http://192.168.0.250:8000/ai-recommend/analyze-color \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://image.msscdn.net/images/goods_img/20241224/4661919/4661919_17352929498498_500.jpg"}'
```

---

## 📋 작업 체크리스트

- [ ] `backend/services/ai_client.py` 생성
- [ ] `backend/api/v1/products.py`에 AI 추천 엔드포인트 추가
- [ ] GPU 서버 연결 테스트
- [ ] API 통합 테스트
- [ ] (선택) 크롤링 시 자동 색상 분석 연동

---

## ⚠️ 주의사항

1. **GPU 서버 주소**: `192.168.0.250:8000` (고정)
2. **타임아웃**: 색상 분석은 최대 30초 소요 가능
3. **배치 처리**: 대량 분석 시 `batch-analyze` 사용 권장
4. **에러 처리**: GPU 서버 다운 시 graceful 처리 필요

---

## 📞 완료 후 알림

작업 완료 후 GPU 서버에 알려줘:
```bash
ssh root@192.168.0.250 "echo '[$(date)] CPU 서버 AI 연동 완료' >> /tmp/cpu_status.txt"
```
