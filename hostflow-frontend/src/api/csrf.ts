/** Cookie-session helpers for Stage 6B (ADR-023 §3.7). */

export const CSRF_COOKIE = 'hf_csrf'
export const CSRF_HEADER = 'X-CSRF-Token'

export function readBrowserCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const parts = document.cookie ? document.cookie.split(';') : []
  for (const part of parts) {
    const idx = part.indexOf('=')
    if (idx < 0) continue
    const key = part.slice(0, idx).trim()
    if (key !== name) continue
    return decodeURIComponent(part.slice(idx + 1).trim())
  }
  return null
}

export function readCsrfToken(): string | null {
  return readBrowserCookie(CSRF_COOKIE)
}
