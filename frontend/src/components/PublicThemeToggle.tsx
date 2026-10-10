import type { PublicTheme } from "../lib/publicTheme";

function SunIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3.5" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>;
}
function MoonIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M20 15.4A8.5 8.5 0 0 1 8.6 4a8.5 8.5 0 1 0 11.4 11.4Z" /></svg>;
}

export function PublicThemeToggle({ theme, onToggle, compact = false }: { theme: PublicTheme; onToggle: () => void; compact?: boolean }) {
  const nextTheme = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`public-theme-toggle ${compact ? "public-theme-toggle--compact" : ""}`}
      aria-label={`Switch to ${nextTheme} theme`}
      title={`Switch to ${nextTheme} theme`}
    >
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
      <span>{theme === "dark" ? "Light" : "Dark"}</span>
    </button>
  );
}
