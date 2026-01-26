# Unity 프로젝트 설정 가이드

## 📦 새 Unity 프로젝트 생성

### 1. Unity Hub에서 프로젝트 생성
```
- Unity 버전: 2022.3 LTS 이상 권장
- 템플릿: 3D (URP) 또는 3D Core
- 프로젝트명: AvatarViewer
```

### 2. 필수 패키지 설치

**Window → Package Manager**에서:

| 패키지 | 용도 |
|--------|------|
| Animation Rigging | IK/FK 리깅 |
| TextMeshPro | UI 텍스트 |
| glTFast | GLB/GLTF 로드 (권장) |

**glTFast 설치** (GLB 파일 로드용):
```
Window → Package Manager → + → Add package from git URL
https://github.com/atteneder/glTFast.git
```

---

## 🎬 씬 구성

### MainScene 계층 구조
```
MainScene
├── --- MANAGERS ---
│   ├── GameManager (WebGLBridge.cs)
│   └── GarmentManager (GarmentManager.cs)
│
├── --- AVATAR ---
│   ├── AvatarRoot (AvatarController.cs)
│   │   └── AvatarModel (로드된 GLB)
│   └── GarmentRoot
│       ├── Top
│       ├── Bottom
│       └── Outer
│
├── --- ENVIRONMENT ---
│   ├── MainCamera
│   ├── Directional Light
│   └── Ground (Plane)
│
└── --- UI ---
    └── Canvas
        └── LoadingPanel
```

---

## ⚙️ 스크립트 설정

### 1. GameManager 오브젝트
```
Create Empty → 이름: GameManager
Add Component → WebGLBridge.cs
```

### 2. AvatarRoot 오브젝트
```
Create Empty → 이름: AvatarRoot
Add Component → AvatarController.cs
- Avatar Parent: 자기 자신
- Default Animator: (선택사항)
- Main Camera: MainCamera 연결
```

### 3. GarmentManager 오브젝트
```
Create Empty → 이름: GarmentManager
Add Component → GarmentManager.cs
- Avatar Controller: AvatarRoot 연결
- Garment Parent: GarmentRoot 연결
```

---

## 🌐 WebGL 빌드 설정

### Player Settings (Edit → Project Settings → Player)

**Resolution and Presentation:**
```
- WebGL Template: Minimal
- Run In Background: ✓
```

**Publishing Settings:**
```
- Compression Format: Gzip
- Name Files As Hashes: ✓
- Data Caching: ✓
- Decompression Fallback: ✓
```

**Other Settings:**
```
- Color Space: Linear (권장)
- Scripting Backend: IL2CPP
- API Compatibility Level: .NET Standard 2.1
```

---

## 📁 빌드 출력

### 빌드 실행
```
File → Build Settings
- Platform: WebGL
- Build → frontend/public/unity/Build 폴더 선택
```

### 생성되는 파일
```
frontend/public/unity/Build/
├── Build.loader.js      # 로더 스크립트
├── Build.data            # 에셋 데이터
├── Build.framework.js    # Unity 런타임
├── Build.wasm            # WebAssembly 바이너리
└── Build.data.gz         # (압축된 경우)
```

---

## 🔗 Next.js 연동

### react-unity-webgl 설정
프론트엔드의 `mypage/page.tsx` 또는 `fitting/page.tsx`에서:

```tsx
const { unityProvider, sendMessage, addEventListener, removeEventListener } = useUnityContext({
    loaderUrl: "/unity/Build/Build.loader.js",
    dataUrl: "/unity/Build/Build.data",
    frameworkUrl: "/unity/Build/Build.framework.js",
    codeUrl: "/unity/Build/Build.wasm",
});

// 아바타 로드
const loadAvatar = (avatarUrl: string) => {
    sendMessage("GameManager", "LoadAvatar", avatarUrl);
};

// 의류 피팅
const fitGarment = (garmentUrl: string) => {
    sendMessage("GameManager", "FitGarment", garmentUrl);
};

// 신체 치수 설정
const setBodyMeasurements = (height: number, weight: number, chest: number) => {
    const data = JSON.stringify({ height, weight, chest });
    sendMessage("GameManager", "SetBodyMeasurements", data);
};
```

---

## 🧪 테스트

### Unity Editor에서 테스트
1. Play 버튼 클릭
2. 플레이스홀더 아바타가 표시되어야 함
3. 마우스 드래그로 회전 테스트

### WebGL 빌드 후 테스트
1. `npm run dev`로 Next.js 실행
2. http://localhost:3000/mypage 접속
3. Unity 뷰어가 로드되는지 확인

---

## ❓ 자주 묻는 질문

### Q: GLB 파일은 어디서 구하나요?
**A:** 
- Ready Player Me (무료 아바타)
- Mixamo (무료 캐릭터 + 애니메이션)
- Sketchfab (유/무료 3D 모델)
- 직접 Blender에서 제작

### Q: 의류 3D 모델은?
**A:** 의류는 2D 이미지에서 3D로 변환하는 AI가 필요하거나, 미리 제작된 템플릿 의류를 사용합니다. 프로젝트에서는 템플릿 + 텍스처 매핑 방식을 권장합니다.

### Q: WebGL 빌드가 너무 크면?
**A:**
- 텍스처 해상도 줄이기
- 사용하지 않는 에셋 제거
- Addressables로 런타임 로드
- 목표: 20MB 이하
