'use client';

import { Bell, Settings } from 'lucide-react';
import styles from './TopBar.module.css';

export default function TopBar() {
    return (
        <header className={styles.header}>
            <h1 className={styles.title}>관심상품</h1>
            <div className={styles.actions}>
                <button className={styles.iconBtn} aria-label="Notifications">
                    <div className={styles.notificationBadge}>
                        <Bell size={24} strokeWidth={2} />
                        <span className={styles.badge} />
                    </div>
                </button>
                <button className={styles.iconBtn} aria-label="Settings">
                    <Settings size={24} strokeWidth={2} />
                </button>
            </div>
        </header>
    );
}
