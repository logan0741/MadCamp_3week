'use client';

import { useEffect, useCallback } from 'react';
import { useUnityContext, Unity } from 'react-unity-webgl';

interface UnityAvatarViewerProps {
    avatarUrl?: string;
    garmentUrl?: string;
    height?: number;
    weight?: number;
    onLoadingProgress?: (progress: number) => void;
    onLoadingComplete?: () => void;
    onError?: (error: string) => void;
    className?: string;
}

/**
 * Unity 아바타 뷰어 컴포넌트
 * WebGL 빌드와 연동하여 3D 아바타를 표시합니다.
 */
export default function UnityAvatarViewer({
    avatarUrl,
    garmentUrl,
    height = 175,
    weight = 70,
    onLoadingProgress,
    onLoadingComplete,
    onError,
    className = ''
}: UnityAvatarViewerProps) {

    const {
        unityProvider,
        loadingProgression,
        isLoaded,
        sendMessage,
        addEventListener,
        removeEventListener
    } = useUnityContext({
        loaderUrl: "/unity/Build/Build.loader.js",
        dataUrl: "/unity/Build/Build.data",
        frameworkUrl: "/unity/Build/Build.framework.js",
        codeUrl: "/unity/Build/Build.wasm",
    });

    // Unity → JS 메시지 수신
    useEffect(() => {
        const handleUnityMessage = (event: CustomEvent) => {
            const { event: eventName, data } = event.detail;

            switch (eventName) {
                case 'loadingProgress':
                    onLoadingProgress?.(data.progress * 100);
                    break;
                case 'loadingComplete':
                    onLoadingComplete?.();
                    break;
                case 'error':
                    onError?.(data.message);
                    break;
            }
        };

        window.addEventListener('unityMessage', handleUnityMessage as EventListener);
        return () => {
            window.removeEventListener('unityMessage', handleUnityMessage as EventListener);
        };
    }, [onLoadingProgress, onLoadingComplete, onError]);

    // Unity 로딩 진행률 전달
    useEffect(() => {
        onLoadingProgress?.(loadingProgression * 100);
    }, [loadingProgression, onLoadingProgress]);

    // Unity 로딩 완료 시
    useEffect(() => {
        if (isLoaded) {
            // 신체 치수 설정
            const measurements = JSON.stringify({ height, weight, chest: 90 });
            sendMessage("GameManager", "SetBodyMeasurements", measurements);

            // 아바타 URL이 있으면 로드
            if (avatarUrl) {
                loadAvatar(avatarUrl);
            }
        }
    }, [isLoaded, height, weight, avatarUrl]);

    // 의류 URL 변경 시
    useEffect(() => {
        if (isLoaded && garmentUrl) {
            fitGarment(garmentUrl);
        }
    }, [isLoaded, garmentUrl]);

    /**
     * 아바타 로드
     */
    const loadAvatar = useCallback((url: string) => {
        if (!isLoaded) return;
        sendMessage("GameManager", "LoadAvatar", url);
    }, [isLoaded, sendMessage]);

    /**
     * 의류 피팅
     */
    const fitGarment = useCallback((url: string) => {
        if (!isLoaded) return;
        sendMessage("GameManager", "FitGarment", url);
    }, [isLoaded, sendMessage]);

    /**
     * 카메라 리셋
     */
    const resetCamera = useCallback(() => {
        if (!isLoaded) return;
        sendMessage("AvatarRoot", "ResetCamera", "");
    }, [isLoaded, sendMessage]);

    /**
     * 아바타 회전
     */
    const rotateAvatar = useCallback((angle: number) => {
        if (!isLoaded) return;
        sendMessage("AvatarRoot", "RotateAvatar", angle.toString());
    }, [isLoaded, sendMessage]);

    return (
        <div className={`unity-container ${className}`} style={{ width: '100%', height: '100%' }}>
            <Unity
                unityProvider={unityProvider}
                style={{
                    width: '100%',
                    height: '100%',
                    visibility: isLoaded ? 'visible' : 'hidden'
                }}
            />

            {/* 로딩 오버레이 */}
            {!isLoaded && (
                <div style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    color: 'white'
                }}>
                    <div className="spinner" style={{
                        width: '40px',
                        height: '40px',
                        border: '3px solid rgba(255,255,255,0.3)',
                        borderTop: '3px solid #ff6b35',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite'
                    }} />
                    <p style={{ marginTop: '16px' }}>
                        3D 아바타 로딩 중... {Math.round(loadingProgression * 100)}%
                    </p>
                </div>
            )}

            <style jsx>{`
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}

// 외부에서 사용할 수 있도록 함수들 export
export { UnityAvatarViewer };
