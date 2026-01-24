'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { productApi, getToken, Product } from '@/lib/api';
import { useStore } from '@/lib/store';
import ProductCard from '@/components/ProductCard';
import AddProductModal from '@/components/AddProductModal';
import PriceChartModal from '@/components/PriceChartModal';
import styles from './dashboard.module.css';

export default function DashboardPage() {
    const router = useRouter();
    const { user, products, setProducts } = useStore();
    const [isLoading, setIsLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

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

    const handleProductAdded = (product: Product) => {
        setProducts([...products, product]);
        setShowAddModal(false);
    };

    const handleProductRemove = async (productId: number) => {
        try {
            await productApi.remove(productId);
            setProducts(products.filter(p => p.id !== productId));
        } catch (err) {
            console.error('Failed to remove product:', err);
        }
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
                        <Link href="/dashboard" className={styles.navLink + ' ' + styles.active}>
                            관심 상품
                        </Link>
                        <Link href="/fitting" className={styles.navLink}>
                            피팅
                        </Link>
                        <Link href="/mypage" className={styles.navLink}>
                            마이페이지
                        </Link>
                    </nav>
                </div>
            </header>

            {/* Main Content */}
            <main className={styles.main}>
                <div className={styles.titleRow}>
                    <h1>관심 상품</h1>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="btn btn-primary"
                    >
                        + 상품 추가
                    </button>
                </div>

                {isLoading ? (
                    <div className={styles.loading}>
                        <div className="spinner" />
                        <p>상품을 불러오는 중...</p>
                    </div>
                ) : products.length === 0 ? (
                    <div className={styles.empty}>
                        <div className={styles.emptyIcon}>📦</div>
                        <h2>등록된 상품이 없습니다</h2>
                        <p>무신사 상품 URL을 등록하여 가격 추적을 시작하세요!</p>
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="btn btn-primary"
                        >
                            첫 상품 추가하기
                        </button>
                    </div>
                ) : (
                    <div className={styles.productGrid}>
                        {products.map(product => (
                            <ProductCard
                                key={product.id}
                                product={product}
                                onViewChart={() => setSelectedProduct(product)}
                                onRemove={() => handleProductRemove(product.id)}
                            />
                        ))}
                    </div>
                )}
            </main>

            {/* Modals */}
            {showAddModal && (
                <AddProductModal
                    onClose={() => setShowAddModal(false)}
                    onAdd={handleProductAdded}
                />
            )}

            {selectedProduct && (
                <PriceChartModal
                    product={selectedProduct}
                    onClose={() => setSelectedProduct(null)}
                />
            )}
        </div>
    );
}
