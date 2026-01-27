# Musinsa Crawler

무신사 상품 크롤링 모듈입니다. 상품 정보, 가격, 사이즈 정보를 수집합니다.

---

## 파일 구조

```
crawling/
├── scraper.py              # 무신사 상품 스크래퍼 (메인)
├── size_scraper.py         # 사이즈 정보 스크래퍼
├── crawl_and_reconstruct.py # 크롤링 + 3D 재구성 (ai-pipeline 연동용)
├── test_onelink.py         # OneLink URL 테스트
├── test_scraper.py         # 스크래퍼 테스트
├── crawling_report.md      # 크롤링 이슈/해결 문서
├── requirements.txt        # 필요 패키지
└── README.md               # 이 파일
```

---

## 설치

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## JSON 양식

### 1. 상품 크롤링 결과 (scraper.py)

`scrape_musinsa_product()` 함수의 반환 양식:

```json
{
  "product_id": "4316145",
  "title": "무신사 스탠다드 릴렉스 핏 크루 넥 반팔 티셔츠 [블랙]",
  "brand": "무신사 스탠다드",
  "thumbnail_url": "https://image.msscdn.net/images/goods_img/20230523/3310706/3310706_17161234567890_500.jpg",
  "image_urls": [
    "https://image.msscdn.net/images/goods_img/20230523/3310706/3310706_1_500.jpg",
    "https://image.msscdn.net/images/goods_img/20230523/3310706/3310706_2_500.jpg"
  ],
  "price": 15920,
  "original_price": 19900,
  "discount_rate": 20
}
```

### 2. 사이즈 크롤링 결과 (size_scraper.py)

`scrape_musinsa_sizes()` 함수의 반환 양식:

```json
{
  "sizes": {
    "S": {
      "length": 65.0,
      "shoulder": 44.0,
      "chest": 53.0,
      "sleeve": 20.0
    },
    "M": {
      "length": 67.0,
      "shoulder": 46.0,
      "chest": 55.0,
      "sleeve": 21.0
    },
    "L": {
      "length": 69.0,
      "shoulder": 48.0,
      "chest": 57.0,
      "sleeve": 22.0
    }
  },
  "source": "https://goods-detail.musinsa.com/api/goods/4316145",
  "updated_at": "2026-01-27T14:00:00.000000"
}
```

### 3. DB 저장용 상품 데이터

Backend에서 DB에 저장할 때 사용하는 양식:

```json
{
  "musinsa_id": "4316145",
  "url": "https://www.musinsa.com/products/4316145",
  "title": "무신사 스탠다드 릴렉스 핏 크루 넥 반팔 티셔츠 [블랙]",
  "brand": "무신사 스탠다드",
  "thumbnail_url": "https://image.msscdn.net/...",
  "image_urls": "[\"url1\", \"url2\"]",
  "original_price": 19900
}
```

---

## CPU 서버 ↔ GPU 서버 통신

### 서버 구성

| 서버 | IP | 역할 |
|------|-----|------|
| **CPU 서버** | 192.168.0.77 | 크롤링, Backend API, Frontend |
| **GPU 서버** | 172.10.5.42 | AI 파이프라인 (색상분석, 3D 모델링) |

### 통신 흐름

```
[사용자 요청]
    ↓
[CPU 서버 Backend:8000]
    ├── 크롤링 실행 (scraper.py)
    │       ↓
    │   무신사에서 상품 정보 수집
    │       ↓
    │   DB에 저장 (PostgreSQL)
    │
    └── AI 처리 요청 (HTTP POST)
            ↓
        [GPU 서버 AI Engine:8001]
            ├── 색상 분석 (PCCS)
            ├── 스타일 추천
            └── 3D 모델링
            ↓
        결과 반환 (JSON)
```

### GPU 서버 AI API 엔드포인트

| Endpoint | Method | 설명 |
|----------|--------|------|
| `/ai-recommend/health` | GET | 서비스 상태 확인 |
| `/ai-recommend/recommend` | POST | 상품 추천 |
| `/ai-recommend/analyze-color` | POST | 색상 분석 |
| `/ai-recommend/batch-analyze` | POST | 배치 색상 분석 |

### AI 추천 요청 JSON

