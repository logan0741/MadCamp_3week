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

                    setUser(userData);
                } catch {
                    router.push('/login');
                }
            }
        };

        checkOnboarding();
    }, [user, setUser, router]);

    if (!user) {
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
