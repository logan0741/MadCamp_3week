# 🎨 AI Fashion Recommendation Algorithm - Tech Spec

## 1. Core Technology Stack (기술 스택)

### **Computer Vision & AI**
- **YOLOv8** (You Only Look Once):
    - **역할**: 이미지 내에서 패션 아이템(상의, 하의, 아우터 등)을 실시간으로 탐지(Object Detection)하고 영역(Bounding Box)을 추출합니다.
    - **특징**: 빠른 속도와 높은 정확도로 배경을 제외한 '옷' 부분만 정확히 타겟팅합니다.

- **OpenCV & Numpy**:
    - **역할**: 이미지 전처리, 색상 공간 변환(RGB <-> HSV <-> LAB).
    - **활용**: 픽셀 단위의 데이터를 분석하여 이미지의 질감이나 패턴을 분석하는 기초 라이브러리입니다.

- **Scikit-learn (K-Means Clustering)**:
    - **역할**: 옷의 **'지배적인 색상(Dominant Color)'** 추출.
    - **원리**: 추출된 옷 영역의 모든 픽셀을 n개의 군집으로 그룹화하여, 가장 많은 비중을 차지하는 대표 색상을 수학적으로 계산합니다.

---

## 2. Algorithm Principles (동작 원리)

### **A. Style & Item Analysis (스타일 분석)**
1.  **Detection (탐지)**: 사용자가 업로드한 사진이나 크롤링된 이미지에서 YOLOv8 모델이 옷의 위치를 찾습니다.
2.  **Classification (분류)**: 탐지된 객체가 `T-Shirt`, `Jeans`, `Coat` 등 어떤 카테고리인지 식별합니다.
3.  **Attribute Extraction (속성 추출)**: (확장 기능) 기장감(Short/Long), 핏(Oversized/Slim) 등의 세부 속성을 룰 기반 또는 추가 분류기로 판단합니다.

### **B. Color Analysis System (퍼스널 컬러 & 색상 매칭)**
단순히 "빨강"이라고 하는 것이 아니라, **PCCS(Practical Color Co-ordinate System)** 색채계를 기반으로 분석합니다.

1.  **Dominant Color Extraction**: K-Means로 추출된 RGB 색상을 분석합니다.
2.  **Color Conversion (색공간 변환)**: 사람의 눈과 가장 유사한 **HSV(Hue, Saturation, Value)** 및 **LAB** 색공간으로 변환합니다.
3.  **Tone Classification (톤 분류)**:
    - 채도(Saturation)와 명도(Value)를 기준으로 `Vivid`, `Pastel`, `Dark`, `Grayish` 등의 **톤(Tone)**을 결정합니다.
4.  **Harmonic Matching (조화 추천)**:
    - **Tone-on-Tone**: 같은 계열의 색상이지만 톤이 다른 조합 (안정감)
    - **Tone-in-Tone**: 색상은 다르지만 톤이 같은 조합 (부드러운 조화)
    - **Complementary**: 보색 관계 (강렬한 대비)
    - 위 이론을 기반으로, 상의 색상이 주어졌을 때 가장 잘 어울리는 하의 색상/코디를 추천합니다.

### **C. Recommendation Engine (추천 엔진)**
- **User Preference**: 유저가 이전에 조회한 상품의 스타일 태그와 색상 데이터를 벡터화합니다.
- **Content-Based Filtering**: 현재 보고 있는 상품과 유사한 **'시각적 특징(Visual Features)'**을 가진 상품을 DB에서 검색하여 추천 목록을 생성합니다.
