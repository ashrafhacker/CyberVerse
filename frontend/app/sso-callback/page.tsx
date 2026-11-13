import { AuthenticateWithRedirectCallback } from '@clerk/nextjs';

// Clerk OAuth/OIDC callback destination. After an SSO/redirect round-trip
// (e.g. Google), clerk-js needs a route to land on and exchange the
// handshake for a session. Clerk's supported <AuthenticateWithRedirectCallback />
// is the entire implementation — this route makes no auth, authorization,
// CSRF, or route-guard changes. The path-routed <SignIn> on /login still
// serves its own /login/sso-callback via the [[...rest]] catch-all; this
// page covers redirect-flow callbacks that target /sso-callback directly
// (previously a 404).
export default function SsoCallbackPage() {
  return <AuthenticateWithRedirectCallback />;
}
