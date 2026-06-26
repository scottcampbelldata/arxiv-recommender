export function AppHeader() {
  return (
    <header className="border-b border-border bg-bg">
      <div className="mx-auto flex max-w-shell items-center justify-between gap-3 px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-surface">
            <span className="font-mono text-sm text-accent">ar</span>
          </div>
          <div>
            <div className="text-sm font-medium text-text">arXiv recommender</div>
            <div className="text-xs text-muted">
              Find ML papers worth your time. Side by side, five algorithms.
            </div>
          </div>
        </div>
        <div className="hidden items-center gap-5 text-xs text-muted sm:flex">
          <a
            className="hover:text-text"
            href="https://github.com/scottcampbelldata/arxiv-recommender"
            target="_blank"
            rel="noreferrer"
          >
            github
          </a>
          <a className="hover:text-text" href="https://scottcampbell.io/projects/arxiv-recommender/">
            case study
          </a>
          <a className="hover:text-text" href="https://scottcampbell.io">
            scottcampbell.io
          </a>
        </div>
      </div>
    </header>
  );
}
