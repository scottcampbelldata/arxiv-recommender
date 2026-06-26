import type { ReactNode } from "react";

interface Props {
  label: string;
  value: string;
  unit?: string;
  sub?: ReactNode;
}

export function KpiCard({ label, value, unit, sub }: Props) {
  return (
    <div className="rounded-md border border-border bg-surface px-5 py-4">
      <div className="text-xs uppercase tracking-[0.12em] text-muted">{label}</div>
      <div className="mt-3 flex items-baseline">
        <span className="font-mono text-[2rem] font-medium leading-none tracking-[-0.02em] tabular-nums text-text">
          {value}
        </span>
        {unit && <span className="ml-1.5 text-sm font-normal text-muted">{unit}</span>}
      </div>
      <div className="mt-2 h-4 text-xs text-muted">{sub}</div>
    </div>
  );
}
