import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function initialTheme(): Theme {
  return localStorage.getItem("emc-veritas-theme") === "dark" ? "dark" : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("emc-veritas-theme", theme);
  }, [theme]);

  const nextTheme = theme === "dark" ? "light" : "dark";
  return <button type="button" className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800" onClick={() => setTheme(nextTheme)} aria-label={`Use ${nextTheme} theme`}>{theme === "dark" ? "Light" : "Dark"}</button>;
}
