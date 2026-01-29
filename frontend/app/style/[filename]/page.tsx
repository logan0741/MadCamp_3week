'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, aiApi } from '@/lib/api';
import type { Photo, AnalysisResult, RecommendationItem, Product } from '@/lib/api';
import BottomNav from '@/components/layout/BottomNav';
import styles from './style-detail.module.css';

type StyleDetailProps = {
    params: { filename: string };
};

export default function StyleDetailPage({ params }: StyleDetailProps) {
    const router = useRouter();
    const filename = useMemo(() => decodeURIComponent(params.filename), [params.filename]);
    const [photo, setPhoto] = useState<Photo | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
    const [trackedProducts, setTrackedProducts] = useState<Product[]>([]);
    const [analysisError, setAnalysisError] = useState<string | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [terroristMessage, setTerroristMessage] = useState<string | null>(null);

    const recommendationLookup = useMemo(() => {
        const map = new Map<string, RecommendationItem>();
        if (!analysis?.recommendations) return map;
        analysis.recommendations.forEach((item) => {
            if (item.musinsa_id) {
                map.set(String(item.musinsa_id), item);
            }
        });
        return map;
    }, [analysis]);

    useEffect(() => {
        const token = getToken();
        if (!token) {
            router.push('/login');
            return;
        }

        const loadPhoto = async () => {
            try {
                const data = await aiApi.getPhotos('daily');
                const match = data.photos?.find(item => item.filename === filename);
                setPhoto(match || null);
            } catch (err) {
                console.error('Failed to load photo detail:', err);
            } finally {
                setIsLoading(false);
            }
        };

        loadPhoto();
    }, [filename, router]);

    useEffect(() => {
        const token = getToken();
        if (!token) {
            return;
        }

        const loadAnalysis = async () => {
            setIsAnalyzing(true);
            setAnalysisError(null);
            setTerroristMessage(null);
            setAnalysis(null);
            setTrackedProducts([]);
            try {
                const response = await aiApi.analyzePhoto(filename);

                if (response.status === 'error') {
                    setAnalysisError(response.message || '분석에 실패했습니다.');
                    setAnalysis(null);
                    setTrackedProducts([]);
                    return;
                }

                if (response.status === 'fashion_terrorist') {
                    setTerroristMessage(response.message || '패션 테러리스트 경고!');
                }

                if (response.data) {
                    setAnalysis(response.data);
                    if (response.data.fashion_terrorist_check?.is_terrorist) {
                        setTerroristMessage(response.data.fashion_terrorist_check.warning_message);
                    }
                } else {
                    setAnalysis(null);
                }

                setTrackedProducts(response.tracked_products || []);
            } catch (err) {
                const message = err instanceof Error ? err.message : '분석에 실패했습니다.';
                setAnalysisError(message);
            } finally {
                setIsAnalyzing(false);
            }
        };

        loadAnalysis();
    }, [filename]);

    return (
        <div className={styles.page}>
            <main className={styles.main}>
                <header className={styles.header}>
                    <button className={styles.backBtn} onClick={() => router.back()}>
                        ← 뒤로
                    </button>
                    <h1 className={styles.title}>스타일 분석</h1>
                </header>

                {isLoading ? (
                    <div className={styles.loading}>
                        <div className="spinner" />
                        <p>로딩 중...</p>
                    </div>
                ) : (
                    <>
                        <section className={styles.photoSection}>
                            {photo ? (
                                <img src={photo.url} alt="Daily look" className={styles.photo} />
                            ) : (
                                <div className={styles.photoPlaceholder}>사진을 불러오지 못했습니다.</div>
                            )}
                        </section>

                        <section className={styles.analysisSection}>
                            <h2 className={styles.sectionTitle}>AI 분석 결과</h2>
                            {isAnalyzing && (
                                <div className={styles.analysisState}>
                                    <div className="spinner" />
                                    <p>분석 중...</p>
                                </div>
                            )}

                            {analysisError && (
                                <div className={styles.errorCard}>
                                    {analysisError}
                                </div>
                            )}

                            {!isAnalyzing && !analysisError && analysis && (
                                <>
                                    <div className={styles.summaryCard}>
                                        <div className={styles.summaryHeader}>
                                            <div>
                                                <p className={styles.summaryLabel}>퍼스널 컬러</p>
                                                <p className={styles.summaryValue}>{analysis.user_analysis.personal_color}</p>
                                            </div>
                                            <div className={styles.skinTone}>
                                                <span
                                                    className={styles.skinSwatch}
                                                    style={{ background: analysis.user_analysis.skin_tone_hex || '#ddd' }}
                                                />
                                                <span className={styles.skinHex}>
                                                    {analysis.user_analysis.skin_tone_hex}
                                                </span>
                                            </div>
                                        </div>

                                        <div className={styles.colorGroup}>
                                            <p className={styles.groupLabel}>어울리는 컬러</p>
                                            <div className={styles.chipRow}>
                                                {analysis.user_analysis.best_colors.map((color) => (
                                                    <span
                                                        key={color}
                                                        className={styles.colorChip}
                                                        style={{ background: color }}
                                                        title={color}
                                                    />
                                                ))}
                                            </div>
                                        </div>

                                        <div className={styles.colorGroup}>
                                            <p className={styles.groupLabel}>피해야 할 컬러</p>
                                            <div className={styles.chipRow}>
                                                {analysis.user_analysis.worst_colors.map((color) => (
                                                    <span
                                                        key={color}
                                                        className={styles.colorChip}
                                                        style={{ background: color }}
                                                        title={color}
                                                    />
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    {terroristMessage && (
                                        <div className={styles.warningCard}>
                                            <p className={styles.warningTitle}>패션 테러리스트 경고</p>
                                            <p className={styles.warningText}>{terroristMessage}</p>
                                        </div>
                                    )}

                                    <div className={styles.recommendSection}>
                                        <h3 className={styles.subTitle}>추천 상품</h3>

                                        {terroristMessage ? (
                                            <div className={styles.emptyState}>
                                                추천이 제한되었습니다. 사진을 다시 촬영해 주세요.
                                            </div>
                                        ) : trackedProducts.length > 0 ? (
                                            <div className={styles.productGrid}>
                                                {trackedProducts.map((product) => {
                                                    const rec = recommendationLookup.get(String(product.musinsa_id));
                                                    const price = product.current_price
                                                        ? `${product.current_price.toLocaleString()}원`
                                                        : '가격 정보 없음';

                                                    return (
                                                        <button
                                                            key={product.id}
                                                            type="button"
                                                            className={styles.productCard}
                                                            onClick={() => router.push(`/product/${product.id}`)}
                                                        >
                                                            <div className={styles.productImage}>
                                                                {product.thumbnail_url ? (
                                                                    <img src={product.thumbnail_url} alt={product.title || '추천 상품'} />
                                                                ) : (
                                                                    <div className={styles.imagePlaceholder}>🛍️</div>
                                                                )}
                                                            </div>
                                                            <div className={styles.productInfo}>
                                                                <span className={styles.productBrand}>{product.brand || '브랜드'}</span>
                                                                <p className={styles.productTitle}>{product.title || product.musinsa_id}</p>
                                                                {(rec?.category || rec?.color) && (
                                                                    <p className={styles.productMeta}>
                                                                        {[rec?.category, rec?.color].filter(Boolean).join(' · ')}
                                                                    </p>
                                                                )}
                                                                <p className={styles.productPrice}>{price}</p>
                                                                {rec?.reason && (
                                                                    <p className={styles.productReason}>{rec.reason}</p>
                                                                )}
                                                            </div>
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        ) : analysis.recommendations.length > 0 ? (
                                            <div className={styles.recommendList}>
                                                {analysis.recommendations.map((item, index) => (
                                                    <div key={`${item.category}-${index}`} className={styles.recommendItem}>
                                                        <div className={styles.recommendHeader}>
                                                            <span className={styles.recommendCategory}>{item.category}</span>
                                                            <span className={styles.recommendBrand}>{item.brand}</span>
                                                        </div>
                                                        <p className={styles.recommendName}>{item.product_name}</p>
                                                        <p className={styles.recommendMeta}>{item.color}</p>
                                                        <p className={styles.recommendReason}>{item.reason}</p>
                                                        {item.url && (
                                                            <a
                                                                className={styles.recommendLink}
                                                                href={item.url}
                                                                target="_blank"
                                                                rel="noreferrer"
                                                            >
                                                                무신사에서 보기
                                                            </a>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <div className={styles.emptyState}>
                                                추천 결과가 없습니다.
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}

                            {!isAnalyzing && !analysisError && !analysis && (
                                <div className={styles.emptyState}>
                                    분석 결과가 없습니다.
                                </div>
                            )}
                        </section>
                    </>
                )}
            </main>

            <BottomNav />
        </div>
    );
}
