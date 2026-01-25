/**
 * usePriceHistory - Price history custom hook
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import { productApi } from '@/lib/api';
import type { PriceLog } from '@/lib/types';

interface PriceStats {
    currentPrice: number;
    minPrice: number;
    maxPrice: number;
}

interface UsePriceHistoryReturn {
    history: PriceLog[];
    stats: PriceStats | null;
    isLoading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
}

export function usePriceHistory(productId: number): UsePriceHistoryReturn {
    const [history, setHistory] = useState<PriceLog[]>([]);
    const [stats, setStats] = useState<PriceStats | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadHistory = useCallback(async () => {
        if (!productId) return;

        setIsLoading(true);
        setError(null);

        try {
            const data = await productApi.getHistory(productId);
            setHistory(data.history);

            // Calculate stats
            if (data.history.length > 0) {
                const prices = data.history.map(h => h.price);
                setStats({
                    currentPrice: prices[prices.length - 1],
                    minPrice: Math.min(...prices),
                    maxPrice: Math.max(...prices),
                });
            }
        } catch (err) {
            console.error('Failed to load price history:', err);
            setError('가격 히스토리를 불러올 수 없습니다.');
        } finally {
            setIsLoading(false);
        }
    }, [productId]);

    useEffect(() => {
        loadHistory();
    }, [loadHistory]);

    return {
        history,
        stats,
        isLoading,
        error,
        refresh: loadHistory,
    };
}
