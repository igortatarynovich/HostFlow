/**
 * After a new deploy, cached index.html may still reference old hashed chunks → dynamic import() 404.
 * One controlled reload often fetches a fresh shell (if CDN/server send no-cache for HTML).
 * Throttle via sessionStorage to avoid infinite loops when HTML stays stale.
 */
const RELOAD_TS_KEY = 'hf:stale_chunk_reload_ts'
const MIN_MS_BETWEEN_RELOADS = 10_000

function isDynamicImportChunkFailure(reason: unknown): boolean {
  const msg =
    reason instanceof Error
      ? reason.message
      : typeof reason === 'string'
        ? reason
        : reason != null
          ? String(reason)
          : ''
  const m = msg.toLowerCase()
  return (
    m.includes('failed to fetch dynamically imported module') ||
    m.includes('error loading dynamically imported module') ||
    m.includes('importing a module script failed')
  )
}

export function installStaleChunkReloadRecovery(): void {
  if (typeof window === 'undefined') return

  window.addEventListener('unhandledrejection', (event) => {
    if (!isDynamicImportChunkFailure(event.reason)) return
    event.preventDefault()

    const now = Date.now()
    let last = 0
    try {
      last = Number(sessionStorage.getItem(RELOAD_TS_KEY) || '0')
    } catch {
      /* private mode / blocked */
    }

    if (now - last < MIN_MS_BETWEEN_RELOADS) {
      console.warn(
        '[HostFlow] Dynamic chunk load failed again shortly after a reload. Fix HTML caching (CDN/nginx) or hard-refresh.',
      )
      return
    }

    try {
      sessionStorage.setItem(RELOAD_TS_KEY, String(now))
    } catch {
      /* still try reload */
    }

    console.warn('[HostFlow] Stale or missing JS chunk; reloading page once for a fresh app shell.')
    window.location.reload()
  })
}
