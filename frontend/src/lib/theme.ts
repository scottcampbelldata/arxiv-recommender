"use client";
import { useCallback, useEffect, useState } from "react";

export type Theme = "system" | "light" | "dark";

const KEY = "theme";

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** Apply a theme to <html>, mirroring the no-FOUC head script. */
function applyTheme(theme: Theme): void {
  const dark = theme === "dark" || (theme === "system" && systemPrefersDark());
  const el = document.documentElement;
  el.classList.toggle("dark", dark);
  el.style.colorScheme = dark ? "dark" : "light";
}

/**
 * Theme state synced to localStorage and the OS preference. `resolved` is the
 * concrete light/dark actually showing, useful for swapping the toggle icon.
 */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("system");
  const [resolved, setResolved] = useState<"light" | "dark">("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = (localStorage.getItem(KEY) as Theme | null) ?? "system";
    setThemeState(stored);
    setResolved(stored === "dark" || (stored === "system" && systemPrefersDark()) ? "dark" : "light");
    setMounted(true);
  }, []);

  // Track OS changes while following the system setting.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      if ((localStorage.getItem(KEY) as Theme | null ?? "system") === "system") {
        applyTheme("system");
        setResolved(mq.matches ? "dark" : "light");
      }
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const setTheme = useCallback((t: Theme) => {
    localStorage.setItem(KEY, t);
    setThemeState(t);
    applyTheme(t);
    setResolved(t === "dark" || (t === "system" && systemPrefersDark()) ? "dark" : "light");
  }, []);

  return { theme, resolved, setTheme, mounted };
}
