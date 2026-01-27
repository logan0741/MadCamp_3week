'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { List, User } from 'lucide-react';
import styles from './BottomNav.module.css';

export default function BottomNav() {
    const pathname = usePathname();

    const isActive = (path: string) => pathname === path || pathname?.startsWith(path + '/');

    return (
        <nav className={styles.navContainer}>
            <Link
                href="/dashboard"
                className={`${styles.navItem} ${isActive('/dashboard') ? styles.active : ''}`}
            >
                <List size={24} strokeWidth={isActive('/dashboard') ? 2.5 : 2} />
                <span className={styles.label}>관심상품</span>
            </Link>

            <Link
                href="/recommend"
                className={`${styles.navItem} ${isActive('/recommend') ? styles.active : ''}`}
            >
                <div style={{ position: 'relative' }}>
                    <span style={{ fontSize: '24px' }}>✨</span>
                </div>
                <span className={styles.label}>AI 추천</span>
            </Link>

            <Link
                href="/mypage"
                className={`${styles.navItem} ${isActive('/mypage') ? styles.active : ''}`}
            >
                <User size={24} strokeWidth={isActive('/mypage') ? 2.5 : 2} />
                <span className={styles.label}>마이페이지</span>
            </Link>
        </nav>
    );
}
