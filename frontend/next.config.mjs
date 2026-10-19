/**
 * Production-only bundler repair: illegal legacy octal escapes.
 *
 * cesium@1.145 pulls in @cesium/engine@26.3 -> @spz-loader/core@0.3.1, whose
 * Emscripten build inlines the raw .wasm binary as a JS *template literal*.
 * The raw dependency is valid, but the production minifier serialises NUL bytes
 * as `\0`; when a NUL byte is immediately followed by a digit character the
 * result is `\0<digit>` — an illegal legacy octal escape inside an (untagged)
 * template literal. The browser then throws a SyntaxError and refuses to parse
 * the whole chunk, which tripped the /globe error boundary in production only
 * (dev/Turbopack is unminified, so it never showed there).
 *
 * We repair the emitted chunks: only `\0` (NUL) that directly precedes a digit
 * is rewritten to the unambiguous `\x00`. The leading-backslash parity check
 * (`(?:\\\\)*`) makes sure an already-escaped backslash (`"\\0"`) is left alone.
 * Non-template/regex uses of `\0<digit>` are vanishingly rare and `\x00` is
 * semantically identical (NUL) wherever it is legal.
 */
function fixLegacyOctalEscapes(source) {
  let fixed = 0;
  const out = source.replace(/([^\\]|^)((?:\\\\)*)\\0(?=[0-9])/g, (_match, pre, pairs) => {
    fixed += 1;
    return `${pre}${pairs}\\x00`;
  });
  return { out, fixed };
}

class FixLegacyOctalEscapesPlugin {
  apply(compiler) {
    const { webpack } = compiler;
    const { RawSource } = webpack.sources;
    compiler.hooks.thisCompilation.tap('FixLegacyOctalEscapesPlugin', (compilation) => {
      compilation.hooks.processAssets.tap(
        {
          name: 'FixLegacyOctalEscapesPlugin',
          // After minification, before [contenthash] substitution, so the
          // repaired bytes are what the emitted filename hashes.
          stage: webpack.Compilation.PROCESS_ASSETS_STAGE_SUMMARIZE,
        },
        () => {
          for (const asset of compilation.getAssets()) {
            if (!asset.name.endsWith('.js')) continue;
            const { out, fixed } = fixLegacyOctalEscapes(asset.source.source().toString());
            if (fixed > 0) {
              compilation.updateAsset(asset.name, new RawSource(out));
              // eslint-disable-next-line no-console
              console.log(
                `[fix-legacy-octal-escapes] repaired ${fixed} illegal escape(s) in ${asset.name}`,
              );
            }
          }
        },
      );
    });
  }
}

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
    // Derive the instance's own Clerk Frontend API origin from the publishable
    // key so *any* instance is allowlisted without editing this file:
    // development (*.clerk.accounts.dev) and, crucially, production on a custom
    // domain (clerk.<yourdomain> + the hosted portal at accounts.<yourdomain>).
    // The key's middle segment is base64("<frontend-api-host>$").
    const clerkPkOrigins = (() => {
      try {
        const b64 = (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? '').split('_')[2] ?? '';
        if (!b64) return [];
        const host = Buffer.from(b64, 'base64').toString('utf8').replace(/\$$/, '');
        if (!host) return [];
        const origins = [`https://${host}`];
        // Production FAPI is clerk.<domain>; the hosted Account Portal is
        // accounts.<domain>. Allowlist the portal too when that shape applies.
        if (host.startsWith('clerk.')) origins.push(`https://accounts.${host.slice('clerk.'.length)}`);
        return origins;
      } catch {
        return [];
      }
    })();
    const clerkOrigins = Array.from(
      new Set([
        'https://clerk.com',
        'https://*.clerk.com',
        'https://*.clerk.accounts.dev',
        ...clerkPkOrigins,
        // NEXT_PUBLIC_CLERK_JS_URL escape hatch: when set, clerk-js is served
        // from an alternate CDN (e.g. jsDelivr). Its origin must be in
        // script-src or the overridden bundle is blocked by CSP. Only added at
        // build time when the env var is present — no effect otherwise.
        ...(process.env.NEXT_PUBLIC_CLERK_JS_URL
          ? [new URL(process.env.NEXT_PUBLIC_CLERK_JS_URL).origin]
          : []),
      ]),
    ).join(' ');
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

// The repair is only meaningful for minified production webpack output. Gating
// on NODE_ENV keeps `next dev --turbopack` free of the "Webpack is configured
// while Turbopack is not" warning by not defining a webpack config at all in dev.
if (process.env.NODE_ENV === 'production') {
  nextConfig.webpack = (config) => {
    config.plugins.push(new FixLegacyOctalEscapesPlugin());
    return config;
  };
}

export default nextConfig;
