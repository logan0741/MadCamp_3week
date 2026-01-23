# Musinsa Price Tracker & 3D Virtual Try-On

무신사 가격 추적 및 3D 가상 피팅 서비스

---

## 🚀 빠른 시작

### 방법 1: Docker로 실행 (권장)

```bash
# 1. 저장소 클론
git clone https://github.com/logan0741/MadCamp_3week.git
cd MadCamp_3week

# 2. 환경변수 설정
cp .env.example .env

# 3. Docker Compose 실행
docker-compose up -d --build

# 4. 접속
# 프론트엔드: http://localhost:3000
# 백엔드 API: http://localhost:8000/docs
```

### 방법 2: 로컬 개발 환경

#### Step 1. 백엔드 설정

```bash
cd backend
```

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

```bash
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000
```

#### Step 2. 프론트엔드 설정 (새 터미널)

```bash
cd frontend
npm install
npm run dev
```

#### Step 3. 접속

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000/docs

---

## 🐳 Docker 상세 가이드

### 환경변수 설정

```bash
cp .env.example .env
# .env 파일에서 SECRET_KEY 수정
```

### Docker Compose 명령어

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

### GPU 서버 배포 (개별 컨테이너)

```bash
# 백엔드만 빌드 & 실행
docker build -t musinsa-backend ./backend
docker run -d -p 8000:8000 musinsa-backend

# 프론트엔드만 빌드 & 실행
docker build -t musinsa-frontend ./frontend
docker run -d -p 3000:3000 musinsa-frontend
```

---

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
├── frontend/          # Next.js 14 프론트엔드
│   ├── app/
│   │   ├── login/     # 로그인 페이지
│   │   ├── register/  # 회원가입 페이지
│   │   ├── onboarding/# 온보딩 (TTS + 카메라 촬영)
│   │   ├── dashboard/ # 관심 상품 대시보드
│   │   └── mypage/    # 마이페이지 (3D 아바타)
│   ├── components/
│   └── lib/
│
├── docker-compose.yml # Docker 통합 실행
└── .env.example       # 환경변수 예시
```

---

## 📱 주요 기능

| 기능           | 설명                                                    |
| -------------- | ------------------------------------------------------- |
| **온보딩**     | TTS 음성 가이드 + 웹 카메라 촬영 → AI 아바타 자동 생성  |
| **가격 추적**  | 무신사 URL 등록, Recharts 가격 변동 그래프, 최저가 알림 |
| **마이페이지** | Unity WebGL 3D 아바타 뷰어, 다시 모델링하기             |

---

## 🔧 기술 스택

| 영역         | 기술                                                         |
| ------------ | ------------------------------------------------------------ |
| **Backend**  | FastAPI, SQLite (SQLAlchemy), JWT, Playwright                |
| **Frontend** | Next.js 14, TypeScript, Recharts, react-unity-webgl, Zustand |
| **DevOps**   | Docker, Docker Compose                                       |

---

## ⚠️ Unity WebGL 설정

마이페이지의 3D 아바타를 표시하려면 Unity 빌드 파일이 필요합니다:

1. Unity에서 WebGL 빌드 생성
2. `frontend/public/unity/` 폴더에 다음 파일 배치:
   - `avatar_viewer.loader.js`
   - `avatar_viewer.data`
   - `avatar_viewer.framework.js`
   - `avatar_viewer.wasm`
