'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Unity, useUnityContext } from 'react-unity-webgl';
import { userApi, getToken } from '@/lib/api';
import { useStore } from '@/lib/store';
import styles from './mypage.module.css';

export default function MyPage() {
    const router = useRouter();
    const { user, setUser } = useStore();
    const [isLoading, setIsLoading] = useState(true);
    const [unityLoaded, setUnityLoaded] = useState(false);

    // Unity WebGL context - paths would need to be set up with actual Unity build
    const { unityProvider, isLoaded, loadingProgression } = useUnityContext({
        loaderUrl: '/unity/avatar_viewer.loader.js',
        dataUrl: '/unity/avatar_viewer.data',
        frameworkUrl: '/unity/avatar_viewer.framework.js',
        codeUrl: '/unity/avatar_viewer.wasm',
    });

    useEffect(() => {
        const token = getToken();
        if (!token) {
            router.push('/login');
            return;
        }

        loadUser();
    }, [router]);

    useEffect(() => {
        if (isLoaded) {
            setUnityLoaded(true);
        }
    }, [isLoaded]);

    const loadUser = async () => {
        try {
            const userData = await userApi.getStatus();
            setUser(userData);
        } catch (err) {
            console.error('Failed to load user:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const formatDate = (dateStr: string | undefined) => {
        if (!dateStr) return '정보 없음';
        return new Date(dateStr).toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
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
                        <Link href="/dashboard" className={styles.navLink}>
                            관심 상품
                        </Link>
                        <Link href="/mypage" className={`${styles.navLink} ${styles.active}`}>
                            마이페이지
                        </Link>
                    </nav>
                </div>
            </header>

            <main className={styles.main}>
                {isLoading ? (
                    <div className={styles.loading}>
                        <div className="spinner" />
                        <p>로딩 중...</p>
                    </div>
                ) : (
                    <>
                        {/* Avatar Section */}
                        <section className={styles.avatarSection}>
                            <div className={styles.avatarContainer}>
                                {user?.is_avatar_created ? (
                                    <>
                                        {!unityLoaded && (
                                            <div className={styles.unityLoading}>
                                                <div className="spinner" />
                                                <p>3D 아바타 로딩 중... {Math.round(loadingProgression * 100)}%</p>
                                            </div>
                                        )}
                                        <Unity
                                            unityProvider={unityProvider}
                                            className={styles.unityCanvas}
                                            style={{ visibility: unityLoaded ? 'visible' : 'hidden' }}
                                        />
                                    </>
                                ) : (
                                    <div className={styles.noAvatar}>
                                        <span className={styles.avatarPlaceholder}>👤</span>
                                        <p>아직 아바타가 생성되지 않았습니다</p>
                                    </div>
                                )}
                            </div>

                            <div className={styles.avatarInfo}>
                                <h1>나의 디지털 트윈</h1>
                                <p className={styles.updateDate}>
                                    {user?.is_avatar_created
                                        ? '아바타가 생성되었습니다'
                                        : '아바타를 생성해주세요'}
                                </p>

                                <Link
                                    href="/onboarding"
                                    className={`btn btn-primary btn-full ${styles.modelBtn}`}
                                >
                                    {user?.is_avatar_created ? '다시 모델링하기' : '아바타 생성하기'}
                                </Link>
                            </div>
                        </section>

                        {/* Profile Section */}
                        <section className={styles.profileSection}>
                            <h2>내 정보</h2>

                            <div className={styles.profileCard}>
                                <div className={styles.profileItem}>
                                    <span className={styles.profileLabel}>아이디</span>
                                    <span className={styles.profileValue}>{user?.username}</span>
                                </div>

                                <div className={styles.profileItem}>
                                    <span className={styles.profileLabel}>키</span>
                                    <span className={styles.profileValue}>
                                        {user?.height ? `${user.height} cm` : '미입력'}
                                    </span>
                                </div>

                                <div className={styles.profileItem}>
                                    <span className={styles.profileLabel}>몸무게</span>
                                    <span className={styles.profileValue}>
                                        {user?.weight ? `${user.weight} kg` : '미입력'}
                                    </span>
                                </div>
                            </div>
                        </section>

                        {/* Settings Section */}
                        <section className={styles.settingsSection}>
                            <h2>설정</h2>

                            <div className={styles.settingsList}>
                                <button className={styles.settingItem}>
                                    <span>알림 설정</span>
                                    <span className={styles.arrow}>→</span>
                                </button>
                                <button className={styles.settingItem}>
                                    <span>가격 알림 기준</span>
                                    <span className={styles.arrow}>→</span>
                                </button>
                                <button
                                    className={`${styles.settingItem} ${styles.danger}`}
                                    onClick={() => {
                                        localStorage.removeItem('auth_token');
                                        localStorage.removeItem('musinsa-tracker-store');
                                        router.push('/login');
                                    }}
                                >
                                    <span>로그아웃</span>
                                    <span className={styles.arrow}>→</span>
                                </button>
                            </div>
                        </section>
                    </>
                )}
            </main>
        </div>
    );
}
