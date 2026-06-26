import type { Paper } from "@/lib/api";
import { formatNumber } from "@/lib/format";

export function SeedCard({ paper }: { paper: Paper }) {
  const arxivLink = paper.arxiv_id ? `https://arxiv.org/abs/${paper.arxiv_id}` : paper.pdf_url;
  return (
    <div className="rounded-md border border-border bg-surface p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-[0.12em] text-muted">Seed</div>
          <h2 className="mt-1 text-lg font-medium text-text">{paper.title}</h2>
          <div className="mt-1 text-sm text-muted">{paper.authors}</div>
        </div>
        {arxivLink && (
          <a
            href={arxivLink}
            target="_blank"
            rel="noreferrer"
            className="whitespace-nowrap rounded-md border border-border bg-bg px-3 py-1.5 font-mono text-xs text-accent hover:bg-surface-hover"
          >
            {paper.arxiv_id ? `arXiv:${paper.arxiv_id}` : "pdf"}
          </a>
        )}
      </div>
      {paper.abstract_preview && (
        <p className="mt-3 line-clamp-3 text-sm text-muted">{paper.abstract_preview}</p>
      )}
      <div className="mt-3 grid grid-cols-2 gap-x-5 gap-y-1 text-xs text-muted sm:grid-cols-4">
        {paper.publication_year && (
          <div>
            <span className="block uppercase tracking-[0.1em]">year</span>
            <span className="font-mono text-text">{paper.publication_year}</span>
          </div>
        )}
        <div>
          <span className="block uppercase tracking-[0.1em]">cited by</span>
          <span className="font-mono text-text">{formatNumber(paper.cited_by_count)}</span>
        </div>
        {paper.primary_topic && (
          <div className="col-span-2">
            <span className="block uppercase tracking-[0.1em]">topic</span>
            <span className="text-text">{paper.primary_topic}</span>
          </div>
        )}
      </div>
    </div>
  );
}
