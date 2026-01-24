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

export interface Product {
    id: number;
    musinsa_id: string;
    url: string;
    title: string | null;
    brand: string | null;
    thumbnail_url: string | null;
    image_urls: string[];  // All product images for carousel
    original_price: number | null;  // Price before discount
    is_garment_modeled: boolean;
    current_price: number | null;
    discount_rate: number | null;
}

export interface ProductListResponse {
    products: Product[];
    total: number;
}

export interface PriceLog {
    id: number;
    price: number;
    discount_rate: number | null;
    captured_at: string;
}

export interface PriceHistoryResponse {
    product_id: number;
    title: string | null;
    history: PriceLog[];
    min_price: number | null;
    max_price: number | null;
    min_date: string | null;
    max_date: string | null;
}

export interface AITaskResponse {
    id: string;
    task_type: string;
    status: string;
    result_url: string | null;
    error_message: string | null;
    created_at: string;
    updated_at: string;
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
    register: async (username: string, password: string, height?: number, weight?: number) => {
        return apiRequest<User>('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, password, height, weight }),
        });
    },
};

export const productApi = {
    getAll: () => apiRequest<ProductListResponse>('/products'),
    track: (url: string) => apiRequest<Product>('/products/track', {
        method: 'POST',
        body: JSON.stringify({ url }),
    }),
    getHistory: (productId: number) => apiRequest<PriceHistoryResponse>(`/products/${productId}/history`),
    remove: (productId: number) => apiRequest<{ message: string }>(`/products/${productId}`, {
        method: 'DELETE',
    }),
};

export const onboardingApi = {
    upload: (file: File) => {
        const formData = new FormData();
        formData.append('video', file);
        return uploadRequest<{ message: string; task_id: string; status: string }>('/onboarding/upload', formData);
    },
    getTaskStatus: (taskId: string) => apiRequest<AITaskResponse>(`/onboarding/task/${taskId}`),
};

export const aiApi = {
    requestFitting: (productId: number) => apiRequest<AITaskResponse>(`/ai/fit/${productId}`, {
        method: 'POST',
    }),
    getTasks: () => apiRequest<AITaskResponse[]>('/ai/tasks'),
    getTaskStatus: (taskId: string) => apiRequest<AITaskResponse>(`/ai/task/${taskId}`),
};

