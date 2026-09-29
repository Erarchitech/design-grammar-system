import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies API routes to the nginx reverse proxy of the live
// Docker stack (design-grammars container at :8080). Only /data-service,
// /llm and /reasoner exist; /neo4j and /n8n were removed in Phase 1205.
// The V2 app runs via the Vite dev server until the Phase 26 cutover ships
// it in the container.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/data-service": "http://localhost:8080",
      "/llm": "http://localhost:8080",
      "/reasoner": "http://localhost:8080"
    }
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
