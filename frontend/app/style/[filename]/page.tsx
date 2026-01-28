'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, aiApi, Photo } from '@/lib/api';
import BottomNav from '@/components/layout/BottomNav';
import styles from './style-detail.module.css';

type StyleDetailProps = {
    params: { filename: string };
};

export default function StyleDetailPage({ params }: StyleDetailProps) {
    const router = useRouter();
    const filename = useMemo(() => decodeURIComponent(params.filename), [params.filename]);
    const [photo, setPhoto] = useState<Photo | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const token = getToken();
        if (!token) {
            router.push('/login');
            return;
        }

        const loadPhoto = async () => {
            try {
                const data = await aiApi.getPhotos('daily');
                const match = data.photos?.find(item => item.filename === filename);
                setPhoto(match || null);
            } catch (err) {
                console.error('Failed to load photo detail:', err);
            } finally {
                setIsLoading(false);
            }
        };

        loadPhoto();
    }, [filename, router]);

    return (
        <div className={styles.page}>
            <main className={styles.main}>
                <header className={styles.header}>
                    <button className={styles.backBtn} onClick={() => router.back()}>
                        ← 뒤로
                    </button>
                    <h1 className={styles.title}>스타일 분석</h1>
                </header>

                {isLoading ? (
                    <div className={styles.loading}>
                        <div className="spinner" />
                        <p>로딩 중...</p>
                    </div>
                ) : (
                    <>
                        <section className={styles.photoSection}>
                            {photo ? (
                                <img src={photo.url} alt="Daily look" className={styles.photo} />
                            ) : (
                                <div className={styles.photoPlaceholder}>사진을 불러오지 못했습니다.</div>
                            )}
                        </section>

                        <section className={styles.analysisSection}>
                            <h2 className={styles.sectionTitle}>AI 분석 결과</h2>
                            <div className={styles.analysisPlaceholder}>
                                추후 알고리즘이 적용될 영역입니다.
                            </div>
                        </section>
                    </>
                )}
            </main>

            <BottomNav />
        </div>
    );
}
