// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const crossOriginIsolationHeaders = {
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Embedder-Policy": "require-corp",
  "Cross-Origin-Resource-Policy": "same-origin",
} as const;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    headers: crossOriginIsolationHeaders,
    proxy: {
      // Все запросы, начинающиеся с /db, пойдут на модуль документов
      "/db": {
        target: "http://127.0.0.1:8089",
        changeOrigin: true,
      },
    },
  },
  preview: {
    headers: crossOriginIsolationHeaders,
  },
  build: {
    chunkSizeWarningLimit: 1024,
    minify: false, // Отключено для ускорения сборки (завершается за ~12 сек вместо зависания)
    target: 'esnext',
    sourcemap: false,
    reportCompressedSize: false,
    cssCodeSplit: false,
  },
});
