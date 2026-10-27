import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiMock = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn() },
  clearTokens: vi.fn(),
  getTokens: vi.fn(),
  setTokens: vi.fn(),
  setTokenRefresher: vi.fn(),
}));

vi.mock('@/lib/api', () => apiMock);

import AIMentorWidget from './AIMentorWidget';

const openPanel = async () => {
  await userEvent.click(screen.getByRole('button', { name: /AI Mentor/i }));
  await screen.findByText(/Greetings Agent!/);
};

describe('AIMentorWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the launcher and opens the mentor panel with its greeting', async () => {
    render(<AIMentorWidget />);
    expect(screen.getByRole('button', { name: /AI Mentor/i })).toBeInTheDocument();

    await openPanel();
    expect(screen.getByPlaceholderText('Ask AI Mentor anything...')).toBeInTheDocument();
    expect(screen.getByText('CyberVerse AI Mentor')).toBeInTheDocument();
  });

  it('posts chat history to /ai/chat and renders the reply', async () => {
    apiMock.api.post.mockResolvedValue({ success: true, data: { reply: 'Reply from mentor' } });
    render(<AIMentorWidget />);
    await openPanel();

    const input = screen.getByPlaceholderText('Ask AI Mentor anything...');
    await userEvent.type(input, 'What is SQL injection?{Enter}');

    await waitFor(() => expect(screen.getByText('Reply from mentor')).toBeInTheDocument());
    expect(apiMock.api.post).toHaveBeenCalledWith(
      '/ai/chat',
      expect.objectContaining({
        messages: expect.arrayContaining([
          { role: 'user', content: 'What is SQL injection?' },
        ]),
      })
    );
  });

  it('shows a mentor-toned outage line instead of raw HTTP jargon on failure', async () => {
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    apiMock.api.post.mockRejectedValue(new Error('Request failed with status 404'));
    render(<AIMentorWidget />);
    await openPanel();

    const input = screen.getByPlaceholderText('Ask AI Mentor anything...');
    await userEvent.type(input, 'hello{Enter}');

    await waitFor(() =>
      expect(screen.getByText(/comms link to the knowledge core is jammed/)).toBeInTheDocument()
    );
    expect(screen.queryByText('Request failed with status 404')).not.toBeInTheDocument();
    expect(errSpy).toHaveBeenCalledWith('AI mentor request failed:', expect.any(Error));
    errSpy.mockRestore();
  });
});
