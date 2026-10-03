import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const authMock = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));

vi.mock('@/lib/auth', () => authMock);
vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    'aria-label'?: string;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
}));

import Navbar from './Navbar';
import type { User } from '@/lib/types';

function userWithRole(role: User['role']): User {
  return {
    id: 'user-1',
    email: 'neo@cyberverse.io',
    full_name: 'Neo Anderson',
    role,
    status: 'active',
    is_verified: true,
    is_2fa_enabled: false,
    provider: 'local',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
}

beforeEach(() => {
  authMock.useAuth.mockReturnValue({ user: null, logout: vi.fn() });
});

describe('Navbar', () => {
  it('shows minimal nav when logged out', () => {
    render(<Navbar />);
    expect(document.querySelector('header')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /log in/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /dashboard/i })).not.toBeInTheDocument();
  });

  it('shows student navigation without admin links', () => {
    authMock.useAuth.mockReturnValue({ user: userWithRole('student'), logout: vi.fn() });
    render(<Navbar />);

    expect(screen.getByRole('link', { name: /dashboard/i })).toHaveAttribute('href', '/dashboard');
    expect(screen.getByRole('link', { name: /courses/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /missions/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /leaderboard/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /profile/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /admin/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /instructor/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /log out/i })).toBeInTheDocument();
  });

  it('shows instructor link for instructor role', () => {
    authMock.useAuth.mockReturnValue({ user: userWithRole('instructor'), logout: vi.fn() });
    render(<Navbar />);
    expect(screen.getByRole('link', { name: /instructor/i })).toHaveAttribute('href', '/instructor');
    expect(screen.queryByRole('link', { name: /admin/i })).not.toBeInTheDocument();
  });

  it('shows admin link for super_admin role', () => {
    authMock.useAuth.mockReturnValue({ user: userWithRole('super_admin'), logout: vi.fn() });
    render(<Navbar />);
    expect(screen.getByRole('link', { name: /admin/i })).toHaveAttribute('href', '/admin');
    expect(screen.getByRole('link', { name: /instructor/i })).toBeInTheDocument();
  });
});
