import type { ReactNode } from "react";

interface Props {
  title?: ReactNode;
  eyebrow?: string;
  subtitle?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Panel({ title, eyebrow, subtitle, right, children, className = "" }: Props) {
  return (
    <section className={`themed overflow-hidden rounded-xl border border-border bg-surface shadow-sm ${className}`}>
      {(title || right) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0">
            {eyebrow && (
              <div className="mb-1 text-[11px] uppercase tracking-eyebrow text-faint">{eyebrow}</div>
            )}
            {title && <h2 className="font-display text-[17px] leading-tight text-text">{title}</h2>}
            {subtitle && <p className="mt-1 text-xs text-muted">{subtitle}</p>}
          </div>
          {right && <div className="text-xs text-muted">{right}</div>}
        </header>
      )}
      <div className="px-5 py-5">{children}</div>
    </section>
  );
}
