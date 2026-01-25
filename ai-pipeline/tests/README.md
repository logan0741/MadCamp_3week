# AI Pipeline Tests

테스트 스위트 문서

## 테스트 구조

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures 및 설정
├── test_vton_api.py        # FastAPI 엔드포인트 테스트
├── test_celery_tasks.py    # Celery 작업 테스트 (유닛 테스트)
└── test_integration.py     # 통합 테스트 (실제 서비스 필요)
```

## 테스트 종류

### 1. 유닛 테스트 (Unit Tests)
개별 컴포넌트를 격리하여 테스트합니다. Mock을 사용하여 외부 의존성을 제거합니다.

**파일**: `test_vton_api.py`, `test_celery_tasks.py`

**실행**:
```bash
pytest tests/test_vton_api.py -v
pytest tests/test_celery_tasks.py -v
```

**특징**:
- 빠른 실행 (< 1초)
- 외부 서비스 불필요
- Mock 사용으로 격리된 테스트

### 2. 통합 테스트 (Integration Tests)
실제 서비스를 구동하고 E2E 워크플로우를 테스트합니다.

**파일**: `test_integration.py`

**실행**:
```bash
# 먼저 서비스 시작
redis-server &
./start_api.sh &
celery -A workers.celery_app worker -Q vton --loglevel=info &

# 통합 테스트 실행
pytest tests/test_integration.py -v -m integration
```

**특징**:
- 실제 Redis, Celery, API 서버 필요
- 느린 실행 (10초 ~ 수분)
- 실제 모델 가중치 필요 (선택적)

## 테스트 실행 방법

### 전체 테스트 실행
```bash
# 유닛 테스트만 (빠름)
pytest tests/ -v -m "not integration"

# 통합 테스트 포함 (느림)
pytest tests/ -v
```

### 특정 테스트 클래스/함수 실행
```bash
# 특정 클래스
pytest tests/test_vton_api.py::TestHealthCheck -v

# 특정 함수
pytest tests/test_vton_api.py::TestHealthCheck::test_health_check -v
```

### 마커 기반 실행
```bash
# 통합 테스트만
pytest -m integration

# 느린 테스트 제외
pytest -m "not slow"

# API 테스트만
pytest -m api
```

### 병렬 실행 (pytest-xdist)
```bash
# 4개 워커로 병렬 실행
pip install pytest-xdist
pytest -n 4
```

## 테스트 환경 설정

### 필수 패키지 설치
```bash
pip install pytest pytest-asyncio httpx
```

### 선택적 패키지
```bash
# 코드 커버리지
pip install pytest-cov

# 병렬 실행
pip install pytest-xdist

# 타임아웃
pip install pytest-timeout
```

### 환경 변수
```bash
# 테스트 환경 설정
export TESTING=true
export REDIS_URL=redis://localhost:6379/1  # 테스트용 DB
```

## Fixtures

`conftest.py`에 정의된 공통 픽스처:

- `test_client`: FastAPI TestClient
- `sample_person_image`: 테스트용 사람 이미지
- `sample_garment_image`: 테스트용 의류 이미지
- `sample_person_image_base64`: Base64 인코딩된 사람 이미지
- `sample_garment_image_base64`: Base64 인코딩된 의류 이미지
- `mock_vton_model`: VTON 모델 Mock (실제 모델 로드 안 함)

## 테스트 커버리지

### 커버리지 리포트 생성
```bash
pytest --cov=api --cov=workers --cov=models tests/
```

### HTML 리포트
```bash
pytest --cov=api --cov=workers --cov=models --cov-report=html tests/
# htmlcov/index.html 열기
```

### 커버리지 목표
- 전체: > 80%
- API 엔드포인트: > 90%
- Celery 작업: > 85%
- 모델 래퍼: > 70%

## CI/CD 통합

### GitHub Actions 예시
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run unit tests
        run: pytest tests/ -v -m "not integration" --cov

      - name: Run integration tests
        run: |
          # Start services
          python api/main.py &
          celery -A workers.celery_app worker -Q vton &

          # Wait for services
          sleep 5

          # Run tests
          pytest tests/test_integration.py -v
```

## 문제 해결

### API 서버가 실행 중이지 않음
```
httpx.ConnectError: [Errno 111] Connection refused
```
**해결**: API 서버를 먼저 시작하세요
```bash
./start_api.sh
```

### Redis 연결 실패
```
redis.exceptions.ConnectionError: Error connecting to Redis
```
**해결**: Redis를 시작하세요
```bash
redis-server &
```

### Celery 작업이 PENDING 상태로 멈춤
**해결**: Celery worker를 시작하세요
```bash
celery -A workers.celery_app worker -Q vton --loglevel=info
```

### 모델 가중치 없음
```
FileNotFoundError: Model weights not found
```
**해결**: Mock을 사용하거나 실제 모델을 다운로드하세요
```bash
# Mock 사용 (유닛 테스트)
pytest tests/test_vton_api.py -v  # mock_vton_model fixture 자동 적용

# 실제 모델 다운로드
python -c "from models.vton.idm_vton import get_vton_model; get_vton_model()"
```

## 베스트 프랙티스

1. **Fast Feedback Loop**
   - 유닛 테스트를 자주 실행 (< 5초)
   - 통합 테스트는 PR 전에만 실행

2. **Test Isolation**
   - 각 테스트는 독립적으로 실행 가능해야 함
   - 테스트 간 상태 공유 금지

3. **Descriptive Names**
   - 테스트 함수명에 무엇을 테스트하는지 명시
   - `test_try_on_with_invalid_steps`

4. **Arrange-Act-Assert**
   ```python
   def test_example():
       # Arrange
       payload = {...}

       # Act
       response = client.post("/api/vton/try-on", json=payload)

       # Assert
       assert response.status_code == 200
   ```

5. **Mock External Services**
   - 네트워크 요청 Mock
   - 무거운 모델 로드 Mock
   - 파일 I/O Mock (tempfile 사용)

## 참고 자료

- [Pytest 공식 문서](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Celery Testing](https://docs.celeryq.dev/en/stable/userguide/testing.html)
