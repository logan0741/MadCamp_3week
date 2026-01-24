import { create } from 'zustand';
import { User, Product } from './api';

interface StoreState {
    user: User | null;
    setUser: (user: User | null) => void;
    products: Product[];
    setProducts: (products: Product[]) => void;
}

export const useStore = create<StoreState>((set) => ({
    user: null,
    setUser: (user) => set({ user }),
    products: [],
    setProducts: (products) => set({ products }),
}));

