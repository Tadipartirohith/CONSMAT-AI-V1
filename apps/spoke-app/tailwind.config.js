/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f1216",
        panel: "#171c22",
        panel2: "#1c222a",
        border: "#272e38",
        accent: "#38bdf8",
        accentHover: "#0ea5e9",
        muted: "#8b949e",
      },
      fontFamily: {
        head: ["Outfit", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
