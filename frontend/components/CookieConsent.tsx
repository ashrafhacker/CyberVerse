'use client';

// First-party cookie/privacy consent banner + preferences panel.
// - "essential only" (default) stores NO analytics and loads NO trackers.
// - "allow analytics" stores localStorage cv-consent=analytics and activates
//   the consent-gated gtag loader in lib/analytics.ts.
// No third-party CMP dependency; dismissal without a choice = essential only.

import { useEffect, useState } from 'react';
import { Cookie, Settings2, X } from 'lucide-react';
import { activateAnalytics, getConsent, type ConsentChoice } from '@/lib/analytics';

const CONSENT_KEY = 'cv-consent';

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);
  const [panel, setPanel] = useState(false);
  const [analyticsOn, setAnalyticsOn] = useState(false);

  useEffect(() => {
    const existing = getConsent();
    if (!existing) {
      // Defer so it never blocks first paint.
      const t = window.setTimeout(() => setVisible(true), 800);
      return () => window.clearTimeout(t);
    }
    if (existing === 'analytics') activateAnalytics();
    return undefined;
  }, []);

  const save = (choice: ConsentChoice) => {
    window.localStorage.setItem(CONSENT_KEY, choice);
    if (choice === 'analytics') activateAnalytics();
    setVisible(false);
    setPanel(false);
  };

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-label="Cookie preferences"
      className="fixed bottom-4 left-4 z-[110] w-[min(420px,calc(100vw-2rem))] rounded-xl border border-cyber-border bg-cyber-surface/95 p-4 shadow-2xl backdrop-blur"
    >
      <div className="mb-2 flex items-center gap-2 text-cyber-primary">
        <Cookie size={16} aria-hidden />
        <p className="text-sm font-semibold text-cyber-text">Cookie preferences</p>
        <button
          aria-label="Dismiss (essential cookies only)"
          className="ml-auto text-cyber-muted hover:text-cyber-text"
          onClick={() => save('essential')}
        >
          <X size={15} />
        </button>
      </div>
      <p className="text-xs leading-relaxed text-cyber-muted">
        We use essential cookies to keep you signed in. Optional analytics cookies help us
        understand which lessons are useful — nothing is collected unless you allow it.
      </p>

      {panel && (
        <div className="mt-3 space-y-2 rounded-lg border border-cyber-border p-3">
          <label className="flex items-start gap-2 text-xs text-cyber-text">
            <input type="checkbox" checked disabled className="mt-0.5" />
            <span>
              <span className="font-medium">Essential</span> — session, security, and load
              balancing. Always on.
            </span>
          </label>
          <label className="flex items-start gap-2 text-xs text-cyber-text">
            <input
              type="checkbox"
              checked={analyticsOn}
              onChange={(e) => setAnalyticsOn(e.target.checked)}
              className="mt-0.5"
            />
            <span>
              <span className="font-medium">Analytics</span> — anonymous usage stats (Google
              Analytics 4) to improve lessons and performance.
            </span>
          </label>
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          className="rounded-md bg-cyber-primary px-3 py-1.5 text-xs font-semibold text-cyber-bg hover:opacity-90"
          onClick={() => (panel ? save(analyticsOn ? 'analytics' : 'essential') : save('analytics'))}
        >
          {panel ? 'Save preferences' : 'Allow analytics'}
        </button>
        <button
          className="rounded-md border border-cyber-border px-3 py-1.5 text-xs font-medium text-cyber-text hover:border-cyber-primary"
          onClick={() => save('essential')}
        >
          Essential only
        </button>
        {!panel && (
          <button
            className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs text-cyber-muted hover:text-cyber-text"
            onClick={() => setPanel(true)}
          >
            <Settings2 size={13} /> Preferences
          </button>
        )}
      </div>
    </div>
  );
}
