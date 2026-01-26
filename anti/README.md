# 🛍️ Musinsa Price Tracker & 3D Virtual Try-On

무신사 가격 추적 및 3D 가상 피팅 서비스

## ✨ 주요 기능

### 📊 스마트 가격 추적
- **무신사 URL 또는 공유 링크** 등록으로 관심 상품 추가
- **OneLink 지원** - 무신사 앱 공유 링크 자동 인식
- **가격 변동 그래프** - 최고가/최저가 시각화
- **할인 알림** - 가격 하락 시 알림

### 🎽 AR 가상 피팅 (개발중)
- Unity WebGL 3D 아바타 뷰어
- 의류 피팅 시뮬레이션

### 🕷️ 무신사 크롤러
Playwright + Network Interception 기반의 안정적인 크롤링:

| 수집 데이터 | 설명 |
|------------|------|
| `title` | 상품명 |
| `brand` | 브랜드명 |
| `price` | 현재 가격 |
| `original_price` | 정가 (할인 전) |
| `discount_rate` | 할인율 % |
| `image_urls` | 상품 이미지 (캐러셀용) |

**지원 URL 형식:**
```
# 일반 무신사 URL
https://www.musinsa.com/products/4316145
https://www.musinsa.com/app/goods/4316145

# 앱 공유 링크 (OneLink)
https://musinsa.onelink.me/ANAQ/nz6i135t
```

---

## 🏗️ 프로젝트 구조

```
anti/
├── backend/                 # FastAPI 백엔드
│   ├── main.py              # 앱 엔트리포인트
│   ├── database.py          # SQLite 설정
│   ├── models.py            # SQLAlchemy 모델
│   ├── schemas.py           # Pydantic 스키마
│   ├── routers/
│   │   ├── auth.py          # 인증 (로그인/회원가입)
│   │   ├── user.py          # 유저 상태
│   │   ├── onboarding.py    # 아바타 생성
│   │   ├── products.py      # 상품 추적 API
│   │   └── ai.py            # AI 태스크
│   └── services/
│       └── scraper.py       # ⭐ 무신사 크롤러 (Next.js 데이터 추출)
│
└── frontend/                # Next.js 14 프론트엔드
    ├── app/
    │   ├── login/           # 로그인
    │   ├── register/        # 회원가입
    │   ├── onboarding/      # TTS 가이드 + 카메라 촬영
    │   ├── dashboard/       # 📊 관심 상품 대시보드
    │   ├── fitting/         # 🎽 AR 피팅 페이지
    │   └── mypage/          # 마이페이지 (3D 아바타)
    ├── components/
    │   ├── ProductCard.tsx       # 상품 카드 (이미지 캐러셀)
    │   ├── AddProductModal.tsx   # 상품 추가 모달
    │   ├── PriceChartModal.tsx   # 가격 차트 (최고/최저 마커)
    │   └── OnboardingGuard.tsx
    └── lib/
        ├── api.ts           # API 유틸리티
        └── store.ts         # Zustand 상태관리
```

---

## 🚀 실행 방법

### 1. 백엔드 설정

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치 (크롤링용)
playwright install chromium

# 서버 실행
uvicorn main:app --reload --port 8000
```

### 2. 프론트엔드 설정

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 3. 접속

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | http://localhost:3000 |
| API 문서 (Swagger) | http://localhost:8000/docs |

---

## 🔧 기술 스택

### Backend
- **FastAPI** - Python 웹 프레임워크
- **SQLite + SQLAlchemy** - 데이터베이스
- **JWT** - 인증
- **Playwright** - 웹 크롤링 (Next.js __NEXT_DATA__ 추출)

### Frontend
- **Next.js 14** (App Router)
- **TypeScript**
- **Recharts** - 가격 차트
- **react-unity-webgl** - 3D 아바타 뷰어
- **Zustand** - 상태관리

---

## 📱 페이지별 기능

### 대시보드 (`/dashboard`)
- 관심 상품 목록 (이미지 3초 캐러셀)
- 현재가 + 정가 (취소선) 표시
- 가격 추이 차트 (최고가/최저가 점 표시)

### 피팅 (`/fitting`)
- Unity WebGL 아바타 뷰어
- 상품 선택 후 피팅 요청

### 마이페이지 (`/mypage`)
- 3D 디지털 트윈 아바타
- 다시 모델링하기

---

## ⚠️ Unity WebGL 설정

3D 아바타를 표시하려면 Unity 빌드 파일 필요:

```
frontend/public/unity/Build/
├── avatar_viewer.loader.js
├── avatar_viewer.data
├── avatar_viewer.framework.js
└── avatar_viewer.wasm
```

---

## 📝 API 예시

### 상품 추적 등록
```bash
POST /products/track
{
  "url": "https://musinsa.onelink.me/ANAQ/nz6i135t"
}
```

### 응답
```json
{
  "id": 1,
  "musinsa_id": "4316145",
  "title": "3 스티치 와이드 워싱 데님 팬츠",
  "brand": "세컨모놀로그",
  "price": 33600,
  "original_price": 96000,
  "discount_rate": 65,
  "image_urls": ["https://image.msscdn.net/..."],
  "thumbnail_url": "https://image.msscdn.net/..."
}
```
