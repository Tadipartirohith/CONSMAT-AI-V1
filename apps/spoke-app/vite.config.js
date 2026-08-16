import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/site": { target: "http://localhost:8003", rewrite: (p) => p.replace(/^\/site/, "/api/v1") },
      "/inv": { target: "http://localhost:8001", rewrite: (p) => p.replace(/^\/inv/, "/api/v1") },
    },
  },
});
