'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Unity, useUnityContext } from 'react-unity-webgl';
import { productApi, aiApi, getToken, Product, AITaskResponse } from '@/lib/api';
import { useStore } from '@/lib/store';
import styles from './fitting.module.css';

export default function FittingPage() {
    const router = useRouter();
    const { user, products, setProducts } = useStore();
    const [isLoading, setIsLoading] = useState(true);
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
    const [fittingTask, setFittingTask] = useState<AITaskResponse | null>(null);
    const [error, setError] = useState('');

    // Unity WebGL Context
    const { unityProvider, isLoaded, loadingProgression, sendMessage } = useUnityContext({
        loaderUrl: '/unity/Build/Build.loader.js',
        dataUrl: '/unity/Build/Build.data',
        frameworkUrl: '/unity/Build/Build.framework.js',
        codeUrl: '/unity/Build/Build.wasm',
    });

    useEffect(() => {
        const token = getToken();
        if (!token) {
            router.push('/login');
            return;
        }
        loadProducts();
    }, [router]);

    const loadProducts = async () => {
        try {
            const data = await productApi.getAll();
            setProducts(data.products);
        } catch (err) {
            console.error('Failed to load products:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleProductSelect = (product: Product) => {
        setSelectedProduct(product);
        setFittingTask(null);
        setError('');
    };

    const handleRequestFitting = async () => {
        if (!selectedProduct) return;

        if (!user?.is_avatar_created) {
            setError('먼저 아바타를 생성해주세요.');
            return;
        }

        try {
            setError('');
            const task = await aiApi.requestFitting(selectedProduct.id);
            setFittingTask(task);

            // If completed, send to Unity
            if (task.status === 'COMPLETED' && task.result_url) {
                sendMessage('AvatarManager', 'LoadGarment', task.result_url);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : '피팅 요청에 실패했습니다.');
        }
    };

    const formatPrice = (price: number | null) => {
        if (!price) return '-';
        return `${price.toLocaleString()}원`;
    };

    return (
        <div className={styles.page}>
            {/* Header */}
            <header className={styles.header}>
                <div className={styles.headerContent}>
                    <Link href="/dashboard" className={styles.logo}>
                        <div className={styles.logoIcon}>M</div>
                        <span>MUSINSA<strong>Tracker</strong></span>
                    </Link>

                    <nav className={styles.nav}>
                        <Link href="/dashboard" className={styles.navLink}>
                            관심 상품
                        </Link>
                        <Link href="/fitting" className={`${styles.navLink} ${styles.active}`}>
                            피팅
                        </Link>
                        <Link href="/mypage" className={styles.navLink}>
                            마이페이지
                        </Link>
                    </nav>
                </div>
            </header>

            <main className={styles.main}>
                {/* Product Sidebar */}
                <aside className={styles.sidebar}>
                    <h2>관심 상품</h2>

                    {isLoading ? (
                        <div className={styles.loading}>
                            <div className="spinner" />
                        </div>
                    ) : products.length === 0 ? (
                        <div className={styles.empty}>
                            <p>등록된 상품이 없습니다.</p>
                            <Link href="/dashboard" className={styles.addLink}>
                                상품 추가하기 →
                            </Link>
                        </div>
                    ) : (
                        <div className={styles.productList}>
                            {products.map(product => (
                                <div
                                    key={product.id}
                                    className={`${styles.productItem} ${selectedProduct?.id === product.id ? styles.selected : ''}`}
                                    onClick={() => handleProductSelect(product)}
                                >
                                    <div className={styles.productThumb}>
                                        {product.thumbnail_url ? (
                                            <img src={product.thumbnail_url} alt={product.title || ''} />
                                        ) : (
                                            <span>🛍️</span>
                                        )}
                                    </div>
                                    <div className={styles.productInfo}>
                                        <span className={styles.productBrand}>{product.brand}</span>
                                        <span className={styles.productTitle}>
                                            {product.title || `상품 #${product.musinsa_id}`}
                                        </span>
                                        <span className={styles.productPrice}>
                                            {formatPrice(product.current_price)}
                                        </span>
                                    </div>
                                    {product.is_garment_modeled && (
                                        <span className={styles.modeledBadge}>3D</span>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </aside>

                {/* Unity Viewer */}
                <div className={styles.viewerContainer}>
                    <div className={styles.viewer}>
                        {!user?.is_avatar_created ? (
                            <div className={styles.noAvatar}>
                                <span className={styles.avatarPlaceholder}>👤</span>
                                <h3>아바타가 필요합니다</h3>
                                <p>가상 피팅을 위해 먼저 아바타를 생성해주세요.</p>
                                <Link href="/onboarding" className="btn btn-primary">
                                    아바타 생성하기
                                </Link>
                            </div>
                        ) : (
                            <>
                                {!isLoaded && (
                                    <div className={styles.unityLoading}>
                                        <div className="spinner" />
                                        <p>3D 뷰어 로딩 중... {Math.round(loadingProgression * 100)}%</p>
                                    </div>
                                )}
                                <Unity
                                    unityProvider={unityProvider}
                                    className={styles.unityCanvas}
                                    style={{ visibility: isLoaded ? 'visible' : 'hidden' }}
                                />
                            </>
                        )}
                    </div>

                    {/* Fitting Controls */}
                    <div className={styles.controls}>
                        {selectedProduct ? (
                            <>
                                <div className={styles.selectedInfo}>
                                    <h3>{selectedProduct.title}</h3>
                                    <div className={styles.priceInfo}>
                                        {selectedProduct.original_price && selectedProduct.original_price > (selectedProduct.current_price || 0) && (
                                            <span className={styles.originalPrice}>
                                                {formatPrice(selectedProduct.original_price)}
                                            </span>
                                        )}
                                        <span className={styles.currentPrice}>
                                            {formatPrice(selectedProduct.current_price)}
                                        </span>
                                        {selectedProduct.discount_rate && selectedProduct.discount_rate > 0 && (
                                            <span className={styles.discountBadge}>
                                                {selectedProduct.discount_rate}% OFF
                                            </span>
                                        )}
                                    </div>
                                </div>

                                {fittingTask ? (
                                    <div className={styles.taskStatus}>
                                        {fittingTask.status === 'PENDING' && (
                                            <span className={styles.pending}>⏳ 대기 중...</span>
                                        )}
                                        {fittingTask.status === 'PROCESSING' && (
                                            <span className={styles.processing}>🔄 3D 모델링 중...</span>
                                        )}
                                        {fittingTask.status === 'COMPLETED' && (
                                            <span className={styles.completed}>✅ 피팅 완료!</span>
                                        )}
                                        {fittingTask.status === 'FAILED' && (
                                            <span className={styles.failed}>❌ 실패: {fittingTask.error_message}</span>
                                        )}
                                    </div>
                                ) : (
                                    <button
                                        onClick={handleRequestFitting}
                                        className="btn btn-primary"
                                        disabled={!user?.is_avatar_created}
                                    >
                                        🎽 피팅하기
                                    </button>
                                )}

                                {error && <div className={styles.error}>{error}</div>}
                            </>
                        ) : (
                            <div className={styles.selectPrompt}>
                                <p>👈 왼쪽에서 상품을 선택하세요</p>
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}
