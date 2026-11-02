import React, { useEffect, useState, useRef } from 'react';
import { useAuth as useClerkAuth } from '@clerk/nextjs';
import { useAuth } from './auth';
import { isAdmin } from './roles';

/** Phase C — real admin WebSocket hook.
 *  Connects to /api/v1/admin/stream?token=<clerk_session_token>
 *  Authenticates via query param; closes 4401 (no/invalid token) or 4403
 *  (below admin tier); receives audit events + ping keep-alive.
 *  Polling fallback: consumers that don't need WS can call loadData()
 *  on an interval, but this hook provides the live stream.
 */
export function useAdminWs(endpointPath = '/admin/stream') {
  const { user, loading } = useAuth();
  const { getToken, isLoaded, isSignedIn } = useClerkAuth();
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [lastEvent, setLastEvent] = useState<Record<string, unknown> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const tokenRef = useRef<string | null>(null);

  const resolveToken = async (): Promise<string | null> => {
    if (!isLoaded || isSignedIn !== true) return null;
    try {
      const t = await getToken();
      if (t && typeof t === 'string') return t;
    } catch {
      // ignore token-fetch failures
    }
    return null;
  };

  useEffect(() => {
    if (loading) return;
    if (!user || !isAdmin(user.role)) return;

    let urlStr = '';
    (async () => {
      const token = await resolveToken();
      tokenRef.current = token ?? null;
      const base = (process.env.NEXT_PUBLIC_API_URL ?? '/api/v1').replace(/\/$/, '');
      const wsBase = base.replace(/^http/, 'ws');
      const query = token ? `?token=${encodeURIComponent(token)}` : '';
      urlStr = `${wsBase}${endpointPath}${query}`;

      try {
        const ws = new WebSocket(urlStr);
        wsRef.current = ws;

        ws.onopen = () => setConnected(true);
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data);
            if (msg && typeof msg === 'object') {
              setLastEvent(msg);
              setEvents((prev) => [...prev.slice(-99), msg]);
            }
          } catch {
            // ignore non-JSON or malformed messages
          }
        };
        ws.onclose = () => {
          setConnected(false);
          wsRef.current = null;
        };
        ws.onerror = () => {
          setConnected(false);
        };
      } catch {
        setConnected(false);
      }
    })();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
    };
  }, [user, loading, endpointPath, isLoaded, isSignedIn, getToken]);

  return {
    connected,
    lastEvent,
    events: events.slice(-20),
  };
}
