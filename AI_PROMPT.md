# MadCamp AI Virtual Try-On 프로젝트 - AI 컨텍스트 프롬프트

## 프로젝트 개요
무신사 스타일 가상 피팅 플랫폼. 사용자가 옷을 2D/3D로 가상 착용할 수 있는 시스템.

**위치**: `/home/MadCamp/MadCamp_3week/`
**브랜치**: `AI`

---

## 아키텍처

```
backend/          - FastAPI 인증/상품 관리 (Port 8000)
frontend/         - Next.js React 앱 (Port 3000)
ai-pipeline/      - AI 가상 피팅 파이프라인 (Port 8001) ⭐ 신규
  ├── api/        - FastAPI VTON 서버
  ├── models/     - IDM-VTON 모델 래퍼
  ├── workers/    - Celery 비동기 작업 큐
  ├── tests/      - pytest 테스트 스위트
  └── docs/       - 통합 가이드 및 예시
```

---

## 구현 완료 기능

### 1. VTON API (ai-pipeline/api/routers/vton.py)

**동기 API**:
- `POST /api/vton/try-on` - 즉시 처리 (20-40초)
- 파일 업로드 또는 Base64 지원

**비동기 API** (NEW):
- `POST /api/vton/try-on-async` - 백그라운드 처리
- `GET /api/vton/task/{task_id}` - 상태 조회 (PENDING/PROGRESS/SUCCESS/FAILURE)
- `POST /api/vton/batch-async` - 배치 처리

### 2. Celery 작업 (ai-pipeline/workers/tasks/vton_tasks.py)

- `process_vton_async` - 단일 작업 (5단계 진행률 추적)
- `process_vton_batch_async` - 배치 작업
- `cleanup_old_results` - 자동 정리

**기능**:
- VRAM 자동 관리 (VRAMContext)
- Webhook 콜백 지원
- 재시도 로직 (최대 3회)

### 3. 테스트 (ai-pipeline/tests/)

- `test_vton_api.py` - API 엔드포인트 유닛 테스트
- `test_celery_tasks.py` - Celery 작업 유닛 테스트
- `test_integration.py` - E2E 통합 테스트
- `conftest.py` - pytest fixtures (Mock 포함)

**실행**:
```bash
cd ai-pipeline
source venv/bin/activate
pytest tests/ -v -m "not integration"  # 유닛 테스트만
```

### 4. 통합 예시 (ai-pipeline/docs/examples/)

- `frontend-integration.tsx` - React 통합 코드
- `backend-proxy.py` - FastAPI 프록시 예시
- `test_api.sh` - API 테스트 스크립트

---

## 실행 방법

### AI Pipeline 단독 실행

```bash
cd /home/MadCamp/MadCamp_3week/ai-pipeline

# 1. Redis 시작
redis-server --daemonize yes

# 2. API 서버 시작
python api/main.py &

# 3. Celery Worker 시작
celery -A workers.celery_app worker -Q vton --loglevel=info &

# 4. 테스트
curl http://localhost:8001/health
```

### 전체 스택 실행 (TODO: Docker Compose 업데이트 필요)

```bash
cd /home/MadCamp/MadCamp_3week
docker-compose up -d
```

---

## 주요 파일

| 파일 | 설명 |
|------|------|
| `ai-pipeline/api/routers/vton.py` | VTON API 엔드포인트 (동기+비동기) |
| `ai-pipeline/workers/tasks/vton_tasks.py` | Celery 비동기 작업 |
| `ai-pipeline/models/vton/idm_vton.py` | IDM-VTON 모델 래퍼 |
| `ai-pipeline/workers/vram_manager.py` | GPU VRAM 관리 |
| `ai-pipeline/config.py` | 설정 (환경변수 로드) |
| `ai-pipeline/tests/conftest.py` | pytest 설정 (Mock) |
| `ai-pipeline/docs/INTEGRATION_GUIDE.md` | 프론트엔드 통합 가이드 |

---

## 환경 변수 (.env)

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8001

# 모델
MODEL_CACHE_DIR=/path/to/models
VTON_IMAGE_SIZE=768

# 출력
OUTPUT_DIR=/path/to/outputs
CDN_BASE_URL=http://localhost:8001
```

---

## API 사용 예시

### 비동기 작업 제출
```bash
curl -X POST http://localhost:8001/api/vton/try-on-async \
  -H "Content-Type: application/json" \
  -d '{
    "person_image_url": "https://example.com/person.jpg",
    "garment_image_url": "https://example.com/garment.jpg",
    "num_inference_steps": 50,
    "callback_url": "https://your-server.com/webhook"
  }'
```

**응답**:
```json
{"task_id": "550e8400-...", "status": "PENDING"}
```

### 상태 조회
```bash
curl http://localhost:8001/api/vton/task/550e8400-...
```

**진행 중**:
```json
{
  "state": "PROGRESS",
  "progress": 60,
  "message": "Running VTON inference..."
}
```

**완료**:
```json
{
  "state": "SUCCESS",
  "result": {
    "result_url": "http://cdn/outputs/vton/async/result_550e8400.png",
    "processing_time_seconds": 24.3
  }
}
```

---

## 데이터 흐름

### 동기 요청
```
Frontend → POST /api/vton/try-on → 즉시 처리 → 결과 반환 (20-40초)
```

### 비동기 요청
```
1. Frontend → POST /api/vton/try-on-async → task_id (즉시)
2. Celery Worker → 백그라운드 처리
   - 이미지 로드 (20%)
   - 전처리 (40%)
   - VTON 추론 (60%)
   - 후처리 (80%)
   - 저장 (100%)
3. Frontend → GET /api/vton/task/{task_id} (폴링)
   또는
   Backend ← Webhook 콜백
```

---

## 테스트 결과

✅ **유닛 테스트** (2/2 passed)
- `test_health_check` - PASSED
- `test_vram_status` - PASSED

⏳ **통합 테스트** (실제 서비스 필요)
- Redis, API, Celery Worker 실행 후 테스트 가능

---

## 최근 커밋

```
aea8e70 feat: Add async VTON API with Celery integration and comprehensive tests

- Celery tasks for async VTON processing (single + batch)
- FastAPI async endpoints with progress tracking
- Comprehensive test suite (unit + integration)
- Integration guides and examples
- 15 files changed, 3337 insertions(+)
```

---

## TODO

### 즉시 가능
- [ ] Docker Compose에 ai-pipeline 서비스 추가
- [ ] Celery Beat 스케줄러 (자동 정리)
- [ ] WebSocket 진행률 전송
- [ ] CDN 통합 (S3/CloudFront)

### 중장기
- [ ] 3D 아바타 생성
- [ ] Unity WebGL 통합
- [ ] 프로덕션 배포 (K8s)

---

## 컨텍스트 복원 시 필요한 명령어

```bash
# 작업 디렉토리 이동
cd /home/MadCamp/MadCamp_3week/ai-pipeline

# 가상환경 활성화 (이미 생성됨)
source venv/bin/activate

# Git 상태 확인
git status
git log --oneline -5

# 서비스 상태 확인
redis-cli ping
curl http://localhost:8001/health

# 테스트 실행
pytest tests/test_vton_api.py -v
```

---

**이 프롬프트를 새 세션에서 제공하면 프로젝트 컨텍스트를 빠르게 복원할 수 있습니다.**
