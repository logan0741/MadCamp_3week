'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { userApi, getToken } from '@/lib/api';
import { useStore } from '@/lib/store';
import BottomNav from '@/components/BottomNav';
import styles from './mypage.module.css';

export default function MyPage() {
    const router = useRouter();
    const { user, setUser } = useStore();
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const token = getToken();
        if (!token) {
            router.push('/login');
            return;
        }

        loadUser();
    }, [router]);

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

    return (
        <div className={styles.page}>
            {/* Header */}
            {/* Header removed for consistent bottom navigation */}

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
                                        <div className={styles.canvasWrapper} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1rem', background: '#111' }}>
                                            <div style={{ fontSize: '4rem', opacity: 0.5 }}>👤</div>
                                            <p style={{ color: '#888', textAlign: 'center' }}>
                                                3D 뷰어 로딩 실패<br />
                                                <span style={{ fontSize: '0.8rem' }}>(라이브러리 호환성 문제로 비활성화됨)</span>
                                            </p>
                                        </div>
                                        <div className={styles.viewerNote}>
                                            * 실제 3D 게이밍 엔진(Unity) 연동을 위해서는 빌드 파일이 필요합니다.<br />
                                            현재는 정적 이미지가 표시됩니다.
                                        </div>
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
                                        ? '성공적으로 생성되었습니다'
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

            <BottomNav />
        </div>
    );
}
