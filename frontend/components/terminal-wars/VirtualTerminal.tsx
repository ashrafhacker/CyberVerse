'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export interface ShellChallenge {
  slug: string;
  title: string;
  story: string;
  hint: string | null;
  flag_hint_prefix: string | null;
  points: number;
}

export interface SubmitResult {
  ok: boolean;
  msg: string;
}

type LineKind = 'sys' | 'out' | 'err' | 'ok' | 'cmd';

interface Line {
  id: number;
  kind: LineKind;
  text: string;
}

const KIND_CLASS: Record<LineKind, string> = {
  sys: 'text-cyber-primary',
  out: 'text-cyber-muted',
  err: 'text-red-400',
  ok: 'text-emerald-400',
  cmd: 'text-cyber-text',
};

let lineSeq = 0;

interface VirtualTerminalProps {
  challenge: ShellChallenge | null;
  solved: boolean;
  /** Sends the flag to the command center (server-side validation). */
  submitFlag: (value: string) => Promise<SubmitResult>;
}

/**
 * In-browser simulated shell for Terminal Wars.
 * Bounded command set against a per-op virtual filesystem; flag delivery is
 * always validated server-side through the parent's submitFlag handler.
 */
export default function VirtualTerminal({ challenge, solved, submitFlag }: VirtualTerminalProps) {
  const [lines, setLines] = useState<Line[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [histIdx, setHistIdx] = useState(-1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Track solved without re-triggering the boot effect (which would wipe terminal output)
  const solvedRef = useRef(solved);
  solvedRef.current = solved;

  const push = useCallback((kind: LineKind, text: string) => {
    setLines((prev) => [...prev, { id: ++lineSeq, kind, text }]);
  }, []);

  const promptPath = challenge ? `/ops/${challenge.slug}` : '~';

  // Boot banner + mission brief on select
  useEffect(() => {
    lineSeq = 0;
    setLines([]);
    push('sys', 'CyberVerse Secure Shell v2.6 — encrypted channel established.');
    push('out', 'Type `help` for available commands.');
    if (challenge) {
      push('sys', '');
      push('sys', `── OP BRIEF: ${challenge.title.toUpperCase()} ${'[+' + challenge.points + ' XP]'}`);
      push('out', challenge.story);
      if (solvedRef.current) push('ok', 'This op is already cleared — replay for practice, points are kept.');
      else push('out', 'When you crack it, deliver the flag: `flag <value>`.');
    } else {
      push('sys', '');
      push('out', 'No op selected. Choose one from the ops roster.');
    }
    setHistory([]);
    setHistIdx(-1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [challenge?.slug]);

  // Autoscroll
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  const catFile = (name: string): string[] => {
    if (!challenge) return [`cat: ${name}: no active op`];
    const files: Record<string, string> = {
      'brief.txt': challenge.story,
      'objective.txt': 'Recover the access token (flag) and deliver it via `flag <value>`.',
      ...(challenge.hint ? { 'hint.txt': challenge.hint } : {}),
    };
    if (files[name]) return files[name].split('\n');
    return [`cat: ${name}: no such file in this op`];
  };

  const run = async (raw: string) => {
    const cmd = raw.trim();
    push('cmd', `agent@cyberverse:${promptPath}$ ${cmd}`);
    if (!cmd) return;

    setHistory((h) => [...h, cmd]);
    setHistIdx(-1);

    const [name, ...args] = cmd.split(/\s+/);
    const arg = args.join(' ');

    switch (name.toLowerCase()) {
      case 'help':
        push('out', 'Available commands:');
        push('out', '  ls              list op files');
        push('out', '  cat <file>      read brief.txt / objective.txt / hint.txt');
        push('out', '  hint            show the op hint (if one exists)');
        push('out', '  flag <value>    deliver the flag to command center');
        push('out', '  pwd · whoami · date · history · clear');
        break;

      case 'ls': {
        if (!challenge) {
          push('err', 'ls: no active op — select one from the roster');
          break;
        }
        const names = ['brief.txt', 'objective.txt'];
        if (challenge.hint) names.push('hint.txt');
        push('out', names.join('   '));
        break;
      }

      case 'cat': {
        if (!arg) {
          push('err', 'usage: cat <file>');
          break;
        }
        catFile(arg).forEach((l) => push('out', l));
        break;
      }

      case 'hint': {
        if (!challenge) {
          push('err', 'hint: no active op');
        } else if (challenge.hint) {
          push('sys', `HINT: ${challenge.hint}`);
        } else {
          push('out', 'No hint issued for this op — you are on your own, operator.');
        }
        break;
      }

      case 'flag':
      case 'submit': {
        if (!arg) {
          push('err', `usage: ${name} <value>`);
          break;
        }
        if (!challenge) {
          push('err', 'flag: no active op — select one from the roster');
          break;
        }
        if (solved) {
          push('ok', 'Op already cleared — no additional points.');
          break;
        }
        setBusy(true);
        push('sys', 'Transmitting to command center…');
        try {
          const res = await submitFlag(arg);
          if (res.ok) {
            push('ok', `✔ ${res.msg}`);
            push('ok', 'OP CLEARED. XP credited by command center.');
          } else {
            push('err', `✘ ${res.msg}`);
          }
        } catch (e) {
          push('err', `✘ ${e instanceof Error && e.message ? e.message : 'channel error — retry'}`);
        } finally {
          setBusy(false);
        }
        break;
      }

      case 'pwd':
        push('out', promptPath);
        break;

      case 'whoami':
        push('out', 'agent');
        break;

      case 'date':
        push('out', new Date().toString());
        break;

      case 'history':
        history.forEach((h, i) => push('out', `  ${i + 1}  ${h}`));
        break;

      case 'clear':
        setLines([]);
        break;

      case 'cd':
        push('err', 'cd: sandbox policy — you operate inside your assigned op directory');
        break;

      case 'sudo':
        push('err', 'sudo: nice try. There is no root in CyberVerse.');
        break;

      default:
        push('err', `command not found: ${name} (type \`help\`)`);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !busy) {
      const v = input;
      setInput('');
      void run(v);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (!history.length) return;
      const next = histIdx === -1 ? history.length - 1 : Math.max(0, histIdx - 1);
      setHistIdx(next);
      setInput(history[next]);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (histIdx === -1) return;
      const next = histIdx + 1;
      if (next >= history.length) {
        setHistIdx(-1);
        setInput('');
      } else {
        setHistIdx(next);
        setInput(history[next]);
      }
    } else if (e.key === 'l' && e.ctrlKey) {
      e.preventDefault();
      setLines([]);
    }
  };

  return (
    <div
      className="relative flex h-full min-h-[420px] flex-col overflow-hidden rounded-xl border border-cyber-border/70 bg-black/85"
      onClick={() => inputRef.current?.focus()}
    >
      {/* scanlines */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-10 opacity-[0.15]"
        style={{
          backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,229,255,0.35) 0px, rgba(0,229,255,0.35) 1px, transparent 1px, transparent 3px)',
        }}
      />

      <div
        ref={scrollRef}
        role="log"
        aria-live="polite"
        aria-label="Terminal output"
        className="relative z-0 flex-1 overflow-y-auto p-4 font-mono text-[13px] leading-relaxed"
      >
        {lines.map((l) => (
          <div
            key={l.id}
            className={`${KIND_CLASS[l.kind]} whitespace-pre-wrap break-words`}
          >
            {l.text || '\u00A0'}
          </div>
        ))}

        <div className="flex items-center gap-1 text-cyber-primary">
          <span className="shrink-0">agent@cyberverse:{promptPath}$</span>
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={busy}
            spellCheck={false}
            autoComplete="off"
            aria-label="Terminal command input"
            className="min-w-0 flex-1 border-none bg-transparent font-mono text-[13px] text-cyber-primary caret-cyber-primary outline-none placeholder:text-cyber-muted/60 disabled:opacity-50"
            placeholder={busy ? 'transmitting…' : 'type here…'}
          />
        </div>
      </div>
    </div>
  );
}
