"use client";
import { useEffect, useState } from "react";
import type { Paper, RecResponse } from "@/lib/api";
import { similarPapers } from "@/lib/api";
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
        setError((e as Error).message ?? "request failed");
        setLoading(false);
      });
    return () => controller.abort();
  }, [paper, k, algo]);

  return (
    <div className="flex min-w-0 flex-col">
      <header className="border-b-2 border-accent pb-2">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-medium text-text">{label}</h3>
          <span className="rounded-full border border-border bg-surface px-2 py-0.5 font-mono text-[11px] text-muted">
            {data ? `${formatMs(data.latency_ms)} ms` : loading ? "..." : "-"}
          </span>
        </div>
        <p className="mt-1 text-xs text-muted">{description}</p>
      </header>
      <div className="mt-3 flex flex-col gap-2">
        {error && (
          <p className="rounded-md border border-border bg-surface px-3 py-2 text-xs text-red-400">
            {error}
          </p>
        )}
        {!data && loading && (
          <div className="space-y-2">
            {Array.from({ length: k }).map((_, i) => (
              <div key={i} className="h-[120px] animate-pulse rounded-md border border-border bg-surface" />
            ))}
          </div>
        )}
        {data?.items.map((item, idx) => (
          <RecCard key={`${algo}-${item.paper.paper_id}-${idx}`} item={item} rank={idx + 1} />
        ))}
      </div>
    </div>
  );
}
