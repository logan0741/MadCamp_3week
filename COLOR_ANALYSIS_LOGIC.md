# 🎨 Color Analysis & Recommendation Logic - Deep Dive

이 문서는 옷의 색상을 추출하고, 분석하여, 어울리는 색상을 추천하는 **전체 알고리즘 파이프라인**을 상세하게 기술합니다.

---

## 🏗️ 1. Overall Pipeline (전체 흐름)

1.  **Input**: 사용자 사진 또는 상품 썸네일 이미지.
2.  **Preprocessing**: 배경 제거 (`rembg`) 및 노이즈 제거.
3.  **Extraction**: K-Means Clustering을 이용한 주요 색상(Dominant Colors) 5가지 추출.
4.  **Conversion**: RGB 값을 사람이 지각하는 색상 모델인 HSV/LAB로 변환.
5.  **Classification**: 명도(Value)와 채도(Saturation)를 기준으로 **PCCS 톤(Tone)** 판별.
6.  **Recommendation**: 색상 조화론(Color Harmony)에 따른 매칭 추천.

---

## 🔬 2. Step-by-Step Logic Details

### **Step 1: Background Removal (전처리)**
옷의 색상만 정확히 추출하기 위해 배경을 제거해야 합니다. 배경이 포함되면 평균 색상이 왜곡됩니다.
- **Library**: `rembg` (U-2-Net 기반)
- **Logic**:
  1. 이미지를 `RGBA`로 변환.
  2. AI 모델이 Foreground(옷)와 Background(배경)를 분리하여 마스크 생성.
  3. 배경 픽셀의 투명도(Alpha)를 0으로 설정.
  4. 이후 분석부터는 `Alpha > 0`인 픽셀만 유효 데이터로 간주.

### **Step 2: K-Means Clustering (색상 군집화)**
픽셀 단위의 수만 가지 색상을 인간이 인지할 수 있는 대표 색상 몇 가지로 압축합니다.
- **Algorithm**: K-Means Clustering
- **Process**:
  1. 이미지의 모든 유효 픽셀을 `(R, G, B)` 3차원 공간의 점으로 매핑.
  2. 임의의 중심점(Centroid) **K=5**개를 설정.
  3. 모든 픽셀을 가장 가까운 중심점 그룹에 할당.
  4. 그룹의 평균 위치로 중심점 이동.
  5. 중심점이 더 이상 움직이지 않을 때까지 반복 수렴.
- **Output**: 색상 비율(%)과 대표 RGB 값 (예: `Red 60%`, `Navy 30%`, `White 10%`).

### **Step 3: Color Space Conversion (색공간 변환)**
RGB는 빛의 3원색으로 기계 친화적이지만, 인간의 '느낌(톤)'을 분석하기엔 부적합합니다.
- **RGB → HSV (Hue, Saturation, Value)**:
  - **Hue (색상)**: 0~360도 (빨강, 노랑, 파랑 등 색의 종류).
  - **Saturation (채도)**: 색의 선명함. (0=회색, 100=원색).
  - **Value (명도)**: 색의 밝기. (0=검정, 100=흰색).
- **RGB → LAB (L, a, b)**:
  - 사람 눈의 인지 거리(Perceptual Distance)를 계산하기 위해 사용 (`Delta E` 계산용).

### **Step 4: PCCS Tone Mapping (톤 분류)**
일본 색채 연구소의 PCCS(Practical Color Co-ordinate System)를 기반으로 12가지 톤으로 매핑합니다.

**Mapping Logic (Thresholds):**
| Tone | 명도 (Value) | 채도 (Saturation) | 느낌 |
|:---:|:---:|:---:|:---|
| **Pale** | 고명도 (>80%) | 저채도 (<30%) | 연하고 부드러움 |
| **Vivid** | 중~고명도 | 고채도 (>80%) | 선명하고 활기참 |
| **Deep** | 저명도 (<40%) | 고채도 (>70%) | 깊고 중후함 |
| **Dull** | 중명도 | 중채도 | 차분함 |
| **Grayish** | 중명도 | 저채도 (<15%) | 탁하고 회색기 |

*(실제 알고리즘은 Hue에 따라 각 임계값이 미세하게 조정됩니다.)*

---

## 🎨 3. Recommendation Rules (추천 로직)

추출된 옷의 **(Hue, Tone)** 정보를 바탕으로 가장 잘 어울리는 조합을 수학적으로 계산합니다.

### **Rule A. Tone-on-Tone (톤온톤: 명도 대비)**
> **"같은 색상, 다른 밝기"**
- **Logic**: 기준 색상과 `Hue` 차이가 **15도 이내**이면서, `Value` 차이가 **30 이상**인 색상.
- **Effect**: 키가 커 보이고 세련된 느낌. 실패 확률이 가장 낮음.
- **Example**: 곤색(Dark Blue) 자켓 + 하늘색(Pale Blue) 셔츠.

### **Rule B. Tone-in-Tone (톤인톤: 색상 대비)**
> **"다른 색상, 같은 톤"**
- **Logic**: 기준 색상과 `Hue` 차이가 **60도 이상**이지만, `Tone` 그룹이 **동일**한 색상.
- **Effect**: 다채롭지만 통일감 있는 느낌.
- **Example**: 파스텔 핑크(Pale Red) + 파스텔 민트(Pale Green).

### **Rule C. Complementary (보색 대비)**
> **"정반대 색상" (포인트)**
- **Logic**: 기준 색상과 `Hue` 차이가 **180도(±15도)** 인 색상.
- **Effect**: 화려하고 강렬한 임팩트.
- **Example**: 데님(Blue) + 오렌지 스티치/신발(Orange).

### **Rule D. Achromatic Matching (무채색 매칭)**
> **"검/흰/회색은 만능"**
- 기준 옷이 채도가 높은 Vivid/Strong 톤일 경우, 하의는 무채색(Black, White, Gray)을 최우선 추천하여 시각적 피로도를 낮춤.

---

## 📊 4. Summary for Presentation

**"사용자의 옷 사진 하나로 1600만 가지 색상을 분석하여, 단 하나의 '베스트 핏' 컬러를 제안합니다."**

1.  **정확성**: 배경을 제거하고 K-Means AI로 핵심 색상만 추출.
2.  **과학적 분석**: PCCS 색채학 이론을 코드로 구현하여 감각이 아닌 데이터 기반 분류.
3.  **조화로운 추천**: 디자이너들이 사용하는 배색 공식(톤온톤/톤인톤)을 알고리즘화.
