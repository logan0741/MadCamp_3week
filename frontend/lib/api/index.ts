/**
 * API - Central export for backward compatibility
 */

// Re-export client utilities
export { getToken, setToken, removeToken, apiRequest, uploadRequest } from './client';

// Re-export all API modules
export { authApi } from './auth';
export { userApi } from './user';
export { productApi } from './product';
export { productApi } from './product';
export * from './ai';

// Re-export types for backward compatibility
export type { User, Product, PriceLog, AITask } from '@/lib/types';
