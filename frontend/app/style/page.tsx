'use client';

import { useEffect, useState, ChangeEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getToken, aiApi, onboardingApi } from '@/lib/api';
import type { Photo } from '@/lib/api';
import BottomNav from '@/components/layout/BottomNav';
import styles from './style.module.css';

export default function StylePage() {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(true);
    const [dailyPhotos, setDailyPhotos] = useState<Photo[]>([]);
    const [isUploading, setIsUploading] = useState(false);

    useEffect(() => {
        const token = getToken();
        if (!token) {
            router.push('/login');
            return;
        }

        loadDailyPhotos();
    }, [router]);

    const loadDailyPhotos = async () => {
        try {
            const data = await aiApi.getPhotos('daily');
            setDailyPhotos(data.photos || []);
        } catch (err) {
            console.error('Failed to load daily photos:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleDailyUpload = async (event: ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        try {
            await onboardingApi.upload(file, 'daily');
            await loadDailyPhotos();
        } catch (err) {
            console.error('Daily upload failed:', err);
            alert('사진 업로드에 실패했습니다.');
        } finally {
            setIsUploading(false);
            event.target.value = '';
        }
    };

    return (
        <div className={styles.page}>
            <main className={styles.main}>
                {isLoading ? (
                    <div className={styles.loading}>
                        <div className="spinner" />
                        <p>로딩 중...</p>
                    </div>
                ) : (
                    <>
                        <section className={styles.headerSection}>
                            <div>
                                <h1 className={styles.pageTitle}>스타일</h1>
                                <p className={styles.pageSubtitle}>나의 데일리 룩을 모아보고 스타일을 분석하세요.</p>
                            </div>
                            <label className={styles.addDailyBtn}>
                                {isUploading ? '...' : '+ 추가'}
                                <input
                                    type="file"
                                    hidden
                                    accept="image/*"
                                    onChange={handleDailyUpload}
                                    disabled={isUploading}
                                />
                            </label>
                        </section>

                        <section className={styles.gallerySection}>
                            <div className={styles.galleryGrid}>
                                {dailyPhotos.length > 0 ? (
                                    dailyPhotos.map((photo, index) => (
                                        <Link
                                            key={photo.filename}
                                            href={`/style/${encodeURIComponent(photo.filename)}`}
                                            className={styles.galleryItem}
                                        >
                                            <img src={photo.url} alt={`Daily Look ${index + 1}`} />
                                        </Link>
                                    ))
                                ) : (
                                    <div className={styles.emptyGallery}>
                                        올린 사진이 없습니다.
                                    </div>
                                )}
                            </div>
                        </section>
                    </>
                )}
            </main>

            <BottomNav />
        </div>
    );
}
