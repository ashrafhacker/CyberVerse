'use client';

import { Radar as RadarIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatNumber, radarPolygonPoints, radarRingPoints } from '@/lib/command-center';
import type { CCDayCell, CCSkillAxis } from '@/lib/command-center';

const RING_RADII = [90, 68, 45, 23];
const INTENSITY_CLASS = [
  'bg-cyber-border/70',
  'bg-cyber-primary/25',
  'bg-cyber-primary/50',
  'bg-cyber-primary/75',
  'bg-cyber-primary shadow-[0_0_8px_rgba(0,229,255,0.5)]',
];

export default function SkillsMatrix({
  axes,
  heatmap,
  hoursLogged,
  isMock,
}: {
  axes: CCSkillAxis[];
  heatmap: CCDayCell[];
  hoursLogged: number;
  isMock: boolean;
}) {
  const values = axes.map((a) => a.percent);
  const activeHours = heatmap.reduce((sum, cell) => sum + cell.activities, 0);

  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-cyber-border/60 bg-cyber-surface p-5 shadow-2xl">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <RadarIcon className="h-5 w-5 text-cyber-primary" />
          <h3 className="text-sm font-bold">Skills matrix</h3>
        </div>
        <span className="rounded-lg border border-cyber-border/60 bg-cyber-bg/60 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-cyber-muted">
          {isMock ? 'hex-profile · placeholder' : 'hex-profile'}
        </span>
      </div>

      <div className="flex justify-center rounded-xl border border-cyber-border/60 bg-cyber-bg/60 p-3 shadow-inner">
        <svg viewBox="0 0 240 240" className="h-56 w-56 text-cyber-border" role="img" aria-label="Skill proficiency radar">
          {RING_RADII.map((r) => (
            <polygon
              key={r}
              points={radarRingPoints(values.length, r)}
              fill="none"
              stroke="currentColor"
              strokeWidth="0.8"
              opacity={0.25 + (1 - r / 90) * 0.35}
            />
          ))}
          {axes.map((axis, i) => {
            const angle = (Math.PI * 2 * i) / Math.max(1, values.length) - Math.PI / 2;
            return (
              <line
                key={axis.slug}
                x1="120"
                y1="120"
                x2={120 + 90 * Math.cos(angle)}
                y2={120 + 90 * Math.sin(angle)}
                stroke="currentColor"
                strokeWidth="0.6"
                opacity="0.35"
              />
            );
          })}

          <polygon
            points={radarPolygonPoints(values)}
            fill="#00e5ff"
            fillOpacity="0.3"
            stroke="#00e5ff"
            strokeWidth="2"
          />
          {axes.map((axis, i) => {
            const angle = (Math.PI * 2 * i) / Math.max(1, values.length) - Math.PI / 2;
            const r = (Math.max(2, axis.percent) / 100) * 90;
            return (
              <circle
                key={axis.slug}
                cx={120 + r * Math.cos(angle)}
                cy={120 + r * Math.sin(angle)}
                r="3.5"
                fill="#e6e9f2"
              />
            );
          })}

          {axes.map((axis, i) => {
            const angle = (Math.PI * 2 * i) / Math.max(1, values.length) - Math.PI / 2;
            const lx = 120 + 112 * Math.cos(angle);
            const ly = 120 + 112 * Math.sin(angle);
            return (
              <text
                key={`${axis.slug}-label`}
                x={lx}
                y={ly}
                fontSize="8"
                fontFamily="monospace"
                textAnchor={lx > 128 ? 'start' : lx < 112 ? 'end' : 'middle'}
                dominantBaseline="middle"
                className="fill-cyber-text"
              >
                {axis.shortName}
              </text>
            );
          })}
        </svg>
      </div>

      <div className="space-y-3 font-mono text-[11px]">
        {axes.map((axis) => (
          <div key={axis.slug}>
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="truncate text-cyber-text">{axis.name}</span>
              <span className={axis.percent >= 85 ? 'font-bold text-cyber-primary' : 'font-bold text-cyber-muted'}>
                {axis.percent}%
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-cyber-border">
              <div
                className={cn(
                  'h-full rounded-full shadow-[0_0_8px_rgba(0,229,255,0.35)]',
                  axis.percent >= 85
                    ? 'bg-gradient-to-r from-cyber-primary to-cyber-secondary'
                    : 'bg-gradient-to-r from-cyber-secondary to-cyber-border',
                )}
                style={{ width: `${axis.percent}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-2.5 border-t border-cyber-border/40 pt-4">
        <div className="flex items-center justify-between font-mono text-[11px]">
          <span className="uppercase text-cyber-muted">30-day activity heatmap</span>
          <span className="font-bold text-cyber-primary">
            {hoursLogged}h logged · {activeHours} updates
          </span>
        </div>

        <div className="grid grid-cols-10 gap-1.5 rounded-xl border border-cyber-border/60 bg-cyber-bg/60 p-3 shadow-inner">
          {heatmap.map((cell) => (
            <div
              key={cell.date}
              title={cell.label}
              aria-label={cell.label}
              role="img"
              className={cn(
                'h-4 rounded-md',
                INTENSITY_CLASS[cell.intensity],
                cell.isToday && 'ring-1 ring-cyber-primary',
              )}
            />
          ))}
        </div>

        <div className="flex items-center justify-between px-1 font-mono text-[10px] text-cyber-muted">
          <span>Less</span>
          <div className="flex items-center gap-1.5">
            {INTENSITY_CLASS.slice(0, 5).map((cls, i) => (
              <span key={i} className={cn('h-3 w-3 rounded-md', cls)} />
            ))}
          </div>
          <span>More</span>
        </div>

        <p className="font-mono text-[10px] text-cyber-muted">
          {formatNumber(activeHours)} progress events · {formatNumber(heatmap.filter((c) => c.activities > 0).length)}/30
          active days
        </p>
      </div>
    </section>
  );
}