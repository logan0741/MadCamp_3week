# AI 파이프라인 통합 가이드

무신사 가상 피팅 서비스 - 전체 시스템 통합 가이드

---

## 📋 목차

1. [시스템 아키텍처](#시스템-아키텍처)
2. [빠른 시작](#빠른-시작)
3. [프론트엔드 통합](#프론트엔드-통합)
4. [백엔드 통합](#백엔드-통합)
5. [API 레퍼런스](#api-레퍼런스)
6. [배포 가이드](#배포-가이드)
7. [트러블슈팅](#트러블슈팅)

---

## 시스템 아키텍처

```
┌─────────────────┐
│  Next.js 14     │  포트 3000
│  Frontend       │
└────────┬────────┘
         │
         │ HTTP
         ▼
┌─────────────────┐
│  FastAPI        │  포트 8000
│  Main Backend   │
└────────┬────────┘
         │
         │ HTTP Proxy
         ▼
┌─────────────────┐
│  FastAPI        │  포트 8001
│  AI Pipeline    │
└────────┬────────┘
         │
         ├─► Redis (Celery Broker)
         │
         ├─► PostgreSQL (Task DB)
         │
         └─► 96GB VRAM (AI Models)
```

---

## 빠른 시작

### 1. AI 파이프라인 실행

```bash
# 1. Redis 시작
redis-server &

# 2. AI API 서버 실행
cd /root/MadCamp_3week/ai-pipeline
./start_api.sh

# 3. Celery Worker 실행 (새 터미널)
./start_celery.sh

# 4. 테스트
chmod +x docs/examples/test_api.sh
./docs/examples/test_api.sh
```

### 2. API 확인

- Swagger UI: http://localhost:8001/docs
- Health Check: http://localhost:8001/health
- VRAM Status: http://localhost:8001/vram-status

---

## 프론트엔드 통합

### 환경 변수 설정

```bash
# frontend/.env.local
NEXT_PUBLIC_AI_API_URL=http://localhost:8001
```

### 컴포넌트 추가

```typescript
// components/VirtualTryOn.tsx
// 전체 코드: docs/examples/frontend-integration.tsx 참고

import VirtualTryOnComponent from "@/components/VirtualTryOn";

export default function ProductPage() {
  return (
    <div>
      <VirtualTryOnComponent />
    </div>
  );
}
```

### API 호출 예시

#### 동기 방식 (즉시 결과)

```typescript
const response = await fetch("http://localhost:8001/api/vton/try-on", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    person_image_url: "https://example.com/person.jpg",
    garment_image_url: "https://example.com/garment.jpg",
    num_inference_steps: 50,
  }),
});

const result = await response.json();
console.log(result.result_url); // 결과 이미지 URL
```

#### 비동기 방식 (진행 상태 표시)

```typescript
// 1. 작업 제출
const submitResponse = await fetch("http://localhost:8001/api/vton/try-on/async", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ /* ... */ }),
});

const { task_id } = await submitResponse.json();

// 2. 폴링으로 상태 확인
const interval = setInterval(async () => {
  const statusResponse = await fetch(
    `http://localhost:8001/api/vton/tasks/${task_id}`
  );
  const status = await statusResponse.json();

  if (status.status === "SUCCESS") {
    clearInterval(interval);
    console.log(status.result.result_url);
  }
}, 1000); // 1초마다
```

---

## 백엔드 통합

### 라우터 추가

```python
# backend/routers/ai_proxy.py
# 전체 코드: docs/examples/backend-proxy.py 참고

from fastapi import APIRouter, Depends
import httpx

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/vton/try-on")
async def proxy_vton(
    request: VTONRequest,
    current_user = Depends(get_current_user),
):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/api/vton/try-on",
            json=request.dict(),
        )
        return response.json()
```

### main.py에 등록

```python
# backend/main.py
from routers import ai_proxy

app.include_router(ai_proxy.router, prefix="/api")
```

### 데이터베이스 스키마

```python
# backend/models.py
class AITask(Base):
    __tablename__ = "ai_tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_type = Column(String(50))  # "VTON"
    celery_task_id = Column(String(255))
    status = Column(String(50))  # PENDING, PROCESSING, COMPLETED, FAILED
    result_url = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
```

---

## API 레퍼런스

### 동기 VTON

**Endpoint**: `POST /api/vton/try-on`

**Request**:
```json
{
  "person_image_url": "https://example.com/person.jpg",
  "garment_image_url": "https://example.com/garment.jpg",
  "num_inference_steps": 50,
  "guidance_scale": 7.5,
  "enhance_output": true,
  "restore_face": true
}
```

**Response**:
```json
{
  "success": true,
  "result_url": "http://localhost:8001/outputs/vton/result_abc123.png",
  "processing_time_seconds": 2.35,
  "vram_allocated_mb": 8192.5
}
```

### 비동기 VTON

**Endpoint**: `POST /api/vton/try-on/async`

**Request**: 동일

**Response**:
```json
{
  "success": true,
  "task_id": "abc123-def456",
  "status_url": "/api/vton/tasks/abc123-def456",
  "message": "Task submitted successfully"
}
```

### 작업 상태 조회

**Endpoint**: `GET /api/vton/tasks/{task_id}`

**Response (진행 중)**:
```json
{
  "task_id": "abc123-def456",
  "status": "PROGRESS",
  "progress": 65,
  "current": 3,
  "total": 5,
  "message": "Running VTON inference..."
}
```

**Response (완료)**:
```json
{
  "task_id": "abc123-def456",
  "status": "SUCCESS",
  "result": {
    "success": true,
    "result_url": "...",
    "processing_time_seconds": 2.35
  }
}
```

### 파일 업로드

**Endpoint**: `POST /api/vton/try-on/upload`

**Request (multipart/form-data)**:
```bash
curl -X POST "http://localhost:8001/api/vton/try-on/upload" \
  -F "person_image=@person.jpg" \
  -F "garment_image=@garment.jpg" \
  -F "num_inference_steps=50"
```

---

## 배포 가이드

### 환경별 설정

#### Development
```bash
# .env
ENVIRONMENT=development
API_PORT=8001
CELERY_MAX_CONCURRENT=2
```

#### Production
```bash
# .env
ENVIRONMENT=production
API_PORT=8001
CELERY_MAX_CONCURRENT=4
CDN_BASE_URL=https://cdn.yourdomain.com
```

### Docker Compose

```yaml
# docker-compose.yml (예시)
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  ai-api:
    build: .
    ports:
      - "8001:8001"
    environment:
      - REDIS_HOST=redis
    depends_on:
      - redis
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

  celery-worker:
    build: .
    command: celery -A workers.celery_app worker --loglevel=info
    environment:
      - REDIS_HOST=redis
    depends_on:
      - redis
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
```

### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/ai-pipeline
upstream ai_api {
    server localhost:8001;
}

server {
    listen 80;
    server_name ai.yourdomain.com;

    location / {
        proxy_pass http://ai_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # 파일 업로드 크기 제한
        client_max_body_size 50M;

        # 타임아웃 설정 (AI 추론 대기)
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

---

## 트러블슈팅

### CUDA Out of Memory

**증상**: `RuntimeError: CUDA out of memory`

**해결**:
```bash
# 1. 모델 재로드
curl -X POST http://localhost:8001/api/vton/model/reload

# 2. Celery worker 재시작
pkill -f "celery worker"
./start_celery.sh

# 3. VRAM 사용량 확인
curl http://localhost:8001/vram-status
```

### Celery 작업이 실행되지 않음

**증상**: 비동기 작업 상태가 계속 PENDING

**확인 사항**:
```bash
# 1. Redis 연결 확인
redis-cli ping

# 2. Celery worker 상태 확인
celery -A workers.celery_app inspect active

# 3. 로그 확인
tail -f logs/ai-pipeline.log
```

### 모델 다운로드 실패

**증상**: `Failed to load IDM-VTON`

**해결**:
```bash
# Hugging Face 캐시 삭제 후 재시도
rm -rf ~/.cache/huggingface

# 또는 직접 다운로드
python3 -c "from diffusers import StableDiffusionInpaintPipeline; \
             StableDiffusionInpaintPipeline.from_pretrained('yisol/IDM-VTON')"
```

### 프론트엔드 CORS 에러

**증상**: `Access-Control-Allow-Origin` 에러

**해결**:
```python
# ai-pipeline/config.py
cors_origins = [
    "http://localhost:3000",  # 프론트엔드 추가
    "https://yourdomain.com",
]
```

---

## 성능 최적화

### 1. 캐싱 전략

```typescript
// 프론트엔드: 결과 이미지 캐싱
const cacheKey = `vton_${personUrl}_${garmentUrl}`;
const cached = localStorage.getItem(cacheKey);

if (cached) {
  return cached; // 캐시된 결과 사용
}
```

### 2. 배치 처리

```python
# 여러 상품을 한 번에 처리
POST /api/vton/try-on/batch-async
{
  "requests": [
    { "person_image_url": "...", "garment_image_url": "..." },
    { "person_image_url": "...", "garment_image_url": "..." }
  ]
}
```

### 3. 이미지 최적화

```typescript
// 프론트엔드: 이미지 리사이징
const resizeImage = async (file: File, maxWidth: 768) => {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const img = await createImageBitmap(file);

  const scale = maxWidth / img.width;
  canvas.width = maxWidth;
  canvas.height = img.height * scale;

  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.9);
};
```

---

## 보안 고려사항

1. **API 인증**: JWT 토큰 또는 API 키 사용
2. **Rate Limiting**: 사용자당 요청 제한
3. **파일 검증**: 업로드 파일 타입 및 크기 확인
4. **HTTPS**: 프로덕션에서 필수

```python
# 예시: Rate limiting
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/try-on")
@limiter.limit("10/minute")
async def try_on(...):
    ...
```

---

## 참고 자료

- [AI Pipeline README](../README.md)
- [Unity 요구사항](./UNITY_REQUIREMENTS.md)
- [구현 상태](./IMPLEMENTATION_STATUS.md)
- [프론트엔드 예시](./examples/frontend-integration.tsx)
- [백엔드 프록시 예시](./examples/backend-proxy.py)

---

**문서 버전**: 1.0
**최종 수정**: 2026-01-24
**작성자**: AI Pipeline Team
