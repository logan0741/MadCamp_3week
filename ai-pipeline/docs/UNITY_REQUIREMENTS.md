# Unity WebGL 개발 요구사항 문서 (v1.0)

## 📋 프로젝트 개요

**목표**: 무신사 가상 피팅 서비스를 위한 Unity WebGL 기반 3D 아바타 뷰어 및 의류 피팅 시스템 구현

**배포 환경**: Next.js 14 App Router (react-unity-webgl 통합)

**예상 작업 기간**: 2주 (프로토타입) + 1주 (최적화)

---

## 🎯 핵심 기능 요구사항

### 1. 3D 아바타 뷰어 (Digital Twin Viewer)

#### 1.1 아바타 로딩 시스템

**입력 데이터 형식**:
- **ECON 모델 출력물**: GLB/GLTF 포맷의 리깅된 메시
  - 위치: `https://ai-server.example.com/avatars/{user_id}/avatar.glb`
  - 포함 요소:
    - SMPL-X 리깅된 인체 메시 (약 10,000 폴리곤)
    - 3DGS 베이킹된 텍스처 (4K 디퓨즈 맵)
    - 본 구조: SMPL-X 표준 (55개 조인트)

**요구사항**:
```csharp
public class AvatarLoader : MonoBehaviour
{
    // 백엔드로부터 아바타 URL을 수신하여 런타임 로드
    public async Task<GameObject> LoadAvatar(string avatarUrl)
    {
        // GLTFUtility 또는 UniGLTF 사용
        // 로드 중 프로그레스 바 표시 (0-100%)
        // 실패 시 기본 T-Pose 모델 fallback
    }

    // 아바타 캐싱: IndexedDB 또는 브라우저 캐시 활용
    public void CacheAvatar(string userId, byte[] gltfData);
}
```

#### 1.2 기본 애니메이션

**필수 애니메이션**:
| 상태 | 설명 | 우선순위 |
|------|------|---------|
| Idle | 대기 상태 (호흡 애니메이션) | P0 |
| T-Pose | 의류 피팅 전 기본 자세 | P0 |
| Rotate | 360도 천천히 회전 (자동 재생) | P1 |
| Walk | 걷기 모션 (옵션) | P2 |

**구현 예시**:
```csharp
public class AvatarAnimationController : MonoBehaviour
{
    private Animator animator;

    public void SetIdleAnimation()
    {
        // Subtle breathing animation (0.5 sec cycle)
        // Procedural or pre-baked blend shapes
    }

    public void Auto360Rotate(float duration = 8f)
    {
        // 카메라 또는 모델 자체를 Y축 기준 회전
        StartCoroutine(RotateCoroutine(duration));
    }
}
```

---

### 2. 의류 피팅 시스템 (Virtual Try-On)

#### 2.1 의류 메시 로딩

**입력 데이터 형식**:
- **BCNet 모델 출력물**: OBJ 또는 FBX 포맷
  - 위치: `https://ai-server.example.com/garments/{product_id}/garment.obj`
  - 포함 요소:
    - 독립적 의류 메시 (상의 기준 약 5,000 폴리곤)
    - UV 맵핑된 텍스처 (무신사 썸네일 기반 2K 텍스처)
    - 버텍스 그룹: `collar`, `sleeve_left`, `sleeve_right`, `torso`, `hem`

**요구사항**:
```csharp
public class GarmentLoader : MonoBehaviour
{
    // 의류 메시 런타임 로드
    public async Task<GameObject> LoadGarment(string garmentUrl)
    {
        // OBJLoader 또는 RuntimeOBJImporter 사용
        // 텍스처 자동 매핑
    }

    // SMPL-X 아바타에 자동 피팅
    public void FitGarmentToAvatar(GameObject avatar, GameObject garment)
    {
        // 1. 아바타의 어깨 너비 감지
        // 2. 의류 메시를 아바타 체형에 맞게 스케일 조정
        // 3. 충돌 감지 및 오프셋 적용 (아래 2.2 참고)
    }
}
```

#### 2.2 충돌 방지 (Clipping Prevention)

**핵심 문제**: 아바타가 움직일 때 피부가 옷을 뚫고 나오는 현상 방지

**해결 방안**:
```csharp
public class ClippingPrevention : MonoBehaviour
{
    public float skinOffset = 0.005f; // 5mm 오프셋

    void Update()
    {
        // 매 프레임마다 의류 버텍스와 아바타 스킨 메시 간 거리 체크
        foreach (var vertex in garmentVertices)
        {
            Vector3 closestPoint = avatar.GetClosestPointOnSkin(vertex);
            float distance = Vector3.Distance(vertex, closestPoint);

            if (distance < skinOffset)
            {
                // 법선 방향으로 버텍스를 밀어냄
                vertex += normal * (skinOffset - distance);
            }
        }
    }
}
```

