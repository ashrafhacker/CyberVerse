import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

/**
 * Node 22+ exposes a global `localStorage` that is only functional when the
 * process is started with `--localstorage-file`. When it is present but
 * unavailable it shadows jsdom's implementation and `localStorage` resolves to
 * `undefined`, which makes every storage-backed test fail for reasons that
 * have nothing to do with the code under test.
 *
 * Install a minimal in-memory implementation when neither is available. On
 * Node versions without the built-in global (and in CI) this is a no-op.
 */
if (typeof globalThis.localStorage === 'undefined') {
  const store = new Map<string, string>();
  const storage = {
    getItem: (key: string) => (store.has(key) ? (store.get(key) as string) : null),
    setItem: (key: string, value: string) => { store.set(key, String(value)); },
    removeItem: (key: string) => { store.delete(key); },
    clear: () => { store.clear(); },
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    get length() { return store.size; },
  };
  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true,
    writable: true,
  });
}

afterEach(() => {
  cleanup();
  if (typeof localStorage !== 'undefined' && localStorage.clear) localStorage.clear();
});
