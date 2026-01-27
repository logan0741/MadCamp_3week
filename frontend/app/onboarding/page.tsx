'use client';

import { useRouter } from 'next/navigation';
import styles from './onboarding.module.css';

export default function OnboardingPage() {
    const router = useRouter();

    return (
        <div className={styles.container}>
            <div className={styles.instructionPanel}>
                <h2>환영합니다!</h2>
                <p className={styles.instruction}>
                    무신사 트래커에 오신 것을 환영합니다.<br />
                    이제부터 나만의 맞춤형 패션 정보를 받아보세요.
                </p>

                <div className={styles.buttonRow}>
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="btn btn-primary btn-full"
                    >
                        시작하기
                    </button>
                </div>
            </div>
        </div>
    );
}
