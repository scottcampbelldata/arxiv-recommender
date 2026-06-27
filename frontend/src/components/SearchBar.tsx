"use client";
import { useEffect, useRef, useState } from "react";
import type { Paper } from "@/lib/api";
import { searchPapers } from "@/lib/api";

interface Props {
  onPick: (paper: Paper) => void;
  picked: Paper | null;
}

export function SearchBar({ onPick, picked }: Props) {
  const [q, setQ] = useState("attention is all you need");
  const [results, setResults] = useState<Paper[]>([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const controller = new AbortController();
      searchPapers(q, 12, controller.signal)
        .then((rs) => {
          setResults(rs);
          setError(null);
          if (!picked && rs.length > 0) onPick(rs[0]);
        })
        .catch((e: unknown) => {
          if (e instanceof DOMException && e.name === "AbortError") return;
          setError((e as Error).message ?? "search failed");
        });
      return () => controller.abort();
    }, 220);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!wrapperRef.current) return;
      if (!wrapperRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <div ref={wrapperRef} className="relative">
      <label className="text-xs uppercase tracking-[0.12em] text-muted">Seed paper</label>
      <input
        type="text"
        value={q}
        placeholder="title or author, e.g. transformer, hinton, contrastive"
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        className="mt-1.5 w-full rounded-md border border-border bg-surface px-4 py-3 font-sans text-base text-text placeholder:text-muted focus:border-accent focus:outline-none"
      />
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
      {open && q.trim().length > 0 && results.length === 0 && !error && (
        <div className="absolute left-0 right-0 z-20 mt-1 rounded-md border border-border bg-surface px-3 py-2 text-sm text-muted shadow-2xl">
          No papers match “{q.trim()}”. Try fewer words or a topic — the corpus is
          CS arXiv papers from 2019 on, so older classics (e.g. ResNet, the original
          Transformer) aren’t included.
        </div>
      )}
      {open && results.length > 0 && (
        <div className="absolute left-0 right-0 z-20 mt-1 max-h-80 overflow-auto rounded-md border border-border bg-surface shadow-2xl">
          {results.map((p) => (
            <button
              key={p.paper_id}
              type="button"
              className="flex w-full items-start gap-3 border-b border-border/60 px-3 py-2 text-left last:border-0 hover:bg-surface-hover"
              onClick={() => {
                onPick(p);
                setOpen(false);
              }}
            >
              <div className="min-w-0 flex-1">
                <div className="line-clamp-1 text-sm text-text">{p.title}</div>
                <div className="line-clamp-1 text-xs text-muted">
                  {p.authors}
                  {p.publication_year ? ` , ${p.publication_year}` : ""}
                </div>
              </div>
              <span className="whitespace-nowrap font-mono text-xs text-muted">
                {p.cited_by_count.toLocaleString()} cites
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