**최적화**:
- 모든 버텍스를 매 프레임 체크하지 말고, **충돌 위험 구역**(관절 주변)만 선택적으로 체크
- Compute Shader 활용하여 GPU에서 병렬 연산

#### 2.3 물리 시뮬레이션 (Cloth Physics)

**요구사항**:
- 옷이 자연스럽게 흔들리는 효과 (Unity Cloth 컴포넌트 활용)
- **주의**: WebGL 환경에서 Cloth 컴포넌트는 성능 이슈가 있으므로 **단순화된 버텍스 애니메이션**으로 대체 권장

**대안 구현**:
```csharp
public class SimpleClothWave : MonoBehaviour
{
    public float waveSpeed = 2f;
    public float waveHeight = 0.01f;

    void Update()
    {
        // 옷자락(Hem) 버텍스에만 사인파 적용
        foreach (var hemVertex in hemVertices)
        {
            hemVertex.y += Mathf.Sin(Time.time * waveSpeed) * waveHeight;
        }
    }
}
```

---

### 3. 카메라 컨트롤 (Camera Control)

#### 3.1 마우스/터치 인터랙션

**필수 기능**:
| 입력 | 동작 | 제한 |
|------|------|------|
| 마우스 드래그 | 아바타 주위를 궤도 회전 (Orbit) | Y축 회전: 360도, X축 회전: -30° ~ 30° |
| 스크롤/핀치 | 줌 인/아웃 | 최소 1.5m, 최대 4m |
| 더블 클릭 | 카메라 초기 위치로 리셋 | - |

**구현 예시**:
```csharp
public class OrbitCamera : MonoBehaviour
{
    public Transform target; // 아바타
    public float distance = 2.5f;
    public float xSpeed = 120f;
    public float ySpeed = 120f;

    private float x = 0f;
    private float y = 0f;

    void LateUpdate()
    {
        if (Input.GetMouseButton(0))
        {
            x += Input.GetAxis("Mouse X") * xSpeed * 0.02f;
            y -= Input.GetAxis("Mouse Y") * ySpeed * 0.02f;
            y = Mathf.Clamp(y, -30f, 30f);
        }

        Quaternion rotation = Quaternion.Euler(y, x, 0);
        Vector3 position = rotation * new Vector3(0, 0, -distance) + target.position;

        transform.rotation = rotation;
        transform.position = position;
    }
}
```

#### 3.2 자동 프레이밍 (Auto-Framing)

**요구사항**: 아바타가 로드될 때 자동으로 화면 중앙에 전신이 보이도록 카메라 위치 조정

```csharp
public void AutoFrameAvatar(GameObject avatar)
{
    Bounds bounds = GetAvatarBounds(avatar);
    float cameraDistance = Mathf.Max(bounds.size.y, bounds.size.x) * 1.5f;

    camera.transform.position = bounds.center + Vector3.back * cameraDistance;
    camera.transform.LookAt(bounds.center);
}
```

---

### 4. React ↔ Unity 통신 (JavaScript Bridge)

#### 4.1 react-unity-webgl 사용

**프론트엔드 측 (Next.js)**:
```typescript
// components/UnityAvatarViewer.tsx
import { Unity, useUnityContext } from "react-unity-webgl";

export default function UnityAvatarViewer({ userId }: { userId: string }) {
  const { unityProvider, sendMessage, addEventListener } = useUnityContext({
    loaderUrl: "/unity/build.loader.js",
    dataUrl: "/unity/build.data",
    frameworkUrl: "/unity/build.framework.js",
    codeUrl: "/unity/build.wasm",
  });

  // Unity에 아바타 URL 전송
  useEffect(() => {
    sendMessage("AvatarManager", "LoadAvatarFromURL",
      `https://ai-server.example.com/avatars/${userId}/avatar.glb`
    );
  }, [userId]);

  // Unity로부터 로딩 진행률 수신
  useEffect(() => {
    addEventListener("LoadingProgress", (progress: number) => {
      console.log(`Avatar loading: ${progress}%`);
    });
  }, [addEventListener]);

  return <Unity unityProvider={unityProvider} style={{ width: "100%", height: "600px" }} />;
}
```

**Unity 측 (C# Script)**:
```csharp
using UnityEngine;

public class AvatarManager : MonoBehaviour
{
    // JavaScript에서 호출 가능한 메서드
    public void LoadAvatarFromURL(string url)
    {
        StartCoroutine(LoadAvatarCoroutine(url));
    }

