# 🛠️ Fashion Data & Recommendation System - Tech Spec

## 1. Technology Stack (기술 스택)

### **Core Backend** (Server)
- **Language**: Python 3.11+
- **Framework**: **FastAPI** (High-perf Async API Framework)
- **ASGI Server**: Uvicorn
- **Architecture**: Clean Architecture (Layered: API -> Service -> Domain -> Core)

### **Crawling & Data Acquisition** (Core Engine)
- **Playwright**:
    - Headless Browser (Chromium) automation.
    - Used for rendering Dynamic SPAs (Single Page Applications, Next.js).
    - Handling redirects for "Short Links" (OneLink).
- **HTTPX**:
    - Asynchronous HTTP Client.
    - Used for high-speed scraping when full browser rendering isn't required.
- **APScheduler**:
    - Background job scheduler.
    - Runs periodic tasks (Daily price checks, Stock updates).

### **Data & Storage**
- **SQLAlchemy (ORM)**: Database abstraction.
- **SQLite/PostgreSQL**: Relational database storage.
- **Pydantic**: Data validation and serialization.

---

## 2. System Principles & Logic (동작 원리)

### **A. Hybrid Scraping Engine (하이브리드 크롤링)**
> **"Speed + Reliability"**
시스템은 **이중 크롤링 전략**을 사용하여 속도와 정확도를 동시에 확보합니다.

1.  **Phase 1 (Fast)**: `HTTPX`를 사용하여 가볍게 페이지 소스를 요청합니다.
2.  **Phase 2 (Deep)**: 만약 정적 요청이 실패하거나 동적 데이터(옵션, 재고)가 필요하면 `Playwright` 브라우저를 띄워 실제 사용자와 동일하게 페이지를 렌더링합니다.
3.  **Data Extraction**: 단순 HTML 파싱이 아닌, Next.js 프레임워크의 **Hydration Data (`__NEXT_DATA__`)** JSON 객체를 직접 추출하여, 화면에 보이지 않는 메타데이터(정확한 사이즈표, 품번, 숨겨진 재고)까지 확보합니다.

### **B. Smart Link Resolution (스마트 링크 리졸버)**
> **"Any Link Works"**
사용자가 앱에서 공유한 `OneLink` (단축/마케팅 URL)를 처리하는 로직입니다.

- 공유된 링크가 `musinsa.onelink.me` 형식이면, 크롤러가 브라우저 컨텍스트에서 해당 링크를 실제로 방문하여 최종 `Redirect`된 실제 상품 페이지의 URL과 상품 ID(GoodsNo)를 역추적합니다.

### **C. Size Normalization (사이즈 정규화)**
> **"Unifying Standards"**
쇼핑몰마다 제각각인 사이즈 표기를 표준화합니다.

- **Heuristic Matching**: `총장`, `기장`, `Total Length` 등 다양한 키워드를 `length`라는 표준 키로 매핑합니다.
- **Data Parsing**: HTML 테이블이나 JSON 구조에서 사이즈 정보를 탐색하여 `Build -> Chest -> Length` 등의 2차원 매트릭스 데이터를 구조화된 객체로 변환합니다.

### **D. Scheduler Architecture (스케줄러 아키텍처)**
- 서버 시작 시 `lifespan` 이벤트를 통해 백그라운드 스케줄러가 데몬으로 실행됩니다.
- **Cron Job**: 매일 오전 6시(또는 설정된 주기)에 등록된 모든 상품의 URL을 재방문하여 가격 변동을 감지하고 `PriceLog` 테이블에 스냅샷을 저장하여 가격 추이를 추적합니다.
