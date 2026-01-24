'use client';

import { useState } from 'react';
import { productApi, Product } from '@/lib/api';
import styles from './AddProductModal.module.css';

interface AddProductModalProps {
    onClose: () => void;
    onAdd: (product: Product) => void;
}

export default function AddProductModal({ onClose, onAdd }: AddProductModalProps) {
    const [url, setUrl] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        // Allow musinsa.com URLs and OneLink share URLs
        const isValidUrl = url.includes('musinsa.com') ||
            url.includes('musinsa.onelink.me') ||
            url.includes('musinsa.app.link') ||
            url.includes('onelink.me');

        if (!isValidUrl) {
            setError('유효한 무신사 URL 또는 공유 링크를 입력해주세요.');
            return;
        }

        setIsLoading(true);

        try {
            const product = await productApi.track(url);
            onAdd(product);
        } catch (err) {
            setError(err instanceof Error ? err.message : '상품 등록에 실패했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className={styles.header}>
                    <h2>상품 추가</h2>
                    <button onClick={onClose} className={styles.closeBtn}>×</button>
                </div>

                <p className={styles.description}>
                    무신사에서 관심 있는 상품의 URL을 붙여넣기 해주세요.<br />
                    가격 변동을 추적하고 알림을 받을 수 있습니다.
                </p>

                <form onSubmit={handleSubmit}>
                    <div className="input-group">
                        <label className="input-label">무신사 상품 URL 또는 공유 링크</label>
                        <input
                            type="url"
                            className="input"
                            placeholder="URL 또는 공유 링크 붙여넣기"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            required
                        />
                    </div>

                    {error && <div className={styles.error}>{error}</div>}

                    <div className={styles.actions}>
                        <button
                            type="button"
                            onClick={onClose}
                            className="btn btn-secondary"
                        >
                            취소
                        </button>
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={isLoading}
                        >
                            {isLoading ? <span className="spinner" /> : '추가하기'}
                        </button>
                    </div>
                </form>

                <div className={styles.help}>
                    <strong>💡 Tip</strong>
                    <p>무신사 앱에서 상품을 보고 &apos;공유&apos; 버튼을 눌러 URL을 복사할 수 있습니다.</p>
                </div>
            </div>
        </div>
    );
}
