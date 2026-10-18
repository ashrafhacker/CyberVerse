/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  output: 'standalone',
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  transpilePackages: ['cesium'],
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion', 'motion', '@radix-ui/react-icons', 'cesium'],
    // Dev proxy hard-kills streams after 30s of socket inactivity (http-proxy
    // proxyTimeout), which broke video playback whenever the player paused
    // reading while its buffer was full (500 "Internal Server Error" mid-stream).
    // A large value effectively disables it; schema requires a number >= 0.
    proxyTimeout: 3600000,
  },
  turbopack: {
    rules: {
      '*.svg': {
        loaders: ['@svgr/webpack'],
        as: '*.js',
      },
    },
  },
  async headers() {
    // Defense-in-depth headers. CSP stays permissive on script/style sources
    // (Next.js inline boot scripts + styled-jsx require 'unsafe-inline'); it
    // still constrains object/frame/media sources and blocks cross-origin
    // framing. HSTS intentionally omitted: this deployment is plain-HTTP
    // localhost — enable only after TLS is confirmed in production.
    const csp = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob: https:",
      "font-src 'self' data:",
      "media-src 'self' blob: data: https:",
      "worker-src 'self' blob:",
      "connect-src 'self' https: wss:",
      "frame-ancestors *",
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; ');
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          // X-Frame-Options intentionally omitted: it can't express "allow all",
          // and CSP frame-ancestors above is the controlling directive. Needed
          // so the app can be embedded (e.g. in a preview/iframe). Re-add
          // "DENY" for production hardening if embedding isn't required.
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=(), usb=()' },
          { key: 'Content-Security-Policy', value: csp },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'}/api/:path*`,
      },
    ];
  },
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    minimumCacheTTL: 31536000,
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
