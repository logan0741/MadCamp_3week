using UnityEngine;
using System.Runtime.InteropServices;

/// <summary>
/// WebGL과 JavaScript 간의 통신을 담당하는 브릿지 클래스
/// Next.js의 react-unity-webgl과 연동됩니다.
/// </summary>
public class WebGLBridge : MonoBehaviour
{
    [DllImport("__Internal")]
    private static extern void SendMessageToJS(string message);

    public static WebGLBridge Instance { get; private set; }
    
    // 이벤트 - JS에서 호출됨
    public System.Action<string> OnAvatarUrlReceived;
    public System.Action<string> OnGarmentUrlReceived;
    public System.Action<float, float, float> OnBodyMeasurementsReceived;

    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }
        else
        {
            Destroy(gameObject);
        }
    }

    /// <summary>
    /// JavaScript에서 호출 - 아바타 URL 수신
    /// react-unity-webgl의 sendMessage로 호출됨
    /// </summary>
    public void LoadAvatar(string avatarUrl)
    {
        Debug.Log($"[WebGLBridge] Received avatar URL: {avatarUrl}");
        OnAvatarUrlReceived?.Invoke(avatarUrl);
    }

    /// <summary>
    /// JavaScript에서 호출 - 의류 피팅 요청
    /// </summary>
    public void FitGarment(string garmentUrl)
    {
        Debug.Log($"[WebGLBridge] Received garment URL: {garmentUrl}");
        OnGarmentUrlReceived?.Invoke(garmentUrl);
    }

    /// <summary>
    /// JavaScript에서 호출 - 신체 치수 설정
    /// JSON 형식: {"height": 175, "weight": 70, "chest": 95}
    /// </summary>
    public void SetBodyMeasurements(string jsonData)
    {
        Debug.Log($"[WebGLBridge] Received body measurements: {jsonData}");
        
        try
        {
            var data = JsonUtility.FromJson<BodyMeasurements>(jsonData);
            OnBodyMeasurementsReceived?.Invoke(data.height, data.weight, data.chest);
        }
        catch (System.Exception e)
        {
            Debug.LogError($"[WebGLBridge] Failed to parse measurements: {e.Message}");
        }
    }

    /// <summary>
    /// Unity에서 JavaScript로 메시지 전송
    /// </summary>
    public void SendToJS(string eventName, string data)
    {
        #if UNITY_WEBGL && !UNITY_EDITOR
        string message = $"{{\"event\":\"{eventName}\",\"data\":{data}}}";
        SendMessageToJS(message);
        #else
        Debug.Log($"[WebGLBridge] Would send to JS: {eventName} - {data}");
        #endif
    }

    /// <summary>
    /// 로딩 진행률 JS에 전송
    /// </summary>
    public void NotifyLoadingProgress(float progress)
    {
        SendToJS("loadingProgress", $"{{\"progress\":{progress}}}");
    }

    /// <summary>
    /// 로딩 완료 알림
    /// </summary>
    public void NotifyLoadingComplete()
    {
        SendToJS("loadingComplete", "{}");
    }

    /// <summary>
    /// 에러 발생 알림
    /// </summary>
    public void NotifyError(string errorMessage)
    {
        SendToJS("error", $"{{\"message\":\"{errorMessage}\"}}");
    }
}

[System.Serializable]
public class BodyMeasurements
{
    public float height;
    public float weight;
    public float chest;
    public float waist;
    public float hip;
}
