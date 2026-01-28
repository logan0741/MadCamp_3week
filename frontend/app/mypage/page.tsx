'use client';

import { useEffect, useState, ChangeEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { userApi, productApi, getToken, Product, onboardingApi, aiApi } from '@/lib/api';
import { useStore } from '@/lib/store';
import BottomNav from '@/components/layout/BottomNav';
import { User, Heart, Bell, Tag, ChevronRight, Camera, X } from 'lucide-react';
import styles from './mypage.module.css';

export default function MyPage() {
    const router = useRouter();
    const { user, setUser, products, setProducts } = useStore();
    const [isLoading, setIsLoading] = useState(true);
    const [stats, setStats] = useState({
        productCount: 0,
        alertCount: 0,
        brandCount: 0
    });
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
    const [latestPhoto, setLatestPhoto] = useState<string | null>(null);

    useEffect(() => {
        const token = getToken();
        if (!token) {
            router.push('/login');
            return;
        }

        loadData();
    }, [router]);

    const loadData = async () => {
        try {
            const [userData, productsData] = await Promise.all([
                userApi.getStatus(),
                productApi.getAll()
            ]);

            setUser(userData);
            setProducts(productsData.products);

            // Calculate stats
            const allProducts = productsData.products;
            const uniqueBrands = new Set(allProducts.map((p: Product) => p.brand).filter(Boolean));

            setStats({
                productCount: allProducts.length,
                alertCount: 0, // 가격 알림 기능 미구현
                brandCount: uniqueBrands.size
            });

        } catch (err) {
            console.error('Failed to load data:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const refreshLatestPhoto = async () => {
        try {
            const data = await aiApi.getPhotos('model');
            const newest = data.photos?.[0];
            if (newest?.filename) {
                setLatestPhoto(newest.filename);
            }
        } catch (err) {
            console.error('Failed to load photos:', err);
        }
    };

    const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        setUploadError(null);
        setUploadSuccess(null);

        try {
            await onboardingApi.upload(file, 'model');
            setUploadSuccess('업로드가 완료되었습니다. 저장된 사진은 이후 분석에 사용됩니다.');
            await refreshLatestPhoto();
        } catch (err) {
            console.error('Upload failed:', err);
            setUploadError('업로드에 실패했습니다. 잠시 후 다시 시도해주세요.');
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
                        {/* Profile Header */}
                        <section className={styles.profileHeader}>
                            <div className={styles.avatarIcon}>
                                <User size={32} />
                            </div>
                            <div className={styles.profileInfo}>
                                <h1 className={styles.username}>{user?.username}</h1>
                                <div className={styles.bodyInfo}>
                                    {user?.height && <span>{user.height}cm</span>}
                                    {user?.height && user?.weight && <span className={styles.dot}>·</span>}
                                    {user?.weight && <span>{user.weight}kg</span>}
                                    {!user?.height && !user?.weight && <span className={styles.muted}>체형 정보 미입력</span>}
                                </div>
                            </div>
                        </section>

                        {/* Activity Stats */}
                        <section className={styles.statsSection}>
                            <h2 className={styles.sectionTitle}>나의 활동</h2>
                            <div className={styles.statsGrid}>
                                <Link href="/dashboard" className={styles.statCard}>
                                    <div className={styles.statIcon}>
                                        <Heart size={20} />
                                    </div>
                                    <span className={styles.statNumber}>{stats.productCount}</span>
                                    <span className={styles.statLabel}>등록 상품</span>
                                </Link>
                                <div className={styles.statCard}>
                                    <div className={styles.statIcon}>
                                        <Bell size={20} />
                                    </div>
                                    <span className={styles.statNumber}>{stats.alertCount}</span>
                                    <span className={styles.statLabel}>가격 알림</span>
                                </div>
                                <div className={styles.statCard}>
                                    <div className={styles.statIcon}>
                                        <Tag size={20} />
                                    </div>
                                    <span className={styles.statNumber}>{stats.brandCount}</span>
                                    <span className={styles.statLabel}>브랜드</span>
                                </div>
                            </div>
                        </section>

                        {/* Profile Section */}
                        <section className={styles.profileSection}>
                            <h2 className={styles.sectionTitle}>내 정보</h2>
                            <div className={styles.profileCard}>
                                <div className={styles.profileItem}>
                                    <span className={styles.profileLabel}>아이디</span>
                                    <span className={styles.profileValue}>{user?.username}</span>
                                </div>
                                <div className={styles.profileItem}>
                                    <span className={styles.profileLabel}>키</span>
                                    <span className={styles.profileValue}>
                                        {user?.height ? `${user.height} cm` : '미입력'}
                                    </span>
                                </div>
                                <div className={styles.profileItem}>
                                    <span className={styles.profileLabel}>몸무게</span>
                                    <span className={styles.profileValue}>
                                        {user?.weight ? `${user.weight} kg` : '미입력'}
                                    </span>
                                </div>
                            </div>
                        </section>

                        {/* Settings Section */}
                        <section className={styles.settingsSection}>
                            <h2 className={styles.sectionTitle}>설정</h2>
                            <div className={styles.settingsList}>
                                <button
                                    className={styles.settingItem}
                                    onClick={() => {
                                        setIsUploadOpen(true);
                                        setUploadError(null);
                                        setUploadSuccess(null);
                                        refreshLatestPhoto();
                                    }}
                                >
                                    <span>사진 올리기</span>
                                    <ChevronRight size={18} className={styles.arrow} />
                                </button>
                                <button className={styles.settingItem}>
                                    <span>알림 설정</span>
                                    <ChevronRight size={18} className={styles.arrow} />
                                </button>
                                <button className={styles.settingItem}>
                                    <span>가격 알림 기준</span>
                                    <ChevronRight size={18} className={styles.arrow} />
                                </button>
                                <button
                                    className={`${styles.settingItem} ${styles.danger}`}
                                    onClick={() => {
                                        localStorage.removeItem('auth_token');
                                        localStorage.removeItem('musinsa-tracker-store');
                                        router.push('/login');
                                    }}
                                >
                                    <span>로그아웃</span>
                                    <ChevronRight size={18} className={styles.arrow} />
                                </button>
                            </div>
                        </section>

                        {isUploadOpen && (
                            <div
                                className={styles.modalOverlay}
                                onClick={() => setIsUploadOpen(false)}
                                role="presentation"
                            >
                                <div
                                    className={styles.modal}
                                    onClick={event => event.stopPropagation()}
                                    role="dialog"
                                    aria-modal="true"
                                    aria-label="사진 올리기"
                                >
                                    <div className={styles.modalHeader}>
                                        <h3>사진 올리기</h3>
                                        <button
                                            className={styles.closeButton}
                                            onClick={() => setIsUploadOpen(false)}
                                            aria-label="닫기"
                                        >
                                            <X size={18} />
                                        </button>
                                    </div>

                                    <div className={styles.guideCard}>
                                        <div className={styles.guideHeader}>
                                            <span className={styles.guideBadge}>촬영 가이드</span>
                                        </div>
                                        <ul className={styles.guideList}>
                                            <li>정면에서 전신으로 찍기</li>
                                            <li>두 팔을 살짝 벌리기</li>
                                        </ul>
                                        <div className={styles.figureWrap}>
                                            <svg
                                                className={styles.stickFigure}
                                                viewBox="0 0 80 120"
                                                role="img"
                                                aria-label="촬영 자세 예시"
                                            >
                                                <circle cx="40" cy="18" r="10" fill="none" stroke="currentColor" strokeWidth="3" />
                                                <line x1="40" y1="28" x2="40" y2="70" stroke="currentColor" strokeWidth="3" />
                                                <line x1="40" y1="40" x2="18" y2="55" stroke="currentColor" strokeWidth="3" />
                                                <line x1="40" y1="40" x2="62" y2="55" stroke="currentColor" strokeWidth="3" />
                                                <line x1="40" y1="70" x2="25" y2="105" stroke="currentColor" strokeWidth="3" />
                                                <line x1="40" y1="70" x2="55" y2="105" stroke="currentColor" strokeWidth="3" />
                                            </svg>
                                        </div>
                                    </div>

                                    <p className={styles.storageNote}>
                                        업로드한 사진은 추천/크롤링 및 3D 모델 생성을 위해 안전하게 저장됩니다.
                                    </p>

                                    {latestPhoto && (
                                        <div className={styles.previewContainer}>
                                            <p className={styles.previewLabel}>최근 저장된 사진</p>
                                            <div className={styles.previewImage}>
                                                <img
                                                    src={`/api/uploads/users/${latestPhoto}`}
                                                    alt="최근 업로드 사진"
                                                />
                                            </div>
                                        </div>
                                    )}

                                    {uploadError && <p className={styles.errorText}>{uploadError}</p>}
                                    {uploadSuccess && <p className={styles.successText}>{uploadSuccess}</p>}

                                    <label
                                        className={`${styles.uploadButton} ${isUploading ? styles.uploadDisabled : ''}`}
                                    >
                                        <Camera size={18} />
                                        {isUploading ? '업로드 중...' : (latestPhoto ? '사진 수정하기' : '사진 선택하기')}
                                        <input
                                            type="file"
                                            hidden
                                            accept="image/*"
                                            onChange={handleUpload}
                                            disabled={isUploading}
                                        />
                                    </label>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </main>

            <BottomNav />
        </div>
    );
}
