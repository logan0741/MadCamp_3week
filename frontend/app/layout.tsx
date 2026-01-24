import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'MUSINSA Tracker',
    description: 'Track prices and create your 3D avatar',
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
<<<<<<< HEAD:frontend/app/layout.tsx
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
=======
            <body>{children}</body>
>>>>>>> anti_back:anti/frontend/app/layout.tsx
        </html>
    );
}
