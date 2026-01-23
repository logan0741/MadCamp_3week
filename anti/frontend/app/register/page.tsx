'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authApi, setToken } from '@/lib/api';
import { useStore } from '@/lib/store';
import styles from '../login/login.module.css';

export default function RegisterPage() {
    const router = useRouter();
    const { setUser } = useStore();
    const [formData, setFormData] = useState({
        username: '',
        password: '',
        confirmPassword: '',
        height: '',
        weight: '',
    });
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (formData.password !== formData.confirmPassword) {
            setError('비밀번호가 일치하지 않습니다.');
            return;
        }

        if (formData.password.length < 6) {
            setError('비밀번호는 최소 6자 이상이어야 합니다.');
            return;
        }

        setIsLoading(true);

        try {
            const user = await authApi.register({
                username: formData.username,
                password: formData.password,
                height: formData.height ? parseFloat(formData.height) : undefined,
                weight: formData.weight ? parseFloat(formData.weight) : undefined,
            });

            // Auto login after registration
            const { access_token } = await authApi.login(formData.username, formData.password);
            setToken(access_token);
            setUser(user);

            // New user always goes to onboarding
            router.push('/onboarding');
        } catch (err) {
            setError(err instanceof Error ? err.message : '회원가입에 실패했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.loginBox}>
                {/* Logo */}
                <div className={styles.logo}>
                    <div className={styles.logoIcon}>M</div>
                    <h1>MUSINSA<span>Tracker</span></h1>
                </div>

                <p className={styles.subtitle}>회원가입</p>

                <form onSubmit={handleSubmit} className={styles.form}>
                    <div className="input-group">
                        <label className="input-label">아이디 *</label>
                        <input
                            type="text"
                            name="username"
                            className="input"
                            placeholder="아이디를 입력하세요"
                            value={formData.username}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label className="input-label">비밀번호 *</label>
                        <input
                            type="password"
                            name="password"
                            className="input"
                            placeholder="비밀번호 (최소 6자)"
                            value={formData.password}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label className="input-label">비밀번호 확인 *</label>
                        <input
                            type="password"
                            name="confirmPassword"
                            className="input"
                            placeholder="비밀번호를 다시 입력하세요"
                            value={formData.confirmPassword}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div style={{ display: 'flex', gap: 'var(--space-md)' }}>
                        <div className="input-group" style={{ flex: 1 }}>
                            <label className="input-label">키 (cm)</label>
                            <input
                                type="number"
                                name="height"
                                className="input"
                                placeholder="170"
                                value={formData.height}
                                onChange={handleChange}
                            />
                        </div>
                        <div className="input-group" style={{ flex: 1 }}>
                            <label className="input-label">몸무게 (kg)</label>
                            <input
                                type="number"
                                name="weight"
                                className="input"
                                placeholder="65"
                                value={formData.weight}
                                onChange={handleChange}
                            />
                        </div>
                    </div>

                    {error && <div className={styles.error}>{error}</div>}

                    <button
                        type="submit"
                        className="btn btn-primary btn-full"
                        disabled={isLoading}
                    >
                        {isLoading ? <span className="spinner" /> : '회원가입'}
                    </button>
                </form>

                <div className={styles.divider}>
                    <span>이미 계정이 있으신가요?</span>
                </div>

                <Link href="/login" className="btn btn-secondary btn-full">
                    로그인
                </Link>
            </div>

            <div className={styles.bgGlow} />
        </div>
    );
}
