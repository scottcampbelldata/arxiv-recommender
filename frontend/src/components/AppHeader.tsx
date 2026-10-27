import { ThemeToggle } from "./ThemeToggle";
import { SiteBar } from "./SiteFrame";

export const CASE_STUDY = "https://scottcampbell.io/projects/arxiv-recommender/";
export const REPO = "https://github.com/scottcampbelldata/arxiv-recommender";

export function AppHeader() {
  return (
    <>
      <SiteBar caseStudy={CASE_STUDY} repo={REPO} />
      <div className="themed border-b border-border bg-bg">
        <div className="mx-auto flex max-w-shell items-center justify-between gap-3 px-6 py-2">
          <a href="/" className="font-display text-[19px] text-text hover:text-accent" aria-label="arXiv recommender, home">
            arXiv recommender
          </a>
          <ThemeToggle />
        </div>
      </div>
    </>
  );
}
