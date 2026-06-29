"use client";
import { useEffect, useId, useRef, useState } from "react";
import type { Paper } from "@/lib/api";
import { searchPapers } from "@/lib/api";
import { CloseIcon, SearchIcon } from "./icons";

interface Props {
  onPick: (paper: Paper) => void;
  picked: Paper | null;
}

export function SearchBar({ onPick, picked }: Props) {
  const [q, setQ] = useState("attention is all you need");
  const [results, setResults] = useState<Paper[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [error, setError] = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  const listboxId = useId();
  const optionId = (i: number) => `${listboxId}-opt-${i}`;

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const controller = new AbortController();
    debounceRef.current = setTimeout(() => {
      searchPapers(q, 12, controller.signal)
        .then((rs) => {
          setResults(rs);
          setError(null);
          setActive(-1);
          if (!picked && rs.length > 0) onPick(rs[0]);
        })
        .catch((e: unknown) => {
          if (e instanceof DOMException && e.name === "AbortError") return;
          setError((e as Error).message ?? "Search failed");
        });
    }, 220);
    return () => {
      controller.abort();
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  // Keep the active option scrolled into view.
  useEffect(() => {
    if (active < 0 || !listRef.current) return;
    listRef.current.querySelector(`#${CSS.escape(optionId(active))}`)?.scrollIntoView({ block: "nearest" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  function choose(p: Paper) {
    onPick(p);
    setOpen(false);
    setActive(-1);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!open) setOpen(true);
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      if (open && active >= 0 && results[active]) {
        e.preventDefault();
        choose(results[active]);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
      setActive(-1);
    }
  }

  const showNoMatch = open && q.trim().length > 0 && results.length === 0 && !error;
  const showList = open && results.length > 0;

  return (
    <div ref={wrapperRef} className="relative">
      <label id={`${listboxId}-label`} htmlFor={`${listboxId}-input`} className="text-[11px] uppercase tracking-eyebrow text-faint">
        Seed paper
      </label>
      <div className="relative mt-1.5">
        <SearchIcon
          aria-hidden
          className="pointer-events-none absolute left-3.5 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-faint"
        />
        <input
          id={`${listboxId}-input`}
          type="search"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? optionId(active) : undefined}
          aria-labelledby={`${listboxId}-label`}
          autoComplete="off"
          spellCheck={false}
          value={q}
          placeholder="Title or author — e.g. transformer, Hinton, contrastive"
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          className="themed w-full rounded-lg border border-border bg-surface-2 py-3 pl-11 pr-10 font-sans text-base text-text placeholder:text-faint focus:border-accent focus:bg-surface focus:outline-none focus:ring-2 focus:ring-ring/40 [&::-webkit-search-cancel-button]:appearance-none"
        />
        {q.length > 0 && (
          <button
            type="button"
            aria-label="Clear search"
            onClick={() => {
              setQ("");
              setResults([]);
              setOpen(true);
            }}
            className="absolute right-2.5 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-faint transition-colors hover:bg-surface-2 hover:text-text"
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        )}
      </div>

      {error && <p className="mt-1.5 text-xs text-algo-als">{error}</p>}

      {showNoMatch && (
        <div className="absolute left-0 right-0 z-20 mt-1.5 rounded-lg border border-border bg-surface px-4 py-3 text-sm text-muted shadow-pop">
          No papers match “{q.trim()}”. Try fewer words or a topic — the corpus is CS arXiv papers
          from 2019 on, so older classics (ResNet, the original Transformer) aren’t included.
        </div>
      )}

      {showList && (
        <ul
          ref={listRef}
          id={listboxId}
          role="listbox"
          aria-label="Matching papers"
          className="absolute left-0 right-0 z-20 mt-1.5 max-h-[22rem] overflow-auto rounded-lg border border-border bg-surface py-1 shadow-pop"
        >
          {results.map((p, i) => {
            const isActive = i === active;
            const isPicked = picked?.paper_id === p.paper_id;
            return (
              <li
                key={p.paper_id}
                id={optionId(i)}
                role="option"
                aria-selected={isPicked}
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => choose(p)}
                className={`flex cursor-pointer items-start gap-3 px-3.5 py-2.5 ${
                  isActive ? "bg-surface-2" : ""
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="line-clamp-1 text-sm text-text">
                    {p.title}
                    {isPicked && <span className="ml-2 text-[11px] text-accent">selected</span>}
                  </div>
                  <div className="line-clamp-1 text-xs text-muted">
                    {p.authors}
                    {p.publication_year ? ` · ${p.publication_year}` : ""}
                  </div>
                </div>
                <span className="mt-0.5 whitespace-nowrap font-mono text-xs text-faint">
                  {p.cited_by_count.toLocaleString()} cites
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
