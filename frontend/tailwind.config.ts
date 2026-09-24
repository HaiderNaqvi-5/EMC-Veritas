import type { Config } from "tailwindcss";

export default {
  // ThemeToggle controls this class on <html>; do not tie admin appearance to OS preference.
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
} satisfies Config;
