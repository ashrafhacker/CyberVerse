import { clerkMiddleware } from '@clerk/nextjs/server';
import { NextResponse, type NextRequest } from 'next/server';

// Enables Clerk session handling (token refresh, auth() availability) across
// the app. We deliberately do NOT call auth.protect() here: route guarding is
// already handled client-side by useRequireAuth, and several pages (courses
// list, leaderboard, tools, contact) are public. Adding server-side redirects
// would risk locking out anonymous visitors.
//
// ─── Per-request nonce CSP (staging) ──────────────────────────────────────
// This middleware is now the single source of truth for the
// Content-Security-Policy. The static CSP previously declared in
// next.config.mjs was removed in the same change: browsers enforce multiple
// CSPs additively, so leaving both would run the old permissive policy
// alongside this one (single-policy rule — never add one without removing
// the other).
//
// Next.js 15 nonce plumbing: the nonce must reach the RENDERER (so inline
// <script> tags in SSR'd HTML get nonce="…") and it must be in the RESPONSE
// header the browser enforces. We attach the CSP to both — request headers
// via NextResponse.next({ request: { headers } }), response headers via
// res.headers.set(...). The root layout must be dynamic
// (`export const dynamic = 'force-dynamic'` in app/layout.tsx) or pages are
// prerendered at build time and their static HTML cannot carry a per-request
// nonce.
//
// Nonce uses Web Crypto + btoa (available in the edge middleware runtime);
// `node:crypto`/Buffer are deliberately avoided here.
//
// Why not Clerk's built-in `clerkMiddleware({ contentSecurityPolicy:
// { strict: true } })`: strict mode forces 'strict-dynamic' (which
// nullifies the explicit host allowlist for vercel.live / Cloudflare
// challenges) and @clerk/nextjs@6.39.7 exposes no nonce prop on
// ClerkProvider, so a strict policy's nonce would never reach framework
// scripts. We therefore build the policy ourselves with an explicit,
// auditable host allowlist and NO 'unsafe-eval' / 'unsafe-inline' in
// script-src (production).

/** 16 cryptographically random bytes, base64 — one per request. */
function generateNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let binary = '';
  for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

// Explicit API origin allowlist (connect-src + frame-src for API-hosted PDFs).
// Staging backend ONLY: production API is deliberately absent so staging can
// never talk to production. Add the prod origin here only when promoting.
const API_ORIGINS = ['https://cyberverse-staging-api.onrender.com'];

// Clerk Frontend API origin derived from the publishable key (the key's
// middle segment is base64("<frontend-api-host>$")). atob instead of Buffer
// for edge-runtime safety. Covers the staging instance
// (accounts.*.clerk.accounts.dev) without hardcoding it.
const clerkPkOrigins = (() => {
  try {
    const b64 = (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? '').split('_')[2] ?? '';
    if (!b64) return [];
    const host = atob(b64).replace(/\$$/, '');
    return host ? [`https://${host}`] : [];
  } catch {
    return [];
  }
})();

// NEXT_PUBLIC_CLERK_JS_URL escape hatch: when set, clerk-js is served from
// an alternate CDN (e.g. jsDelivr); its origin must be in script-src. Only
// present when the env var is set — no effect otherwise.
const clerkJsOverrideOrigin = (() => {
  try {
    const url = process.env.NEXT_PUBLIC_CLERK_JS_URL;
    return url ? [new URL(url).origin] : [];
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
    ...clerkJsOverrideOrigin,
  ]),
);

function buildCsp(nonce: string): string {
  const scriptSrc = [
    "'self'",
    `'nonce-${nonce}'`,
    ...clerkOrigins,
    'https://vercel.live', // Vercel preview feedback/debug toolbar
    'https://challenges.cloudflare.com', // Clerk Turnstile challenge script
    'https://*.protect.clerk.com', // Clerk bot-protection script
    // Dev-only: webpack/Turbopack HMR evaluates module factories. Excluded
    // automatically in production builds (NODE_ENV === 'production').
    ...(process.env.NODE_ENV === 'development' ? ["'unsafe-eval'"] : []),
  ];

  const connectSrc = [
    "'self'",
    ...API_ORIGINS, // REST calls (lib/api.ts)
    ...API_ORIGINS.map((origin) => origin.replace(/^https:/, 'wss:')), // adminWs.ts
    ...clerkOrigins, // clerk-js -> FAPI
    'https://clerk-telemetry.com',
    'https://*.clerk-telemetry.com',
    'https://vercel.live',
    // Latent: NEXT_PUBLIC_GA_ID is unset on staging, so gtag is dormant.
    // When GA is enabled, add 'https://*.googletagmanager.com' here.
  ];

  const frameSrc = [
    "'self'",
    ...clerkOrigins,
    ...API_ORIGINS, // lesson PDF previews served from the API host
    'https://drive.google.com', // lesson Drive-preview iframes
    'https://challenges.cloudflare.com', // Turnstile challenge iframe
    'https://*.protect.clerk.com',
  ];

  return [
    "default-src 'self'",
    `script-src ${scriptSrc.join(' ')}`,
    "style-src 'self' 'unsafe-inline'", // Clerk CSS-in-JS injects <style> tags
    "img-src 'self' data: blob: https:",
    `font-src 'self' data: ${clerkOrigins.join(' ')}`,
    "media-src 'self' blob: data: https:",
    "worker-src 'self' blob:",
    `connect-src ${connectSrc.join(' ')}`,
    `frame-src ${frameSrc.join(' ')}`,
    // Narrowed from `*`: no actual embedder is documented anywhere in the
    // repo — the old comment only speculated "e.g. in a preview/iframe".
    // 'self' covers self-embedding; vercel.com covers the Vercel dashboard
    // preview/comments iframe. IMPACT: any other third-party embed of the
    // staging app breaks — add that origin here if a real embedder appears.
    "frame-ancestors 'self' https://vercel.com",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');
}

export default clerkMiddleware(async (_auth, req: NextRequest) => {
  const nonce = generateNonce();
  const csp = buildCsp(nonce);

  // 1) Request header: Next.js reads this during render and stamps the
  //    nonce onto every framework-generated inline <script>/<link>.
  // 2) Response header: what the browser enforces for this navigation.
  const requestHeaders = new Headers(req.headers);
  requestHeaders.set('x-nonce', nonce);
  requestHeaders.set('content-security-policy', csp);

  const res = NextResponse.next({ request: { headers: requestHeaders } });
  res.headers.set('Content-Security-Policy', csp);
  return res;
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files.
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes.
    '/(api|trpc)(.*)',
  ],
};
