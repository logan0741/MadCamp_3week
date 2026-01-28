/**
 * useAuth - Authentication custom hook
 */
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, setToken, removeToken, userApi } from '@/lib/api';
import { useStore } from '@/lib/store';
import type { User } from '@/lib/types';

interface UseAuthReturn {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (token: string) => void;
    logout: () => void;
    refreshUser: () => Promise<void>;
}

export function useAuth(redirectOnUnauthenticated: boolean = false): UseAuthReturn {
    const router = useRouter();
    const { user, setUser, logout: storeLogout } = useStore();
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const checkAuth = async () => {
            const token = getToken();

            if (!token) {
                setIsLoading(false);
                if (redirectOnUnauthenticated) {
                    router.push('/login');
                }
                return;
            }

            try {
                const userData = await userApi.getStatus();
                setUser(userData);
            } catch (error) {
                console.error('Failed to get user status:', error);
                removeToken();
                if (redirectOnUnauthenticated) {
                    router.push('/login');
                }
            } finally {
                setIsLoading(false);
            }
        };

        checkAuth();
    }, [router, redirectOnUnauthenticated, setUser]);

    const login = (token: string) => {
        setToken(token);
    };

    const logout = () => {
        removeToken();
        localStorage.removeItem('musinsa-tracker-store');
        storeLogout();
        router.push('/login');
    };

    const refreshUser = async () => {
        try {
            const userData = await userApi.getStatus();
            setUser(userData);
        } catch (error) {
            console.error('Failed to refresh user:', error);
        }
    };

    return {
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
    };
}
