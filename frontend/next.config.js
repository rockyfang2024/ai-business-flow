/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['43.160.205.9', '43.160.205.9:3000'],

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;