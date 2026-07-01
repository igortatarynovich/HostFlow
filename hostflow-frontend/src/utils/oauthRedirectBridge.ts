/** After Google redirects to `/app/email?code=...`, stash for Communications setup (OAuth complete). */
export const GMAIL_OAUTH_PENDING_CODE_KEY = 'hf:oauth:pending_gmail_code'

export function stashPendingGmailOAuthCode(code: string) {
  const trimmed = String(code || '').trim()
  if (!trimmed) return
  try {
    sessionStorage.setItem(GMAIL_OAUTH_PENDING_CODE_KEY, trimmed)
  } catch {
    // ignore quota / private mode
  }
}

