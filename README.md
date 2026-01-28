# Musinsa Price Tracker & 3D Virtual Try-On

무신사 가격 추적 및 3D 가상 피팅 서비스

---

## 🚀 빠른 시작

### 1단계: 서버 초기 설정 (최초 1회만)

아무것도 설치되지 않은 깡통 서버(Ubuntu)라면 다음 설정을 먼저 진행해주세요.

**1. 필수 패키지 설치**
```bash
# 시스템 업데이트 & Git 설치
sudo apt update && sudo apt upgrade -y
sudo apt install -y git

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker 권한 설정
sudo usermod -aG docker $USER
newgrp docker
```

**2. NVIDIA Container Toolkit 설치 (GPU 사용 시)**
```bash
# 저장소 설정
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 툴킷 설치 및 Docker 재시작
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

---

### 2단계: 프로젝트 배포 및 실행 (반복)

서버에 접속할 때마다 또는 코드를 업데이트할 때 사용하는 명령어입니다.

**1. 코드 가져오기 (처음)**
```bash
git clone https://github.com/logan0741/MadCamp_3week.git
cd MadCamp_3week
```

**2. 코드 최신화 (업데이트 시)**
```bash
git pull origin main
```

**3. Docker 실행 (빌드 및 실행)**
```bash
# 기존 컨테이너 중지 및 삭제
docker compose down

# 새로 빌드하여 백그라운드 실행 (프로덕션 환경)
docker compose -f docker-compose.prod.yml up -d --build

# 로그 실시간 확인
docker compose logs -f
```

---

## 💻 로컬 개발 환경 설정

로컬에서도 Docker를 사용하면 서버 환경과 동일한 조건에서 개발할 수 있어 권장합니다.

### 방법 1: Docker로 개발 (권장)

`docker-compose.dev.yml`을 사용하여 코드가 실시간으로 반영(Hot Reload)되는 개발 환경을 실행합니다.

```bash
# 개발용 컨테이너 실행
docker-compose -f docker-compose.dev.yml up --build

# 접속
# 프론트엔드: http://localhost:3000 (코드 수정 시 자동 반영)
# 백엔드: http://localhost:8000 (코드 수정 시 자동 재시작)
```

### 방법 2: 직접 설치 (Manual Setup)

Docker를 사용할 수 없는 경우에만 사용하세요.

#### Backend
```bash
cd backend
python3 -m venv venv        # Mac
# python -m venv venv       # Windows

source venv/bin/activate    # Mac
# venv\Scripts\activate     # Windows

pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
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
