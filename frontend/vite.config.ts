/// <reference types="vitest" />
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    strictPort: true,
    // Same origin in development, so the session cookie stays first-party.
    proxy: { "/api": { target: process.env.API_PROXY ?? "http://127.0.0.1:8101", changeOrigin: false } },
  },
  build: {
    rollupOptions: {
      output: { manualChunks: { editor: ["@codemirror/state", "@codemirror/view", "@codemirror/language", "@codemirror/lang-python", "@codemirror/commands"] } },
    },
  },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test-setup.ts"], include: ["src/**/*.test.{ts,tsx}"] },
});
