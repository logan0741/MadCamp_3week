# MemeForty 서버 간 통신 가이드

## 📍 서버 구성

| 역할 | 서버명 | IP | 용도 |
|------|--------|-----|------|
| **CPU 서버** | camp-69 | 192.168.0.77 | 크롤링, API, Frontend |
| **GPU 서버** | - | 172.10.5.42 | AI 파이프라인, 3D 모델링 |

---

## 🔐 SSH 접근 정보

### CPU → GPU 서버
```bash
ssh root@172.10.5.42
# 비밀번호: 1234 (또는 SSH 키로 접근)
```

### GPU → CPU 서버
```bash
ssh root@192.168.0.77
# 비밀번호: 1234 (또는 SSH 키로 접근)
```

---

## 🏗️ 서비스 역할 분담

### CPU 서버 (192.168.0.77)
담당: **크롤링 + 메인 서비스**

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Frontend | 3000 | Next.js 웹 UI |
| Backend | 8000 | FastAPI 메인 API |
| PostgreSQL | 5432 | 메인 데이터베이스 |

**기능:**
- 무신사 상품 크롤링 (`scraper.py`, `size_scraper.py`)
- 가격 추적 스케줄러
- 사용자 인증/상품 관리 API
- 크롤링 결과를 GPU 서버로 전송

### GPU 서버 (172.10.5.42)
담당: **AI 처리**

| 서비스 | 포트 | 설명 |
|--------|------|------|
| AI Engine | 8001 | AI 파이프라인 API |
| Redis | 6379 | Celery 작업 큐 |
| Nginx Static | 8080 | AI 결과물 서빙 |

**기능:**
- 3D 아바타 생성
- 의류 3D 모델링 (Wonder3D)
- PCCS 색상 분석
- 스타일 추천 엔진

---

## 🔄 데이터 흐름

```
[사용자] 
    ↓
[CPU 서버 - Frontend:3000]
    ↓
[CPU 서버 - Backend:8000]
    ├── 크롤링 요청 → 무신사 API
    ├── DB 조회/저장 → PostgreSQL
    └── AI 요청 → [GPU 서버 - AI Engine:8001]
                        ↓
                   AI 처리 (GPU)
                        ↓
                   결과 → [Nginx Static:8080]
                        ↓
                   결과 URL 반환
```

---

## 🚀 서비스 시작 명령

### CPU 서버
```bash
cd /home/gunhee/MadCamp_3week
docker compose -f docker-compose.prod.yml up -d --build
```

### GPU 서버
```bash
cd /path/to/MadCamp_3week
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 🔧 API 연동 설정

### CPU Backend → GPU AI Engine
CPU 서버의 `backend/.env` 또는 docker-compose에 설정:
```env
AI_PIPELINE_BASE_URL=http://172.10.5.42:8001
STATIC_BASE_URL=http://172.10.5.42:8080
```

### GPU AI Engine → CPU Backend (필요시)
GPU 서버의 AI 파이프라인에서 CPU 백엔드 호출 시:
```env
MAIN_BACKEND_URL=http://192.168.0.77:8000
```

---

## 📡 SSH 터널 설정 (네트워크 제한 시)

### CPU → GPU 포트 포워딩
```bash
# AI Engine 포트를 로컬에서 접근
ssh -L 8001:localhost:8001 root@172.10.5.42
```

### GPU → CPU 포트 포워딩
```bash
# Backend API를 로컬에서 접근
ssh -L 8000:localhost:8000 root@192.168.0.77
```

---

## ⚠️ 네트워크 제한 사항

- **GPU 서버 내부망**: 외부 HTTPS(443) 아웃바운드 차단됨
- 무신사 크롤링은 **CPU 서버에서만** 가능
- CPU 서버에서 크롤링 후 결과를 GPU 서버로 전달

---

## 📝 역방향 SSH 키 설정 (GPU → CPU)

GPU 서버에서 실행:
```bash
# SSH 키 생성
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

# CPU 서버에 키 등록
sshpass -p '1234' ssh-copy-id -o StrictHostKeyChecking=no root@192.168.0.77

# 테스트
ssh root@192.168.0.77 "echo 'CPU 서버 연결 성공'"
```

---

## 🛠️ 트러블슈팅

### SSH 연결 실패
```bash
# 방화벽 확인
sudo ufw status

# SSH 서비스 확인
systemctl status ssh

# 포트 오픈 확인
ss -tlnp | grep 22
```

### Docker 컨테이너 간 통신 실패
```bash
# 컨테이너 네트워크 확인
docker network ls
docker network inspect memeforty-network

# 컨테이너 IP 확인
docker inspect <container_name> | grep IPAddress
```
