import type { ReactNode } from "react";

interface Props {
  label: string;
  value: string;
  unit?: string;
  sub?: ReactNode;
  /** Optional identity colour (CSS colour string) for the accent rule. */
  accent?: string;
}

export function KpiCard({ label, value, unit, sub, accent }: Props) {
  return (
    <div className="themed relative overflow-hidden rounded-xl border border-border bg-surface px-5 py-4 shadow-sm">
      {accent && (
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-[3px]"
          style={{ background: accent }}
        />
      )}
      <div className="text-[11px] uppercase tracking-eyebrow text-faint">{label}</div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="font-mono text-[2rem] font-medium leading-none tracking-[-0.02em] tabular-nums text-text">
          {value}
        </span>
        {unit && <span className="text-sm font-normal text-muted">{unit}</span>}
      </div>
      <div className="mt-2 min-h-4 text-xs text-muted">{sub}</div>
    </div>
  );
}
