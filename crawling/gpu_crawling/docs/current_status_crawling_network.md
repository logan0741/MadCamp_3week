# MemeForty 현재 문제/크롤링/서버 작업 요약 (2026-01-26)

## 1) 현재 문제 핵심
- 내부 GPU 서버는 **아웃바운드 443 차단** 상태라 무신사 API(HTTPS)로 직접 나갈 수 없음.
- Nginx SSL Termination은 **외부 → 내부 인바운드**용이고, **내부 → 외부 아웃바운드**와는 무관함.
- 그래서 “서버 내부에서 직접 크롤링”은 터널/프록시 없으면 실패.

## 1-1) 에러가 났던 정확한 이유
- 크롤링 시 `api.musinsa.com` 호출이 **TLS handshake/ConnectTimeout**으로 실패.
- 컨테이너 내부에서 `curl https://api.musinsa.com/...` 요청이 타임아웃됨 → **아웃바운드 443 차단 확인**.
- 결과적으로 **카테고리 리스트(PLP) 호출 실패 → 추천 후보 DB 누적 실패 → 추천 결과 없음** 상태 발생.

## 2) 크롤링/네트워크 관련 작업 완료 내역
- **프록시/터널 지원 코드 추가**
  - `backend/services/musinsa_proxy.py` : 프록시 URL 리라이트 + 헤더 키 주입 + SOCKS/HTTP 프록시 지원
  - 크롤링/이미지/상세/사이즈/카테고리 API 전부 프록시 적용
    - `backend/services/scraper.py`
    - `backend/services/category_crawler.py`
    - `backend/services/color_analyzer.py`
    - `backend/services/size_scraper.py`
- **프록시 Nginx 템플릿**
  - `nginx/musinsa_proxy.conf`
  - API/상품상세/이미지/온링크 전부 프록시 경유
- **터널(양방향) 구성**
  - `docker-compose.tunnel.yml`
    - `socks-tunnel` (SOCKS5 동적 포워딩)
    - `reverse-tunnel` (외부 VPS → 내부 백엔드 역방향)

## 2-1) Nginx로 로컬과 소통하는 구조(현재)
- `docker-compose.yml` 기준:
  - `frontend`(localhost:3000) → 내부 `backend:8000`로 API 요청 (NEXT_PUBLIC_API_URL=http://backend:8000)
  - `backend`는 로컬 DB(`db:5432`)와 통신
  - **외부 HTTPS는 Nginx가 받아서 내부로 넘기는 구조**(인바운드 SSL termination)
- 현재는 **로컬 브라우저 → localhost:3000 → backend:8000 → db**로 정상 연결 확인됨.

## 2-2) 프록시 기반 외부 통신 구조(준비 완료)
- 내부 서버 → (HTTP/SSH) → 프록시/VPS → 무신사 HTTPS(443)
- 프록시 서버 Nginx 설정: `nginx/musinsa_proxy.conf`
- SOCKS5 터널 기반 외부 통신도 지원됨 (`docker-compose.tunnel.yml`)

## 2-3) 크롤링 진행 방식(현재 동작 로직)
1) **상품 상세 크롤링**
   - 입력: 무신사 상품 URL 또는 OneLink 공유 URL
   - 처리: `scraper.py`가 `__NEXT_DATA__`에서 상품 메타 추출
   - 수집: 제목/브랜드/가격/썸네일/이미지/카테고리/스타일번호/성별
   - 저장: `products` 테이블에 저장 (이미 있으면 부족 필드 보강)

2) **스타일/색상 추출**
   - `style_analyzer.py`로 제목에서 스타일 키워드 추출
   - `color_analyzer.py`로 이미지 기반 PCCS 추출
   - 실패 시 제목 기반 색상 키워드로 fallback

3) **카테고리 추천용 후보 시딩**
   - `category_crawler.py`가 무신사 카테고리 API(PLP)에서 상품 리스트를 가져옴
   - 현재는 내부망 아웃바운드 443 제한 때문에 **터널/프록시가 없으면 실패**
   - 테스트에서는 **호스트 선시딩**으로 DB 후보를 채움

4) **추천 생성**
   - `recommendation_service.py`에서 스타일 교집합 + 색상 거리 + 톤 선호 필터링
   - 소스가 무채색일 경우 팔레트 기반 매칭 우선

5) **테스트 실행**
   - `test/run_crawl_test.py`가 회원가입 → 퍼스널컬러 분석 → 상품 추적 → 추천 결과 저장
   - 결과 저장: `test/crawl_personalcolor_recommendation_result.json`

## 3) 서버 상태/테스트 결과
- 크롤링 테스트 스크립트: `test/run_crawl_test.py`
  - 결과 파일: `test/crawl_personalcolor_recommendation_result.json`
  - 요약: `overall_success: true`, `recommendation_total_items: 6`
  - **주의:** 현재는 **호스트 선시딩 방식**으로 성공. (터널 미연결 상태)
- 프런트 로컬: `http://localhost:3000` 응답 OK
- 백엔드 헬스체크: `http://localhost:8000/health` OK
- DB 연결: `musinsa-db` 내부 `select 1` OK

## 4) 터널 기반 “서버 내부 크롤링” 검증 절차
1) 터널 기동
```
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d socks-tunnel reverse-tunnel
```
2) 백엔드 SOCKS 프록시 주입
```
MUSINSA_SOCKS_PROXY=socks5://socks-tunnel:1080
```
3) 백엔드 재빌드/재시작
```
docker compose build backend
docker compose up -d backend
```
4) 서버 내부 크롤링 테스트
```
python3 test/run_crawl_test.py
```

## 5) 남은 요구사항/열린 이슈
- **VPS(또는 외부 HTTPS 가능 서버) 정보 미확인**
  - 터널/프록시는 “외부 443 가능 서버”가 있어야 성립.
- **RAG(ChromaDB) 재정렬 로직 미구현**
  - 프롬프트 기준: 텍스트 0.4 + PCCS 0.6

## 6) 주요 파일 목록
- 크롤링/프록시
  - `backend/services/musinsa_proxy.py`
  - `backend/services/scraper.py`
  - `backend/services/category_crawler.py`
  - `backend/services/color_analyzer.py`
  - `backend/services/size_scraper.py`
  - `nginx/musinsa_proxy.conf`
- 터널
  - `docker-compose.tunnel.yml`
- 테스트
  - `test/run_crawl_test.py`
  - `test/crawl_personalcolor_recommendation_result.json`
