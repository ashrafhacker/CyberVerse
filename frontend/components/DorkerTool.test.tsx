import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DorkerTool from './DorkerTool';

describe('DorkerTool', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders all filetypes and engines', () => {
    render(<DorkerTool />);
    expect(screen.getByRole('button', { name: /TV\/Movies\/Video/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Books/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Software\/ISO\/DMG\/Games/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Google$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /FilePursuit/i })).toBeInTheDocument();
  });

  it('builds a dork with the selected filetype extensions', async () => {
    const user = userEvent.setup();
    render(<DorkerTool />);
    await user.type(screen.getByRole('textbox', { name: /search query/i }), 'The.Blacklist.S01');
    expect(screen.getByText(/\+\(mkv\|mp4\|avi\|mov\|mpg\|wmv\|divx\|mpeg\)/)).toBeInTheDocument();
    expect(screen.getByText(/intitle:index\.of/)).toBeInTheDocument();
  });

  it('omits extensions when Other is selected', async () => {
    const user = userEvent.setup();
    render(<DorkerTool />);
    await user.click(screen.getByRole('button', { name: /^Other$/i }));
    await user.type(screen.getByRole('textbox', { name: /search query/i }), 'something');
    expect(screen.getByText(/something/)).toBeInTheDocument();
    expect(screen.queryByText(/\+\(/)).not.toBeInTheDocument();
  });

  it('opens the search engine in a new tab on submit', async () => {
    const openMock = vi.spyOn(window, 'open').mockImplementation(() => null);
    const user = userEvent.setup();
    render(<DorkerTool />);
    await user.type(screen.getByRole('textbox', { name: /search query/i }), 'foo');
    await user.click(screen.getByRole('button', { name: /run search/i }));
    expect(openMock).toHaveBeenCalledTimes(1);
    expect(openMock.mock.calls[0][0]).toContain('https://www.google.com/search?q=');
  });

  it('uses the filepursuit url format when selected', async () => {
    const openMock = vi.spyOn(window, 'open').mockImplementation(() => null);
    const user = userEvent.setup();
    render(<DorkerTool />);
    await user.click(screen.getByRole('button', { name: /FilePursuit/i }));
    await user.type(screen.getByRole('textbox', { name: /search query/i }), 'foo bar');
    await user.click(screen.getByRole('button', { name: /run search/i }));
    expect(openMock.mock.calls[0][0]).toBe('https://filepursuit.com/search/foo+bar/type/video');
  });

  it('disables run search while the query is empty', () => {
    render(<DorkerTool />);
    expect(screen.getByRole('button', { name: /run search/i })).toBeDisabled();
  });
});
