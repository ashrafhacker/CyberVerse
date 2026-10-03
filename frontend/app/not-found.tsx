import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center space-y-6 text-center">
      <h2 className="text-4xl font-bold text-cyber-primary">404 - Area Restricted</h2>
      <p className="text-cyber-muted max-w-md">
        The sector you are trying to access does not exist or has been wiped from the mainframe.
      </p>
      <Link href="/" className="terminal-button">
        Return to Base
      </Link>
    </div>
  );
}
