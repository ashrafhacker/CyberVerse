import { ArrowUpRight, Clock, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface LibraryItem {
  id: string;
  title: string;
  description: string;
  category: string;
  resource_type: string;
  difficulty: string;
  provider: string | null;
  url: string | null;
  duration_minutes: number | null;
  tags: string[];
  is_free: boolean;
  view_count: number;
}

const TYPE_BADGE: Record<string, string> = {
  article: 'text-cyan-300 border-cyan-500/40 bg-cyan-500/10',
  video: 'text-violet-300 border-violet-500/40 bg-violet-500/10',
  course: 'text-amber-300 border-amber-500/40 bg-amber-500/10',
  book: 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10',
  lab: 'text-rose-300 border-rose-500/40 bg-rose-500/10',
  tool: 'text-sky-300 border-sky-500/40 bg-sky-500/10',
  podcast: 'text-fuchsia-300 border-fuchsia-500/40 bg-fuchsia-500/10',
};

const DIFFICULTY_DOT: Record<string, string> = {
  beginner: 'bg-green-400',
  intermediate: 'bg-amber-400',
  advanced: 'bg-orange-400',
  expert: 'bg-red-400',
};

export default function ResourceCard({ resource }: { resource: LibraryItem }) {
  return (
    <article className="terminal-card flex flex-col gap-3 p-5 transition-colors hover:border-cyber-primary">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className={cn('rounded border px-2 py-0.5 text-xs font-mono', TYPE_BADGE[resource.resource_type] ?? 'text-cyber-muted border-cyber-border')}>
            {resource.resource_type}
          </span>
          <span className="rounded border border-cyber-border px-2 py-0.5 text-xs font-mono text-cyber-muted">
            {resource.category}
          </span>
          <span className="flex items-center gap-1.5 font-mono text-xs text-cyber-muted" title={`${resource.difficulty} difficulty`}>
            <span className={cn('h-1.5 w-1.5 rounded-full', DIFFICULTY_DOT[resource.difficulty] ?? 'bg-cyber-muted')} />
            {resource.difficulty}
          </span>
        </div>
        {resource.is_free && (
          <span className="font-mono text-xs text-green-400">free</span>
        )}
      </div>

      <div>
        <h3 className="font-semibold text-cyber-primary">{resource.title}</h3>
        {resource.provider && (
          <p className="mt-0.5 font-mono text-xs text-cyber-muted">{resource.provider}</p>
        )}
      </div>

      <p className="flex-1 text-sm text-cyber-muted">{resource.description}</p>

      {resource.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {resource.tags.map((tag) => (
            <span key={tag} className="rounded bg-cyber-bg px-2 py-0.5 font-mono text-[11px] text-cyber-secondary">
              #{tag}
            </span>
          ))}
        </div>
      )}

      <div className="mt-auto flex items-center justify-between border-t border-cyber-border pt-3">
        {resource.duration_minutes ? (
          <span className="flex items-center gap-1 font-mono text-xs text-cyber-muted">
            <Clock className="h-3 w-3" />
            {Math.round(resource.duration_minutes / 60)}h
          </span>
        ) : (
          <span />
        )}
        {resource.url ? (
          <a
            href={resource.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 font-mono text-sm text-cyber-primary hover:text-cyber-secondary"
          >
            open <ExternalLink className="h-3.5 w-3.5" />
          </a>
        ) : (
          <span className="flex items-center gap-1 font-mono text-sm text-cyber-muted">
            in library <ArrowUpRight className="h-3.5 w-3.5" />
          </span>
        )}
      </div>
    </article>
  );
}
