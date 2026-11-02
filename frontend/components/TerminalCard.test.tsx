import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AuthRequired, AuthUnavailable, LoadingScreen, StatCard, TerminalCard, XPBar } from './TerminalCard';
import { Target } from 'lucide-react';

describe('TerminalCard', () => {
  it('renders title and children', () => {
    render(
      <TerminalCard title="briefing">
        <p>mission content</p>
      </TerminalCard>,
    );
    expect(screen.getByText('briefing')).toBeInTheDocument();
    expect(screen.getByText('mission content')).toBeInTheDocument();
  });

  it('renders without title bar', () => {
    render(<TerminalCard>content</TerminalCard>);
    expect(screen.getByText('content')).toBeInTheDocument();
    expect(document.querySelectorAll('.border-b')).toHaveLength(0);
  });

  it('applies custom className', () => {
    render(<TerminalCard className="custom-panel">x</TerminalCard>);
    expect(screen.getByText('x').parentElement).toHaveClass('terminal-card', 'custom-panel');
  });
});

describe('StatCard', () => {
  it('renders label and value', () => {
    render(<StatCard label="XP" value={1500} />);
    expect(screen.getByText('XP')).toBeInTheDocument();
    expect(screen.getByText('1500')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    render(<StatCard label="Missions" value={3} icon={Target} />);
    expect(document.querySelector('svg')).toBeInTheDocument();
  });
});

describe('XPBar', () => {
  it('shows level and xp ratio', () => {
    render(<XPBar xp={250} level={4} xpForNext={1000} />);
    expect(screen.getByText('LEVEL 4')).toBeInTheDocument();
    expect(screen.getByText('250 / 1000 XP')).toBeInTheDocument();
  });

  it('caps the progress bar at 100%', () => {
    render(<XPBar xp={5000} level={9} xpForNext={1000} />);
    const bar = document.querySelector('.bg-gradient-to-r') as HTMLElement;
    expect(bar.style.width).toBe('100%');
  });

  it('computes partial progress', () => {
    render(<XPBar xp={500} level={1} xpForNext={1000} />);
    const bar = document.querySelector('.bg-gradient-to-r') as HTMLElement;
    expect(bar.style.width).toBe('50%');
  });
});

describe('LoadingScreen', () => {
  it('renders connection message', () => {
    render(<LoadingScreen />);
    expect(screen.getByText('> establishing secure connection...')).toBeInTheDocument();
  });
});

describe('AuthRequired', () => {
  it('shows a sign-in prompt instead of an endless connection screen', () => {
    render(<AuthRequired />);
    expect(screen.getByText('You need to sign in')).toBeInTheDocument();
    expect(screen.queryByText('> establishing secure connection...')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
  });
});

describe('AuthUnavailable', () => {
  it('shows the reason and a retry action', () => {
    const onRetry = vi.fn();
    render(<AuthUnavailable message="Server unreachable" onRetry={onRetry} />);
    expect(screen.getByText('Could not verify your session')).toBeInTheDocument();
    expect(screen.getByText('Server unreachable')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('omits the retry button when no handler is given', () => {
    render(<AuthUnavailable />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
