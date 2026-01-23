'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { getToken } from '@/lib/api';

export default function Home() {
    const router = useRouter();
    const { user } = useStore();

    useEffect(() => {
        const token = getToken();

        if (!token) {
            router.push('/login');
        } else if (user && !user.is_avatar_created) {
            router.push('/onboarding');
        } else {
            router.push('/dashboard');
        }
    }, [user, router]);

    return (
        <div className="page flex items-center justify-center">
            <div className="spinner" />
        </div>
    );
}
