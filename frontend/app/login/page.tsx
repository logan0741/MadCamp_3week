'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authApi, userApi, setToken } from '@/lib/api';
import { useStore } from '@/lib/store';
import styles from './login.module.css';

export default function LoginPage() {
    const router = useRouter();
    const { setUser } = useStore();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            const { access_token } = await authApi.login(username, password);
            setToken(access_token);

            // Get user status
            const user = await userApi.getStatus();
            setUser(user);

            // Redirect based on avatar status
            if (!user.is_avatar_created) {
                router.push('/onboarding');
            } else {
                router.push('/dashboard');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : '로그인에 실패했습니다.');
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

                <p className={styles.subtitle}>가격 추적 & 가상 피팅</p>

                <form onSubmit={handleSubmit} className={styles.form}>
                    <div className="input-group">
                        <label className="input-label">아이디</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="아이디를 입력하세요"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label className="input-label">비밀번호</label>
                        <input
                            type="password"
                            className="input"
                            placeholder="비밀번호를 입력하세요"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    {error && <div className={styles.error}>{error}</div>}

                    <button
                        type="submit"
                        className="btn btn-primary btn-full"
                        disabled={isLoading}
                    >
                        {isLoading ? <span className="spinner" /> : '로그인'}
                    </button>
                </form>

                <div className={styles.divider}>
                    <span>또는</span>
                </div>

                <Link href="/register" className="btn btn-secondary btn-full">
                    회원가입
                </Link>
            </div>

            {/* Background decoration */}
            <div className={styles.bgGlow} />
        </div>
    );
}
