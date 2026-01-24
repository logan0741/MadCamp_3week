/**
 * AI API - AI tasks and onboarding endpoints
 */

import { apiRequest, uploadRequest } from './client';
import type { AITask, OnboardingUploadResponse } from '@/lib/types';

export const onboardingApi = {
    upload: (video: File) => {
        const formData = new FormData();
        formData.append('video', video);
        return uploadRequest<OnboardingUploadResponse>('/onboarding/upload', formData);
    },

    getTaskStatus: (taskId: string) =>
        apiRequest<AITask>(`/onboarding/task/${taskId}`),
};

export const aiApi = {
    requestFitting: (productId: number) =>
        apiRequest<AITask>(`/ai/fit/${productId}`, { method: 'POST' }),

    getTasks: () =>
        apiRequest<AITask[]>('/ai/tasks'),

    getTaskStatus: (taskId: string) =>
        apiRequest<AITask>(`/ai/task/${taskId}`),
};
