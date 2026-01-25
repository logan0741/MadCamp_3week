# MadCamp Week 3 - AI Virtual Try-On Project

## 프로젝트 개요

무신사 스타일의 가상 피팅 플랫폼 구축 프로젝트입니다. 사용자가 옷을 가상으로 입어볼 수 있는 2D/3D 통합 솔루션을 제공합니다.

---

## 프로젝트 구조

```
MadCamp_3week/
├── backend/                 # FastAPI 백엔드 (사용자 인증, 상품 관리)
├── frontend/                # Next.js 프론트엔드 (React + TypeScript)
├── ai-pipeline/             # AI 가상 피팅 파이프라인
│   ├── api/                 # FastAPI AI 서버
│   │   ├── main.py
│   │   └── routers/
│   │       ├── vton.py      # 2D VTON 엔드포인트
│   │       └── avatar.py    # 3D 아바타 엔드포인트 (NEW)
│   ├── models/              # AI 모델 래퍼
│   │   ├── vton/            # 2D Virtual Try-On
│   │   │   ├── idm_vton.py
│   │   │   ├── preprocessor.py
│   │   │   └── postprocessor.py
│   │   ├── avatar/          # 3D 아바타 생성 (NEW)
│   │   │   ├── shapy_wrapper.py    # SHAPY 신체 추정
│   │   │   └── smplx_wrapper.py    # SMPL-X 메시 생성
│   │   ├── garment/         # 옷 시뮬레이션 (NEW)
│   │   │   ├── snug_wrapper.py     # SNUG 시뮬레이션
│   │   │   └── garment_types.py    # 옷 종류 정의
│   │   └── 3d/              # 외부 라이브러리 (NEW)
│   │       ├── shapy/       # SHAPY 원본
│   │       └── snug/        # SNUG 원본
│   ├── workers/             # Celery 작업 큐
│   │   ├── celery_app.py
│   │   ├── vram_manager.py
│   │   └── tasks/
│   │       └── vton_tasks.py
│   ├── tests/               # 테스트 스위트
│   ├── docs/                # 문서 및 예시
│   └── config.py
└── docker-compose.yml
```

---

## 주요 기능 구현 완료 사항

### 1. AI 파이프라인 - 2D 가상 피팅

#### ✅ 동기 API (즉시 응답)
- **엔드포인트**: `POST /api/vton/try-on`
- **처리 방식**: 요청 시 즉시 처리 (20-40초)
- **사용 사례**: 실시간 프리뷰, 단건 처리

**요청 예시:**
```bash
curl -X POST http://localhost:8001/api/vton/try-on \
  -F "person_image=@person.jpg" \
  -F "garment_image=@garment.jpg" \
  -F "num_inference_steps=50"
```

**응답:**
```json
{
  "success": true,
  "result_url": "http://cdn/outputs/vton/result_uuid.png",
  "processing_time_seconds": 23.45
}
```

#### ✅ 비동기 API (백그라운드 처리) ⭐ NEW

- **엔드포인트**: `POST /api/vton/try-on-async`
- **처리 방식**: Celery 작업 큐로 백그라운드 처리
- **장점**:
  - 즉시 응답 (< 100ms)
  - 진행률 추적 가능
  - 완료 시 Webhook 콜백
  - 배치 처리 지원

**작업 제출:**
```bash
curl -X POST http://localhost:8001/api/vton/try-on-async \
  -H "Content-Type: application/json" \
  -d '{
    "person_image_url": "https://example.com/person.jpg",
    "garment_image_url": "https://example.com/garment.jpg",
    "callback_url": "https://your-server.com/webhook"
  }'
```

**즉시 응답:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "message": "Task submitted successfully"
}
```

**상태 조회:**
```bash
curl http://localhost:8001/api/vton/task/550e8400-e29b-41d4-a716-446655440000
```

**진행 중 응답:**
```json
{
  "task_id": "550e8400-...",
  "state": "PROGRESS",
  "status": "processing",
  "progress": 60,
  "current": 3,
  "total": 5,
  "message": "Running VTON inference..."
}
```

**완료 응답:**
```json
{
  "task_id": "550e8400-...",
  "state": "SUCCESS",
  "status": "completed",
  "result": {
    "success": true,
    "result_url": "http://cdn/outputs/vton/async/result_550e8400.png",
    "processing_time_seconds": 24.3
  }
}
```

#### ✅ 배치 처리
- **엔드포인트**: `POST /api/vton/batch-async`
- **처리 방식**: 여러 이미지를 순차 처리
- **사용 사례**: 카탈로그 전체 처리, 대량 생성

```bash
curl -X POST http://localhost:8001/api/vton/batch-async \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"person_image_url": "...", "garment_image_url": "..."},
      {"person_image_url": "...", "garment_image_url": "..."}
    ]
  }'
