# Unity WebGL Avatar Viewer

이 폴더에 Unity WebGL 빌드 파일을 배치해주세요.

## 필요한 파일

Unity에서 WebGL 빌드 후 다음 파일들을 이 폴더에 복사하세요:

- `avatar_viewer.loader.js`
- `avatar_viewer.data`
- `avatar_viewer.framework.js`
- `avatar_viewer.wasm`

## Unity 빌드 설정

1. Unity에서 Build Settings 열기
2. Platform을 WebGL로 변경
3. Player Settings에서:
   - Compression Format: Disabled (개발용) 또는 Gzip
   - Memory Size: 256MB 이상 권장
4. Build 실행

## 아바타 뷰어 요구사항

- SMPL-X 기반 아바타 메시 로드
- Idle 애니메이션 재생
- 마우스 드래그로 회전
