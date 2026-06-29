/**
 * Single source of truth for algorithm identity. Each algorithm carries a
 * persistent colour (a CSS variable defined per theme) that is reused on its
 * column, its recommendation cards, and the leaderboard charts, so colour
 * encodes *which model*, not decoration.
 */
export interface AlgoMeta {
  key: string;
  label: string;
  tagline: string;
  description: string;
}

/** Columns shown side by side, hybrid first (it is the deployed default). */
export const COLUMN_ALGORITHMS: AlgoMeta[] = [
  {
    key: "hybrid",
    label: "Hybrid",
    tagline: "the tuned blend",
    description: "TF-IDF + neural + ALS + popularity, weights tuned on held-out NDCG",
  },
  {
    key: "neural",
    label: "Neural",
    tagline: "sentence embeddings",
    description: "MiniLM sentence-transformer over title + abstract, cosine",
  },
  {
    key: "tfidf",
    label: "TF-IDF",
    tagline: "lexical overlap",
    description: "Title + abstract + authors + topic, sparse cosine",
  },
  {
    key: "als",
    label: "Citation ALS",
    tagline: "who cites what",
    description: "Implicit ALS over citing → cited edges, 96 latent factors",
  },
];

/** Full leaderboard order, baseline first. */
export const LEADERBOARD_ORDER = ["popularity", "tfidf", "neural", "als", "hybrid"];

export const ALGO_LABEL: Record<string, string> = {
  popularity: "Popularity",
  tfidf: "TF-IDF",
  neural: "Neural",
  als: "Citation ALS",
  hybrid: "Hybrid",
};

/** CSS colour for an algorithm, theme-aware. Pass `alpha` for tints. */
export function algoColor(key: string, alpha = 1): string {
  return alpha === 1 ? `rgb(var(--algo-${key}))` : `rgb(var(--algo-${key}) / ${alpha})`;
}
