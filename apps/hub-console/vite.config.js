import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy mirrors the nginx path-proxy used in production, so `npm run dev`
// can talk to the compose services on their host ports.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/inv": { target: "http://localhost:8001", rewrite: (p) => p.replace(/^\/inv/, "/api/v1") },
      "/proc": { target: "http://localhost:8002", rewrite: (p) => p.replace(/^\/proc/, "/api/v1") },
      "/site": { target: "http://localhost:8003", rewrite: (p) => p.replace(/^\/site/, "/api/v1") },
      "/price": { target: "http://localhost:8004", rewrite: (p) => p.replace(/^\/price/, "/api/v1") },
    },
  },
});