```json
{
  "product": {
    "id": "4316145",
    "title": "무신사 스탠다드 오버핏 티셔츠",
    "thumbnail_url": "https://image.msscdn.net/...",
    "image_urls": ["url1", "url2"],
    "brand": "무신사 스탠다드",
    "category": "상의",
    "price": 29900
  },
  "tone_preference": "warm",
  "limit": 6
}
```

### AI 추천 응답 JSON

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
    "color_temperature": "cool"
  },
  "recommendations": [
    {
      "product_id": "12345",
      "score": 0.95,
      "match_reasons": ["tone:dkg", "temp:cool"],
      "pccs_tone": "dkg"
    }
  ],
  "style_suggestions": [
    "다크 그레이시 톤으로 시크하고 모던한 느낌을 줘보세요.",
    "차가운 톤의 색상이어서 쿨톤 계열 제품과 매칭해보세요."
  ]
}
```

### 색상 분석 요청/응답

**요청:**
```json
{
  "image_url": "https://image.msscdn.net/...",
  "additional_urls": ["url1", "url2"]
}
```

**응답:**
```json
{
  "status": "success",
  "analysis": {
    "dominant_hex": "#2F4F4F",
    "pccs_hue": 180.0,
    "pccs_value": 3.5,
    "pccs_chroma": 2.1,
    "pccs_tone": "dkg",
    "color_temperature": "cool"
  }
}
```

---

## 수정 내역

### 원본 위치 → 현재 위치

| 원본 경로 | 현재 경로 |
|-----------|-----------|
| `backend/services/scraper.py` | `crawling/scraper.py` |
| `backend/services/size_scraper.py` | `crawling/size_scraper.py` |
| `backend/test_onelink.py` | `crawling/test_onelink.py` |
| `backend/test_scraper.py` | `crawling/test_scraper.py` |
| `ai-pipeline/scripts/crawl_and_reconstruct.py` | `crawling/crawl_and_reconstruct.py` |
| `docs/crawling_report.md` | `crawling/crawling_report.md` |

### Import 경로 수정

**test_onelink.py:**
```python
# Before
from services.scraper import scrape_musinsa_product

# After
from scraper import scrape_musinsa_product
```

**test_scraper.py:**
```python
# Before
from services.scraper import scrape_musinsa_product, resolve_onelink_url

# After
from scraper import scrape_musinsa_product, resolve_onelink_url
```

**crawl_and_reconstruct.py:**
```python
# Before (복잡한 importlib 로직)
size_scraper_path = BACKEND_ROOT / "services" / "size_scraper.py"
spec = importlib.util.spec_from_file_location("size_scraper", size_scraper_path)
...

# After (단순화)
from size_scraper import scrape_musinsa_sizes
```

---

## 사용 예시

### 상품 크롤링

```python
import asyncio
from scraper import scrape_musinsa_product

async def main():
    # 일반 URL
    result = await scrape_musinsa_product(
        "https://www.musinsa.com/products/4316145",
        "4316145"
    )
    print(result)

    # OneLink URL (앱 공유 링크)
    result = await scrape_musinsa_product(
        "https://musinsa.onelink.me/ANAQ/nz6i135t",
        "onelink_test"
    )
    print(result)

asyncio.run(main())
```

### 사이즈 크롤링

```python
import asyncio
from size_scraper import scrape_musinsa_sizes

async def main():
    result = await scrape_musinsa_sizes(
        product_id="4316145",
        product_url="https://www.musinsa.com/products/4316145"
    )
    print(result.sizes)  # {'S': {...}, 'M': {...}, 'L': {...}}

asyncio.run(main())
```

### 테스트 실행

```bash
# 스크래퍼 테스트
python test_scraper.py

# OneLink URL 테스트
python test_onelink.py
```

---

## 주의사항

1. **네트워크 제한**: GPU 서버에서는 외부 HTTPS 접근이 차단됨 → 크롤링은 CPU 서버에서만 가능
2. **Rate Limiting**: 과도한 요청 방지를 위해 적절한 딜레이 필요
3. **Bot 탐지**: Playwright fallback으로 우회 가능하나, 남용 금지
4. **robots.txt**: 무신사 robots.txt 정책 준수 필요

---

## 문제 해결

크롤링 관련 이슈 및 해결 방안은 `crawling_report.md` 참조.
