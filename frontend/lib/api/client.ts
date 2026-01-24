/**
 * API Client - Core HTTP utilities and token management
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============= Token Management =============

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

// ============= API Request Helpers =============

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
        // Handle 401 Unauthorized - redirect to login
        if (response.status === 401) {
            removeToken();
            if (typeof window !== 'undefined') {
                window.location.href = '/login';
            }
            throw new Error('세션이 만료되었습니다. 다시 로그인해주세요.');
        }

        const error = await response.json().catch(() => ({ detail: 'Request failed' }));

        // Handle FastAPI validation error (array of errors)
        if (Array.isArray(error.detail)) {
            const firstError = error.detail[0];
            const msg = firstError.msg || 'Validation error';
            throw new Error(msg);
        }

        throw new Error(error.detail || 'Request failed');
    }

    return response.json();
}

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
        if (response.status === 401) {
            removeToken();
            if (typeof window !== 'undefined') {
                window.location.href = '/login';
            }
            throw new Error('세션이 만료되었습니다. 다시 로그인해주세요.');
        }

        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
}

export { API_BASE };
