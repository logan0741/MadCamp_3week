/**
 * API utilities for frontend-backend communication
 */

const API_BASE = 'http://localhost:8000';

// Token management
export const getToken = (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('auth_token');
};

export const setToken = (token: string): void => {
    localStorage.setItem('auth_token', token);
};

export const removeToken = (): void => {
    localStorage.removeItem('auth_token');
};

// API request helper
export async function apiRequest<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const token = getToken();

    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
    };

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || 'Request failed');
    }

    return response.json();
}

// Form data request (for file uploads)
export async function uploadRequest<T>(
    endpoint: string,
    formData: FormData
): Promise<T> {
    const token = getToken();

    const headers: HeadersInit = {
        ...(token && { Authorization: `Bearer ${token}` }),
    };

    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers,
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
}

// Types
export interface User {
    id: number;
    username: string;
    is_avatar_created: boolean;
    height: number | null;
    weight: number | null;
    avatar_url: string | null;
}

// API functions
export const userApi = {
    getStatus: () => apiRequest<User>('/user/status'),
};

export const authApi = {
    login: async (username: string, password: string) => {
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

        return response.json() as Promise<{ access_token: string; token_type: string }>;
    },
};
