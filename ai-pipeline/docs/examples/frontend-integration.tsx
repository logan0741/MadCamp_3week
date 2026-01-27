/**
 * Frontend Integration Example - Virtual Try-On Component
 *
 * 무신사 가상 피팅 서비스 - 프론트엔드 통합 예시
 * Framework: Next.js 14 App Router + TypeScript
 */

"use client";

import { useState, useRef } from "react";
import Image from "next/image";

// ============================================
// Types
// ============================================

interface VTONRequest {
  person_image_url?: string;
  garment_image_url?: string;
  person_image_base64?: string;
  garment_image_base64?: string;
  num_inference_steps?: number;
  guidance_scale?: number;
  seed?: number;
  enhance_output?: boolean;
  restore_face?: boolean;
}

interface VTONResponse {
  success: boolean;
  result_url: string;
  processing_time_seconds: number;
  vram_allocated_mb?: number;
}

interface AsyncTaskResponse {
  success: boolean;
  task_id: string;
  status_url: string;
  message: string;
}

interface TaskStatus {
  task_id: string;
  status: "PENDING" | "PROGRESS" | "SUCCESS" | "FAILURE";
  progress?: number;
  message?: string;
  result?: VTONResponse;
  error?: string;
}

// ============================================
// API Configuration
// ============================================

const AI_API_BASE_URL = process.env.NEXT_PUBLIC_AI_API_URL || "http://localhost:8001";


// ============================================
// API Utility Functions
// ============================================

/**
 * 동기 가상 피팅 (즉시 결과 반환)
 */
async function tryOnSync(request: VTONRequest): Promise<VTONResponse> {
  const response = await fetch(`${AI_API_BASE_URL}/api/vton/try-on`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "가상 피팅 실패");
  }

  return response.json();
}

/**
 * 비동기 가상 피팅 (태스크 제출)
 */
async function tryOnAsync(request: VTONRequest): Promise<AsyncTaskResponse> {
  const response = await fetch(`${AI_API_BASE_URL}/api/vton/try-on/async`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error("비동기 작업 제출 실패");
  }

  return response.json();
}

/**
 * 작업 상태 조회
 */
async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await fetch(`${AI_API_BASE_URL}/api/vton/tasks/${taskId}`);

  if (!response.ok) {
    throw new Error("작업 상태 조회 실패");
  }

  return response.json();
}

/**
 * 이미지를 Base64로 변환
 */
function imageToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result as string;
      // Remove data URL prefix (data:image/jpeg;base64,)
      const base64Data = base64.split(",")[1];
      resolve(base64Data);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}


// ============================================
// React Component: Virtual Try-On
// ============================================

