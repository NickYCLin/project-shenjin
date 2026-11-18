import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";
import { attachWar } from "./server/war.js";
export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  plugins: [
    {
      name: "shenjin-war",
      configureServer(server) {
        if (server.httpServer) attachWar(server.httpServer);
      },
      configurePreviewServer(server) {
        attachWar(server.httpServer);
      },
    },
  ],
  base: "./",
  build: {
    rollupOptions: {
      input: {
        journey: fileURLToPath(new URL("index.html", import.meta.url)),
        war: fileURLToPath(new URL("war.html", import.meta.url)),
      },
    },
    outDir: "../dist",
    emptyOutDir: true,
    chunkSizeWarningLimit: 850,
  },
  server: { port: 4173, strictPort: true },
  preview: { port: 4173, strictPort: true },
});
