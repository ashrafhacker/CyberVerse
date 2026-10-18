'use client';

// Consent-gated analytics. Nothing is loaded or sent until the visitor
// opts in via the cookie banner (localStorage key cv-consent, value
// "analytics" | "essential"). If NEXT_PUBLIC_GA_ID is unset the module is a
// silent no-op, so localhost/dev never phones home.

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

const GA_ID = process.env.NEXT_PUBLIC_GA_ID ?? '';
const CONSENT_KEY = 'cv-consent';

export type ConsentChoice = 'analytics' | 'essential';

export function getConsent(): ConsentChoice | null {
  if (typeof window === 'undefined') return null;
  const v = window.localStorage.getItem(CONSENT_KEY);
  return v === 'analytics' || v === 'essential' ? v : null;
}

let injected = false;

function ensureGaScript() {
  if (injected || !GA_ID || typeof window === 'undefined') return;
  injected = true;
  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag(...args: unknown[]) {
    window.dataLayer!.push(args);
  };
  window.gtag('js', new Date());
  window.gtag('config', GA_ID, { send_page_view: false });
  const s = document.createElement('script');
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_ID)}`;
  document.head.appendChild(s);
}

/** Call after the user accepts analytics in the consent banner. */
export function activateAnalytics() {
  if (getConsent() !== 'analytics') return;
  ensureGaScript();
  trackPageView();
}

/** Fire-and-forget page view (SPA navigation). */
export function trackPageView(path?: string) {
  if (getConsent() !== 'analytics' || !window.gtag) return;
  window.gtag('event', 'page_view', {
    page_path: path ?? window.location.pathname + window.location.search,
  });
}

/**
 * Conversion events. Named per GA4 recommended events where a match exists.
 * gtag is absent until consent, so calls before opt-in are safe no-ops.
 */
export function trackConversion(
  name:
    | 'sign_up'
    | 'login'
    | 'enroll_trial_start'
    | 'begin_lesson'
    | 'complete_lesson'
    | 'lab_session_start'
    | 'challenge_complete'
    | 'contact_submit'
    | string,
  params: Record<string, unknown> = {},
) {
  if (getConsent() !== 'analytics' || !window.gtag) return;
  window.gtag('event', name, params);
}
