import React, { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.error('Admin UI error boundary caught:', error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded border border-red-700 bg-red-950/40 p-6 text-center">
          <h3 className="text-red-300 font-semibold">Admin component error</h3>
          <p className="text-sm text-red-200/70 mt-1">Retry or reload the page.</p>
          <button
            className="mt-3 rounded bg-red-600 px-4 py-2 text-sm font-medium hover:bg-red-500"
            onClick={() => this.setState({ hasError: false })}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export function LoadingState({ label = 'Loading...' }: { label?: string }) {
  return (
    <div className="rounded bg-zinc-900/30 border border-zinc-800 p-8 text-center animate-pulse">
      <div className="mx-auto h-8 w-8 rounded-full border-2 border-zinc-700 border-t-blue-400 animate-spin" />
      <p className="mt-3 text-sm text-zinc-400">{label}</p>
    </div>
  );
}

export function EmptyState({ title, message }: { title: string; message?: string }) {
  return (
    <div className="rounded border border-zinc-800 bg-zinc-950/20 p-8 text-center">
      <h4 className="text-zinc-300 font-medium">{title}</h4>
      {message && <p className="text-sm text-zinc-500 mt-1">{message}</p>}
    </div>
  );
}

export function RetryButton({ onRetry }: { onRetry: () => void }) {
  return (
    <button
      onClick={onRetry}
      className="rounded bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400/40"
    >
      Retry
    </button>
  );
}
