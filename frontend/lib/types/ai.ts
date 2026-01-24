/**
 * AI related types
 */

export interface AITask {
    id: string;
    task_type: string;
    status: string;
    result_url: string | null;
    error_message: string | null;
    created_at: string;
    updated_at: string;
}

export interface OnboardingUploadResponse {
    message: string;
    task_id: string;
    status: string;
}
