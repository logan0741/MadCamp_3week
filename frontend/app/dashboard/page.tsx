'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { productApi, getToken, Product } from '@/lib/api';
import { useStore } from '@/lib/store';
import { Plus } from 'lucide-react';
import ProductCard from '@/components/ProductCard';
import AddProductModal from '@/components/AddProductModal';
import PriceChartModal from '@/components/PriceChartModal';
import TopBar from '@/components/TopBar';
import BottomNav from '@/components/BottomNav';
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
            <TopBar />

<<<<<<< HEAD:frontend/app/dashboard/page.tsx
=======
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
>>>>>>> anti_back:anti/frontend/app/dashboard/page.tsx
            <main className={styles.main}>
                {isLoading ? (
                    <div className={styles.loading}>
                        <div className="spinner" />
                        <p>상품을 불러오는 중...</p>
                    </div>
                ) : (
                    <div className={styles.grid}>
                        {/* Static Add Card as first item */}
                        <div
                            className={styles.addCard}
                            onClick={() => setShowAddModal(true)}
                        >
                            <Plus className={styles.addIcon} strokeWidth={1} />
                            <span className={styles.addText}>추가</span>
                        </div>

                        {/* Product Cards */}
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

            <BottomNav />

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
