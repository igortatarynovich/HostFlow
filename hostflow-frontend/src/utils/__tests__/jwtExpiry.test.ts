import { describe, expect, it } from 'vitest'
import { isJwtExpiredOrExpiring, readJwtExpSeconds } from '../jwtExpiry'
import { isHttpUnauthorized, isTransientRequestError } from '../errorHandling'

function unsignedJwt(payload: Record<string, unknown>): string {
  const json = JSON.stringify(payload)
  const b64 = btoa(json).replace(/=+$/g, '').replace(/\+/g, '-').replace(/\//g, '_')
  return `eyJhbGciOiJub25lIn0.${b64}.sig`
}

describe('jwtExpiry', () => {
  it('reads exp from an unsigned JWT payload', () => {
    expect(readJwtExpSeconds(unsignedJwt({ exp: 1_700_000_000 }))).toBe(1_700_000_000)
  })

  it('treats a still-valid token as not expired', () => {
    const token = unsignedJwt({ exp: 2_000 })
    expect(isJwtExpiredOrExpiring(token, { nowMs: 1_000_000, skewSeconds: 30 })).toBe(false)
  })

  it('treats a token inside the skew window as expiring', () => {
    const token = unsignedJwt({ exp: 1_020 })
    expect(isJwtExpiredOrExpiring(token, { nowMs: 1_000_000, skewSeconds: 30 })).toBe(true)
  })

  it('treats an already-expired token as expired', () => {
    const token = unsignedJwt({ exp: 500 })
    expect(isJwtExpiredOrExpiring(token, { nowMs: 1_000_000, skewSeconds: 30 })).toBe(true)
  })

  it('does not treat a token without exp as expired', () => {
    expect(isJwtExpiredOrExpiring(unsignedJwt({ sub: 'u1' }), { nowMs: Date.now() })).toBe(false)
  })
})

describe('isHttpUnauthorized', () => {
  it('detects axios 401 responses', () => {
    expect(isHttpUnauthorized({ response: { status: 401 } })).toBe(true)
    expect(isHttpUnauthorized({ response: { status: 403 } })).toBe(false)
    expect(isHttpUnauthorized({ message: 'Network Error' })).toBe(false)
    expect(isTransientRequestError({ response: { status: 401 } })).toBe(false)
  })
})
