using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;

/// <summary>
/// 의류 피팅을 담당하는 매니저
/// 아바타에 의류 메시를 장착하고 관리합니다.
/// </summary>
public class GarmentManager : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private AvatarController avatarController;
    [SerializeField] private Transform garmentParent;
    
    [Header("Garment Settings")]
    [SerializeField] private Material defaultGarmentMaterial;

    // 현재 장착된 의류들
    private Dictionary<string, GameObject> equippedGarments = new Dictionary<string, GameObject>();
    
    // 의류 카테고리
    public enum GarmentCategory
    {
        Top,        // 상의
        Bottom,     // 하의
        Outer,      // 아우터
        Shoes,      // 신발
        Accessory   // 악세서리
    }

    private void Start()
    {
        // WebGL 브릿지 이벤트 연결
        if (WebGLBridge.Instance != null)
        {
            WebGLBridge.Instance.OnGarmentUrlReceived += LoadGarmentFromUrl;
        }
    }

    /// <summary>
    /// URL에서 의류 로드
    /// </summary>
    public void LoadGarmentFromUrl(string url)
    {
        StartCoroutine(LoadGarmentCoroutine(url));
    }

    private IEnumerator LoadGarmentCoroutine(string url)
    {
        Debug.Log($"[GarmentManager] Loading garment from: {url}");
        
        WebGLBridge.Instance?.NotifyLoadingProgress(0f);

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
                Debug.LogError($"[GarmentManager] Failed to download: {request.error}");
                WebGLBridge.Instance?.NotifyError(request.error);
                yield break;
            }

            // TODO: GLB 파서로 의류 메시 로드
            // 임시로 플레이스홀더 생성
            CreatePlaceholderGarment("top", GarmentCategory.Top);
            
            WebGLBridge.Instance?.NotifyLoadingProgress(1f);
            WebGLBridge.Instance?.NotifyLoadingComplete();
        }
    }

    /// <summary>
    /// 플레이스홀더 의류 생성 (개발용)
    /// </summary>
    private void CreatePlaceholderGarment(string garmentId, GarmentCategory category)
    {
        // 기존 같은 카테고리 의류 제거
        RemoveGarmentByCategory(category);

        GameObject garment = new GameObject($"Garment_{garmentId}");
        garment.transform.SetParent(garmentParent);
        garment.transform.localPosition = Vector3.zero;
        garment.transform.localRotation = Quaternion.identity;

        // 카테고리별 메시 생성
        switch (category)
        {
            case GarmentCategory.Top:
                CreateTopGarment(garment);
                break;
            case GarmentCategory.Bottom:
                CreateBottomGarment(garment);
                break;
            case GarmentCategory.Outer:
                CreateOuterGarment(garment);
                break;
        }

        equippedGarments[garmentId] = garment;
        
        Debug.Log($"[GarmentManager] Equipped garment: {garmentId} ({category})");
    }

    private void CreateTopGarment(GameObject parent)
    {
        // 상의 플레이스홀더 (상자 형태)
        GameObject mesh = GameObject.CreatePrimitive(PrimitiveType.Cube);
        mesh.transform.SetParent(parent.transform);
        mesh.transform.localPosition = new Vector3(0, 1.2f, 0);
        mesh.transform.localScale = new Vector3(0.6f, 0.5f, 0.35f);
        
        // 의류 색상 (무신사 스타일 블랙)
        Material mat = new Material(Shader.Find("Standard"));
        mat.color = new Color(0.1f, 0.1f, 0.1f);
        mesh.GetComponent<Renderer>().material = mat;
        
        // 콜라이더 제거 (렌더링용)
        Destroy(mesh.GetComponent<Collider>());
    }

    private void CreateBottomGarment(GameObject parent)
    {
        // 하의 플레이스홀더
        // 왼쪽 다리
        GameObject leftLeg = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        leftLeg.transform.SetParent(parent.transform);
        leftLeg.transform.localPosition = new Vector3(-0.12f, 0.4f, 0);
        leftLeg.transform.localScale = new Vector3(0.2f, 0.4f, 0.2f);
        
        // 오른쪽 다리
        GameObject rightLeg = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        rightLeg.transform.SetParent(parent.transform);
        rightLeg.transform.localPosition = new Vector3(0.12f, 0.4f, 0);
        rightLeg.transform.localScale = new Vector3(0.2f, 0.4f, 0.2f);
        
        // 데님 블루 색상
        Material mat = new Material(Shader.Find("Standard"));
        mat.color = new Color(0.2f, 0.3f, 0.5f);
        leftLeg.GetComponent<Renderer>().material = mat;
        rightLeg.GetComponent<Renderer>().material = mat;
        
        Destroy(leftLeg.GetComponent<Collider>());
        Destroy(rightLeg.GetComponent<Collider>());
    }

    private void CreateOuterGarment(GameObject parent)
    {
        // 아우터 플레이스홀더 (상의보다 큰 상자)
        GameObject mesh = GameObject.CreatePrimitive(PrimitiveType.Cube);
        mesh.transform.SetParent(parent.transform);
        mesh.transform.localPosition = new Vector3(0, 1.15f, 0);
        mesh.transform.localScale = new Vector3(0.7f, 0.6f, 0.4f);
        
        Material mat = new Material(Shader.Find("Standard"));
        mat.color = new Color(0.3f, 0.25f, 0.2f); // 브라운
        mesh.GetComponent<Renderer>().material = mat;
        
        Destroy(mesh.GetComponent<Collider>());
    }

    /// <summary>
    /// 카테고리별 의류 제거
    /// </summary>
    public void RemoveGarmentByCategory(GarmentCategory category)
    {
        string prefix = $"Garment_";
        List<string> toRemove = new List<string>();
        
        foreach (var pair in equippedGarments)
        {
            // TODO: 카테고리 정보 저장 및 확인
            // 임시로 모든 같은 종류 제거
        }
        
        foreach (string id in toRemove)
        {
            RemoveGarment(id);
        }
    }

    /// <summary>
    /// 특정 의류 제거
    /// </summary>
    public void RemoveGarment(string garmentId)
    {
        if (equippedGarments.TryGetValue(garmentId, out GameObject garment))
        {
            Destroy(garment);
            equippedGarments.Remove(garmentId);
            Debug.Log($"[GarmentManager] Removed garment: {garmentId}");
        }
    }

    /// <summary>
    /// 모든 의류 제거
    /// </summary>
    public void ClearAllGarments()
    {
        foreach (var garment in equippedGarments.Values)
        {
            if (garment != null)
            {
                Destroy(garment);
            }
        }
        equippedGarments.Clear();
        Debug.Log("[GarmentManager] Cleared all garments");
    }

    /// <summary>
    /// 테스트용: 샘플 의류 장착
    /// </summary>
    public void EquipSampleOutfit()
    {
        CreatePlaceholderGarment("sample_top", GarmentCategory.Top);
        CreatePlaceholderGarment("sample_bottom", GarmentCategory.Bottom);
    }

    private void OnDestroy()
    {
        if (WebGLBridge.Instance != null)
        {
            WebGLBridge.Instance.OnGarmentUrlReceived -= LoadGarmentFromUrl;
        }
    }
}
