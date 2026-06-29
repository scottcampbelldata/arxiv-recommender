"use client";
import { useEffect, useState } from "react";
import type { Paper, RecResponse } from "@/lib/api";
import { similarPapers } from "@/lib/api";
import { algoColor } from "@/lib/algorithms";
import { formatMs } from "@/lib/format";
import { RecCard } from "./RecCard";

interface Props {
  paper: Paper | null;
  k: number;
  algo: string;
  label: string;
  description: string;
}

export function AlgoColumn({ paper, k, algo, label, description }: Props) {
  const [data, setData] = useState<RecResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const color = algoColor(algo);

  useEffect(() => {
    if (!paper) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    similarPapers(paper.paper_id, k, algo, controller.signal)
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError((e as Error).message ?? "Request failed");
        setLoading(false);
      });
    return () => controller.abort();
  }, [paper, k, algo]);

  return (
    <section className="flex min-w-0 flex-col" aria-label={`${label} recommendations`}>
      <header className="border-t-2 pb-2.5 pt-2" style={{ borderColor: color }}>
        <div className="flex items-center justify-between gap-2">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-text">
            <span className="h-2 w-2 rounded-full" style={{ background: color }} aria-hidden />
            {label}
          </h3>
          <span className="rounded-full border border-border bg-surface px-2 py-0.5 font-mono text-[11px] tabular-nums text-muted">
            {data ? `${formatMs(data.latency_ms)} ms` : loading ? "···" : "—"}
          </span>
        </div>
        <p className="mt-1.5 text-xs leading-snug text-muted">{description}</p>
      </header>

      <div className="mt-3 flex flex-col gap-2.5">
        {error && (
          <p className="rounded-lg border border-algo-als/30 bg-surface px-3 py-2 text-xs text-algo-als">
            {error}
          </p>
        )}
        {!paper && !loading && (
          <p className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-xs text-faint">
            Pick a seed to see results
          </p>
        )}
        {!data && loading &&
          Array.from({ length: Math.min(k, 6) }).map((_, i) => (
            <div
              key={i}
              className="h-[116px] animate-pulse rounded-lg border border-border bg-surface-2 motion-reduce:animate-none"
            />
          ))}
        {data?.items.map((item, idx) => (
          <RecCard key={`${algo}-${item.paper.paper_id}-${idx}`} item={item} rank={idx + 1} accent={color} />
        ))}
      </div>
    </section>
  );
}
