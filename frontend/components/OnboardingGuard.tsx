'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { getToken, userApi } from '@/lib/api';

interface OnboardingGuardProps {
    children: React.ReactNode;
}

export default function OnboardingGuard({ children }: OnboardingGuardProps) {
    const router = useRouter();
    const { user, setUser } = useStore();

    useEffect(() => {
        const checkOnboarding = async () => {
            const token = getToken();

            if (!token) {
                router.push('/login');
                return;
            }

            if (!user) {
                try {
                    const userData = await userApi.getStatus();
                    setUser(userData);

                    if (!userData.is_avatar_created) {
                        // TTS announcement
                        if ('speechSynthesis' in window) {
                            const msg = new SpeechSynthesisUtterance(
                                '반갑습니다. 서비스를 시작하기 전, 당신의 아바타를 먼저 만들겠습니다.'
                            );
                            msg.lang = 'ko-KR';
                            window.speechSynthesis.speak(msg);
                        }
                        router.push('/onboarding');
                    }
                } catch {
                    router.push('/login');
                }
            } else if (!user.is_avatar_created) {
                router.push('/onboarding');
            }
        };

        checkOnboarding();
    }, [user, setUser, router]);

    if (!user || !user.is_avatar_created) {
        return (
            <div style={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'var(--color-bg-primary)',
            }}>
                <div className="spinner" />
            </div>
        );
    }

    return <>{children}</>;
}
