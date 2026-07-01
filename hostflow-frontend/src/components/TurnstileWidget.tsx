import { useEffect, useId, useRef } from 'react'
import { loadTurnstile } from '../lib/turnstile'

type Props = {
  sitekey: string
  onToken: (token: string | null) => void
  /** Optional identifier passed to Cloudflare as `action` for analytics. */
  action?: string
  /** Width wrapper — Turnstile widget is 300x65 by default. */
  className?: string
  theme?: 'light' | 'dark' | 'auto'
  size?: 'normal' | 'compact' | 'flexible'
}

/**
 * Mounts a Cloudflare Turnstile widget and streams the token to `onToken`.
 *
 * Lifecycle:
 *   - On mount: lazy-load the Turnstile script, then `render()` into our div.
 *   - On success: emit `onToken(token)`.
 *   - On expiry / error: emit `onToken(null)` so the submit button disables
 *     itself until the user re-challenges.
 *   - On unmount: `remove(widgetId)` to free the slot.
 *
 * Failure to load (ad-blockers, corporate CSP) is logged but does NOT block
 * the surrounding form — the backend is the source of truth and will gate if
 * configured to require Turnstile. Callers can decide whether to show a
 * graceful fallback ("please disable tracker blockers").
 */
export default function TurnstileWidget({
  sitekey,
  onToken,
  action,
  className,
  theme = 'auto',
  size = 'flexible',
}: Props) {
  const elementId = useId().replace(/[:]/g, '_')
  const hostRef = useRef<HTMLDivElement | null>(null)
  const widgetIdRef = useRef<string | null>(null)

  useEffect(() => {
    let cancelled = false
    loadTurnstile()
      .then((api) => {
        if (cancelled || !hostRef.current) return
        try {
          widgetIdRef.current = api.render(hostRef.current, {
            sitekey,
            action,
            theme,
            size,
            callback: (token) => onToken(token),
            'error-callback': () => onToken(null),
            'expired-callback': () => onToken(null),
            'timeout-callback': () => onToken(null),
          })
        } catch (err) {
          console.warn('[turnstile] render failed', err)
          onToken(null)
        }
      })
      .catch((err) => {
        console.warn('[turnstile] script load failed', err)
        onToken(null)
      })
    return () => {
      cancelled = true
      try {
        if (widgetIdRef.current && window.turnstile?.remove) {
          window.turnstile.remove(widgetIdRef.current)
        }
      } catch {
        /* swallow — widget may already be gone */
      }
    }
  }, [sitekey, action, theme, size, onToken])

  return <div id={elementId} ref={hostRef} className={className} />
}
