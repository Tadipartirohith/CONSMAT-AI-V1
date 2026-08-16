import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/id": { target: "http://localhost:8005", rewrite: (p) => p.replace(/^\/id/, "/api/v1") },
      "/site": { target: "http://localhost:8003", rewrite: (p) => p.replace(/^\/site/, "/api/v1") },
    },
  },
});
