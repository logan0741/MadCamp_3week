# AI 파이프라인 구현 상태 및 작업 계획

## ✅ 현재 완료된 것 (바로 사용 가능)

### 1. IDM-VTON 2D 가상 피팅
**상태**: 100% 완료 ✅

**사용 방법**:
```bash
# 1. 환경 설정
cd /root/MadCamp_3week/ai-pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. .env 파일 생성
cp .env.example .env

# 3. Redis 실행
redis-server &

# 4. API 서버 실행
./start_api.sh

# 5. 테스트
curl -X POST "http://localhost:8001/api/vton/try-on" \
  -H "Content-Type: application/json" \
  -d '{
    "person_image_url": "https://example.com/person.jpg",
    "garment_image_url": "https://example.com/garment.jpg"
  }'
```

**모델 다운로드**: 자동 (첫 실행 시 Hugging Face에서 다운로드)

---

## ⚠️ 부분 완료 (구조만 있음)

### 2. FastAPI 서버
**상태**: 30% 완료

**완료**:
- ✅ VTON 엔드포인트 (/api/vton/*)
- ✅ 헬스 체크 (/health)
- ✅ VRAM 모니터링 (/vram-status)

**미완성**:
- ❌ 아바타 생성 엔드포인트 (/api/avatar/*)
- ❌ 의류 모델링 엔드포인트 (/api/garment/*)
- ❌ 비동기 작업 상태 조회 (/api/tasks/{task_id})

### 3. Celery 작업 큐
**상태**: 40% 완료

**완료**:
- ✅ Celery 앱 설정
- ✅ VRAM 자원 관리 시스템
- ✅ 큐 분리 (vton/avatar/garment)

**미완성**:
- ❌ VTON 비동기 작업 (workers/tasks/vton_tasks.py)
- ❌ ECON 작업 (workers/tasks/avatar_tasks.py)
- ❌ BCNet 작업 (workers/tasks/garment_tasks.py)

---

## ❌ 미구현 (코드 없음)

### 4. ECON 아바타 생성
**필요한 작업**:

```
ai-pipeline/models/econ/
├── econ_model.py          # ECON 메인 모델 (미작성)
├── smplx_wrapper.py       # SMPL-X 리깅 (미작성)
├── video_processor.py     # 비디오 프레임 추출 (미작성)
└── mesh_exporter.py       # GLB/GLTF 내보내기 (미작성)
```

**예상 작업량**: 3-5일
**난이도**: 상 (SMPL-X 라이브러리 복잡도 높음)

### 5. BCNet 의류 모델링
**필요한 작업**:

```
ai-pipeline/models/bcnet/
├── bcnet_model.py         # BCNet 메인 모델 (미작성)
├── garment_segmenter.py   # 상품 이미지 분할 (미작성)
├── mesh_generator.py      # 3D 메시 생성 (미작성)
└── texture_mapper.py      # UV 매핑 (미작성)
```

**예상 작업량**: 3-4일
**난이도**: 상

### 6. 3D Gaussian Splatting
**필요한 작업**:

```
ai-pipeline/models/3dgs/
├── gaussian_renderer.py   # 3DGS 렌더러 (미작성)
├── point_cloud_builder.py # 포인트 클라우드 생성 (미작성)
└── unity_exporter.py      # Unity 포맷 변환 (미작성)
```

**예상 작업량**: 4-6일
**난이도**: 매우 상 (CUDA 커널 필요)

---

## 🔧 추가로 필요한 것

### 7. Unity 클라이언트 개발
**담당**: Unity 개발자
**문서**: [UNITY_REQUIREMENTS.md](./UNITY_REQUIREMENTS.md) 제공됨

**필요한 구현**:
- Unity WebGL 프로젝트 생성
- GLB/GLTF 로더 통합 (GLTFUtility)
- 아바타 뷰어 씬
- 의류 피팅 시스템 (충돌 방지)
- React ↔ Unity 통신

**예상 작업량**: 2-3주
**난이도**: 중상

### 8. 프론트엔드 통합
**담당**: 프론트엔드 개발자
**위치**: `/root/MadCamp_3week/frontend/`

**필요한 구현**:
- react-unity-webgl 설치 및 설정
- Unity 빌드 파일 호스팅
- AI API 호출 (axios/fetch)
- 로딩 상태 UI
- 에러 처리

**예상 작업량**: 3-5일
**난이도**: 중

### 9. 백엔드 API 통합
**담당**: 백엔드 개발자
**위치**: `/root/MadCamp_3week/backend/`

**필요한 통합**:
- AI API 프록시 (FastAPI 8001 → Main Backend)
- 사용자 인증 연동
- 파일 업로드 처리
- PostgreSQL 연동 (ai_tasks 테이블)
- Webhook 콜백 처리

**예상 작업량**: 2-3일
**난이도**: 중하

---

## 📋 전체 개발 타임라인

### Phase 1: 즉시 가능 (현재)
- [x] 2D VTON API 사용

### Phase 2: 1주차 (AI 모델 통합)
- [ ] ECON 모델 구현 및 테스트
- [ ] BCNet 모델 구현 및 테스트
- [ ] 비동기 API 엔드포인트 추가
- [ ] Celery 작업 구현

### Phase 3: 2주차 (Unity 개발)
- [ ] Unity WebGL 프로젝트 생성
- [ ] 아바타 뷰어 구현
- [ ] 의류 피팅 시스템 구현
- [ ] 성능 최적화

### Phase 4: 3주차 (통합 및 배포)
- [ ] 프론트엔드 통합
- [ ] 백엔드 API 통합
- [ ] E2E 테스트
- [ ] Docker 배포 설정
- [ ] 프로덕션 최적화

---

## 💰 필요한 모델 가중치

### 자동 다운로드 (설정 불필요)
- ✅ IDM-VTON: Hugging Face (yisol/IDM-VTON)

### 수동 다운로드 필요
**ECON**:
- 다운로드: https://github.com/YuliangXiu/ECON/releases
- 위치: `models/weights/econ/econ_checkpoint.pth`
- 크기: ~3GB

**SMPL-X**:
- 다운로드: https://smpl-x.is.tue.mpg.de/ (회원가입 필요)
- 위치: `models/weights/smplx/SMPLX_NEUTRAL.npz`
- 크기: ~100MB

**BCNet**:
- 다운로드: TBD (논문 저자에게 요청 필요)
- 위치: `models/weights/bcnet/bcnet_checkpoint.pth`
- 크기: ~500MB

---

## 🚀 빠른 시작 가이드

### 지금 당장 테스트 가능한 것:

```bash
# 1. 2D 가상 피팅만 먼저 테스트
cd /root/MadCamp_3week/ai-pipeline
python3 -m venv venv
source venv/bin/activate

# PyTorch 설치 (CUDA)
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 나머지 패키지
pip install -r requirements.txt

# 환경 설정
cp .env.example .env

# Redis 시작
redis-server &

# API 서버 실행
python3 api/main.py
```

**테스트 방법**:
- Swagger UI: http://localhost:8001/docs
- VTON 엔드포인트로 테스트 이미지 업로드

### 3D 기능을 사용하려면:

1. **AI 모델 구현** (1-2주 소요)
   - ECON, BCNet, 3DGS 코드 작성
   - 모델 가중치 다운로드

2. **Unity 클라이언트** (2-3주 소요)
   - Unity 프로젝트 생성
   - 문서 참고하여 구현

3. **통합** (1주 소요)
   - 프론트엔드 ↔ Unity 연동
   - 백엔드 ↔ AI API 연동

---

## ⚡ 결론

### 현재 상태:
- 2D 가상 피팅: **즉시 사용 가능** ✅
- 3D 아바타 생성: **4주 정도 추가 개발 필요** ⏳
- Unity 통합: **Unity 팀 개발 필요** 👥

### 권장 접근:
1. **먼저 2D VTON으로 MVP 구축** (이번 주)
2. **병렬로 Unity 개발 시작** (다음 주부터)
3. **3D 모델은 점진적 추가** (여유 있을 때)

실제 무신사 가격 추적 기능은 2D만으로도 충분히 가치가 있습니다!
