import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { LoadingScreen, StatCard, TerminalCard, XPBar } from './TerminalCard';
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
