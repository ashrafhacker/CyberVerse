/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  output: 'standalone',
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  // NOTE: cesium is intentionally NOT in transpilePackages. cesium@1.145 ships
  // native ESM ("type":"module", exports["."].import -> ./Source/Cesium.js)
  // plus a CJS entry, so Next/Turbopack consume it directly. Transpiling the
  // 79 MB package on every compile was a major dev-time cost with no benefit.
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion', 'motion', '@radix-ui/react-icons'],
    // Dev proxy hard-kills streams after 30s of socket inactivity (http-proxy
    // proxyTimeout), which broke video playback whenever the player paused
    // reading while its buffer was full (500 "Internal Server Error" mid-stream).
    // A large value effectively disables it; schema requires a number >= 0.
    proxyTimeout: 3600000,
  },
  // The old `turbopack.rules` block mapped *.svg through @svgr/webpack. That
  // package isn't installed and no module imports an .svg, so the rule was dead
  // config — and it blocked `next dev --turbopack`. Removed.
  async headers() {
    // Defense-in-depth headers. CSP stays permissive on script/style sources
    // (Next.js inline boot scripts + styled-jsx require 'unsafe-inline'); it
    // still constrains object/frame/media sources and blocks cross-origin
    // framing. HSTS intentionally omitted: this deployment is plain-HTTP
    // localhost — enable only after TLS is confirmed in production.
    // Clerk ($CLERK) loads its browser bundle and hosted UI (sign-in modal)
    // from its own origins, so those hosts must be allowlisted or the client
    // throws ClerkRuntimeError: failed_to_load_clerk_js. The array covers both
    // production (clerk.com) and development FAPI (*.clerk.accounts.dev).
    const clerkOrigins = [
      'https://clerk.com',
      'https://*.clerk.com',
      'https://*.clerk.accounts.dev',
      // NEXT_PUBLIC_CLERK_JS_URL escape hatch: when set, clerk-js is served
      // from an alternate CDN (e.g. jsDelivr). Its origin must be in
      // script-src or the overridden bundle is blocked by CSP. Only added at
      // build time when the env var is present — no effect otherwise.
      ...(process.env.NEXT_PUBLIC_CLERK_JS_URL
        ? [new URL(process.env.NEXT_PUBLIC_CLERK_JS_URL).origin]
        : []),
    ].join(' ');
    const csp = [
      "default-src 'self'",
      `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${clerkOrigins}`,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob: https:",
      `font-src 'self' data: ${clerkOrigins}`,
      "media-src 'self' blob: data: https:",
      "worker-src 'self' blob:",
      "connect-src 'self' https: wss:",
      `frame-src 'self' ${clerkOrigins}`,
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
