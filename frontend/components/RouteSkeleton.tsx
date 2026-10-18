import { TerminalCard } from '@/components/TerminalCard';

/**
 * Shared route-level skeleton. Rendered by Next.js while a client page
 * hydrates (route loading files under app/), replacing the blank-frame flash
 * with a terminal-themed pulse that matches the rest of the UI.
 */
export default function RouteSkeleton({ title = 'loading' }: { title?: string }) {
  return (
    <div className="mx-auto max-w-5xl animate-pulse px-6 py-10">
      <TerminalCard title={`${title}://fetching`}>
        <div className="space-y-4">
          <div className="h-7 w-2/3 rounded bg-cyber-border/60" />
          <div className="h-4 w-full rounded bg-cyber-border/40" />
          <div className="h-4 w-5/6 rounded bg-cyber-border/40" />
          <div className="grid gap-3 pt-2 sm:grid-cols-3">
            <div className="h-20 rounded bg-cyber-border/40" />
            <div className="h-20 rounded bg-cyber-border/40" />
            <div className="h-20 rounded bg-cyber-border/40" />
          </div>
          <div className="h-4 w-1/2 rounded bg-cyber-border/30" />
          <div className="h-4 w-2/3 rounded bg-cyber-border/30" />
        </div>
      </TerminalCard>
    </div>
  );
}
