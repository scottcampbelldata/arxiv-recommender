import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0b0e",
        surface: "#131519",
        "surface-hover": "#1a1d23",
        border: "#23262d",
        text: "#e5e7eb",
        muted: "#8b919e",
        accent: "#4f8bf5",
        "accent-dim": "rgba(79,139,245,0.10)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      maxWidth: {
        shell: "1400px",
      },
    },
  },
  plugins: [],
};

export default config;
