/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Soft-UI "clay" charcoal palette. Surfaces extrude from the canvas via
        // the .nm-* dual-shadow utilities in index.css; borders are used sparingly.
        bg: "#1e232b",       // app canvas
        panel: "#242a34",    // raised surface base (slightly lifted from canvas)
        panel2: "#191d24",   // recessed wells / inset controls (darker than canvas)
        border: "#2f3743",
        accent: "#38bdf8",
        accentHover: "#0ea5e9",
        muted: "#9aa6b4",    // lifted for WCAG AA on the lighter panels
      },
      fontFamily: {
        head: ["Outfit", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      borderRadius: { xl: "0.75rem", "2xl": "1rem" },
    },
  },
  plugins: [],
};
