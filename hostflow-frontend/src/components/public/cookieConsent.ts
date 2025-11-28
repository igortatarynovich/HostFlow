const COOKIE_NAME = 'cookies_accepted'
const CONSENT_EVENT = 'hf:cookie-consent'
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365

export function isCookieConsentGranted(): boolean {
  if (typeof document === 'undefined') return false
  return document.cookie.split(';').some((chunk) => chunk.trim().startsWith(`${COOKIE_NAME}=true`))
}

export function persistCookieConsent(): void {
  if (typeof document === 'undefined') return
  const expires = ONE_YEAR_SECONDS
  document.cookie = `${COOKIE_NAME}=true; path=/; max-age=${expires}`
  try {
    window.localStorage.setItem(COOKIE_NAME, 'true')
  } catch {
    /* ignore storage errors */
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: true }))
  }
}

export function subscribeCookieConsent(handler: () => void): () => void {
  if (typeof window === 'undefined') {
    return () => {}
  }
  const listener = () => handler()
  window.addEventListener(CONSENT_EVENT, listener)
  return () => window.removeEventListener(CONSENT_EVENT, listener)
}
