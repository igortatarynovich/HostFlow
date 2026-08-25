const META_OAUTH_RETURN_KEY = 'hostflow:meta-oauth-return'

export function setMetaOAuthReturnPath(path: string): void {
  try {
    const value = path.trim()
    if (value) sessionStorage.setItem(META_OAUTH_RETURN_KEY, value)
  } catch {
    /* ignore */
  }
}

export function consumeMetaOAuthReturnPath(): string | null {
  try {
    const value = sessionStorage.getItem(META_OAUTH_RETURN_KEY)?.trim()
    sessionStorage.removeItem(META_OAUTH_RETURN_KEY)
    return value || null
  } catch {
    return null
  }
}

export function peekMetaOAuthReturnPath(): string | null {
  try {
    return sessionStorage.getItem(META_OAUTH_RETURN_KEY)?.trim() || null
  } catch {
    return null
  }
}
