import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import ResourceCard, { type LibraryItem } from './ResourceCard';

const resource: LibraryItem = {
  id: 'abc',
  title: 'OWASP Top 10',
  description: 'The ten most critical web application risks.',
  category: 'defensive',
  resource_type: 'article',
  difficulty: 'beginner',
  provider: 'OWASP',
  url: 'https://owasp.org/www-project-top-ten/',
  duration_minutes: 120,
  tags: ['web', 'owasp'],
  is_free: true,
  view_count: 0,
};

describe('ResourceCard', () => {
  it('renders title, provider, and description', () => {
    render(<ResourceCard resource={resource} />);
    expect(screen.getByText('OWASP Top 10')).toBeInTheDocument();
    expect(screen.getByText('OWASP')).toBeInTheDocument();
    expect(screen.getByText('The ten most critical web application risks.')).toBeInTheDocument();
  });

  it('shows type, category, and difficulty badges', () => {
    render(<ResourceCard resource={resource} />);
    expect(screen.getByText('article')).toBeInTheDocument();
    expect(screen.getByText('defensive')).toBeInTheDocument();
    expect(screen.getByText('beginner')).toBeInTheDocument();
    expect(screen.getByText('free')).toBeInTheDocument();
  });

  it('renders tags as hashtags', () => {
    render(<ResourceCard resource={resource} />);
    expect(screen.getByText('#web')).toBeInTheDocument();
    expect(screen.getByText('#owasp')).toBeInTheDocument();
  });

  it('links out to the resource URL in a new tab', () => {
    render(<ResourceCard resource={resource} />);
    const link = screen.getByRole('link', { name: /open/i });
    expect(link).toHaveAttribute('href', 'https://owasp.org/www-project-top-ten/');
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('falls back to "in library" when no URL exists', () => {
    render(<ResourceCard resource={{ ...resource, url: null }} />);
    expect(screen.getByText('in library')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /open/i })).not.toBeInTheDocument();
  });
});
