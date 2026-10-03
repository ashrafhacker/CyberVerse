'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen w-full flex-col items-center justify-center p-8 text-center">
          <h2 className="mb-4 text-2xl font-bold text-red-500">Critical System Failure</h2>
          <p className="mb-8">{error.message || 'Something went completely wrong.'}</p>
          <button
            onClick={() => reset()}
            className="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
          >
            Reboot Application
          </button>
        </div>
      </body>
    </html>
  );
}
