// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

/**
 * По умолчанию — обычная сборка Vite/Rollup (как до экспериментов с RAM).
 *
 * `HOSTFLOW_LOW_MEM_BUILD=1` — maxParallelFileOps=1 и дробление тяжёлых vendor-чанков (npm `build`).
 * react + react-dom — один чанк `vendor-react-core`. На VPS без swap сборка часто падает по OOM — нужен swap или сборка на машине с большим RAM.
 * Не использовать `experimentalMinChunkSize`: он склеивает чанки в несколько гигантских графов
 * и на VPS даёт OOM («Killed») + своп → SSH «висит».
 */
const lowMemBuild = process.env.HOSTFLOW_LOW_MEM_BUILD === "1";

const crossOriginIsolationHeaders = {
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Embedder-Policy": "require-corp",
  "Cross-Origin-Resource-Policy": "same-origin",
} as const;

export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ["react", "react-dom"],
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@api": path.resolve(__dirname, "./src/api"),
      "@components": path.resolve(__dirname, "./src/components"),
      "@pages": path.resolve(__dirname, "./src/pages"),
      "@utils": path.resolve(__dirname, "./src/utils"),
      "@modules": path.resolve(__dirname, "./src/modules"),
      "@hooks": path.resolve(__dirname, "./src/hooks"),
      "@store": path.resolve(__dirname, "./src/store"),
      "@i18n": path.resolve(__dirname, "./src/i18n"),
      "@shared": path.resolve(__dirname, "../shared"),
    },
  },
  server: {
    port: 5173,
    fs: {
      allow: [path.resolve(__dirname, "..")],
    },
    headers: crossOriginIsolationHeaders,
    proxy: {
      // Все запросы, начинающиеся с /db, пойдут на модуль документов
      "/db": {
        target: "http://127.0.0.1:8089",
        changeOrigin: true,
      },
      // Avatars / uploads must be same-origin under COEP; backend also mounts /api/uploads.
      "/api/uploads": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/uploads": {
        target: "http://127.0.0.1:8000",
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
    rollupOptions: {
      ...(lowMemBuild ? { maxParallelFileOps: 1 } : {}),
      output: {
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return;
          if (id.includes("@tabler/icons")) return "vendor-tabler-icons";
          if (lowMemBuild) {
            if (
              id.includes("node_modules/react/") ||
              id.includes("node_modules/react-dom/")
            ) {
              return "vendor-react-core";
            }
            if (id.includes("recharts")) return "vendor-recharts";
            if (id.includes("@dnd-kit")) return "vendor-dnd-kit";
            if (id.includes("date-fns")) return "vendor-date-fns";
            if (id.includes("react-router")) return "vendor-react-router";
          }
        },
      },
    },
  },
});
