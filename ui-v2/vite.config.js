import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies API routes to the nginx reverse proxy of the live
// Docker stack (design-grammars container at :8080). The V2 app runs via
// the Vite dev server until the Phase 26 cutover ships it in the container.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/neo4j": "http://localhost:8080",
      "/n8n": "http://localhost:8080",
      "/data-service": "http://localhost:8080"
    }
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
