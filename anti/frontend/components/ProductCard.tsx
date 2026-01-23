'use client';

import { Product } from '@/lib/api';
import styles from './ProductCard.module.css';

interface ProductCardProps {
    product: Product;
    onViewChart: () => void;
    onRemove: () => void;
}

export default function ProductCard({ product, onViewChart, onRemove }: ProductCardProps) {
    const formatPrice = (price: number | null) => {
        if (!price) return '가격 정보 없음';
        return `${price.toLocaleString()}원`;
    };

    return (
        <div className={styles.card}>
            <div className={styles.imageContainer}>
                {product.thumbnail_url ? (
                    <img
                        src={product.thumbnail_url}
                        alt={product.title || '상품 이미지'}
                        className={styles.image}
                    />
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
                    <span className={styles.price}>
                        {formatPrice(product.current_price)}
                    </span>
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
