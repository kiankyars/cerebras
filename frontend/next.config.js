/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  // Enable static exports for simpler deployment
  output: 'export',
  // Configure image optimization for static exports
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig
