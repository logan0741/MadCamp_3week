# MemeForty 프로젝트 기술 기록물 (Technical Report)

## 1. 프로젝트 개요

본 문서는 MemeForty 프로젝트의 기술적 구현 상세, 데이터 수집 방식(Action), 그리고 기획되었으나 구현 과정에서 발생한 기술적 이슈들을 기록으로 남기기 위해 작성되었습니다.

---

## 2. 데이터 수집 액션 (Crawling Action Flow)

무신사 상품 데이터를 수집하여 DB에 적재하는 과정은 **"Hybrid Scraping Strategy"**를 통해 이루어집니다.

### 2.1 액션 흐름도 (Sequence)

1. **URL 입력 (`POST /api/v1/products/track`)**
   - 사용자가 무신사 상품 URL 또는 공유 링크(`musinsa.onelink.me`)를 입력.
2. **URL 해석 (Resolve)**
   - 공유 링크인 경우 `scraper.resolve_onelink_url()`이 Playwright headless 브라우저를 띄워 리다이렉트를 추적, 실제 상품 ID(`goodsNo`)가 포함된 URL 획득.
3. **데이터 추출 (Scraping)**
   - **1차 시도 (Fast)**: `httpx`로 HTML 요청 -> `__NEXT_DATA__` 스크립트 파싱 -> JSON 데이터 추출 (가장 빠름).
   - **2차 시도 (Fallback)**: 실패 시 `Playwright` 브라우저 실행 -> 페이지 렌더링 대기 -> DOM 요소 직접 추출.
4. **사이즈 정보 수집 (Size Scraping)**
   - `size_scraper.py`가 9개의 서로 다른 API 엔드포인트에 순차적으로 요청하여 사이즈 제원표(실측 사이즈) 확보.
5. **DB 저장 (Persistence)**
   - 추출된 데이터(가격, 이미지, 브랜드 등)를 `MusinsaProduct` 테이블에 저장.
   - 가격 변동 추적을 위해 `PriceLog` 테이블에 레코드 추가.

---

## 3. 색상 및 스타일 분석 (Color & Style Analysis)

이 프로젝트의 핵심 차별점인 "퍼스널 컬러 기반 추천"을 위해 PCCS(Practical Color Coordinate System) 색체계 도입을 기획했습니다.

### 3.1 기획 내용 (How it was designed)

*   **목표**: 단순 RGB/Hex 코드가 아닌, 감성 배색이 가능한 **PCCS 톤(Cone system)** 으로 의류를 분류.
*   **분류 체계**:
    *   **Hue (색상)**: 1~24 (Red, Orange, Yellow, Green, Blue, Purple 등)
    *   **Tone (톤)**: 12가지 톤 (Vivid, Pale, Grayish, Dark 등)
    *   **Style**: 이미지 벡터 임베딩을 통한 유사 스타일 검색.

### 3.2 DB 설계 (Schema Definition)

`ai-pipeline/database/models.py`에 해당 기획을 반영한 스키마가 설계되어 있습니다.

```python
class MusinsaProduct(Base):
    # ...
    # PCCS color information
    pccs_hue = Column(Float)        # 색상 (0-360 or PCCS index)
    pccs_tone = Column(String(10))  # 톤 코드 (v, dp, lt, g 등)
    primary_color_hex = Column(String(7))
    
    # Vector embedding
    embedding_vector = Column(Text) # 스타일 유사도 검색용
```

### 3.3 구현 현황 및 실패/지연 분석 (Challenges)

현재 코드베이스 분석 결과, **DB 스키마는 준비되었으나 실제 분석 로직은 구현되지 않았거나 통합되지 않은 상태**입니다.

*   **원인 1: 크롤링 안정화 이슈**
    *   무신사의 보안 정책(Bot Detection) 우회가 최우선 과제였기에, AI 분석보다는 데이터 파이프라인(크롤링 -> DB 적재) 안정화에 개발 리소스가 집중됨.
*   **원인 2: 이미지 처리 파이프라인 부재**
    *   이미지 URL은 확보했으나, 이를 다운로드하여 `cv2`나 `K-means` 클러스터링으로 주요 색상을 추출하고, PCCS 좌표로 변환하는 모듈(`color_analysis.py` 등)이 백엔드에 통합되지 않음.
*   **원인 3: 벡터 임베딩 모델 미선정**
    *   스타일 분석을 위한 Feature Extractor(예: ResNet, CLIP) 선정 및 벡터 DB(pgvector) 연동 로직이 아직 작성되지 않음.

---

## 4. 인프라 구축 기록 (Infrastructure)

최종적으로 **"Zero-Touch 배포"**를 목표로 Docker 기반 인프라를 구축했습니다.

### 4.1 구성 요소
*   **Reverse Proxy**: 외부망(VPS)의 Nginx가 HTTPS 처리 후 Autossh 터널을 통해 내부망 Docker 컨테이너로 트래픽 전달.
*   **Frontend**: Next.js (Port 3000)
*   **Backend**: FastAPI (Port 8000)
*   **Process**:
    1. 외부 요청 -> `voice-anime-fight.p-e.kr` (VPS)
    2. SSH Tunnel -> 내부망 localhost
    3. Docker 프록시 -> 각 컨테이너(Frontend/Backend)

이 기록물은 프로젝트의 기술적 자산으로, 향후 PCCS 분석 로직 구현 시 중요한 참고 자료가 될 것입니다.
