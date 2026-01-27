/**
 * Auth API - Authentication endpoints
 */

import { apiRequest, API_BASE } from './client';
import type { User } from '@/lib/types';

interface TokenResponse {
    access_token: string;
    token_type: string;
}

interface RegisterData {
    username: string;
    password: string;
}

export const authApi = {
    register: (data: RegisterData) =>
        apiRequest<User>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),

    login: async (username: string, password: string): Promise<TokenResponse> => {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Login failed' }));
            throw new Error(error.detail || 'Login failed');
        }

        return response.json();
    },
};
