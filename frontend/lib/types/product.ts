/**
 * Product related types
 */

export interface Product {
    id: number;
    musinsa_id: string;
    url: string;
    title: string | null;
    brand: string | null;
    thumbnail_url: string | null;
    is_garment_modeled: boolean;
    current_price: number | null;
    discount_rate: number | null;
}

export interface PriceLog {
    id: number;
    price: number;
    discount_rate: number | null;
    captured_at: string;
}

export interface ProductListResponse {
    products: Product[];
    total: number;
}

export interface PriceHistoryResponse {
    product_id: number;
    title: string;
    history: PriceLog[];
}
