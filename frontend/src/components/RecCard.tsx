import type { RecItem } from "@/lib/api";
import { formatScore } from "@/lib/format";

interface Props {
  item: RecItem;
  rank: number;
}

export function RecCard({ item, rank }: Props) {
  const { paper, score, reason } = item;
  const arxivLink = paper.arxiv_id ? `https://arxiv.org/abs/${paper.arxiv_id}` : paper.pdf_url;
  return (
    <article className="rounded-md border border-border bg-surface p-3">
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-[11px] text-muted">{rank.toString().padStart(2, "0")}</span>
        <span className="font-mono text-[11px] text-muted">
          score <span className="text-text">{formatScore(score)}</span>
        </span>
      </div>
      <h4 className="mt-1 line-clamp-2 text-sm font-medium leading-tight text-text">
        {arxivLink ? (
          <a href={arxivLink} target="_blank" rel="noreferrer" className="hover:text-accent">
            {paper.title}
          </a>
        ) : (
          paper.title
        )}
      </h4>
      <div className="mt-1 line-clamp-1 text-[11px] text-muted">{paper.authors}</div>
      <div className="mt-1 flex items-center gap-3 text-[11px] text-muted">
        {paper.publication_year && (
          <span className="font-mono">{paper.publication_year}</span>
        )}
        <span className="font-mono">
          <span className="text-text">{paper.cited_by_count.toLocaleString()}</span> cites
        </span>
      </div>
      {paper.abstract_preview && (
        <p className="mt-2 line-clamp-2 text-[11px] leading-snug text-muted">{paper.abstract_preview}</p>
      )}
      {reason && (
        <div className="mt-2 line-clamp-2 text-[11px] italic text-muted">{reason}</div>
      )}
    </article>
  );
}
