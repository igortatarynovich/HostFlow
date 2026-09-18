/** Clock claims from a JWT payload. Signature is not verified (client-side expiry gate). */

export type JwtClockClaims = {
  exp?: number
}

function decodeJwtPayloadJson(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4)
    const json = typeof atob === 'function' ? atob(padded) : ''
    if (!json) return null
    const payload = JSON.parse(json) as Record<string, unknown>
    return payload && typeof payload === 'object' ? payload : null
  } catch {
    return null
  }
}

export function readJwtExpSeconds(token: string): number | null {
  const payload = decodeJwtPayloadJson(token)
  const exp = payload?.exp
  return typeof exp === 'number' && Number.isFinite(exp) ? exp : null
}

/**
 * True when the access token is already expired or will expire within `skewSeconds`.
 * Tokens without `exp` are treated as still valid (cookie session can still work).
 */
export function isJwtExpiredOrExpiring(
  token: string,
  opts?: { skewSeconds?: number; nowMs?: number },
): boolean {
  const exp = readJwtExpSeconds(token)
  if (exp == null) return false
  const skewMs = (opts?.skewSeconds ?? 30) * 1000
  const now = opts?.nowMs ?? Date.now()
  return exp * 1000 <= now + skewMs
}
