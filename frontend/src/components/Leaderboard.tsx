"use client";
import { useEffect, useState } from "react";
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
import { ALGO_LABEL, LEADERBOARD_ORDER, algoColor } from "@/lib/algorithms";
import { LEADERBOARD } from "@/lib/leaderboard";
import { Panel } from "./Panel";

function fmt(v: number, d = 4): string {
  return v.toFixed(d);
}

/** Read concrete colours from the CSS variables, re-reading when the theme toggles. */
function useThemeColors() {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const obs = new MutationObserver(() => setTick((t) => t + 1));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);
  const read = (name: string) => {
    if (typeof window === "undefined") return "";
    return `rgb(${getComputedStyle(document.documentElement).getPropertyValue(name).trim()})`;
  };
  // tick forces recompute on theme change
  void tick;
  return { grid: read("--border"), axis: read("--muted"), surface: read("--surface"), text: read("--text") };
}

export function Leaderboard() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const c = useThemeColors();

  const rows = LEADERBOARD_ORDER.map((a) => LEADERBOARD.find((r) => r.algorithm === a)).filter(
    (r): r is (typeof LEADERBOARD)[number] => !!r
  );
  const bestAlgo = rows.reduce((acc, r) => (r["map@k"] > (acc?.["map@k"] ?? -1) ? r : acc), rows[0]);
  const chartData = rows.map((r) => ({
    name: ALGO_LABEL[r.algorithm] ?? r.algorithm,
    key: r.algorithm,
    "MAP@10": r["map@k"],
    "NDCG@10": r["ndcg@k"],
    "Recall@10": r["recall@k"],
  }));

  return (
    <Panel
      eyebrow="Offline evaluation"
      title="How the five algorithms actually score"
      subtitle={`Held-out citations, ${rows[0]?.n_seeds_eval.toLocaleString()} seeds, top-10, bootstrap 95% CIs. Hybrid is the deployed model.`}
    >
      <div className="-mx-1 overflow-x-auto px-1">
        <table className="min-w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] uppercase tracking-eyebrow text-faint">
              <th className="py-2 pr-4 font-normal">Algorithm</th>
              <th className="py-2 pl-4 text-right font-normal font-mono">MAP@10</th>
              <th className="py-2 pl-4 text-right font-normal font-mono">NDCG@10</th>
              <th className="py-2 pl-4 text-right font-normal font-mono">Recall@10</th>
              <th className="py-2 pl-4 text-right font-normal font-mono">Hit-rate</th>
              <th className="py-2 pl-4 text-right font-normal font-mono">Coverage</th>
              <th className="py-2 pl-4 text-right font-normal font-mono">p95 ms</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isBest = r.algorithm === bestAlgo?.algorithm;
              return (
                <tr
                  key={r.algorithm}
                  className={`border-b border-border/60 ${isBest ? "bg-accent-soft/60" : ""}`}
                >
                  <td className="py-2.5 pr-4">
                    <span className="flex items-center gap-2.5">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ background: algoColor(r.algorithm) }}
                        aria-hidden
                      />
                      <span className="text-text">{ALGO_LABEL[r.algorithm]}</span>
                      {isBest && (
                        <span className="rounded-full border border-accent/40 px-1.5 py-0.5 text-[10px] uppercase tracking-eyebrow text-accent">
                          deployed
                        </span>
                      )}
                    </span>
                  </td>
                  <td className="py-2.5 pl-4 text-right font-mono tabular-nums text-text">{fmt(r["map@k"])}</td>
                  <td className="py-2.5 pl-4 text-right font-mono tabular-nums text-text">{fmt(r["ndcg@k"])}</td>
                  <td className="py-2.5 pl-4 text-right font-mono tabular-nums text-text">{fmt(r["recall@k"])}</td>
                  <td className="py-2.5 pl-4 text-right font-mono tabular-nums text-text">{fmt(r["hit_rate@k"], 3)}</td>
                  <td className="py-2.5 pl-4 text-right font-mono tabular-nums text-muted">{fmt(r.coverage, 3)}</td>
                  <td className="py-2.5 pl-4 text-right font-mono tabular-nums text-muted">{r.latency_p95_ms.toFixed(1)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        {(["MAP@10", "NDCG@10", "Recall@10"] as const).map((metric) => (
          <figure key={metric} className="themed rounded-lg border border-border bg-bg p-3">
            <figcaption className="px-1 pb-2 text-[11px] uppercase tracking-eyebrow text-faint">
              {metric}
            </figcaption>
            <ResponsiveContainer width="100%" height={168}>
              <BarChart data={chartData} margin={{ top: 4, right: 4, left: -18, bottom: 0 }}>
                <CartesianGrid stroke={c.grid} vertical={false} />
                <XAxis dataKey="name" stroke={c.axis} fontSize={10.5} tickLine={false} axisLine={{ stroke: c.grid }} />
                <YAxis
                  stroke={c.axis}
                  fontSize={10.5}
                  tickLine={false}
                  axisLine={{ stroke: c.grid }}
                  tickFormatter={(v) => v.toFixed(2)}
                />
                {mounted && (
                  <Tooltip
                    cursor={{ fill: c.grid, opacity: 0.4 }}
                    contentStyle={{
                      background: c.surface,
                      border: `1px solid ${c.grid}`,
                      borderRadius: 8,
                      fontSize: 12,
                      color: c.text,
                    }}
                    labelStyle={{ color: c.text }}
                    formatter={(v: number) => v.toFixed(4)}
                  />
                )}
                <Bar dataKey={metric} radius={[3, 3, 0, 0]} isAnimationActive={false}>
                  {chartData.map((entry) => (
                    <Cell key={entry.key} fill={algoColor(entry.key)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </figure>
        ))}
      </div>
    </Panel>
  );
}
