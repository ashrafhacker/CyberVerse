'use client';

// Minimal in-house toast system (no third-party dependency).
// API: const toast = useToast(); toast.success('Saved'); toast.error('Oops');
// Positioning/animation lives in the rendered <ToastViewport />.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

export type ToastTone = 'success' | 'error' | 'info';

export interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastApi {
  show: (message: string, tone?: ToastTone, ttlMs?: number) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const DEFAULT_TTL: Record<ToastTone, number> = {
  success: 3200,
  info: 3200,
  error: 6000,
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setItems((list) => list.filter((t) => t.id !== id));
  }, []);

  const show = useCallback(
    (message: string, tone: ToastTone = 'info', ttlMs?: number) => {
      const id = nextId.current++;
      setItems((list) => [...list.slice(-3), { id, message, tone }]);
      const ttl = ttlMs ?? DEFAULT_TTL[tone];
      if (ttl > 0) window.setTimeout(() => dismiss(id), ttl);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({
      show,
      success: (m) => show(m, 'success'),
      error: (m) => show(m, 'error'),
      info: (m) => show(m, 'info'),
    }),
    [show],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastViewport items={items} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}

const TONE_STYLE: Record<ToastTone, { border: string; icon: string; symbol: string }> = {
  success: { border: 'border-emerald-400/40', icon: 'text-emerald-300', symbol: '✓' },
  error: { border: 'border-rose-400/40', icon: 'text-rose-300', symbol: '✕' },
  info: { border: 'border-cyan-300/40', icon: 'text-cyan-200', symbol: 'i' },
};

function ToastViewport({
  items,
  onDismiss,
}: {
  items: ToastItem[];
  onDismiss: (id: number) => void;
}) {
  if (!items.length) return null;
  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="pointer-events-none fixed bottom-4 right-4 z-[120] flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2"
    >
      {items.map((t) => {
        const tone = TONE_STYLE[t.tone];
        return (
          <button
            key={t.id}
            role="status"
            onClick={() => onDismiss(t.id)}
            className={`pointer-events-auto flex items-start gap-3 rounded-xl border ${tone.border} bg-cyber-surface/95 px-4 py-3 text-left text-sm text-cyber-text shadow-lg backdrop-blur animate-slide-in-right`}
          >
            <span className={`mt-0.5 font-bold ${tone.icon}`} aria-hidden>
              {tone.symbol}
            </span>
            <span className="flex-1">{t.message}</span>
            <span className="sr-only">Click to dismiss</span>
          </button>
        );
      })}
    </div>
  );
}