export default function VirtualTryOnComponent() {
  // State
  const [personImage, setPersonImage] = useState<File | null>(null);
  const [garmentImage, setGarmentImage] = useState<File | null>(null);
  const [personPreview, setPersonPreview] = useState<string>("");
  const [garmentPreview, setGarmentPreview] = useState<string>("");
  const [resultImage, setResultImage] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string>("");
  const [processingTime, setProcessingTime] = useState<number>(0);

  // Refs
  const personInputRef = useRef<HTMLInputElement>(null);
  const garmentInputRef = useRef<HTMLInputElement>(null);

  // ============================================
  // Handlers
  // ============================================

  /**
   * 사람 이미지 선택
   */
  const handlePersonImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setPersonImage(file);
      setPersonPreview(URL.createObjectURL(file));
      setError("");
    }
  };

  /**
   * 옷 이미지 선택
   */
  const handleGarmentImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setGarmentImage(file);
      setGarmentPreview(URL.createObjectURL(file));
      setError("");
    }
  };

  /**
   * 동기 방식 피팅 (즉시 결과)
   */
  const handleTryOnSync = async () => {
    if (!personImage || !garmentImage) {
      setError("사진과 옷 이미지를 모두 선택해주세요.");
      return;
    }

    setLoading(true);
    setError("");
    setProgress(0);

    try {
      // 이미지를 Base64로 변환
      const personBase64 = await imageToBase64(personImage);
      const garmentBase64 = await imageToBase64(garmentImage);

      // API 호출
      const result = await tryOnSync({
        person_image_base64: personBase64,
        garment_image_base64: garmentBase64,
        num_inference_steps: 50,
        guidance_scale: 7.5,
        enhance_output: true,
        restore_face: true,
      });

      // 결과 표시
      setResultImage(result.result_url);
      setProcessingTime(result.processing_time_seconds);

    } catch (err: any) {
      setError(err.message || "가상 피팅 실패");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 비동기 방식 피팅 (진행 상태 표시)
   */
  const handleTryOnAsync = async () => {
    if (!personImage || !garmentImage) {
      setError("사진과 옷 이미지를 모두 선택해주세요.");
      return;
    }

    setLoading(true);
    setError("");
    setProgress(0);

    try {
      // 이미지를 Base64로 변환
      const personBase64 = await imageToBase64(personImage);
      const garmentBase64 = await imageToBase64(garmentImage);

      // 비동기 작업 제출
      const taskResponse = await tryOnAsync({
        person_image_base64: personBase64,
        garment_image_base64: garmentBase64,
        num_inference_steps: 50,
        guidance_scale: 7.5,
        enhance_output: true,
        restore_face: true,
      });

      // 폴링으로 작업 상태 확인
      const taskId = taskResponse.task_id;
      const pollInterval = setInterval(async () => {
        try {
          const status = await getTaskStatus(taskId);

          if (status.status === "PROGRESS") {
            setProgress(status.progress || 0);
          } else if (status.status === "SUCCESS") {
            clearInterval(pollInterval);
            setResultImage(status.result!.result_url);
            setProcessingTime(status.result!.processing_time_seconds);
            setLoading(false);
          } else if (status.status === "FAILURE") {
            clearInterval(pollInterval);
            setError(status.error || "작업 실패");
            setLoading(false);
          }
        } catch (err) {
          clearInterval(pollInterval);
          setError("상태 조회 실패");
          setLoading(false);
        }
      }, 1000); // 1초마다 폴링

    } catch (err: any) {
      setError(err.message || "비동기 작업 제출 실패");
      setLoading(false);
    }
  };

  /**
   * 초기화
   */
  const handleReset = () => {
    setPersonImage(null);
    setGarmentImage(null);
    setPersonPreview("");
    setGarmentPreview("");
    setResultImage("");
    setError("");
    setProgress(0);
    setProcessingTime(0);
  };

  // ============================================
  // Render
  // ============================================

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8 text-center">
        무신사 가상 피팅
      </h1>

      {/* 입력 섹션 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* 사람 이미지 */}
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">내 사진</h2>

          {personPreview ? (
            <div className="relative aspect-square mb-4">
              <Image
                src={personPreview}
                alt="사람 사진"
                fill
                className="object-cover rounded-lg"
              />
            </div>
          ) : (
            <div className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center mb-4">
              <p className="text-gray-500">사진을 선택해주세요</p>
            </div>
          )}

          <input
            ref={personInputRef}
            type="file"
            accept="image/*"
            onChange={handlePersonImageChange}
            className="hidden"
          />
          <button
            onClick={() => personInputRef.current?.click()}
            className="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600"
          >
            사진 선택
          </button>
        </div>

        {/* 옷 이미지 */}
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">입어볼 옷</h2>

          {garmentPreview ? (
            <div className="relative aspect-square mb-4">
              <Image
                src={garmentPreview}
                alt="옷 이미지"
                fill
                className="object-cover rounded-lg"
              />
            </div>
          ) : (
            <div className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center mb-4">
              <p className="text-gray-500">옷 이미지를 선택해주세요</p>
            </div>
          )}

          <input
            ref={garmentInputRef}
            type="file"
            accept="image/*"
            onChange={handleGarmentImageChange}
            className="hidden"
          />
          <button
            onClick={() => garmentInputRef.current?.click()}
            className="w-full bg-green-500 text-white py-2 rounded-lg hover:bg-green-600"
          >
            옷 선택
          </button>
        </div>
      </div>

      {/* 액션 버튼 */}
      <div className="flex gap-4 mb-8">
        <button
          onClick={handleTryOnSync}
          disabled={loading || !personImage || !garmentImage}
          className="flex-1 bg-purple-600 text-white py-3 rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {loading ? "처리 중..." : "바로 입어보기 (동기)"}
        </button>

        <button
          onClick={handleTryOnAsync}
          disabled={loading || !personImage || !garmentImage}
          className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          입어보기 (비동기)
        </button>

        <button
          onClick={handleReset}
          className="px-6 bg-gray-500 text-white py-3 rounded-lg font-semibold hover:bg-gray-600"
        >
          초기화
        </button>
      </div>

      {/* 진행 상태 */}
      {loading && progress > 0 && (
        <div className="mb-8">
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div
              className="bg-blue-600 h-4 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-center mt-2 text-gray-600">{progress}% 완료</p>
        </div>
      )}

      {/* 에러 표시 */}
      {error && (
        <div className="mb-8 p-4 bg-red-100 border border-red-400 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {/* 결과 표시 */}
      {resultImage && (
        <div className="border-2 border-gray-300 rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold">피팅 결과</h2>
            <span className="text-gray-600">
              처리 시간: {processingTime.toFixed(2)}초
            </span>
          </div>

          <div className="relative aspect-square max-w-2xl mx-auto">
            <Image
              src={resultImage}
              alt="가상 피팅 결과"
              fill
              className="object-contain rounded-lg"
            />
          </div>

          <div className="mt-6 flex gap-4">
            <a
              href={resultImage}
              download="virtual-tryon-result.png"
              className="flex-1 bg-blue-600 text-white py-3 rounded-lg text-center font-semibold hover:bg-blue-700"
            >
              다운로드
            </a>
            <button
              onClick={() => {
                // 무신사 장바구니 or 관심 상품 추가 로직
                console.log("Add to wishlist");
              }}
              className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700"
            >
              관심 상품 추가
            </button>
          </div>
        </div>
      )}
    </div>
  );
}


// ============================================
// Usage Example in Page
// ============================================

/*
// app/virtual-tryon/page.tsx

import VirtualTryOnComponent from "@/components/VirtualTryOnComponent";

export default function VirtualTryOnPage() {
  return (
    <main>
      <VirtualTryOnComponent />
    </main>
  );
}
*/
