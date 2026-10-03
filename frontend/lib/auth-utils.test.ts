import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { ApiError } from './api';
import {
  authErrorMessage,
  consumeRedirectTarget,
  resolveLoginRedirect,
  saveRedirectTarget,
} from './auth-utils';

describe('redirect target storage', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('round-trips a valid relative path and is one-shot', () => {
    saveRedirectTarget('/courses/course-1');
    expect(consumeRedirectTarget()).toBe('/courses/course-1');
    expect(consumeRedirectTarget()).toBeNull();
  });

  it('preserves query strings', () => {
    saveRedirectTarget('/courses/course-1?tab=modules');
    expect(consumeRedirectTarget()).toBe('/courses/course-1?tab=modules');
  });

  it('refuses paths that would recreate a login loop', () => {
    saveRedirectTarget('/login');
    expect(consumeRedirectTarget()).toBeNull();
    saveRedirectTarget('/register');
    expect(consumeRedirectTarget()).toBeNull();
    saveRedirectTarget('/login?redirect=/x');
    expect(consumeRedirectTarget()).toBeNull();
  });

  it('refuses absolute / protocol-relative / api paths (open-redirect guard)', () => {
    saveRedirectTarget('//evil.com/x');
    expect(consumeRedirectTarget()).toBeNull();
    saveRedirectTarget('https://evil.com/x');
    expect(consumeRedirectTarget()).toBeNull();
    saveRedirectTarget('/api/v1/auth/google');
    expect(consumeRedirectTarget()).toBeNull();
  });
});

describe('resolveLoginRedirect', () => {
  beforeEach(() => {
    sessionStorage.clear();
    window.history.pushState({}, '', '/login');
  });

  afterEach(() => {
    window.history.pushState({}, '', '/');
  });

  it('uses the ?redirect query param when valid', () => {
    window.history.pushState({}, '', '/login?redirect=/courses/course-1');
    expect(resolveLoginRedirect()).toBe('/courses/course-1');
  });

  it('clears the stored target when the URL param is authoritative', () => {
    saveRedirectTarget('/stale');
    window.history.pushState({}, '', '/login?redirect=/courses/course-1');
    resolveLoginRedirect();
    expect(consumeRedirectTarget()).toBeNull();
  });

  it('falls back to a stored target when no valid URL param exists', () => {
    saveRedirectTarget('/dashboard');
    expect(resolveLoginRedirect()).toBe('/dashboard');
  });

  it('falls back to the dashboard when nothing is saved', () => {
    expect(resolveLoginRedirect()).toBe('/dashboard');
  });

  it('ignores unsafe ?redirect and falls back to the stored target', () => {
    saveRedirectTarget('/profile');
    window.history.pushState({}, '', '/login?redirect=//evil.com');
    expect(resolveLoginRedirect()).toBe('/profile');
  });
});

describe('authErrorMessage', () => {
  it('maps network errors to a connectivity message', () => {
    expect(authErrorMessage(new ApiError(0, 'fail', { network: true }), 'fb')).toMatch(
      /reach the CyberVerse server/i,
    );
  });

  it('maps 401 to an invalid/expired session message', () => {
    expect(authErrorMessage(new ApiError(401, 'x'), 'fb')).toMatch(/invalid or expired/i);
  });

  it('maps 429 to a rate-limit message', () => {
    expect(authErrorMessage(new ApiError(429, 'x'), 'fb')).toMatch(/too many attempts/i);
  });

  it('maps 5xx to a server-unavailable message', () => {
    expect(authErrorMessage(new ApiError(503, 'x'), 'fb')).toMatch(/server is unavailable/i);
  });

  it('surfaces the API message for other statuses', () => {
    expect(authErrorMessage(new ApiError(403, 'no access'), 'fb')).toBe('no access');
  });

  it('falls back gracefully for non-ApiError errors', () => {
    expect(authErrorMessage(new Error('boom'), 'fallback')).toBe('boom');
    expect(authErrorMessage('weird', 'fallback')).toBe('fallback');
  });
});
