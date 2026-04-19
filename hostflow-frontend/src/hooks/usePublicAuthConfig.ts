import { useEffect, useState } from 'react'
import { fetchPublicAuthConfig, type PublicAuthConfig } from '../api/users'

const DEFAULT_CONFIG: PublicAuthConfig = {
  turnstile_enabled: false,
  turnstile_sitekey: null,
}

// Module-scope cache so every unauthenticated page (login, signup, reset,
// public intake) shares the same fetch and we don't hit the backend per route.
let cached: PublicAuthConfig | null = null
let pending: Promise<PublicAuthConfig> | null = null

async function loadOnce(): Promise<PublicAuthConfig> {
  if (cached) return cached
  if (pending) return pending
  pending = fetchPublicAuthConfig()
    .then((cfg) => {
      cached = cfg
      return cfg
    })
    .catch(() => {
      cached = DEFAULT_CONFIG
      return DEFAULT_CONFIG
    })
    .finally(() => {
      pending = null
    })
  return pending
}

/**
 * Read the unauthenticated `/auth/public-config` payload.
 *
 * Returns `DEFAULT_CONFIG` while the network call is in flight, so callers
 * can render their form immediately without a blocking spinner. The widget
 * simply doesn't render until `turnstile_enabled && turnstile_sitekey` are
 * both truthy, matching the server contract.
 */
export function usePublicAuthConfig(): PublicAuthConfig {
  const [cfg, setCfg] = useState<PublicAuthConfig>(cached ?? DEFAULT_CONFIG)
  useEffect(() => {
    let active = true
    loadOnce().then((loaded) => {
      if (active) setCfg(loaded)
    })
    return () => {
      active = false
    }
  }, [])
  return cfg
}
