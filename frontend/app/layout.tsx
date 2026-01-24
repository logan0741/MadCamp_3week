import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'Musinsa Price Tracker & Virtual Try-On',
    description: '무신사 가격 추적 및 3D 가상 피팅 서비스',
};

export const viewport = {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="ko">
            <head>
                <link
                    href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
                    rel="stylesheet"
                />
            </head>
            <body>
                <div className="mobile-layout-container">
                    <div className="mobile-scroll-area">
                        {children}
                    </div>
                </div>
            </body>
        </html>
    );
}
