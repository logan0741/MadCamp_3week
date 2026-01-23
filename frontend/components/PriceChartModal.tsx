'use client';

import { useState, useEffect } from 'react';
import { productApi, Product, PriceLog } from '@/lib/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import styles from './PriceChartModal.module.css';

interface PriceChartModalProps {
    product: Product;
    onClose: () => void;
}

export default function PriceChartModal({ product, onClose }: PriceChartModalProps) {
    const [history, setHistory] = useState<PriceLog[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        loadHistory();
    }, [product.id]);

    const loadHistory = async () => {
        try {
            const data = await productApi.getHistory(product.id);
            setHistory(data.history);
        } catch (err) {
            setError('가격 히스토리를 불러올 수 없습니다.');
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
    const currentPrice = prices.length > 0 ? prices[prices.length - 1] : 0;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className={`modal-content ${styles.chartModal}`} onClick={e => e.stopPropagation()}>
                <div className={styles.header}>
                    <div>
                        <h2>{product.title || '상품 가격 추이'}</h2>
                        {product.brand && <span className={styles.brand}>{product.brand}</span>}
                    </div>
                    <button onClick={onClose} className={styles.closeBtn}>×</button>
                </div>

                {isLoading ? (
                    <div className={styles.loading}>
                        <div className="spinner" />
                        <p>데이터를 불러오는 중...</p>
                    </div>
                ) : error ? (
                    <div className={styles.error}>{error}</div>
                ) : history.length === 0 ? (
                    <div className={styles.empty}>
                        <p>아직 수집된 가격 데이터가 없습니다.</p>
                        <p className={styles.emptyHint}>가격은 매일 자동으로 수집됩니다.</p>
                    </div>
                ) : (
                    <>
                        <div className={styles.stats}>
                            <div className={styles.statItem}>
                                <span className={styles.statLabel}>현재 가격</span>
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
                            <ResponsiveContainer width="100%" height={300}>
                                <AreaChart data={chartData}>
                                    <defs>
                                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#ff4d00" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#ff4d00" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#2a2a35" />
                                    <XAxis
                                        dataKey="date"
                                        stroke="#6b6b7b"
                                        tick={{ fill: '#a0a0b0', fontSize: 12 }}
                                    />
                                    <YAxis
                                        stroke="#6b6b7b"
                                        tick={{ fill: '#a0a0b0', fontSize: 12 }}
                                        tickFormatter={(value) => `${(value / 1000).toFixed(0)}천`}
                                        domain={['dataMin - 5000', 'dataMax + 5000']}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            background: '#16161f',
                                            border: '1px solid #2a2a35',
                                            borderRadius: '8px',
                                            color: '#fff',
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
                            <div className={styles.alert}>
                                💡 이 상품의 역대 최저가는 <strong>{formatPrice(minPrice)}</strong> 입니다.
                                현재가보다 <strong>{formatPrice(currentPrice - minPrice)}</strong> 저렴했습니다.
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
