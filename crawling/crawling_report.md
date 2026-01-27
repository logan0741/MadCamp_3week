# 무신사 크롤링 이슈 및 해결 방안 보고서

## 1. 개요
본 프로젝트에서는 무신사 상품 정보(가격, 이미지, 사이즈 등)를 수집하기 위해 **Hybrid Scraping Strategy**를 사용하고 있습니다. 개발 과정에서 직면했던 주요 이슈들과 이를 해결하기 위해 적용된 기술적 전략을 정리합니다.

## 2. 주요 발생 이슈

### 🚨 Bot 탐지 및 차단 (Cloudflare / WAF)
- **증상**: 단순 `requests`나 `httpx` 요청 시 403 Forbidden 또는 캡차 페이지 반환.
- **원인**: 무신사의 보안 솔루션이 비정상적인 트래픽(헤더 미비, TLS 핑거프린트 등)을 감지.
- **해결책**:
  1. **User-Agent Rotation**: 최신 브라우저의 User-Agent를 사용하여 일반 사용로 위장.
  2. **Playwright 폴백**: `httpx` 요청 실패 시, 실제 브라우저 엔진(Chromium)을 사용하는 `Playwright`로 전환하여 탐지 우회.
  3. **Stealth Mode**: `playwright-stealth` 플러그인과 유사한 기술(navigator.webdriver 숨기기 등) 적용.

### 🧩 동적 데이터 로딩 (SSR + CSR)
- **증상**: 초기 HTML에는 상품 정보(특히 가격, 옵션별 재고)가 비어있고, JavaScript 실행 후 렌더링됨.
- **원인**: Next.js 기반의 웹사이트 구조로, 데이터가 Client-Side Rendering(CSR)으로 로드되거나 Hydration 과정을 거침.
- **해결책**:
  - **__NEXT_DATA__ 추출**: 무신사 페이지 소스 내에 포함된 `<script id="__NEXT_DATA__">` 태그를 파싱하여, 렌더링에 사용되는 원본 JSON 데이터를 직접 추출. 이는 DOM 파싱보다 훨씬 안정적이고 빠릅니다.

### 📏 사이즈 정보 추출 난이도
- **증상**: 사이즈표가 이미지로 되어 있거나, 별도의 팝업/API로 로드되어 HTML에서 찾을 수 없음.
- **해결책**:
  - **Multi-Source Strategy**: `size_scraper.py`에서 9개 이상의 서로 다른 API 엔드포인트(`goods-detail`, `api.musinsa` 등)를 순차적으로 시도하여 사이즈 정보를 탐색.
  - **Network Interception**: Playwright 사용 시 발생하는 모든 네트워크 요청(XHR/Fetch)을 가로채서, 사이즈 정보가 담긴 JSON 응답을 캡처.

### 🔗 URL 구조의 다양성
- **증상**: 모바일 앱 공유 링크(`musinsa.onelink.me`), 단축 URL, PC/모바일 버전 URL 등 형식이 제각각임.
- **해결책**:
  - **URL Resolver 구현**: `resolve_onelink_url` 함수를 통해 리다이렉트를 따라가 실제 상품 ID(`goodsNo`)가 포함된 최종 URL을 획득.

## 3. 현재 구현된 아키텍처 (Hybrid)

```mermaid
graph TD
    A[요청 URL] --> B{URL 타입 확인}
    B -- OneLink --> C[Playwright로 리다이렉트 추적]
    B -- 일반 URL --> D[HTTPX 요청 (Fast)]
    
    C --> D
    D --> E{성공?}
    E -- Yes --> F[__NEXT_DATA__ JSON 파싱]
    E -- No --> G[Playwright 브라우저 실행 (Slow & Reliable)]
    
    G --> H[DOM 로딩 대기]
    H --> I{__NEXT_DATA__ 존재?}
    I -- Yes --> F
    I -- No --> J[DOM 요소 직접 스크래핑 (Fallback)]
    
    F --> K[상품 정보 정규화]
    J --> K
    K --> L[DB 저장]
```

## 4. 향후 유지보수 포인트
1. **API 엔드포인트 변경**: 무신사 앱 업데이트로 API 주소가 바뀔 경우 `size_scraper.py`의 후보 URL 목록 업데이트 필요.
2. **DOM 구조 변경**: `__NEXT_DATA__` 방식이 막힐 경우 DOM 파싱에 의존해야 하므로, 주기적인 CSS Selector 점검 필요.
3. **법적/윤리적 고려**: `robots.txt` 준수 및 과도한 요청 방지(Rate Limiting) 로직 유지 필요.
