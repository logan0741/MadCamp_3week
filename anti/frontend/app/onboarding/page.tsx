'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { onboardingApi, getToken } from '@/lib/api';
import { useStore } from '@/lib/store';
import styles from './onboarding.module.css';

const INTRO_STEPS = [
    '반갑습니다! 서비스를 시작하기 전, 당신만의 3D 아바타를 만들겠습니다.',
    '카메라 앞에 서서 전신이 보이도록 해주세요.',
    '준비가 되셨으면 촬영 시작 버튼을 눌러주세요.',
];

const RECORDING_POSES = [
    '정면을 바라봐주세요.',
    '양팔을 옆으로 들어주세요.',
    '천천히 왼쪽으로 돌아주세요.',
    '뒷면을 보여주세요.',
    '계속해서 오른쪽으로 돌아주세요.',
    '다시 정면을 바라봐주세요.',
];

export default function OnboardingPage() {
    const router = useRouter();
    const { user, setUser } = useStore();
    const videoRef = useRef<HTMLVideoElement>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    const [step, setStep] = useState<'intro' | 'recording' | 'uploading' | 'complete'>('intro');
    const [introStep, setIntroStep] = useState(0);
    const [recordingPose, setRecordingPose] = useState(0);
    const [isRecording, setIsRecording] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [error, setError] = useState('');
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    // Check authentication on mount
    useEffect(() => {
        const token = getToken();
        if (!token) {
            router.push('/login');
            return;
        }
        setIsAuthenticated(true);
    }, [router]);

    // TTS function with promise
    const speak = useCallback((text: string): Promise<void> => {
        return new Promise((resolve) => {
            if ('speechSynthesis' in window) {
                setIsSpeaking(true);
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'ko-KR';
                utterance.rate = 0.9;
                utterance.onend = () => {
                    setIsSpeaking(false);
                    resolve();
                };
                utterance.onerror = () => {
                    setIsSpeaking(false);
                    resolve();
                };
                window.speechSynthesis.speak(utterance);
            } else {
                resolve();
            }
        });
    }, []);

    // Stop TTS
    const stopSpeaking = useCallback(() => {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            setIsSpeaking(false);
        }
    }, []);

    // Initialize camera only after auth check
    useEffect(() => {
        if (!isAuthenticated) return;

        const initCamera = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'user', width: 1280, height: 720 },
                    audio: false,
                });

                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                }
            } catch (err) {
                setError('카메라 접근이 거부되었습니다. 카메라 권한을 허용해주세요.');
            }
        };

        initCamera();

        return () => {
            stopSpeaking();
            if (videoRef.current?.srcObject) {
                const stream = videoRef.current.srcObject as MediaStream;
                stream.getTracks().forEach(track => track.stop());
            }
        };
    }, [isAuthenticated, stopSpeaking]);

    // Speak current intro step when it changes
    useEffect(() => {
        if (step === 'intro' && introStep < INTRO_STEPS.length) {
            speak(INTRO_STEPS[introStep]);
        }
    }, [step, introStep, speak]);

    // Handle next intro step
    const handleNextIntro = () => {
        stopSpeaking();
        if (introStep < INTRO_STEPS.length - 1) {
            setIntroStep(prev => prev + 1);
        }
    };

    // Speak current recording pose when it changes
    useEffect(() => {
        if (isRecording && recordingPose < RECORDING_POSES.length) {
            speak(RECORDING_POSES[recordingPose]);
        }
    }, [isRecording, recordingPose, speak]);

    // Handle next recording pose
    const handleNextPose = () => {
        stopSpeaking();
        if (recordingPose < RECORDING_POSES.length - 1) {
            setRecordingPose(prev => prev + 1);
        } else {
            // Finish recording
            stopRecording();
        }
    };

    const startRecording = async () => {
        if (!videoRef.current?.srcObject) return;

        setStep('recording');
        setIsRecording(true);
        setRecordingPose(0);
        chunksRef.current = [];

        const stream = videoRef.current.srcObject as MediaStream;
        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                chunksRef.current.push(e.data);
            }
        };

        mediaRecorder.onstop = () => {
            uploadVideo();
        };

        mediaRecorderRef.current = mediaRecorder;
        mediaRecorder.start(100);
    };

    const stopRecording = () => {
        setIsRecording(false);
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
    };

    const uploadVideo = async () => {
        setStep('uploading');

        try {
            const blob = new Blob(chunksRef.current, { type: 'video/webm' });
            const file = new File([blob], 'onboarding.webm', { type: 'video/webm' });

            // Simulate upload progress
            const progressInterval = setInterval(() => {
                setUploadProgress(prev => Math.min(prev + 10, 90));
            }, 300);

            const result = await onboardingApi.upload(file);

            clearInterval(progressInterval);
            setUploadProgress(100);

            // Update user state
            if (user) {
                setUser({ ...user, is_avatar_created: true });
            }

            setStep('complete');
            speak('아바타 생성이 시작되었습니다. 약 5분 정도 소요됩니다.');

            // Redirect to dashboard after delay
            setTimeout(() => {
                router.push('/dashboard');
            }, 4000);

        } catch (err) {
            setError(err instanceof Error ? err.message : '업로드에 실패했습니다.');
            setStep('intro');
            setIntroStep(0);
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.cameraContainer}>
                <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className={styles.video}
                />

                {/* Silhouette overlay */}
                <div className={styles.silhouette}>
                    <svg viewBox="0 0 200 400" className={styles.silhouetteSvg}>
                        <ellipse cx="100" cy="50" rx="35" ry="40" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="5,5" />
                        <path d="M65 90 L65 200 L40 260 L40 380 M135 90 L135 200 L160 260 L160 380 M65 90 L135 90 M65 120 L30 180 M135 120 L170 180"
                            fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="5,5" />
                    </svg>
                </div>

                {/* Recording indicator */}
                {isRecording && (
                    <div className={styles.recordingIndicator}>
                        <span className={styles.recordingDot} />
                        REC
                    </div>
                )}
            </div>

            {/* Instruction panel */}
            <div className={styles.instructionPanel}>
                {step === 'intro' && (
                    <>
                        <h2>3D 아바타 생성</h2>
                        <p className={styles.instruction}>
                            {INTRO_STEPS[introStep]}
                        </p>

                        {isSpeaking && (
                            <div className={styles.speakingIndicator}>
                                <span className={styles.speakingDot}></span>
                                <span className={styles.speakingDot}></span>
                                <span className={styles.speakingDot}></span>
                            </div>
                        )}

                        <div className={styles.buttonRow}>
                            {introStep < INTRO_STEPS.length - 1 ? (
                                <button
                                    onClick={handleNextIntro}
                                    className="btn btn-primary btn-full"
                                >
                                    다음 →
                                </button>
                            ) : (
                                <button
                                    onClick={startRecording}
                                    className="btn btn-primary btn-full"
                                >
                                    촬영 시작
                                </button>
                            )}
                        </div>

                        <div className={styles.stepIndicator}>
                            {INTRO_STEPS.map((_, i) => (
                                <span
                                    key={i}
                                    className={`${styles.stepDot} ${i === introStep ? styles.active : ''} ${i < introStep ? styles.completed : ''}`}
                                />
                            ))}
                        </div>
                    </>
                )}

                {step === 'recording' && (
                    <>
                        <h2>촬영 중...</h2>
                        <p className={styles.instruction}>
                            {RECORDING_POSES[recordingPose]}
                        </p>

                        {isSpeaking && (
                            <div className={styles.speakingIndicator}>
                                <span className={styles.speakingDot}></span>
                                <span className={styles.speakingDot}></span>
                                <span className={styles.speakingDot}></span>
                            </div>
                        )}

                        <div className={styles.progress}>
                            <div
                                className={styles.progressBar}
                                style={{ width: `${((recordingPose + 1) / RECORDING_POSES.length) * 100}%` }}
                            />
                        </div>

                        <div className={styles.poseCounter}>
                            {recordingPose + 1} / {RECORDING_POSES.length}
                        </div>

                        <button
                            onClick={handleNextPose}
                            className="btn btn-primary btn-full"
                        >
                            {recordingPose < RECORDING_POSES.length - 1 ? '다음 포즈 →' : '촬영 완료 ✓'}
                        </button>
                    </>
                )}

                {step === 'uploading' && (
                    <>
                        <h2>업로드 중...</h2>
                        <p className={styles.instruction}>영상을 서버로 전송하고 있습니다.</p>
                        <div className={styles.progress}>
                            <div
                                className={styles.progressBar}
                                style={{ width: `${uploadProgress}%` }}
                            />
                        </div>
                        <span className={styles.progressText}>{uploadProgress}%</span>
                    </>
                )}

                {step === 'complete' && (
                    <>
                        <div className={styles.successIcon}>✓</div>
                        <h2>촬영 완료!</h2>
                        <p className={styles.instruction}>
                            아바타 생성이 시작되었습니다.<br />
                            잠시 후 대시보드로 이동합니다.
                        </p>
                    </>
                )}

                {error && <div className={styles.error}>{error}</div>}
            </div>
        </div>
    );
}
