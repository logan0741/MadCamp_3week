# Crawling & Recommendation Playbook

이 폴더는 현재 서버에서 돌아가는 MemeForty/MadCamp_3week 프로젝트의 **크롤링**과 **AI 기반 스타일/색상 추천** 흐름을 통합 정리하고, 관련 설정·프롬프트·참고 문서를 한 곳에 모아 놓은 참조용 자료입니다.

## 핵심 요약
1. **전체 아키텍처**
   - `backend/`: FastAPI + Scheduler + Musinsa 크롤러/추천 로직(`/services/musinsa_proxy.py`, `services/scheduler.py`)
   - `frontend/`: Next.js UI (로그인/온보딩/추천/스타일 페이지) → `/api` 요청을 Nginx가 `dashboard-backend`로 프록시
   - `nginx/`: SSL 종료와 리버스 프록시 (HTTP→HTTPS 리디렉션, `/api/`, `/admin/` 프록시)
   - `ai-pipeline/`(추가 구성 예정): Celery + FastAPI VTON + static-serving Nginx + autossh tunnels
2. **크롤링 흐름**
   - `test_scraper.py`/`services/scraper.py`가 Musinsa 상품 페이지를 Playwright 없이(`httpx`) 크롤링하며, `ProductService`에서 DB 저장 및 price log 관리
   - 크롤링 결과(`title`, `brand`, `price`, `images`)는 `/uploads`와 `musinsa_tracker` DB에 저장되고, Frontend는 `/api/v1/products`→ `/components` → UI card로 노출
3. **추천/색상 분석 원리**
   - `COLOR_ANALYSIS_LOGIC.md` · `COLOR_ANALYSIS_PRINCIPLES.md` · `RECOMMENDATION_ALGO.md` 문서에서 PCCS 기반 톤 분석, K-Means Dominant Color 추출, Tone-on-Tone/Tone-in-Tone/Complementary 룰을 다룸
   - 요약: 배경 제거 → K-Means 나눔(K=5) → RGB→HSV/LAB 변환 → Tone 매핑 → Tone/Complementary 조화 규칙 적용 → 추천 candidate 출력
   - AI/CV 스택: YOLOv8 (옷 detection) + OpenCV/Numpy + Scikit-learn clustering + vectorized user preference filtering
4. **AI 파이프라인 참고**
   - `AI_PROMPT.md`에 VTON API(동기/비동기) + Celery tasks + 테스트 명령(`pytest`, `curl http://localhost:8001/health`) 정리
   - 환경 변수: `REDIS_URL`, `API_HOST`, `MODEL_CACHE_DIR`, `OUTPUT_DIR` 등
5. **배포/검증 체크리스트**
   - `docker compose up --build -d nginx dashboard-backend dashboard-frontend dashboard-db` (현재 `homecheck` 프로젝트 이름으로 실행)
   - `docker exec dashboard-backend curl http://localhost:8000/health` → `{"status":"healthy"}` 확인
   - `docker exec dashboard-backend python test_scraper.py`로 Musinsa 상품 크롤러/추천 로직 검증
   - Nginx 내부에서 `curl -I http://dashboard-frontend:3000` 및 `curl -I http://dashboard-backend:8000/health`로 서비스 연동 확인
   - 결과/로그는 `development_progress.md`에 타임스탬프와 함께 기록하여 진행 상황 공유

## 참고 문서
- `AI_PROMPT.md`: VTON AI 파이프라인 정리, Celery/테스트/환경 변수 가이드
- `RECOMMENDATION_ALGO.md`: YOLOv8 + OpenCV + K-Means → PCCS 기반 톤 추천 알고리즘 설명
- `COLOR_ANALYSIS_LOGIC.md`, `COLOR_ANALYSIS_PRINCIPLES.md`: 배경 제거 → dominant color → PCCS 분류 → Tone 온톈톤/톤인톤/보색 조합 철학
- `development_progress.md`: 작업 로그 및 다음 액션 아이템 기록
- `docker-compose.yml`: `dashboard-*` 서비스, Postgres, Nginx, 그리고 향후 `ai-pipeline`/`autossh` 터널(별도 compose) 설정

## Prompt for Ngrok/Tunnel-assisted Exposure
자세한 자동화/검증 프롬프트는 `prompt.txt`를 참고해 주세요. 로컬 AI 엔진이 SSH → ngrok 터널(포트 22) → nginx(80/443) 흐름으로 웹앱을 외부에 노출하면서 크롤링/추천 검증을 반복할 수 있도록 구성되어 있습니다.
