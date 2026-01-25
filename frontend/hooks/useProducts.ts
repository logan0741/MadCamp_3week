/**
 * useProducts - Product management custom hook
 */
'use client';

import { useState, useCallback } from 'react';
import { productApi } from '@/lib/api';
import { useStore } from '@/lib/store';
import type { Product } from '@/lib/types';

interface UseProductsReturn {
    products: Product[];
    isLoading: boolean;
    error: string | null;
    loadProducts: () => Promise<void>;
    addProduct: (url: string) => Promise<Product>;
    removeProduct: (productId: number) => Promise<void>;
}

export function useProducts(): UseProductsReturn {
    const { products, setProducts, addProduct: storeAddProduct, removeProduct: storeRemoveProduct } = useStore();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadProducts = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            const data = await productApi.getAll();
            setProducts(data.products);
        } catch (err) {
            console.error('Failed to load products:', err);
            setError('상품을 불러올 수 없습니다.');
        } finally {
            setIsLoading(false);
        }
    }, [setProducts]);

    const addProduct = useCallback(async (url: string): Promise<Product> => {
        setError(null);

        try {
            const product = await productApi.track(url);
            storeAddProduct(product);
            return product;
        } catch (err: any) {
            const message = err.message || '상품을 추가할 수 없습니다.';
            setError(message);
            throw err;
        }
    }, [storeAddProduct]);

    const removeProduct = useCallback(async (productId: number) => {
        setError(null);

        try {
            await productApi.remove(productId);
            storeRemoveProduct(productId);
        } catch (err) {
            console.error('Failed to remove product:', err);
            setError('상품을 삭제할 수 없습니다.');
            throw err;
        }
    }, [storeRemoveProduct]);

    return {
        products,
        isLoading,
        error,
        loadProducts,
        addProduct,
        removeProduct,
    };
}
