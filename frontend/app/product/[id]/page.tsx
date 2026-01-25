'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { productApi, getToken, Product, PriceLog } from '@/lib/api';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import styles from './product.module.css';

export default function ProductDetailPage() {
    const router = useRouter();
    const params = useParams();
    const productId = Number(params.id);

    const [product, setProduct] = useState<Product | null>(null);
    const [history, setHistory] = useState<PriceLog[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const token = getToken();
        if (!token) {
            router.push('/login');
            return;
        }

        loadProductData();
    }, [productId, router]);

    const loadProductData = async () => {
        try {
            // Load all products and find the one we need
            const productsData = await productApi.getAll();
            const foundProduct = productsData.products.find(p => p.id === productId);

            if (!foundProduct) {
                setError('상품을 찾을 수 없습니다.');
                setIsLoading(false);
                return;
            }

            setProduct(foundProduct);

            // Load price history
            const historyData = await productApi.getHistory(productId);
            setHistory(historyData.history);
        } catch (err) {
            console.error('Failed to load product:', err);
            setError('상품 정보를 불러올 수 없습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return `${date.getMonth() + 1}/${date.getDate()}`;
    };

    const formatPrice = (price: number) => {
        return `${price.toLocaleString()}원`;
    };

    const chartData = history.map(log => ({
        date: formatDate(log.captured_at),
        price: log.price,
        discount: log.discount_rate || 0,
    }));

    // Calculate stats
    const prices = history.map(h => h.price);
    const minPrice = prices.length > 0 ? Math.min(...prices) : 0;
    const maxPrice = prices.length > 0 ? Math.max(...prices) : 0;
    const currentPrice = product?.current_price || (prices.length > 0 ? prices[prices.length - 1] : 0);

    if (isLoading) {
        return (
            <div className={styles.page}>
                <div className={styles.loading}>
                    <div className="spinner" />
                    <p>상품 정보를 불러오는 중...</p>
                </div>
            </div>
        );
    }

    if (error || !product) {
        return (
            <div className={styles.page}>
                <div className={styles.error}>
                    <p>{error || '상품을 찾을 수 없습니다.'}</p>
                    <button onClick={() => router.back()} className="btn btn-secondary">
                        돌아가기
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.page}>
            {/* Header */}
            <header className={styles.header}>
                <button onClick={() => router.back()} className={styles.backBtn}>
                    <ArrowLeft size={24} />
                </button>
                <h1 className={styles.headerTitle}>
                    {product.title || `상품 #${product.musinsa_id}`}
                </h1>
            </header>

            {/* Main Content */}
            <main className={styles.main}>
                {/* 3D Avatar Section - Placeholder */}
                <section className={styles.avatarSection}>
                    <div className={styles.avatarPlaceholder}>
                        <div className={styles.avatarIcon}>👤</div>
                        <p className={styles.avatarText}>3D 피팅 뷰</p>
                        <p className={styles.avatarSubtext}>AI 모델 준비 중입니다</p>
                    </div>
                </section>

                {/* Product Info */}
                <section className={styles.productInfo}>
                    {product.thumbnail_url && (
                        <img
                            src={product.thumbnail_url}
                            alt={product.title || '상품 이미지'}
                            className={styles.productImage}
                        />
                    )}
                    <div className={styles.productDetails}>
                        {product.brand && (
                            <span className={styles.brand}>{product.brand}</span>
                        )}
                        <h2 className={styles.productTitle}>
                            {product.title || `상품 #${product.musinsa_id}`}
                        </h2>
                        <div className={styles.priceInfo}>
                            <span className={styles.currentPrice}>
                                {formatPrice(currentPrice)}
                            </span>
                            {product.discount_rate && product.discount_rate > 0 && (
                                <span className={styles.discountBadge}>
                                    {product.discount_rate}% OFF
                                </span>
                            )}
                        </div>
                    </div>
                </section>

                {/* Price Chart Section */}
                <section className={styles.chartSection}>
                    <h3 className={styles.sectionTitle}>📊 가격 추이</h3>

                    {history.length === 0 ? (
                        <div className={styles.emptyChart}>
                            <p>아직 수집된 가격 데이터가 없습니다.</p>
                            <p className={styles.emptyHint}>가격은 매일 자동으로 수집됩니다.</p>
                        </div>
                    ) : (
                        <>
                            <div className={styles.stats}>
                                <div className={styles.statItem}>
                                    <span className={styles.statLabel}>현재가</span>
                                    <span className={styles.statValue}>{formatPrice(currentPrice)}</span>
                                </div>
                                <div className={styles.statItem}>
                                    <span className={styles.statLabel}>최저가</span>
                                    <span className={`${styles.statValue} ${styles.success}`}>{formatPrice(minPrice)}</span>
                                </div>
                                <div className={styles.statItem}>
                                    <span className={styles.statLabel}>최고가</span>
                                    <span className={styles.statValue}>{formatPrice(maxPrice)}</span>
                                </div>
                            </div>

                            <div className={styles.chartContainer}>
                                <ResponsiveContainer width="100%" height={250}>
                                    <AreaChart data={chartData}>
                                        <defs>
                                            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#ff4d00" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="#ff4d00" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                                        <XAxis
                                            dataKey="date"
                                            stroke="#999"
                                            tick={{ fill: '#666', fontSize: 12 }}
                                        />
                                        <YAxis
                                            stroke="#999"
                                            tick={{ fill: '#666', fontSize: 12 }}
                                            tickFormatter={(value) => `${(value / 1000).toFixed(0)}천`}
                                            domain={['dataMin - 5000', 'dataMax + 5000']}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                background: '#fff',
                                                border: '1px solid #eee',
                                                borderRadius: '8px',
                                                color: '#111',
                                            }}
                                            formatter={(value: number) => [formatPrice(value), '가격']}
                                        />
                                        <Area
                                            type="monotone"
                                            dataKey="price"
                                            stroke="#ff4d00"
                                            strokeWidth={2}
                                            fillOpacity={1}
                                            fill="url(#colorPrice)"
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>

                            {minPrice < currentPrice && (
                                <div className={styles.priceAlert}>
                                    💡 이 상품의 역대 최저가는 <strong>{formatPrice(minPrice)}</strong> 입니다.
                                    현재가보다 <strong>{formatPrice(currentPrice - minPrice)}</strong> 저렴했습니다.
                                </div>
                            )}
                        </>
                    )}
                </section>

                {/* Musinsa Link Button */}
                <section className={styles.actionSection}>
                    <a
                        href={product.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.musinsaBtn}
                    >
                        <ExternalLink size={20} />
                        무신사에서 보기
                    </a>
                </section>
            </main>
        </div>
    );
}
