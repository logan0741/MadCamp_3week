'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { userApi, productApi, getToken, Product } from '@/lib/api';
import { useStore } from '@/lib/store';
import BottomNav from '@/components/layout/BottomNav';
import { User, Heart, Bell, Tag, ChevronRight } from 'lucide-react';
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
    const [recentProducts, setRecentProducts] = useState<Product[]>([]);

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

            // Get recent products (최근 3개)
            setRecentProducts(allProducts.slice(0, 3));
        } catch (err) {
            console.error('Failed to load data:', err);
        } finally {
            setIsLoading(false);
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

                        {/* Recent Wishlist Preview */}
                        {recentProducts.length > 0 && (
                            <section className={styles.recentSection}>
                                <div className={styles.sectionHeader}>
                                    <h2 className={styles.sectionTitle}>최근 등록 상품</h2>
                                    <Link href="/dashboard" className={styles.viewAll}>
                                        전체보기 <ChevronRight size={16} />
                                    </Link>
                                </div>
                                <div className={styles.recentGrid}>
                                    {recentProducts.map(product => (
                                        <Link
                                            key={product.id}
                                            href={`/product/${product.id}`}
                                            className={styles.recentCard}
                                        >
                                            <div className={styles.recentImage}>
                                                {product.thumbnail_url ? (
                                                    <img src={product.thumbnail_url} alt={product.title || ''} />
                                                ) : (
                                                    <div className={styles.placeholder}>👕</div>
                                                )}
                                            </div>
                                            <div className={styles.recentInfo}>
                                                <span className={styles.recentBrand}>{product.brand}</span>
                                                <span className={styles.recentPrice}>
                                                    {product.current_price?.toLocaleString()}원
                                                </span>
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            </section>
                        )}

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
                    </>
                )}
            </main>

            <BottomNav />
        </div>
    );
}