    private IEnumerator LoadAvatarCoroutine(string url)
    {
        for (int i = 0; i <= 100; i += 10)
        {
            // React로 진행률 전송
            SendMessageToReact("LoadingProgress", i);
            yield return new WaitForSeconds(0.1f);
        }

        // 실제 로드 로직...
    }

    private void SendMessageToReact(string eventName, object data)
    {
        #if UNITY_WEBGL && !UNITY_EDITOR
        Application.ExternalCall(eventName, data);
        #endif
    }
}
```

#### 4.2 통신 프로토콜

**Unity → React 이벤트**:
| 이벤트명 | 파라미터 | 설명 |
|---------|---------|------|
| `LoadingProgress` | `number` (0-100) | 아바타 로딩 진행률 |
| `AvatarLoaded` | `{ userId: string, success: boolean }` | 로딩 완료 |
| `GarmentFitted` | `{ productId: string }` | 의류 피팅 완료 |
| `Error` | `{ code: string, message: string }` | 에러 발생 |

**React → Unity 메서드**:
| 메서드명 | 파라미터 | 설명 |
|---------|---------|------|
| `LoadAvatarFromURL` | `string` (URL) | 아바타 로드 |
| `FitGarment` | `string` (productId) | 의류 피팅 시작 |
| `SetAnimation` | `string` (animationName) | 애니메이션 변경 |
| `ResetCamera` | - | 카메라 초기화 |

---

## 🚀 성능 최적화 요구사항

### 5.1 폴리곤 최적화

**목표 폴리곤 수**:
| 에셋 | 목표 | 최대 |
|------|------|------|
| 아바타 메시 | 10,000 tris | 15,000 tris |
| 의류 메시 (상의) | 5,000 tris | 8,000 tris |
| 의류 메시 (하의) | 4,000 tris | 6,000 tris |

**최적화 기법**:
- LOD (Level of Detail) 시스템: 카메라 거리에 따라 메시 해상도 자동 조정
- Mesh Simplification: Blender 또는 Unity ProBuilder로 사전 최적화

### 5.2 텍스처 압축

**권장 포맷**:
- **WebGL**: ETC2 (안드로이드) / PVRTC (iOS) 대신 **DXT 압축** 사용
- **해상도**: 4K → 2K로 다운스케일 (화면 크기 고려 시 차이 미미)

**구현**:
```csharp
public class TextureOptimizer : MonoBehaviour
{
    void Start()
    {
        var renderer = GetComponent<Renderer>();
        var texture = renderer.material.mainTexture;

        // 런타임 압축 (WebGL 환경)
        if (texture.width > 2048)
        {
            texture.Compress(true); // 손실 압축
        }
    }
}
```

### 5.3 드로우 콜 최적화

**목표**: 전체 씬 드로우 콜 30개 이하

**기법**:
- **Static Batching**: 아바타와 의류를 하나의 메시로 결합
- **Material Sharing**: 동일한 셰이더를 사용하는 오브젝트는 Material Instance 공유

```csharp
public class BatchingManager : MonoBehaviour
{
    public void CombineAvatarAndGarment(GameObject avatar, GameObject garment)
    {
        MeshFilter[] meshFilters = new MeshFilter[] {
            avatar.GetComponent<MeshFilter>(),
            garment.GetComponent<MeshFilter>()
        };

        CombineInstance[] combine = new CombineInstance[meshFilters.Length];
        for (int i = 0; i < meshFilters.Length; i++)
        {
            combine[i].mesh = meshFilters[i].sharedMesh;
            combine[i].transform = meshFilters[i].transform.localToWorldMatrix;
        }

        Mesh combinedMesh = new Mesh();
        combinedMesh.CombineMeshes(combine);

        GetComponent<MeshFilter>().sharedMesh = combinedMesh;
    }
}
```

### 5.4 WebGL 빌드 최적화

**Unity 빌드 설정**:
- **Compression Format**: Brotli (Gzip보다 20% 더 압축)
- **Code Stripping**: Medium 이상 (사용하지 않는 코드 제거)
- **IL2CPP**: 활성화 (Mono보다 30% 빠름)
- **Exceptions**: None (예외 처리 비활성화로 크기 감소)

**예상 빌드 크기**:
- 초기 다운로드: 약 15MB (Brotli 압축 시)
- 로드 시간: 4G 기준 약 3-5초

---

## 📦 필수 Unity 패키지

| 패키지 | 버전 | 용도 |
|--------|------|------|
| **GLTFUtility** | 5.0.0+ | GLTF/GLB 런타임 로드 |
| **RuntimeOBJImporter** | 1.1.0+ | OBJ 런타임 로드 |
| **TextMesh Pro** | 3.0.6 | UI 텍스트 렌더링 |
| **Cinemachine** | 2.8.9 | 카메라 컨트롤 (옵션) |

**설치 방법**:
```bash
# Package Manager에서 Git URL로 추가
https://github.com/Siccity/GLTFUtility.git
https://github.com/hammmm/unity-obj-loader.git
```

---

## 🧪 테스트 체크리스트

### 기능 테스트
- [ ] 아바타 GLB 파일을 URL로 로드하여 씬에 정상 표시
- [ ] T-Pose 상태에서 의류 OBJ 파일 로드 후 자동 피팅
- [ ] 아바타가 Idle 애니메이션 재생 중 옷이 뚫고 나오지 않음 (Clipping 0건)
- [ ] 마우스 드래그로 360도 회전, 스크롤로 줌 인/아웃 정상 작동
- [ ] React에서 `LoadAvatarFromURL` 호출 시 Unity가 정상 응답

### 성능 테스트
- [ ] FPS: Chrome 브라우저에서 60fps 유지 (최소 30fps)
- [ ] 드로우 콜: 30개 이하
- [ ] 메모리 사용량: 200MB 이하 (Chrome DevTools 확인)
- [ ] 초기 로딩 시간: 10초 이하 (WiFi 환경)

### 호환성 테스트
- [ ] Chrome 최신 버전 (데스크톱)
- [ ] Safari 16+ (macOS/iOS)
- [ ] Firefox 최신 버전
- [ ] Android Chrome (Galaxy S21 기준)

---

## 📞 백엔드 API 인터페이스

Unity가 호출해야 하는 백엔드 엔드포인트 (추후 FastAPI에서 제공 예정):

```http
### 아바타 메타데이터 조회
GET https://ai-server.example.com/api/avatars/{userId}
Response:
{
  "userId": "abc123",
  "avatarUrl": "https://cdn.example.com/avatars/abc123.glb",
  "status": "completed",
  "createdAt": "2026-01-24T00:00:00Z"
}

