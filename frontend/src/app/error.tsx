"use client";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-5">
      <div className="max-w-md text-center">
        <p className="text-[11px] uppercase tracking-eyebrow text-faint">Something broke</p>
        <h1 className="mt-3 font-display text-2xl text-text">The dashboard hit an error.</h1>
        <p className="mt-2 text-sm text-muted">
          The page failed to render. The backend may be waking up; try again in a moment.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-fg transition-opacity hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-ring/50"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
