# Musinsa Price Tracker & 3D Virtual Try-On

무신사 가격 추적 + 퍼스널 컬러/스타일 추천 + 3D 아바타 뷰어를 제공하는 서비스입니다.

---

## ✨ 주요 기능

- **가격 추적**: 무신사 상품 URL 등록, 가격 변동 기록 및 알림
- **온보딩**: TTS 가이드 + 웹캠 촬영 → 아바타 생성 흐름
- **AI 추천(옵션)**: 퍼스널 컬러/스타일 분석 기반 추천
- **3D 뷰어**: Unity WebGL 아바타 뷰어 제공

---

## 🧩 서비스 구성

- **Frontend**: Next.js 14 (port 3000)
- **Backend**: FastAPI (port 8000)
- **DB**: PostgreSQL (Docker) / SQLite (로컬 기본)
- **Nginx**: 리버스 프록시 (port 80/443)
- **GPU AI 서버(옵션)**: `gpu_server.py` (port 8001)

---

## 🚀 빠른 시작 (Docker)

### 0) 환경 변수 준비 (프로덕션)

`.env.prod`는 Git에 포함되지 않습니다. 아래처럼 생성해주세요.

```bash
cp .env.example .env.prod
```

**필수 항목 예시**
```env
# Security
SECRET_KEY=change-me

# Database (docker-compose.prod.yml 기준: 서비스명 postgres)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=musinsa
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/musinsa

# Frontend
NEXT_PUBLIC_API_URL=/api
API_URL=http://backend:8000

# GPU AI (옵션)
GPU_API_URL=http://host.docker.internal:8001
GPU_API_TIMEOUT_SECONDS=30
```

> `docker-compose.yml` 또는 `docker-compose.dev.yml` 사용 시 DB 서비스명이 `db`이므로 `DATABASE_URL`이 달라집니다.
> 예: `postgresql://postgres:postgres@db:5432/musinsa`

---

### 1) 프로덕션 실행

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (health: `/health`)
- Nginx: http://localhost

---

### 2) 개발 실행 (Docker)

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- PostgreSQL: localhost:5432

---

## 💻 로컬 개발 (Manual Setup)

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

> 로컬 기본 DB는 SQLite입니다. PostgreSQL을 쓰려면 `DATABASE_URL`을 환경 변수로 지정하세요.

---

## 🧠 GPU AI 서버 (옵션)

퍼스널 컬러/스타일 추천 API를 로컬로 띄울 수 있습니다.

```bash
# backend 가상환경을 재사용해도 됩니다.
python gpu_server.py
```

- Health: http://localhost:8001/ai-recommend/health
- Backend는 기본적으로 `GPU_API_URL` 또는 `AI_RECOMMEND_BASE_URL`을 읽습니다.

---

## 🗂️ 프로젝트 구조

```
./
├── backend/                    # FastAPI 백엔드
│   ├── api/v1/                 # API 라우터
│   ├── application/            # 서비스 레이어
│   ├── domain/                 # 도메인 모델
│   ├── infrastructure/         # 외부 연동 (DB/AI)
│   ├── core/                   # 설정/공통
│   └── main.py                 # 앱 엔트리포인트
├── frontend/                   # Next.js 프론트엔드
├── crawling/                   # 무신사 크롤러 모듈
├── crawling_deployment_kit/    # 크롤링 배포용 도구
├── nginx/                      # Nginx 설정
├── scripts/                    # 로컬/서버 운영 스크립트
├── docker-compose*.yml         # Docker 실행 파일
├── gpu_server.py               # GPU 추천 서버 (옵션)
└── .env.example                # 환경 변수 예시
```

---

## 🔧 기술 스택

- **Backend**: FastAPI, SQLAlchemy, Playwright, PostgreSQL
- **Frontend**: Next.js 14, TypeScript, Zustand, Recharts
- **Infra**: Docker, Docker Compose, Nginx

---

## ⚠️ Unity WebGL 설정

Unity WebGL 빌드 파일을 아래 경로에 배치해야 3D 아바타 뷰어가 표시됩니다.

```
frontend/public/unity/
  ├── avatar_viewer.loader.js
  ├── avatar_viewer.data
  ├── avatar_viewer.framework.js
  └── avatar_viewer.wasm
```

자세한 내용은 `frontend/public/unity/README.md`를 참고하세요.
