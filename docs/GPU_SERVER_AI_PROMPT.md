# GPU 서버 AI 작업 프롬프트 (Claude에게 전달)

## 📍 현재 상황

너는 **GPU 서버 (camp-gpu-20, 172.10.5.42)** 에서 작업 중이야.
CPU 서버 (camp-69, 192.168.0.77)와 협업해서 MemeForty 프로젝트를 완성해야 해.

---

## 🔐 서버 접근 정보

| 서버 | IP | 비밀번호 | SSH 명령 |
|------|-----|---------|----------|
| CPU 서버 | 192.168.0.77 | 1234 | `ssh root@192.168.0.77` |
| GPU 서버 (현재) | 172.10.5.42 | 1234 | - |

**SSH 키 설정 완료** - 비밀번호 없이 접근 가능

---

## 🏗️ 프로젝트 구조 (GPU 서버)

```
/root/MadCamp_3week/
├── ai-pipeline/
│   ├── data/              # AI 데이터
│   ├── logs/              # 로그
│   ├── models/
│   │   └── weights/       # AI 모델 가중치
│   └── utils/             # 유틸리티
├── backend/               # FastAPI 백엔드
│   └── services/
│       ├── scraper.py     # 크롤링 (사용 불가 - 443 차단)
│       ├── product_service.py
│       └── auth_service.py
├── frontend/              # Next.js
└── docs/                  # 문서
    ├── SERVER_COMMUNICATION.md  # 서버 통신 가이드
    └── GPU_SERVER_AI_PROMPT.md  # 이 문서
```

---

## 🎯 네가 해야 할 작업

### 1. AI 추천 API 생성

`backend/api/v1/ai_recommend.py` 생성:

```python
"""
AI 추천 API - CPU 서버에서 호출
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx

router = APIRouter()

class ProductInput(BaseModel):
    id: str
    title: Optional[str] = None
    brand: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_urls: Optional[List[str]] = []
    price: Optional[int] = None
    category: Optional[str] = None

class RecommendRequest(BaseModel):
    product: ProductInput
    user_preferences: Optional[dict] = {}
    limit: int = 6

class RecommendResponse(BaseModel):
    status: str
    recommendations: List[dict]
    color_analysis: Optional[dict] = None

@router.post("/recommend", response_model=RecommendResponse)
async def get_recommendations(request: RecommendRequest):
    """상품 추천 생성 (CPU 서버에서 호출)"""
    
    # TODO: ai-pipeline의 추천 로직 호출
    # 현재는 더미 응답
    
    return RecommendResponse(
        status="success",
        recommendations=[
            {
                "product_id": "1234567",
                "score": 0.95,
                "match_reasons": ["color_match", "style_similar"],
                "pccs_tone": "bright"
            }
        ],
        color_analysis={
            "dominant_color": "#FF5733",
            "pccs_tone": "vivid"
        }
    )

@router.get("/health")
async def health_check():
    """AI 서비스 상태 확인"""
    return {"status": "healthy", "service": "ai-recommend"}
```

### 2. 라우터 등록

`backend/api/v1/__init__.py` 수정:
```python
from api.v1 import ai_recommend
router.include_router(ai_recommend.router, prefix="/ai", tags=["AI Recommendation"])
```

### 3. ai-pipeline 연동

기존 `ai-pipeline/` 코드를 분석하고 API와 연결:
- 색상 분석 로직
- PCCS 톤 분류
- 스타일 키워드 추출
- 유사도 계산

---

## ⚠️ 네트워크 제한 (중요!)

- **외부 HTTPS(443) 차단됨** - 무신사 API 직접 호출 불가
- 크롤링은 **CPU 서버에서만** 가능
- **CPU 서버가 크롤링 후 상품 정보를 너에게 전송**
- 너는 그 데이터로 **AI 추천만 수행**

---

## � 데이터 흐름

```
1. [사용자] 상품 URL 등록
2. [CPU 서버] 무신사 크롤링 → 상품 정보 수집
3. [CPU 서버] POST http://172.10.5.42:8000/ai/recommend
   - 상품 정보 전송 (title, brand, image_urls, price 등)
4. [GPU 서버 - 너] 
   - 이미지에서 색상 분석
   - PCCS 톤 분류
   - 스타일 키워드 추출
   - 유사 상품 추천 생성
5. [GPU 서버 - 너] 추천 결과 JSON 반환
6. [CPU 서버] 사용자에게 추천 결과 표시
```

---

## 🧪 테스트 방법

### CPU 서버 연결 테스트
```bash
ssh root@192.168.0.77 "echo 'CPU 서버 연결 성공'"
```

### API 테스트
```bash
curl -X POST http://localhost:8000/ai/recommend \
  -H "Content-Type: application/json" \
  -d '{"product": {"id": "test", "title": "테스트 상품"}}'
```

### CPU 서버에서 GPU API 호출 테스트
```bash
ssh root@192.168.0.77 "curl -X GET http://172.10.5.42:8000/ai/health"
```

---

## 📋 작업 체크리스트

- [ ] `backend/api/v1/ai_recommend.py` 생성
- [ ] `backend/api/v1/__init__.py`에 라우터 등록
- [ ] ai-pipeline 분석 및 추천 로직 구현
- [ ] 색상 분석 API 추가 (`POST /ai/analyze-color`)
- [ ] Docker 서비스 재시작
- [ ] CPU 서버에서 API 호출 테스트

---

## 📞 CPU 서버 담당자와 소통

CPU 서버 AI(다른 Claude)가 이 문서를 참고해서:
1. `backend/services/ai_client.py` - GPU API 호출 클라이언트 생성
2. `backend/api/v1/products.py` - 추천 기능 추가

**완료되면 CPU 서버에 알려줘:**
```bash
ssh root@192.168.0.77 "echo 'GPU 서버 AI API 준비 완료' >> /tmp/gpu_status.txt"
```

---

## � 참고 문서

- `/root/MadCamp_3week/docs/SERVER_COMMUNICATION.md` - 서버 통신 가이드
- `/root/MadCamp_3week/ai-pipeline/` - 기존 AI 코드
- `/root/MadCamp_3week/README.md` - 프로젝트 개요