```

---

### 2. Celery 작업 큐 시스템

#### 구현된 작업 (workers/tasks/vton_tasks.py)

1. **process_vton_async**: 단일 VTON 작업
   - 진행률 추적 (5단계)
   - VRAM 자동 관리
   - 재시도 로직 (최대 3회)
   - Webhook 콜백 지원

2. **process_vton_batch_async**: 배치 작업
   - 여러 요청을 순차 처리
   - 실패한 항목 추적
   - 전체 결과 요약

3. **cleanup_old_results**: 자동 파일 정리
   - 오래된 결과 파일 삭제
   - 주기적 실행 가능 (Celery Beat)

#### 작업 흐름
```
1. Client → API 요청
2. API → Celery 작업 제출 → task_id 즉시 반환
3. Celery Worker → 백그라운드 처리
   ├─ 이미지 로드 (진행률 20%)
   ├─ 전처리 (진행률 40%)
   ├─ VTON 추론 (진행률 60%)
   ├─ 후처리 (진행률 80%)
   └─ 결과 저장 (진행률 100%)
4. Worker → Webhook 전송 (선택사항)
5. Client → 상태 폴링 또는 Webhook 수신
```

---

### 3. 프론트엔드 통합 가이드

#### React + TypeScript 통합 예시

**파일**: `docs/examples/frontend-integration.tsx`

```typescript
// 비동기 작업 제출
const response = await fetch('http://localhost:8001/api/vton/try-on-async', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    person_image_url: personImageUrl,
    garment_image_url: garmentImageUrl,
  })
});

const { task_id } = await response.json();

// 상태 폴링 (1초마다)
const checkStatus = async () => {
  const statusRes = await fetch(`http://localhost:8001/api/vton/task/${task_id}`);
  const data = await statusRes.json();

  if (data.state === 'SUCCESS') {
    setResultUrl(data.result.result_url);
  } else if (data.state === 'PROGRESS') {
    setProgress(data.progress);
  }
};
```

**UI 컴포넌트**:
- VTONUploader: 이미지 업로드
- ProgressBar: 작업 진행률 표시
- ResultViewer: 결과 이미지 표시

---

### 4. 백엔드 프록시 설정

**파일**: `docs/examples/backend-proxy.py`

Node.js/Express 백엔드가 AI API를 프록시하는 예시:

```python
# FastAPI 프록시
@app.post("/api/proxy/vton/try-on-async")
async def proxy_vton_async(request: VTONRequest):
    # AI API 호출
    response = httpx.post(
        "http://ai-pipeline:8001/api/vton/try-on-async",
        json=request.dict()
    )
    return response.json()
```

**장점**:
- CORS 이슈 해결
- 인증/권한 검사 추가 가능
- 요청 로깅
- Rate limiting

---

### 5. 테스트 스위트

#### 유닛 테스트
**파일**:
- `tests/test_vton_api.py` - API 엔드포인트 테스트
- `tests/test_celery_tasks.py` - Celery 작업 테스트

**실행**:
```bash
cd ai-pipeline
source venv/bin/activate
pytest tests/ -v -m "not integration"
```

**테스트 커버리지**:
- ✅ Health check
- ✅ VRAM 상태 조회
- ✅ 동기 VTON API (Mock)
- ✅ 비동기 VTON API
- ✅ 작업 상태 조회
- ✅ 배치 처리
- ✅ 에러 처리 (잘못된 파라미터, 존재하지 않는 task_id)

#### 통합 테스트
**파일**: `tests/test_integration.py`

**전제 조건**:
- Redis 실행
- API 서버 실행
- Celery Worker 실행

**실행**:
```bash
# 서비스 시작
redis-server --daemonize yes
python api/main.py &
celery -A workers.celery_app worker -Q vton &

# 통합 테스트
pytest tests/test_integration.py -v -m integration
```

---

## 시스템 아키텍처

```
┌─────────────┐
│   Frontend  │ (Next.js)
│  (Port 3000)│
└──────┬──────┘
       │
       ├──────────────┐
       │              │
