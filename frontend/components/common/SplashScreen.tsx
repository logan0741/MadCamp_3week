'use client';

import { useEffect, useState } from 'react';
import styles from './SplashScreen.module.css';

export default function SplashScreen() {
    const [isVisible, setIsVisible] = useState(true);
    const [opacity, setOpacity] = useState(1);
    const [logoOpacity, setLogoOpacity] = useState(0);

    useEffect(() => {
        // Prevent body scroll when splash is visible
        document.body.style.overflow = 'hidden';

        // 1. Logo fade in
        const fadeInTimer = setTimeout(() => {
            setLogoOpacity(1);
        }, 100);

        // 2. Start fade out of the entire screen
        const fadeOutTimer = setTimeout(() => {
            setOpacity(0);
        }, 2500); // Wait for logo to be fully visible + read time

        // 3. Remove component from DOM
        const removeTimer = setTimeout(() => {
            setIsVisible(false);
            // Restore body scroll
            document.body.style.overflow = '';
        }, 3000); // fadeOutTimer + transition duration

        return () => {
            clearTimeout(fadeInTimer);
            clearTimeout(fadeOutTimer);
            clearTimeout(removeTimer);
            document.body.style.overflow = '';
        };
    }, []);

    if (!isVisible) return null;

    return (
        <div
            className={styles.container}
            style={{ opacity: opacity }}
        >
            <div
                className={styles.logoContainer}
                style={{ opacity: logoOpacity }}
            >
                <img
                    src="/images/splash_logo.png"
                    alt="FitMe Logo"
                    className={styles.logo}
                />
            </div>
        </div>
    );
}
