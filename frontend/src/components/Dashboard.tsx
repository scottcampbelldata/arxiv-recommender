"use client";
import { useState } from "react";
import type { Paper } from "@/lib/api";
import { COLUMN_ALGORITHMS, LEADERBOARD_ORDER, ALGO_LABEL, algoColor } from "@/lib/algorithms";
import { LEADERBOARD } from "@/lib/leaderboard";
import { formatLift, formatMs } from "@/lib/format";
import { AlgoColumn } from "./AlgoColumn";
import { AppHeader } from "./AppHeader";
import { KpiCard } from "./KpiCard";
import { Leaderboard } from "./Leaderboard";
import { Panel } from "./Panel";
import { SearchBar } from "./SearchBar";
import { SeedCard } from "./SeedCard";

const by = (a: string) => LEADERBOARD.find((r) => r.algorithm === a);

export function Dashboard() {
  const [paper, setPaper] = useState<Paper | null>(null);
  const [k, setK] = useState(10);

  const hybrid = by("hybrid");
  const pop = by("popularity");
  const mapLift = hybrid && pop ? hybrid["map@k"] / Math.max(pop["map@k"], 1e-9) : null;
  const hitLift = hybrid && pop ? hybrid["hit_rate@k"] / Math.max(pop["hit_rate@k"], 1e-9) : null;

  return (
    <div className="themed min-h-screen bg-bg">
      <AppHeader />
      <main className="mx-auto max-w-shell space-y-7 px-5 py-8 sm:py-10">
        {/* Hero: text on the left, the headline metrics on the right, so the row
            reads as one balanced unit instead of leaving the width empty. */}
        <section className="reveal grid items-center gap-x-10 gap-y-8 lg:grid-cols-2">
          <div>
            <p className="text-[11px] uppercase tracking-eyebrow text-faint">
              Paper recommender · OpenAlex computer-science corpus
            </p>
            <h1 className="mt-3 font-display text-[2.1rem] font-medium leading-[1.08] tracking-[-0.01em] text-text sm:text-[2.75rem]">
              Find the next paper{" "}
              <span className="italic text-accent">worth reading.</span>
            </h1>
            <p className="mt-4 text-[15px] leading-relaxed text-muted">
              Pick any arXiv ML paper and four models return their most-similar work, side by side:
              a tuned hybrid, a sentence-transformer, classic TF-IDF, and a citation-graph model, all
              measured against a popularity baseline. Latency badges are live calls; the leaderboard
              is held-out evaluation with bootstrap confidence intervals.
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 font-mono text-sm">
              <Stat label="MAP@10" value={hybrid ? hybrid["map@k"].toFixed(3) : "-"} />
              <Dot />
              <Stat label="vs popularity" value={mapLift ? formatLift(mapLift) : "-"} />
              <Dot />
              <Stat label="p95" value={hybrid ? `${formatMs(hybrid.latency_p95_ms)} ms` : "-"} />
            </div>

            <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted">
              {LEADERBOARD_ORDER.map((key) => (
                <li key={key} className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full" style={{ background: algoColor(key) }} aria-hidden />
                  {ALGO_LABEL[key]}
                  {key === "popularity" && <span className="text-faint">(baseline)</span>}
                </li>
              ))}
            </ul>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <KpiCard
              label="Best MAP@10 · hybrid"
              value={hybrid ? hybrid["map@k"].toFixed(3) : "-"}
              accent={algoColor("hybrid")}
              sub={mapLift ? <span><span className="text-text">{formatLift(mapLift)}</span> the popularity baseline</span> : null}
            />
            <KpiCard
              label="Hit-rate@10 · hybrid"
              value={hybrid ? hybrid["hit_rate@k"].toFixed(2) : "-"}
              sub={hitLift ? <span>finds a citation <span className="text-text">{formatLift(hitLift)}</span> as often</span> : null}
            />
            <KpiCard
              label="p95 latency · hybrid"
              value={hybrid ? formatMs(hybrid.latency_p95_ms) : "-"}
              unit="ms"
              sub={<span>top-10 over 28,436 papers</span>}
            />
            <KpiCard
              label="Catalogue"
              value="28,436"
              sub={<span>CS arXiv papers since 2019</span>}
            />
          </div>
        </section>

        <div className="reveal" style={{ animationDelay: "120ms" }}>
          <Panel
            eyebrow="Step 1"
            title="Choose a seed paper"
            subtitle="Type a title or author. The FastAPI service does the lookup."
            right={
              <label className="flex items-center gap-2">
                <span className="uppercase tracking-eyebrow text-faint">top-k</span>
                <select
                  value={k}
                  onChange={(e) => setK(parseInt(e.target.value, 10))}
                  className="themed rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-text focus:border-accent focus:outline-none focus:ring-2 focus:ring-ring/40"
                >
                  {[5, 8, 10, 15, 20].map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </label>
            }
          >
            <SearchBar onPick={setPaper} picked={paper} />
            {paper && (
              <div className="mt-5">
                <SeedCard paper={paper} />
              </div>
            )}
          </Panel>
        </div>

        <section className="reveal space-y-3" style={{ animationDelay: "180ms" }}>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <div className="text-[11px] uppercase tracking-eyebrow text-faint">Step 2</div>
              <h2 className="mt-1 font-display text-[17px] text-text">Recommendations, side by side</h2>
            </div>
            <p className="text-xs text-muted">
              {paper
                ? `for “${paper.title.slice(0, 72)}${paper.title.length > 72 ? "…" : ""}”`
                : "pick a seed paper above"}
            </p>
          </div>
          <div className="grid grid-cols-1 gap-x-5 gap-y-8 sm:grid-cols-2 xl:grid-cols-4">
            {COLUMN_ALGORITHMS.map((c) => (
              <AlgoColumn key={c.key} paper={paper} k={k} algo={c.key} label={c.label} description={c.description} />
            ))}
          </div>
        </section>

        <div className="reveal" style={{ animationDelay: "220ms" }}>
          <Leaderboard />
        </div>

        <footer className="border-t border-border pt-6 text-xs leading-relaxed text-muted">
          <p>
            Data: <span className="font-mono">OpenAlex</span> computer-science works on arXiv, 2019
            onward, citation graph included. Models: popularity, TF-IDF, MiniLM sentence-transformer,
            implicit ALS over citations, and a held-out-tuned hybrid. Serving: FastAPI + FAISS.
            Frontend: Next.js on Cloudflare Pages.{" "}
            <a
              className="text-accent hover:underline"
              href="https://github.com/scottcampbelldata/arxiv-recommender"
              target="_blank"
              rel="noreferrer"
            >
              Source on GitHub
            </a>
            .
          </p>
        </footer>
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="text-text">{value}</span>
      <span className="text-faint">{label}</span>
    </span>
  );
}

function Dot() {
  return <span className="text-border-strong" aria-hidden>·</span>;
}
