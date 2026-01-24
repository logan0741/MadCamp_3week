using UnityEngine;
using UnityEngine.Networking;
using System.Collections;

/// <summary>
/// 3D 아바타 로드 및 제어를 담당하는 컨트롤러
/// GLB/GLTF 형식의 아바타를 런타임에 로드합니다.
/// </summary>
public class AvatarController : MonoBehaviour
{
    [Header("Avatar Settings")]
    [SerializeField] private Transform avatarParent;
    [SerializeField] private RuntimeAnimatorController defaultAnimator;
    
    [Header("Camera")]
    [SerializeField] private Camera mainCamera;
    [SerializeField] private float rotationSpeed = 100f;
    [SerializeField] private float zoomSpeed = 2f;
    [SerializeField] private float minZoom = 1f;
    [SerializeField] private float maxZoom = 5f;

    private GameObject currentAvatar;
    private Animator avatarAnimator;
    private bool isLoading = false;
    
    // 신체 치수
    private float height = 175f;
    private float weight = 70f;

    private void Start()
    {
        // WebGL 브릿지 이벤트 연결
        if (WebGLBridge.Instance != null)
        {
            WebGLBridge.Instance.OnAvatarUrlReceived += LoadAvatarFromUrl;
            WebGLBridge.Instance.OnBodyMeasurementsReceived += SetBodyMeasurements;
        }
        
        // 기본 아바타가 없으면 플레이스홀더 생성
        if (currentAvatar == null)
        {
            CreatePlaceholderAvatar();
        }
    }

    private void Update()
    {
        HandleCameraControl();
    }

    /// <summary>
    /// 마우스/터치로 카메라 제어
    /// </summary>
    private void HandleCameraControl()
    {
        if (mainCamera == null || currentAvatar == null) return;

        // 마우스 드래그로 회전
        if (Input.GetMouseButton(0))
        {
            float mouseX = Input.GetAxis("Mouse X");
            currentAvatar.transform.Rotate(Vector3.up, -mouseX * rotationSpeed * Time.deltaTime);
        }

        // 스크롤로 줌
        float scroll = Input.GetAxis("Mouse ScrollWheel");
        if (Mathf.Abs(scroll) > 0.01f)
        {
            Vector3 camPos = mainCamera.transform.position;
            float newZ = Mathf.Clamp(camPos.z + scroll * zoomSpeed, -maxZoom, -minZoom);
            mainCamera.transform.position = new Vector3(camPos.x, camPos.y, newZ);
        }
    }

    /// <summary>
    /// URL에서 아바타 로드 (GLB/GLTF 형식)
    /// Ready Player Me 또는 커스텀 아바타 URL
    /// </summary>
    public void LoadAvatarFromUrl(string url)
    {
        if (isLoading)
        {
            Debug.LogWarning("[AvatarController] Already loading an avatar");
            return;
        }

        StartCoroutine(LoadAvatarCoroutine(url));
    }

    private IEnumerator LoadAvatarCoroutine(string url)
    {
        isLoading = true;
        WebGLBridge.Instance?.NotifyLoadingProgress(0f);

        Debug.Log($"[AvatarController] Loading avatar from: {url}");

        // GLB 파일 다운로드
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            request.SendWebRequest();

            while (!request.isDone)
            {
                WebGLBridge.Instance?.NotifyLoadingProgress(request.downloadProgress * 0.5f);
                yield return null;
            }

            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"[AvatarController] Failed to download: {request.error}");
                WebGLBridge.Instance?.NotifyError(request.error);
                isLoading = false;
                yield break;
            }

            // GLB 데이터 파싱 및 로드
            byte[] glbData = request.downloadHandler.data;
            
            WebGLBridge.Instance?.NotifyLoadingProgress(0.7f);

            // TODO: GLTFUtility 또는 glTFast 패키지로 GLB 로드
            // 여기서는 예시로 플레이스홀더 생성
            
            // 기존 아바타 제거
            if (currentAvatar != null)
            {
                Destroy(currentAvatar);
            }

            // 임시: 플레이스홀더 아바타 생성
            // 실제 구현에서는 GLB 파서 사용
            CreatePlaceholderAvatar();
            
            WebGLBridge.Instance?.NotifyLoadingProgress(1f);
            WebGLBridge.Instance?.NotifyLoadingComplete();
        }

        isLoading = false;
    }

    /// <summary>
    /// 플레이스홀더 아바타 생성 (개발용)
    /// </summary>
    private void CreatePlaceholderAvatar()
    {
        // 캡슐 형태의 기본 아바타
        currentAvatar = new GameObject("Avatar");
        currentAvatar.transform.SetParent(avatarParent);
        currentAvatar.transform.localPosition = Vector3.zero;
        currentAvatar.transform.localRotation = Quaternion.identity;

        // 몸통
        GameObject body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        body.transform.SetParent(currentAvatar.transform);
        body.transform.localPosition = new Vector3(0, 1f, 0);
        body.transform.localScale = new Vector3(0.5f, 0.8f, 0.3f);
        body.GetComponent<Renderer>().material.color = new Color(0.8f, 0.7f, 0.6f);

        // 머리
        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        head.transform.SetParent(currentAvatar.transform);
        head.transform.localPosition = new Vector3(0, 2f, 0);
        head.transform.localScale = new Vector3(0.4f, 0.4f, 0.4f);
        head.GetComponent<Renderer>().material.color = new Color(0.8f, 0.7f, 0.6f);

        // 신체 비율 적용
        ApplyBodyProportions();
    }

    /// <summary>
    /// 신체 치수 설정
    /// </summary>
    public void SetBodyMeasurements(float h, float w, float chest)
    {
        height = h;
        weight = w;
        
        Debug.Log($"[AvatarController] Body measurements: H={h}cm, W={w}kg");
        
        ApplyBodyProportions();
    }

    /// <summary>
    /// 신체 비율을 아바타에 적용
    /// </summary>
    private void ApplyBodyProportions()
    {
        if (currentAvatar == null) return;

        // 키에 따른 스케일 조정 (기준: 175cm = 1.0)
        float heightScale = height / 175f;
        
        // 체중에 따른 가로 스케일 (간단한 BMI 기반)
        float bmi = weight / ((height / 100f) * (height / 100f));
        float widthScale = Mathf.Clamp(bmi / 22f, 0.8f, 1.3f);

        currentAvatar.transform.localScale = new Vector3(widthScale, heightScale, widthScale);
    }

    /// <summary>
    /// 아바타 회전 (캐러셀 효과)
    /// </summary>
    public void RotateAvatar(float angle)
    {
        if (currentAvatar != null)
        {
            currentAvatar.transform.Rotate(Vector3.up, angle);
        }
    }

    /// <summary>
    /// 카메라 위치 리셋
    /// </summary>
    public void ResetCamera()
    {
        if (mainCamera != null)
        {
            mainCamera.transform.position = new Vector3(0, 1f, -3f);
            mainCamera.transform.LookAt(avatarParent);
        }
        
        if (currentAvatar != null)
        {
            currentAvatar.transform.rotation = Quaternion.identity;
        }
    }

    private void OnDestroy()
    {
        if (WebGLBridge.Instance != null)
        {
            WebGLBridge.Instance.OnAvatarUrlReceived -= LoadAvatarFromUrl;
            WebGLBridge.Instance.OnBodyMeasurementsReceived -= SetBodyMeasurements;
        }
    }
}
