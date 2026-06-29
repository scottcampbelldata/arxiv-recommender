import type { Config } from "tailwindcss";

/** Map a CSS variable holding RGB channels to a Tailwind colour with alpha support. */
const v = (name: string) => `rgb(var(${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: v("--bg"),
        surface: v("--surface"),
        "surface-2": v("--surface-2"),
        border: v("--border"),
        "border-strong": v("--border-strong"),
        text: v("--text"),
        muted: v("--muted"),
        faint: v("--faint"),
        accent: v("--accent"),
        "accent-soft": v("--accent-soft"),
        "accent-fg": v("--accent-fg"),
        ring: v("--ring"),
        algo: {
          hybrid: v("--algo-hybrid"),
          neural: v("--algo-neural"),
          tfidf: v("--algo-tfidf"),
          als: v("--algo-als"),
          popularity: v("--algo-popularity"),
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "ui-serif", "Georgia", "serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        pop: "var(--shadow-pop)",
      },
      maxWidth: {
        shell: "1320px",
      },
      letterSpacing: {
        eyebrow: "0.16em",
      },
    },
  },
  plugins: [],
};

export default config;
