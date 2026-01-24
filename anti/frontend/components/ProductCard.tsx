'use client';

import { useState, useEffect } from 'react';
import { Product } from '@/lib/api';
import styles from './ProductCard.module.css';

interface ProductCardProps {
    product: Product;
    onViewChart: () => void;
    onRemove: () => void;
}

export default function ProductCard({ product, onViewChart, onRemove }: ProductCardProps) {
    const [currentImageIndex, setCurrentImageIndex] = useState(0);

    // Image carousel - rotate every 3 seconds
    useEffect(() => {
        const images = product.image_urls || [];
        if (images.length <= 1) return;

        const timer = setInterval(() => {
            setCurrentImageIndex(prev => (prev + 1) % images.length);
        }, 3000);

        return () => clearInterval(timer);
    }, [product.image_urls]);

    const formatPrice = (price: number | null) => {
        if (!price) return '가격 정보 없음';
        return `${price.toLocaleString()}원`;
    };

    const images = product.image_urls || [];
    const currentImage = images[currentImageIndex] || product.thumbnail_url;
    const hasDiscount = product.original_price && product.current_price &&
        product.original_price > product.current_price;

    return (
        <div className={styles.card}>
            <div className={styles.imageContainer}>
                {currentImage ? (
                    <>
                        <img
                            src={currentImage}
                            alt={product.title || '상품 이미지'}
                            className={styles.image}
                        />
                        {/* Image carousel indicators */}
                        {images.length > 1 && (
                            <div className={styles.indicators}>
                                {images.map((_, idx) => (
                                    <span
                                        key={idx}
                                        className={`${styles.indicator} ${idx === currentImageIndex ? styles.active : ''}`}
                                        onClick={() => setCurrentImageIndex(idx)}
                                    />
                                ))}
                            </div>
                        )}
                    </>
                ) : (
                    <div className={styles.placeholder}>
                        <span>🛍️</span>
                    </div>
                )}

                {product.discount_rate && product.discount_rate > 0 && (
                    <div className={styles.discountBadge}>
                        {product.discount_rate}% OFF
                    </div>
                )}

                <button
                    onClick={onRemove}
                    className={styles.removeBtn}
                    title="삭제"
                >
                    ×
                </button>
            </div>

            <div className={styles.content}>
                {product.brand && (
                    <span className={styles.brand}>{product.brand}</span>
                )}

                <h3 className={styles.title}>
                    {product.title || `상품 #${product.musinsa_id}`}
                </h3>

                <div className={styles.priceRow}>
                    {hasDiscount && (
                        <span className={styles.originalPrice}>
                            {formatPrice(product.original_price)}
                        </span>
                    )}
                    <span className={styles.price}>
                        {formatPrice(product.current_price)}
                    </span>
                    {hasDiscount && (
                        <span className={styles.discount}>
                            {formatPrice((product.original_price || 0) - (product.current_price || 0))} 할인
                        </span>
                    )}
                </div>

                <div className={styles.actions}>
                    <button
                        onClick={onViewChart}
                        className={styles.chartBtn}
                    >
                        📊 가격 추이
                    </button>

                    <a
                        href={product.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.linkBtn}
                    >
                        무신사 →
                    </a>
                </div>

                {product.is_garment_modeled && (
                    <div className={styles.modeledBadge}>
                        ✓ 3D 모델링 완료
                    </div>
                )}
            </div>
        </div>
    );
}

