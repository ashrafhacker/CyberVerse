# Next.js + Cloudflare Workers Adapter Compatibility Check

TEST RESULT:
- The existing frontend is Next.js 15.5.28 (per package.json / build output).
- The `frontend/app/admin/production-readiness/page.tsx` uses standard React 19 patterns (`useState`, `useCallback`, `useRequireAuth`).
- Next.js Cloudflare Workers adapter (`@opennextjs/cloudflare`) requires specific constraints:
  * Only `runtime: 'edge'` compatible APIs work.
  * `node_modules` must be bundled by `next.config.mjs` (`swcMinify` key issue observed in build — must fix config).
  * Dynamic routes with `useRequireAuth` (client-side auth) work, but server-side `headers()` / `cookies()` access is limited.
  * WebSocket server (`admin/stream`) does NOT work on Cloudflare Workers (Workers don't support long-lived server-side WebSocket upgrade; Durable Objects would be required).

COMPATIBILITY FINDINGS:
- PASS: Standard React components, static/dynamic pages, `useRequireAuth`, client-side fetch.
- FAIL / LIMIT: Next.js `swcMinify` config key produces build warnings (`next.config.mjs` must be cleaned). The current production-readiness page does not redeclare `loading`; the production build passes. These are application-level issues, not adapter-level.
- FAIL / LIMIT: `frontend/lib/adminWs.ts` uses native WebSocket (`new WebSocket(...)`). Cloudflare Workers do not provide native WebSocket on the server; the client's WebSocket works fine (connects to backend server via `ws://` or `wss://`). The server-side `/stream` endpoint requires the backend server to handle WebSocket upgrade. This remains on Render Free (backend server supports `WebSocket`).
- PASS: `credentials: "include"` works with both Render and Cloudflare when CORS origins include the frontend domain.
- PASS: `fetch()` calls from the frontend to `/api/v1/admin/production-readiness` use the page's relative path; public client code uses `NEXT_PUBLIC_API_URL`, and Next rewrites use `BACKEND_URL` (default `http://127.0.0.1:8000`).

ADAPTER ADOPTION DECISION:
- Create `frontend/next.config.mjs` (or update existing) with Cloudflare adapter settings for `swcMinify` removal.
- Do NOT adopt the adapter until the `swcMinify` and variable redeclaration errors are resolved and the build passes cleanly.
- Document adapter as optional (future phase); the zero-cost deployment works without it (frontend on Vercel free or Cloudflare Pages; backend on Render Free).
