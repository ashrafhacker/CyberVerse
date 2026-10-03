'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[400px] w-full flex-col items-center justify-center space-y-4 rounded-lg border border-cyber-border bg-cyber-bg/50 p-8 text-center backdrop-blur">
      <div className="text-cyber-danger text-4xl">⚠</div>
      <h2 className="text-xl font-bold text-cyber-primary">A system error occurred</h2>
      <p className="text-cyber-muted max-w-md">
        {error.message || 'The CyberVerse neural link experienced an unexpected interruption.'}
      </p>
      <button
        onClick={() => reset()}
        className="terminal-button mt-4"
      >
        Reboot System
      </button>
    </div>
  );
}
