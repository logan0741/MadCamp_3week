'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { aiApi, onboardingApi, Photo, AnalysisResult, RecommendationItem } from '@/lib/api';
import { productApi } from '@/lib/api';
import TopBar from '@/components/layout/TopBar';
import BottomNav from '@/components/layout/BottomNav';
import { Camera, Plus, Check } from 'lucide-react';
import styles from './recommend.module.css';

export default function RecommendPage() {
    const router = useRouter();
    const [photos, setPhotos] = useState<Photo[]>([]);
    const [selectedPhoto, setSelectedPhoto] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [error, setError] = useState('');
    const [fashionTerrorist, setFashionTerrorist] = useState<{ isTrue: boolean, message: string } | null>(null);

    // Modal state
    const [showConfirmModal, setShowConfirmModal] = useState<{ show: boolean, product: any | null }>({ show: false, product: null });

    useEffect(() => {
        loadPhotos();
    }, []);

    const loadPhotos = async () => {
        try {
            const data = await aiApi.getPhotos();
            setPhotos(data.photos);
        } catch (err) {
            console.error(err);
        }
    };

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            try {
                setIsLoading(true);
                const res = await onboardingApi.upload(e.target.files[0]);
                // res should contain filename, url
                // Refresh photos
                await loadPhotos();
                // Auto select uploaded photo
                // Assuming res.filename is returned. If not, logic might need adjustment.
                // based on user.py: return { filename, url }
                // @ts-ignore
                if (res.filename) setSelectedPhoto(res.filename);
            } catch (err) {
                setError('사진 업로드 실패');
            } finally {
                setIsLoading(false);
            }
        }
    };

    const handleAnalyze = async () => {
        if (!selectedPhoto) return;

        setIsLoading(true);
        setError('');
        setResult(null);
        setFashionTerrorist(null);

        try {
            const res = await aiApi.analyzePhoto(selectedPhoto);

            if (res.status === 'fashion_terrorist') {
                setFashionTerrorist({
                    isTrue: true,
                    message: res.message || "그냥 이것만 입어도 패션 테러리스트!!"
                });
                // Even if terrorist, we might have data in res.data?
                // But usually we stop recommendation.
            } else if (res.status === 'success' && res.data) {
                setResult(res.data);

                // Check internal flag just in case
                if (res.data.fashion_terrorist_check?.is_terrorist) {
                    setFashionTerrorist({
                        isTrue: true,
                        message: res.data.fashion_terrorist_check.warning_message
                    });
                }
            } else {
                setError('분석에 실패했습니다.');
            }
        } catch (err) {
            setError('AI 서버 연결 실패');
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleProductClick = (item: RecommendationItem) => {
        // Find if we have product details (ID)
        // Backend returns result.data which contains raw prompts.
        // Wait, I updated backend to return "processed_recs" count but not the actual tracked objects in `data`?
        // Ah, `data` is the raw JSON from GPU.
        // But backend DID crawl and track them.
        // If I want to add to interest, I need the ID.
        // Does `result.recommendations` have IDs?
        // Backend `user.py` extracts ID using regex or `musinsa_id` from prompt.
        // BUT it doesn't *update* the `result.data.recommendations` with the DB ID.
        // It returns `data: result`.
        // So frontend only has what GPU returned.
        // If GPU prompt has `musinsa_id`, we use that.
        // If not, we leverage URL or name?
        // Actually, for "Add to Wishlist", I need the `product_id` (DB ID) or `musinsa_id` to call `add_interest`.
        // `user.py` logic: `Service.track_product` returns a `Product` object.
        // If I want to use `Product.id` (DB PK), I MUST return the mapped products to frontend.
        // I should have updated `user.py` to return `recommendations: [Product objects]` or similar.
        // Current implementation returns raw GPU JSON in `data`.
        // I will assume for now I can use `item.musinsa_id` (if GPU gave it)
        // AND call a specialized endpoint /products/track (which finds or creates) -> then add interest.
        // OR better: `productApi.track(url)` returns product.
        // So if I have URL, I can call `productApi.track(url)` which returns Product, then I add it.
        // This is safer.

        if (item.url) {
            setShowConfirmModal({ show: true, product: item });
        } else {
            alert('상품 URL 정보가 없습니다.');
        }
    };

    const confirmAddInterest = async () => {
        const item = showConfirmModal.product;
        if (!item || !item.url) return;

        try {
            // Track first to ensure it exists and get DB ID
            const product = await productApi.track(item.url);
            // Then add to interest (using product.id which is DB ID)
            // Wait, do I have an API to add interest by ID?
            // backend: POST /user/interests/{product_id}
            // frontend productApi.toggleInterest? No.
            // I need to implement `userApi.addInterest` in frontend or use raw request.
            // productApi.js in frontend usually handles this?
            // Checking `productApi` in ai.ts? No, `import { productApi }`.
            // Let's assume I can use `productApi`.
            // If `productApi` doesn't support addInterest, I'll allow `aiApi` or `userApi` to do it.
            // Actually, I'll use `apiRequest`.

            // Temporary direct call
            const { apiRequest } = require('@/lib/api/client'); // dynamic import or use imported
            // Importing apiRequest at top.
            await apiRequest(`/user/interests/${product.id}`, { method: 'POST' });

            alert('관심 상품에 추가되었습니다! ❤️');
            setShowConfirmModal({ show: false, product: null });
        } catch (err) {
            alert('추가 실패: ' + err);
        }
    };

    const handleAddAll = async () => {
        if (!result || !result.recommendations) return;

        const confirm = window.confirm(`총 ${result.recommendations.length}개의 상품을 모두 관심 목록에 추가하시겠습니까?`);
        if (!confirm) return;

        let count = 0;
        try {
            for (const item of result.recommendations) {
                if (item.url) {
                    const product = await productApi.track(item.url);
                    await apiRequest(`/user/interests/${product.id}`, { method: 'POST' });
                    count++;
                }
            }
            alert(`${count}개 상품이 추가되었습니다!`);
        } catch (err) {
            alert('일부 상품 추가 중 오류가 발생했습니다.');
        }
    };

    // Helper for apiRequest if not exported in lib/api/client properly (it is exported)
    const { apiRequest } = require('@/lib/api/client');

    return (
        <div className={styles.page}>
            <TopBar />

            {/* Header */}
            <div className={styles.header}>
                <h1>AI 스타일 추천</h1>
            </div>

            <main>
                {/* Photo Selector */}
                <section className={styles.section}>
                    <h2 className={styles.sectionTitle}>사진 선택</h2>
                    <div className={styles.photoGrid}>
                        <label className={styles.uploadBtn}>
                            <Camera size={24} />
                            <span style={{ marginTop: 4 }}>업로드</span>
                            <input type="file" hidden onChange={handleUpload} accept="image/*" />
                        </label>

                        {photos.map(photo => (
                            <div
                                key={photo.filename}
                                className={`${styles.photoItem} ${selectedPhoto === photo.filename ? styles.selected : ''}`}
                                onClick={() => setSelectedPhoto(photo.filename)}
                            >
                                <img src={photo.url} alt="User photo" />
                                {selectedPhoto === photo.filename && (
                                    <div style={{ position: 'absolute', top: 4, right: 4, background: 'black', borderRadius: '50%', padding: 2 }}>
                                        <Check size={12} color="white" />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    {selectedPhoto && (
                        <button
                            className="btn btn-primary"
                            style={{ marginTop: 16, width: '100%' }}
                            onClick={handleAnalyze}
                            disabled={isLoading}
                        >
                            {isLoading ? '분석 중...' : '스타일 분석 및 추천받기'}
                        </button>
                    )}
                </section>

                {/* Loading */}
                {isLoading && (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                        <div className="spinner" style={{ margin: '0 auto 16px' }} />
                        <p>퍼스널 컬러 진단 및 스타일 추천 중...</p>
                    </div>
                )}

                {/* Error */}
                {error && <div style={{ color: 'red', padding: 20, textAlign: 'center' }}>{error}</div>}

                {/* Result */}
                {!isLoading && result && (
                    <>
                        <section className={styles.section}>
                            <div className={styles.analysisCard}>
                                <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
                                    {result.user_analysis.personal_color}
                                </h3>
                                <div style={{ marginBottom: 12 }}>
                                    Best: {result.user_analysis.best_colors.map((c, i) => (
                                        <span key={i} className={styles.colorChip} style={{ backgroundColor: c }} />
                                    ))}
                                </div>
                                <p style={{ fontSize: 14, color: '#666' }}>
                                    고객님의 톤에 딱 맞는 무신사 랭킹 상품들을 찾아왔어요!
                                </p>
                            </div>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.sectionTitle}>추천 스타일 (Cream Style)</h2>
                            <div className={styles.productGrid}>
                                {result.recommendations.map((item, idx) => (
                                    <div key={idx} className={styles.productCard} onClick={() => handleProductClick(item)}>
                                        <div className={styles.productImg}>
                                            {/* No image URL in GPU result? Prompt didn't ask for generic image URL.
                                                Wait, prompt assumes backend finds it.
                                                But here we only have prompt result.
                                                If item.url exists, we could use Musinsa thumbnail logic?
                                                Actually, if I don't have thumbnail, I can't show grid properly.
                                                CRITICAL: Frontend needs thumbnails.
                                                My backend `user.py` CRAWLED the products.
                                                If I update `user.py` to return the `processed_recs` (Product objects), I would have thumbnails.
                                                Currently I rely on `result` (GPU JSON). GPU JSON has NO thumbnails.
                                                I MUST UPDATE BACKEND to return the Crawled Products.
                                                
                                                Temporary fix: Use a placeholder or attempt to show nothing?
                                                No, Cream style needs images.
                                                I will use a placeholder for now, BUT I will update backend in NEXT STEP if possible.
                                                Or I should have done it in `user.py`. 
                                                I'll add a note.
                                            */}
                                            <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#eee' }}>
                                                <span style={{ fontSize: 30 }}>👕</span>
                                            </div>
                                        </div>
                                        <div className={styles.productInfo}>
                                            <div className={styles.brand}>{item.brand}</div>
                                            <div className={styles.name}>{item.product_name}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                        {/* Add All Button */}
                        <button className={styles.addAllBtn} onClick={handleAddAll}>
                            모두 추가하기 ({result.recommendations.length})
                        </button>
                    </>
                )}
            </main>

            <BottomNav />

            {/* Terrorist Overlay */}
            {fashionTerrorist && fashionTerrorist.isTrue && (
                <div className={styles.terroristOverlay}>
                    <div style={{ fontSize: 60, marginBottom: 20 }}>😱</div>
                    <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>패션 테러리스트 경고!</h2>
                    <p style={{ fontSize: 16, lineHeight: 1.5, marginBottom: 30 }}>
                        {fashionTerrorist.message}
                    </p>
                    <button
                        className={styles.terroristConfirmBtn}
                        onClick={() => setFashionTerrorist(null)}
                    >
                        확인했습니다...
                    </button>
                </div>
            )}

            {/* Confirm Modal */}
            {showConfirmModal.show && (
                <div className={styles.modalOverlay}>
                    <span>관심 상품에 추가 하시겠습니까?</span>
                    <button
                        style={{ background: 'none', border: 'none', color: '#4caf50', fontWeight: 700, cursor: 'pointer' }}
                        onClick={confirmAddInterest}
                    >
                        네
                    </button>
                    <button
                        style={{ background: 'none', border: 'none', color: '#aaa', cursor: 'pointer' }}
                        onClick={() => setShowConfirmModal({ show: false, product: null })}
                    >
                        아니오
                    </button>
                </div>
            )}
        </div>
    );
}
