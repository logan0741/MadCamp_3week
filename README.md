# Musinsa Price Tracker & 3D Virtual Try-On

무신사 가격 추적 및 3D 가상 피팅 서비스

## 🏗️ 프로젝트 구조

```
./
├── backend/           # FastAPI 백엔드
│   ├── main.py        # 앱 엔트리포인트
│   ├── database.py    # SQLite 설정
│   ├── models.py      # SQLAlchemy 모델
│   ├── schemas.py     # Pydantic 스키마
│   ├── routers/       # API 라우터
│   │   ├── auth.py    # 인증 (로그인/회원가입)
│   │   ├── user.py    # 유저 상태
│   │   ├── onboarding.py  # 아바타 생성
│   │   ├── products.py    # 상품 추적
│   │   └── ai.py      # AI 태스크
│   └── services/
│       └── scraper.py # 무신사 크롤러
│
└── frontend/          # Next.js 14 프론트엔드
    ├── app/
    │   ├── login/     # 로그인 페이지
    │   ├── register/  # 회원가입 페이지
    │   ├── onboarding/# 온보딩 (TTS + 카메라 촬영)
    │   ├── dashboard/ # 관심 상품 대시보드
    │   └── mypage/    # 마이페이지 (3D 아바타)
    ├── components/
    │   ├── ProductCard.tsx      # 상품 카드
    │   ├── AddProductModal.tsx  # 상품 추가 모달
    │   ├── PriceChartModal.tsx  # 가격 차트 모달
    │   └── OnboardingGuard.tsx  # 온보딩 가드
    └── lib/
        ├── api.ts     # API 유틸리티
        └── store.ts   # Zustand 상태관리
```

## 🚀 실행 방법

### 1. 백엔드 설정

```bash
cd backend
```

#### 가상환경 생성 및 활성화

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

#### 의존성 설치 및 실행

```bash
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

- **프론트엔드**: http://localhost:3000
- **백엔드 API 문서**: http://localhost:8000/docs

---

## 🐳 Docker로 실행 (권장)

### 환경변수 설정

```bash
# .env.example을 복사하여 .env 생성
cp .env.example .env

# .env 파일에서 SECRET_KEY 등 수정
```

### Docker Compose로 실행

```bash
# 빌드 및 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

### 개별 컨테이너 빌드 (GPU 서버 배포 시)

```bash
# 백엔드만 빌드
docker build -t musinsa-backend ./backend

# 프론트엔드만 빌드
docker build -t musinsa-frontend ./frontend

# 실행
docker run -d -p 8000:8000 musinsa-backend
docker run -d -p 3000:3000 musinsa-frontend
```

## 📱 주요 기능

### 1. 온보딩 (아바타 생성)
- TTS 음성 가이드로 촬영 안내
- 웹 카메라로 전신 촬영
- AI 아바타 자동 생성

### 2. 가격 추적
- 무신사 URL 등록으로 관심 상품 추가
- Recharts 기반 가격 변동 그래프
- 최저가 알림

### 3. 마이페이지
- Unity WebGL 3D 아바타 뷰어
- '다시 모델링하기' 기능

## 🔧 기술 스택

### Backend
- FastAPI (Python)
- SQLite (SQLAlchemy ORM)
- JWT 인증
- Playwright (웹 크롤링)

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Recharts (차트)
- react-unity-webgl (3D 뷰어)
- Zustand (상태관리)

## ⚠️ Unity WebGL 설정

마이페이지의 3D 아바타를 표시하려면 Unity 빌드 파일이 필요합니다:

1. Unity에서 WebGL 빌드 생성
2. `frontend/public/unity/` 폴더에 다음 파일 배치:
   - `avatar_viewer.loader.js`
   - `avatar_viewer.data`
   - `avatar_viewer.framework.js`
   - `avatar_viewer.wasm`
