import { clerkMiddleware } from '@clerk/nextjs/server';

// Enables Clerk session handling (token refresh, auth() availability) across
// the app. We deliberately do NOT call auth.protect() here: route guarding is
// already handled client-side by useRequireAuth, and several pages (courses
// list, leaderboard, tools, contact) are public. Adding server-side redirects
// would risk locking out anonymous visitors.
export default clerkMiddleware();

export const config = {
  matcher: [
    // Skip Next.js internals and all static files.
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes.
    '/(api|trpc)(.*)',
  ],
};
