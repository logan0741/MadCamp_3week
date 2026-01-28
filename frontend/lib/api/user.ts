/**
 * User API - User management endpoints
 */

import { apiRequest } from './client';
import type { User } from '@/lib/types';

interface ProfileUpdateData {
    height?: number;
    weight?: number;
}

export const userApi = {
    getStatus: () =>
        apiRequest<User>('/user/status'),

    updateProfile: (data: ProfileUpdateData) =>
        apiRequest<User>('/user/profile', { method: 'PUT', body: JSON.stringify(data) }),
};
