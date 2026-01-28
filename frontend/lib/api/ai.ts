import { apiRequest, uploadRequest } from './client';

export interface Photo {
    filename: string;
    url: string;
}

export interface RecommendationItem {
    category: string;
    brand: string;
    product_name: string;
    musinsa_id?: string;
    url?: string;
    color: string;
    reason: string;
}

export interface AnalysisResult {
    user_analysis: {
        personal_color: string;
        skin_tone_hex: string;
        best_colors: string[];
        worst_colors: string[];
    };
    fashion_terrorist_check: {
        is_terrorist: boolean;
        mismatch_score: number;
        warning_message: string;
    };
    recommendations: RecommendationItem[];
}

export interface AIResponse {
    status: 'success' | 'error' | 'fashion_terrorist';
    message?: string;
    data?: AnalysisResult;
    processed_count?: number;
}

export const aiApi = {
    // List uploaded user photos by type
    getPhotos: async (photoType: 'model' | 'daily' = 'model'): Promise<{ photos: Photo[] }> => {
        return apiRequest(`/user/photos?photo_type=${photoType}`, {
            method: 'GET'
        });
    },

    // Trigger AI analysis with selected photo
    analyzePhoto: async (filename: string): Promise<AIResponse> => {
        return apiRequest('/user/ai/analyze', {
            method: 'POST',
            body: JSON.stringify({ filename })
        });
    }
};

export const onboardingApi = {
    upload: async (file: File, photoType: 'model' | 'daily' = 'model') => {
        const formData = new FormData();
        formData.append('file', file);

        // Use the new /user/photos endpoint with type
        return uploadRequest(`/user/photos?photo_type=${photoType}`, formData);
    }
};