┌──────▼──────┐  ┌───▼────────────┐
│  Backend    │  │  AI Pipeline   │
│  (Port 8000)│  │  (Port 8001)   │
│  FastAPI    │  │  FastAPI       │
└─────────────┘  └────┬───────────┘
                      │
                      ├─────────────┬──────────────┐
                      │             │              │
                ┌─────▼─────┐  ┌───▼──────┐  ┌───▼────────┐
                │   Redis   │  │  Celery  │  │   Models   │
                │ (Port 6379│  │  Worker  │  │  (GPU)     │
                └───────────┘  └──────────┘  └────────────┘
```

### 데이터 흐름

1. **동기 요청**:
   ```
   User → Frontend → AI API → Model → Response → Frontend
   ```

2. **비동기 요청**:
   ```
   User → Frontend → AI API → Celery → Redis (task_id)
                                  ↓
                              Worker → Model → Save Result
                                  ↓
   User ← Frontend ← Webhook (or Polling)
   ```

---

## 환경 설정

### 필수 요구사항

1. **Python 3.10+**
2. **Redis** (Celery broker)
3. **CUDA GPU** (VTON 모델 추론)

### 설치 및 실행

#### 1. AI Pipeline 설정

```bash
cd ai-pipeline

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집:
# - REDIS_URL=redis://localhost:6379/0
# - MODEL_CACHE_DIR=/path/to/models
# - OUTPUT_DIR=/path/to/outputs
```

#### 2. Redis 시작
```bash
redis-server --daemonize yes
```

#### 3. API 서버 시작
```bash
python api/main.py
# 또는
./start_api.sh
```

#### 4. Celery Worker 시작
```bash
celery -A workers.celery_app worker -Q vton --loglevel=info
# 또는
./start_worker.sh
```

#### 5. 테스트
```bash
# 단순 헬스체크
curl http://localhost:8001/health

# 동기 VTON 테스트
bash docs/examples/test_api.sh sync

# 비동기 VTON 테스트
bash docs/examples/test_api.sh async
```

---

## API 엔드포인트 전체 목록

### 시스템 관리

| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 헬스 체크 |
| GET | `/vram-status` | GPU VRAM 상태 조회 |

### 2D VTON (Virtual Try-On)

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/vton/try-on` | 동기 가상 피팅 (즉시 응답) |
| POST | `/api/vton/try-on-async` | 비동기 가상 피팅 (백그라운드) |
| POST | `/api/vton/batch-async` | 배치 가상 피팅 |
| GET | `/api/vton/task/{task_id}` | 작업 상태 조회 |

### 3D 아바타 (NEW)

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/avatar/generate` | 이미지/치수에서 3D 아바타 생성 |
| POST | `/api/avatar/garment/simulate` | 아바타에 옷 시뮬레이션 |
| POST | `/api/avatar/combined` | 아바타+옷 통합 생성 |
| GET | `/api/avatar/garments/types` | 사용 가능한 옷 종류 조회 |
| GET | `/api/avatar/{avatar_id}` | 아바타 정보 조회 |
| DELETE | `/api/avatar/{avatar_id}` | 아바타 삭제 |

---

## 문제 해결

### 일반적인 문제

#### 1. Redis 연결 실패
```
redis.exceptions.ConnectionError
```
**해결**: Redis 시작
```bash
redis-server --daemonize yes
```

#### 2. Celery 작업이 PENDING 상태로 멈춤
**원인**: Worker가 실행되지 않음
**해결**:
```bash
celery -A workers.celery_app worker -Q vton --loglevel=info
```

#### 3. CUDA Out of Memory
**원인**: GPU VRAM 부족
**해결**:
- `config.py`에서 `vton_image_size` 줄이기 (768 → 512)
- 병렬 작업 수 제한

#### 4. 모델 가중치 없음
```
FileNotFoundError: Model weights not found
```
**해결**:
```python
# 모델 자동 다운로드
from models.vton.idm_vton import get_vton_model
get_vton_model()
```

---

## 3D 아바타 생성 파이프라인 (NEW)

### 개요
SMPL-X 기반 3D 아바타 생성 및 옷 시뮬레이션 파이프라인입니다.

### 사용 라이브러리
- **SHAPY** (https://github.com/muelea/shapy): 이미지에서 신체 형상(SMPL-X 파라미터) 추정
- **SNUG** (https://github.com/isantesteban/snug): 신경망 기반 옷 시뮬레이션
- **SMPL-X**: 파라메트릭 인체 모델

### API 엔드포인트

#### 1. 아바타 생성
```bash
# 이미지에서 아바타 생성
POST /api/avatar/generate
{
  "image_url": "https://example.com/person.jpg",
  "output_format": "glb"
}

# 신체 치수에서 아바타 생성
POST /api/avatar/generate
{
  "measurements": {
    "height": 1.75,
    "weight": 70,
    "chest": 95,
    "waist": 80,
    "hips": 95,
    "gender": "male"
  },
  "output_format": "glb"
}
```

**응답:**
```json
{
  "success": true,
  "avatar_id": "uuid",
  "mesh_url": "http://cdn/outputs/avatars/avatar_uuid.glb",
  "betas": [0.1, -0.2, ...],
  "measurements": {"height": 1.75, ...},
  "processing_time_seconds": 2.5
}
```

#### 2. 옷 시뮬레이션
```bash
POST /api/avatar/garment/simulate
{
  "avatar_id": "uuid",
  "garment_type": "tshirt",
  "output_format": "glb"
}
```

**응답:**
```json
{
  "success": true,
  "garment_mesh_url": "http://cdn/outputs/garments/garment_uuid.glb",
  "combined_mesh_url": "http://cdn/outputs/garments/combined_uuid.glb",
  "processing_time_seconds": 1.2
}
```

#### 3. 통합 아바타+옷 생성
```bash
POST /api/avatar/combined
{
  "person_image_url": "https://example.com/person.jpg",
  "garment_type": "tshirt",
  "output_format": "glb"
}
```

#### 4. 사용 가능한 옷 종류 조회
```bash
GET /api/avatar/garments/types
```

**응답:**
```json
{
  "garments": [
    {"type": "tshirt", "name": "T-Shirt"},
    {"type": "tank", "name": "Tank Top"},
    {"type": "dress", "name": "Dress"},
    {"type": "pants", "name": "Pants"},
    {"type": "shorts", "name": "Shorts"}
  ]
}
```

### 파이프라인 아키텍처
```
1. 이미지 입력 → SHAPY → SMPL-X 파라미터 (betas)
2. SMPL-X 파라미터 → SMPL-X 모델 → 3D 인체 메시
3. 3D 인체 메시 + 옷 템플릿 → SNUG → 3D 옷 메시
4. 인체 메시 + 옷 메시 → 통합 3D 모델 (GLB/OBJ)
```

### 모델 설치 (필요)
SHAPY와 SNUG는 추가 모델 파일이 필요합니다:

1. **SMPL-X 모델**: https://smpl-x.is.tue.mpg.de 에서 다운로드
2. **SHAPY 학습 모델**: https://shapy.is.tue.mpg.de 에서 다운로드
3. **SMPL 모델** (SNUG용): https://smpl.is.tue.mpg.de 에서 다운로드

---

## 다음 단계 (TODO)

### 즉시 구현 가능
- [ ] Celery Beat 스케줄러 설정 (자동 정리 작업)
- [ ] 결과 이미지 CDN 업로드
- [ ] WebSocket 실시간 진행률 전송
- [ ] Docker Compose에 AI pipeline 추가
- [x] 3D 아바타 생성 API 엔드포인트
- [ ] SMPL-X 모델 파일 다운로드 및 설정
- [ ] SHAPY 학습 모델 다운로드 및 설정

### 중장기 계획
- [x] 3D 아바타 생성 파이프라인 (기본 구조)
- [ ] Unity WebGL 통합
- [ ] 모델 A/B 테스트 프레임워크
- [ ] 프로덕션 배포 (Kubernetes)

---

## 프로젝트 파일 위치

- **작업 디렉토리**: `/home/MadCamp/MadCamp_3week/`
- **Git 브랜치**: `AI`
- **최근 커밋**: `aea8e70 - feat: Add async VTON API with Celery integration`

---

## 문서

- [통합 가이드](ai-pipeline/docs/INTEGRATION_GUIDE.md)
- [구현 상태](ai-pipeline/docs/IMPLEMENTATION_STATUS.md)
- [테스트 가이드](ai-pipeline/tests/README.md)

---

## 연락처 및 참고

- **프로젝트**: MadCamp Week 3
- **주제**: AI Virtual Try-On
- **기술 스택**:
  - Frontend: Next.js, React, TypeScript
  - Backend: FastAPI, SQLite
  - AI: PyTorch, Diffusers, IDM-VTON
  - Queue: Celery, Redis
  - Test: pytest

---

**Last Updated**: 2026-01-25
