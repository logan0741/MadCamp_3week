/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    images: {
        domains: ['image.musinsa.com', 'cdn.musinsa.com'],
    },
    transpilePackages: ['three', '@react-three/fiber', '@react-three/drei'],
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://localhost:8000/:path*',
            },
        ];
    },
};

module.exports = nextConfig;
