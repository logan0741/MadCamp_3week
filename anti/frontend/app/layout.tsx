import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'MUSINSA Tracker',
    description: 'Track prices and create your 3D avatar',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="ko">
            <body>{children}</body>
        </html>
    );
}
