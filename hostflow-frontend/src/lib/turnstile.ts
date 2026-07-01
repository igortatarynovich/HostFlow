/**
 * Cloudflare Turnstile — browser-side glue.
 *
 * We intentionally avoid adding an npm dependency and load the official script
 * from `challenges.cloudflare.com` on demand. Reasons:
 *   1. Turnstile is optional (operator can disable it) — pay nothing when off.
 *   2. Cloudflare ships security fixes through the same URL; no-rebuild updates.
 *   3. The script auto-registers `window.turnstile` with the explicit render API
 *      we use below (`render`, `reset`, `remove`). No framework integration.
 *
 * The companion component `TurnstileWidget.tsx` wraps this in React lifecycle.
 * The backend `/api/v1/auth/public-config` tells us whether Turnstile is on and
 * which sitekey to use.
 */

export type TurnstileRenderOptions = {
  sitekey: string
  callback?: (token: string) => void
  'error-callback'?: (code?: string) => void
  'expired-callback'?: () => void
  'timeout-callback'?: () => void
  theme?: 'light' | 'dark' | 'auto'
  size?: 'normal' | 'compact' | 'invisible' | 'flexible'
  appearance?: 'always' | 'execute' | 'interaction-only'
  action?: string
  language?: string
}

type TurnstileApi = {
  render: (element: string | HTMLElement, options: TurnstileRenderOptions) => string
  reset: (widgetId?: string) => void
  remove: (widgetId?: string) => void
  getResponse?: (widgetId?: string) => string | undefined
}

declare global {
  interface Window {
    turnstile?: TurnstileApi
    __turnstileScriptPromise?: Promise<TurnstileApi>
  }
}

const TURNSTILE_SCRIPT_SRC =
  'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'

/**
 * Load the Cloudflare Turnstile script exactly once per page.
 *
 * Returns a Promise that resolves to the `window.turnstile` API handle.
 * Rejects if the script fails to load (network blocked, CSP, etc.) so callers
 * can fall back gracefully (we don't want Turnstile to hard-break signup).
 */
export function loadTurnstile(): Promise<TurnstileApi> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('turnstile: window not available (SSR)'))
  }
  if (window.turnstile) {
    return Promise.resolve(window.turnstile)
  }
  if (window.__turnstileScriptPromise) {
    return window.__turnstileScriptPromise
  }
  window.__turnstileScriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src^="${TURNSTILE_SCRIPT_SRC.split('?')[0]}"]`,
    )
    const script = existing ?? document.createElement('script')
    if (!existing) {
      script.src = TURNSTILE_SCRIPT_SRC
      script.async = true
      script.defer = true
      document.head.appendChild(script)
    }
    const finalize = () => {
      if (window.turnstile) resolve(window.turnstile)
      else reject(new Error('turnstile: script loaded but window.turnstile missing'))
    }
    if (existing && window.turnstile) {
      finalize()
      return
    }
    script.addEventListener('load', finalize, { once: true })
    script.addEventListener(
      'error',
      () => reject(new Error('turnstile: failed to load script')),
      { once: true },
    )
  })
  return window.__turnstileScriptPromise
}
