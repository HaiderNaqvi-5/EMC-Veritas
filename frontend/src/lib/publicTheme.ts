import { useEffect, useState } from "react";

export type PublicTheme = "light" | "dark";

const STORAGE_KEY = "emc-veritas-public-theme";

function preferredTheme(): PublicTheme {
  if (typeof window === "undefined") return "light";
  try {
    const saved = window.localStorage?.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    // Storage can be unavailable in private/test contexts; the theme still works in memory.
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function usePublicTheme() {
  const [theme, setTheme] = useState<PublicTheme>(preferredTheme);

  useEffect(() => {
    try {
      window.localStorage?.setItem(STORAGE_KEY, theme);
    } catch {
      // Persistence is an enhancement, never a requirement for rendering.
    }
  }, [theme]);

  return {
    theme,
    toggleTheme: () => setTheme((current) => current === "dark" ? "light" : "dark"),
  };
}
