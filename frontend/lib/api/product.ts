/**
 * Product API - Product and price tracking endpoints
 */

import { apiRequest } from './client';
import type { Product, ProductListResponse, PriceHistoryResponse } from '@/lib/types';

export const productApi = {
    track: (url: string) =>
        apiRequest<Product>('/products/track', { method: 'POST', body: JSON.stringify({ url }) }),

    getAll: () =>
        apiRequest<ProductListResponse>('/products'),

    getHistory: (productId: number) =>
        apiRequest<PriceHistoryResponse>(`/products/${productId}/history`),

    remove: (productId: number) =>
        apiRequest<{ message: string }>(`/products/${productId}`, { method: 'DELETE' }),

    forceUpdateAll: () =>
        apiRequest<{ message: string; status: string }>('/admin/update-prices', { method: 'POST' }),

    createFitting: (productId: number) =>
        apiRequest<{ status: string; image_url: string; message: string }>(`/products/${productId}/fitting`, { method: 'POST' }),
};
