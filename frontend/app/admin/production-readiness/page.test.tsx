import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ProductionReadinessPage from './page';

vi.mock('@/lib/auth', () => ({
  useRequireAuth: () => ({ user: { id: 'u1', role: 'administrator' }, authLoading: false, error: null }),
}));
vi.mock('@/lib/roles', () => ({ isAdmin: () => true }));

describe('ProductionReadinessPage', () => {
  it('renders readiness cards', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({
      overall_status: 'operational',
      checks: {
        backup: { status: 'not_checked', details: 'No evidence' },
        clerk_auth: { status: 'not_checked', details: 'Not verified' },
        database: { status: 'pass', details: 'SELECT 1 OK' },
      },
    }) });
    render(<ProductionReadinessPage />);
    await waitFor(() => expect(screen.getByText('Overall Status: OPERATIONAL')).not.toBeNull());
    expect(screen.getByText('Backup Verification')).not.toBeNull();
  });

  it('shows loading then error on fetch failure', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('fail'));
    render(<ProductionReadinessPage />);
    await waitFor(() => expect(screen.getByText('fail')).not.toBeNull());
  });

  it('refresh button triggers fetch (button present)', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ overall_status: 'not_checked', checks: {} }) });
    render(<ProductionReadinessPage />);
    await waitFor(() => expect(screen.getByText('Refresh')).not.toBeNull());
  });
});
