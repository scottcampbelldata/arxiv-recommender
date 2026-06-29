import { ThemeToggle } from "./ThemeToggle";

export function AppHeader() {
  return (
    <header className="themed sticky top-0 z-40 border-b border-border bg-bg/80 backdrop-blur-md supports-[backdrop-filter]:bg-bg/65">
      <div className="mx-auto flex max-w-shell items-center justify-between gap-3 px-5 py-3.5">
        <a href="/" className="group flex items-center gap-3" aria-label="arXiv recommender, home">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent font-mono text-[13px] font-medium text-accent-fg shadow-sm">
            ar
          </span>
          <span className="flex items-baseline gap-1.5">
            <span className="font-mono text-sm text-text">arXiv</span>
            <span className="font-display text-sm italic text-muted group-hover:text-text">
              recommender
            </span>
          </span>
        </a>

        <div className="flex items-center gap-2 sm:gap-4">
          <nav className="hidden items-center gap-4 text-[13px] text-muted sm:flex">
            <a
              className="transition-colors hover:text-text"
              href="https://github.com/scottcampbelldata/arxiv-recommender"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
            <a
              className="transition-colors hover:text-text"
              href="https://scottcampbell.io/projects/arxiv-recommender/"
            >
              Case study
            </a>
          </nav>
          <span className="hidden h-4 w-px bg-border sm:block" aria-hidden />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
