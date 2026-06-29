import type { Paper } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { ArrowUpRight } from "./icons";

export function SeedCard({ paper }: { paper: Paper }) {
  const arxivLink = paper.arxiv_id ? `https://arxiv.org/abs/${paper.arxiv_id}` : paper.pdf_url;
  return (
    <div className="themed rounded-lg border border-border bg-surface-2 p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-eyebrow text-faint">Seed paper</div>
          <h3 className="mt-1.5 text-lg font-medium leading-snug text-text">{paper.title}</h3>
          <div className="mt-1 text-sm text-muted">{paper.authors}</div>
        </div>
        {arxivLink && (
          <a
            href={arxivLink}
            target="_blank"
            rel="noreferrer"
            className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-border bg-surface px-3 py-1.5 font-mono text-xs text-accent transition-colors hover:border-accent/40 hover:bg-accent-soft"
          >
            {paper.arxiv_id ? `arXiv:${paper.arxiv_id}` : "PDF"}
            <ArrowUpRight className="h-3.5 w-3.5" />
          </a>
        )}
      </div>
      {paper.abstract_preview && (
        <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-muted">{paper.abstract_preview}</p>
      )}
      <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 border-t border-border pt-4 text-xs sm:grid-cols-4">
        {paper.publication_year && (
          <Meta term="Year" value={<span className="font-mono text-text">{paper.publication_year}</span>} />
        )}
        <Meta term="Cited by" value={<span className="font-mono text-text">{formatNumber(paper.cited_by_count)}</span>} />
        {paper.primary_topic && (
          <div className="col-span-2">
            <Meta term="Topic" value={<span className="text-text">{paper.primary_topic}</span>} />
          </div>
        )}
      </dl>
    </div>
  );
}

function Meta({ term, value }: { term: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="uppercase tracking-eyebrow text-faint">{term}</dt>
      <dd className="mt-0.5">{value}</dd>
    </div>
  );
}
