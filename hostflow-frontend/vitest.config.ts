import { mergeConfig } from 'vite'
import { defineConfig } from 'vitest/config'
import viteConfig from './vite.config'

// Inherit `resolve.alias` (e.g. `@utils`) from Vite — required for suites that pull app modules.
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'happy-dom',
      globals: true,
      setupFiles: ['./src/setupTests.ts'],
      coverage: {
        // Phase 0 #7: v8 provider is fastest and installs with the
        // `@vitest/coverage-v8` devDep. The gate itself lives in
        // `scripts/check-coverage.mjs` — here we only declare scope + formats.
        provider: 'v8',
        reporter: ['text', 'json-summary'],
        reportsDirectory: './coverage',
        include: ['src/**/*.{ts,tsx}'],
        exclude: [
          'src/**/*.d.ts',
          'src/**/__generated__/**',
          'src/**/__tests__/**',
          'src/**/*.test.ts',
          'src/**/*.test.tsx',
          'src/setupTests.ts',
          'src/main.tsx',
          'src/vite-env.d.ts',
        ],
      },
    },
  }),
)