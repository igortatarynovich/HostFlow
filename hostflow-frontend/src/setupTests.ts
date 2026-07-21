// src/setupTests.ts
import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

/**
 * happy-dom's XHR/fetch can attempt real localhost calls when a test leaves an
 * unmocked axios request pending (e.g. after axios CVE bumps). Default to a
 * rejected fetch so CI does not hang on ECONNREFUSED AggregateErrors.
 * Tests that need network should mock their API modules explicitly.
 */
globalThis.fetch = vi.fn(() =>
  Promise.reject(new TypeError('Network request blocked in vitest (mock your API client)')),
) as unknown as typeof fetch
