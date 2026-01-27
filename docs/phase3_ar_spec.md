# MemeForty Phase 3: AR Integration & Interaction Specification

## System Overview
Unity URP 환경에서 서버 생성 GLB 아바타를 로드하고 실시간 인터랙션 구현.

---

## Client Constraints
- **Platform**: iOS/Android (AR Foundation)
- **Render Pipeline**: URP (Mobile optimized)
- **Asset Loading**: UnityWebRequest / Addressables로 런타임 GLB 로드

---

## 3대 핵심 기술

### 1. High-Fidelity PBR Shader Setup
| Channel | Source | Description |
|---------|--------|-------------|
| Base Map (RGB) | Phase 1 Color Corrected 텍스처 | 의류 색상 |
| Metallic-Smoothness | R: Metallic, A: Smoothness | 재질 반사 |
| Normal Map | Texture Baker 출력 | 주름/재질감 |

**Light Estimation**: AR 카메라 환경광 → 아바타 조명 동기화

### 2. Real-time Motion Sync
| Component | Technology |
|-----------|------------|
| Tracking | MediaPipe / ARKit Body Tracking |
| Skeleton | 33+ 관절 → SMPL-X Humanoid Rig |
| IK | Final IK / Animation Rigging (Foot Grounding) |
| Smoothing | One Euro Filter / Lerp |

### 3. Dynamic Cloth Simulation
| Region | Max Distance | Description |
|--------|--------------|-------------|
| 어깨/가슴/허리 | 0 (Fixed) | 밀착 영역 |
| 밑단/소매/치마 | 0.5~1.2 (Free) | 흔들리는 영역 |

**Optimization**: Self Collision OFF, Capsule Collider로 클리핑 방지

---

## Server API Endpoints (for Unity Client)

### GET `/api/avatar/{user_id}`
GLB 아바타 다운로드

**Response:**
```json
{
  "glb_url": "https://server.com/avatars/{user_id}.glb",
  "textures": {
    "albedo": "/textures/albedo.png",
    "normal": "/textures/normal.png",
    "roughness": "/textures/roughness.png"
  },
  "skeleton": "smplx_22bone",
  "created_at": "2026-01-27T18:00:00Z"
}
```

### POST `/api/generate`
아바타 생성 요청

**Request:**
```json
{
  "person_image": "base64...",
  "garment_front": "base64...",
  "garment_back": "base64...",
  "height_cm": 170,
  "mobile_optimized": true
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "estimated_time": 30
}
```

### GET `/api/status/{job_id}`
생성 상태 확인

---

## Unity Client Checklist
- [ ] GLB Loader (glTFast / UniGLTF)
- [ ] PBR Material Auto-Setup Script
- [ ] Cloth Component Injector
- [ ] MediaPipe Skeleton Mapper
- [ ] AR Light Estimation Sync
- [ ] Mesh Combining & Atlasing
