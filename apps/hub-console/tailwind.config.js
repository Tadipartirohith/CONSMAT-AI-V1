/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      // Tokens resolve to CSS variables (channel form) so alpha modifiers work: bg-accent/10 etc.
      colors: {
        bg: "rgb(var(--bg) / <alpha-value>)",
        panel: "rgb(var(--surface) / <alpha-value>)",
        panel2: "rgb(var(--surface-2) / <alpha-value>)",
        border: "rgb(var(--border) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        accentHover: "rgb(var(--accent-hover) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        onAccent: "rgb(var(--on-accent) / <alpha-value>)",
      },
      fontFamily: {
        head: ["'Geist Variable'", "Geist", "system-ui", "sans-serif"],
        sans: ["'Geist Variable'", "Geist", "system-ui", "sans-serif"],
        mono: ["'Geist Mono Variable'", "'Geist Mono'", "ui-monospace", "monospace"],
      },
      // One radius scale: controls 10px, cards 12-14px, pills full.
      borderRadius: { lg: "0.625rem", xl: "0.75rem", "2xl": "0.875rem" },
    },
  },
  plugins: [],
};
