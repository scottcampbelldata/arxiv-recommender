"use client";
import { useState } from "react";
import type { Paper } from "@/lib/api";
import { LEADERBOARD } from "@/lib/leaderboard";
import { formatLift, formatMs } from "@/lib/format";
import { AlgoColumn } from "./AlgoColumn";
import { AppHeader } from "./AppHeader";
import { KpiCard } from "./KpiCard";
import { KpiRow } from "./KpiRow";
import { Leaderboard } from "./Leaderboard";
import { Panel } from "./Panel";
import { SearchBar } from "./SearchBar";
import { SeedCard } from "./SeedCard";

const COLUMNS = [
  { algo: "hybrid", label: "Hybrid", description: "Neural + ALS + TF-IDF + popularity blend, cold-paper aware" },
  { algo: "neural", label: "Neural", description: "MiniLM sentence-transformer over title + abstract, cosine" },
  { algo: "tfidf", label: "Content (TF-IDF)", description: "Title + abstract + authors + topic, sparse cosine" },
  { algo: "als", label: "Citation ALS", description: "Implicit ALS over citing -> cited edges, 96 factors" },
];

export function Dashboard() {
  const [paper, setPaper] = useState<Paper | null>(null);
  const [k, setK] = useState(10);

  // Pick the headline metric dynamically: whichever algorithm wins on MAP@10
  // becomes the KPI value. Falls back to a sensible default for the lift card.
  const best = LEADERBOARD.reduce((acc, r) => (r["map@k"] > (acc?.["map@k"] ?? -1) ? r : acc), LEADERBOARD[0]);
  const popularity = LEADERBOARD.find((r) => r.algorithm === "popularity");
  const liftVsPop = best && popularity ? best["map@k"] / Math.max(popularity["map@k"], 1e-9) : null;
  const totalLatency = best?.latency_p95_ms ?? 0;

  return (
    <div className="min-h-screen bg-bg">
      <AppHeader />
      <main className="mx-auto max-w-shell space-y-6 px-5 py-6">
        <div className="space-y-1.5">
          <h1 className="text-xl font-medium text-text">
            Find ML papers worth your time. Five algorithms, side by side.
          </h1>
          <p className="max-w-3xl text-sm text-muted">
            Pick any arXiv paper from the ML / AI / NLP / CV corpus on OpenAlex. Four algorithms each
            return their own top-{k} most-similar papers: a hybrid blend, a sentence-transformer
            content tower, classic TF-IDF, and an ALS model fit on the citation graph. Latency
            badges are live calls against the FastAPI service. The leaderboard at the bottom is the
            offline evaluation with bootstrap 95% confidence intervals on every metric.
          </p>
        </div>

        <KpiRow>
          <KpiCard
            label={`Best MAP@10 (${best?.algorithm ?? "-"})`}
            value={best ? best["map@k"].toFixed(3) : "-"}
            sub={
              liftVsPop ? (
                <span>
                  <span className="text-text">{formatLift(liftVsPop)}</span> the popularity baseline
                </span>
              ) : null
            }
          />
          <KpiCard
            label="Citation graph"
            value="46.4k"
            unit="edges"
            sub={<span>in-subset, citing to cited</span>}
          />
          <KpiCard
            label="Best p95 latency"
            value={formatMs(totalLatency)}
            unit="ms"
            sub={<span>top-10 from a 28,000-paper catalogue</span>}
          />
          <KpiCard
            label="Catalogue"
            value="28,424"
            sub={<span>CS arXiv papers since 2019 via OpenAlex</span>}
          />
        </KpiRow>

        <Panel
          title="Seed selection"
          subtitle="Type any title or author. The FastAPI service does the lookup."
          right={
            <label className="flex items-center gap-2">
              <span className="uppercase tracking-[0.08em]">top-k</span>
              <select
                value={k}
                onChange={(e) => setK(parseInt(e.target.value, 10))}
                className="rounded-md border border-border bg-surface px-2 py-1 font-mono text-text focus:border-accent focus:outline-none"
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

        <section className="space-y-3">
          <div className="flex items-baseline justify-between">
            <h2 className="text-sm font-medium text-text">Recommendations, side by side</h2>
            <p className="text-xs text-muted">
              {paper ? `For "${paper.title.slice(0, 80)}${paper.title.length > 80 ? "..." : ""}"` : "Pick a seed paper above"}
            </p>
          </div>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
            {COLUMNS.map((c) => (
              <AlgoColumn
                key={c.algo}
                paper={paper}
                k={k}
                algo={c.algo}
                label={c.label}
                description={c.description}
              />
            ))}
          </div>
        </section>

        <Leaderboard />

        <footer className="border-t border-border pt-6 text-xs text-muted">
          <p>
            Data: <span className="font-mono">OpenAlex</span> Computer Science works hosted on arXiv,
            2019 onwards, citation graph included. Algorithms: popularity, TF-IDF, MiniLM
            sentence-transformer, implicit ALS over citations, hybrid linear blend. Serving:
            FastAPI + FAISS. Frontend: Next.js on Cloudflare Pages. Source:{" "}
            <a
              className="text-accent hover:underline"
              href="https://github.com/scottcampbelldata/arxiv-recommender"
              target="_blank"
              rel="noreferrer"
            >
              github.com/scottcampbelldata/arxiv-recommender
            </a>
            .
          </p>
        </footer>
      </main>
    </div>
  );
}
