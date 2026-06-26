export const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8820"
).replace(/\/+$/, "");

export interface Paper {
  paper_id: number;
  arxiv_id: string | null;
  title: string;
  authors: string;
  abstract_preview: string;
  primary_topic: string | null;
  publication_year: number | null;
  cited_by_count: number;
  venue: string | null;
  pdf_url: string | null;
}

export interface RecItem {
  paper: Paper;
  score: number;
  reason: string;
}

export interface RecResponse {
  algorithm: string;
  seed_paper: number;
  k: number;
  latency_ms: number;
  items: RecItem[];
}

export interface HealthResponse {
  status: string;
  algorithms_loaded: string[];
  n_papers: number;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    signal,
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
  return (await res.json()) as T;
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return getJson<HealthResponse>("/healthz", signal);
}

export function searchPapers(q: string, limit = 12, signal?: AbortSignal): Promise<Paper[]> {
  if (!q.trim()) return Promise.resolve([]);
  const params = new URLSearchParams({ q, limit: String(limit) });
  return getJson<Paper[]>(`/papers?${params}`, signal);
}

export function similarPapers(
  paperId: number,
  k: number,
  algo: string,
  signal?: AbortSignal
): Promise<RecResponse> {
  const params = new URLSearchParams({ k: String(k), algo });
  return getJson<RecResponse>(`/similar/${paperId}?${params}`, signal);
}
