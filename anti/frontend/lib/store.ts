import { create } from 'zustand';
import { User } from './api';

interface StoreState {
    user: User | null;
    setUser: (user: User | null) => void;
}

export const useStore = create<StoreState>((set) => ({
    user: null,
    setUser: (user) => set({ user }),
}));
