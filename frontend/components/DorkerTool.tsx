'use client';

import { useState } from 'react';
import { Check, Copy, ExternalLink, Search } from 'lucide-react';
import {
  buildDork,
  buildSearchUrl,
  DORK_ENGINES,
  DORK_PRESETS,
  type DorkCategory,
  type DorkEngine,
} from '@/lib/dorker';

export default function DorkerTool() {
  const [category, setCategory] = useState<DorkCategory>('video');
  const [engine, setEngine] = useState<DorkEngine>('google');
  const [query, setQuery] = useState('');
  const [copied, setCopied] = useState(false);

  const placeholder = DORK_PRESETS.find((preset) => preset.id === category)?.placeholder ?? 'Search anything';
  const dork = buildDork(query, category);
  const url = buildSearchUrl(query, category, engine);

  function runSearch() {
    if (!url) return;
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  async function copyDork() {
    if (!dork) return;
    await navigator.clipboard.writeText(dork);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="terminal-card flex flex-col gap-5 p-5">
      <div>
        <p className="mb-2 font-mono text-xs text-cyber-muted">&gt; select filetype</p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {DORK_PRESETS.map((preset) => (
            <button
              key={preset.id}
              onClick={() => setCategory(preset.id)}
              className={`rounded-md border px-3 py-2 text-sm transition-colors ${
                category === preset.id
                  ? 'border-cyber-primary bg-cyber-primary/10 text-cyber-primary'
                  : 'border-cyber-border bg-cyber-surface/40 text-cyber-muted hover:border-cyber-primary/50 hover:text-cyber-primary'
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 font-mono text-xs text-cyber-muted">&gt; select search engine</p>
        <div className="flex flex-wrap gap-2">
          {DORK_ENGINES.map((candidate) => (
            <button
              key={candidate.id}
              onClick={() => setEngine(candidate.id)}
              className={`rounded-md border px-3 py-1.5 font-mono text-xs transition-colors ${
                engine === candidate.id
                  ? 'border-cyber-secondary bg-cyber-secondary/10 text-cyber-secondary'
                  : 'border-cyber-border bg-cyber-surface/40 text-cyber-muted hover:border-cyber-secondary/50 hover:text-cyber-secondary'
              }`}
            >
              {candidate.label}
            </button>
          ))}
        </div>
      </div>

      <form
        className="flex flex-col gap-3 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault();
          runSearch();
        }}
      >
        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={placeholder}
          aria-label="search query"
          className="flex-1 rounded-md border border-cyber-border bg-cyber-bg px-3 py-2 font-mono text-sm text-cyber-text outline-none transition-colors placeholder:text-cyber-muted/60 focus:border-cyber-primary"
        />
        <button
          type="submit"
          disabled={!url}
          className="terminal-button flex items-center justify-center gap-2 px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Search className="h-4 w-4" />
          Run Search
        </button>
      </form>

      <div className="rounded-md border border-cyber-border bg-cyber-bg/60 p-3">
        <div className="mb-2 flex items-center justify-between gap-3">
          <p className="font-mono text-xs text-cyber-muted">&gt; generated_dork.query</p>
          <button
            onClick={() => void copyDork()}
            disabled={!dork}
            className="terminal-button-ghost flex items-center gap-1.5 px-2 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-40"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-cyber-success" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? 'copied' : 'copy'}
          </button>
        </div>
        <p className="break-all font-mono text-xs leading-relaxed text-cyber-secondary">
          {dork || '&gt; enter a query to build the dork'}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-md px-3 py-2">
        <ExternalLink className="h-4 w-4 flex-shrink-0" />
        <span>
          Opens the generated query in {DORK_ENGINES.find((candidate) => candidate.id === engine)?.label ?? engine} —
          OSINT technique for educational use only, applied to sources you are authorized to inspect.
        </span>
      </div>
    </div>
  );
}