### 의류 메타데이터 조회
GET https://ai-server.example.com/api/garments/{productId}
Response:
{
  "productId": "musinsa_12345",
  "garmentUrl": "https://cdn.example.com/garments/12345.obj",
  "textureUrl": "https://cdn.example.com/garments/12345_diffuse.png",
  "category": "top",
  "isModelingComplete": true
}
```

---

## 🛠️ 개발 워크플로우

### Phase 1: 프로토타입 (1주차)
1. Unity 프로젝트 생성 (Unity 2022.3 LTS)
2. 테스트용 GLTF 아바타 파일 준비 (ReadyPlayerMe 샘플 사용 가능)
3. OrbitCamera + 기본 로더 구현
4. React와의 통신 테스트 (sendMessage/addEventListener)

### Phase 2: 의류 피팅 (2주차)
1. OBJ 로더 통합
2. 충돌 방지 로직 구현 및 테스트
3. 실제 BCNet 출력물로 테스트 (AI 팀과 협업)

### Phase 3: 최적화 (3주차)
1. LOD 시스템 구현
2. WebGL 빌드 최적화
3. 성능 프로파일링 및 병목 제거

---

## ⚠️ 주의사항 및 제약사항

1. **Unity 버전**: 2022.3 LTS 이상 필수 (WebGL 안정성)
2. **CORS 정책**: 아바타/의류 URL은 CORS 헤더 필수 (`Access-Control-Allow-Origin: *`)
3. **파일 크기**: GLB 파일은 개당 5MB 이하 권장 (로딩 시간 고려)
4. **브라우저 제약**: Safari는 WebGL 2.0 지원이 제한적 → Fallback 필요
5. **SMPL-X 라이선스**: 상업적 사용 시 라이선스 확인 필요

---

## 📚 참고 자료

- [Unity WebGL Best Practices](https://docs.unity3d.com/Manual/webgl-building.html)
- [GLTFUtility Documentation](https://github.com/Siccity/GLTFUtility)
- [react-unity-webgl Examples](https://react-unity-webgl.dev/)
- [SMPL-X Official Repo](https://github.com/vchoutas/smplx)

---

## 🤝 협업 채널

- **Slack**: `#unity-dev` 채널
- **파일 공유**: Google Drive `Unity Assets` 폴더
- **주간 리뷰**: 매주 금요일 15:00 (Google Meet)

---

**문서 버전**: 1.0
**최종 수정**: 2026-01-24
**작성자**: AI Pipeline Team
**검토자**: Unity Developer (TBD)
