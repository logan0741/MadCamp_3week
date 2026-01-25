/**
 * Zustand store for global state management
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Product } from '@/lib/types';

interface AppState {
    user: User | null;
    products: Product[];
    isLoading: boolean;

    setUser: (user: User | null) => void;
    setProducts: (products: Product[]) => void;
    addProduct: (product: Product) => void;
    removeProduct: (productId: number) => void;
    setLoading: (loading: boolean) => void;
    logout: () => void;
}

export const useStore = create<AppState>()(
    persist(
        (set) => ({
            user: null,
            products: [],
            isLoading: false,

            setUser: (user) => set({ user }),
            setProducts: (products) => set({ products }),
            addProduct: (product) => set((state) => ({
                products: [...state.products, product]
            })),
            removeProduct: (productId) => set((state) => ({
                products: state.products.filter((p) => p.id !== productId)
            })),
            setLoading: (isLoading) => set({ isLoading }),
            logout: () => set({ user: null, products: [] }),
        }),
        {
            name: 'musinsa-tracker-store',
            partialize: (state) => ({ user: state.user }),
        }
    )
);
