"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { LEADERBOARD } from "@/lib/leaderboard";
import { Panel } from "./Panel";

const ORDER = ["popularity", "tfidf", "neural", "als", "hybrid"];
const LABEL: Record<string, string> = {
  popularity: "Popularity",
  tfidf: "TF-IDF",
  neural: "Neural",
  als: "Citation ALS",
  hybrid: "Hybrid",
};

function fmt(v: number, d = 4): string {
  return v.toFixed(d);
}

export function Leaderboard() {
  const rows = ORDER.map((a) => LEADERBOARD.find((r) => r.algorithm === a)).filter(
    (r): r is (typeof LEADERBOARD)[number] => !!r
  );
  // The "best" algorithm by MAP@10 is whoever the headline call-out should
  // highlight; ranking dynamically so this stays honest after retrains.
  const bestAlgo = rows.reduce((acc, r) => (r["map@k"] > (acc?.["map@k"] ?? -1) ? r : acc), rows[0]);
  const chartData = rows.map((r) => ({
    name: LABEL[r.algorithm] ?? r.algorithm,
    isBest: r.algorithm === bestAlgo?.algorithm,
    "MAP@10": r["map@k"],
    "NDCG@10": r["ndcg@k"],
    "Recall@10": r["recall@k"],
  }));

  return (
    <Panel
      title="Leaderboard"
      subtitle={`Held-out evaluation on ${rows[0]?.n_seeds_eval.toLocaleString()} citing-paper seeds, top-10, bootstrap 95% confidence intervals`}
    >
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-[0.08em] text-muted">
              <th className="py-2 pr-4 font-normal">Algorithm</th>
              <th className="py-2 pr-4 text-right font-normal font-mono">MAP@10</th>
              <th className="py-2 pr-4 text-right font-normal font-mono">NDCG@10</th>
              <th className="py-2 pr-4 text-right font-normal font-mono">Recall@10</th>
              <th className="py-2 pr-4 text-right font-normal font-mono">Precision@10</th>
              <th className="py-2 pr-4 text-right font-normal font-mono">Coverage</th>
              <th className="py-2 pr-0 text-right font-normal font-mono">p95 lat (ms)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isBest = r.algorithm === bestAlgo?.algorithm;
              return (
                <tr key={r.algorithm} className={`border-b border-border/60 ${isBest ? "bg-accent-dim" : ""}`}>
                  <td className="py-2 pr-4 text-text">
                    {LABEL[r.algorithm]}
                    {isBest && (
                      <span className="ml-2 rounded-full border border-accent/40 px-2 py-0.5 text-[10px] uppercase tracking-[0.1em] text-accent">
                        best
                      </span>
                    )}
                  </td>
                  <td className="py-2 pr-4 text-right font-mono text-text">{fmt(r["map@k"])}</td>
                  <td className="py-2 pr-4 text-right font-mono text-text">{fmt(r["ndcg@k"])}</td>
                  <td className="py-2 pr-4 text-right font-mono text-text">{fmt(r["recall@k"])}</td>
                  <td className="py-2 pr-4 text-right font-mono text-text">{fmt(r["precision@k"])}</td>
                  <td className="py-2 pr-4 text-right font-mono text-text">{fmt(r.coverage, 3)}</td>
                  <td className="py-2 pr-0 text-right font-mono text-text">{r.latency_p95_ms.toFixed(1)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        {(["MAP@10", "NDCG@10", "Recall@10"] as const).map((metric) => (
          <div key={metric} className="rounded-md border border-border bg-bg p-3">
            <div className="px-1 pb-2 text-xs uppercase tracking-[0.12em] text-muted">{metric}</div>
            <ResponsiveContainer width="100%" height={170}>
              <BarChart data={chartData} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
                <CartesianGrid stroke="#23262d" vertical={false} />
                <XAxis
                  dataKey="name"
                  stroke="#8b919e"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: "#23262d" }}
                />
                <YAxis
                  stroke="#8b919e"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: "#23262d" }}
                  tickFormatter={(v) => v.toFixed(2)}
                />
                <Tooltip
                  contentStyle={{ background: "#131519", border: "1px solid #23262d", borderRadius: 6, fontSize: 12 }}
                  labelStyle={{ color: "#e5e7eb" }}
                  formatter={(v: number) => v.toFixed(4)}
                />
                <Bar dataKey={metric} radius={[2, 2, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.isBest ? "#4f8bf5" : "#3b4150"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>
    </Panel>
  );
}
