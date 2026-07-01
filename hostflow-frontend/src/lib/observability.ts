/**
 * Observability: Sentry initialization for the browser.
 *
 * This module is a no-op if `VITE_SENTRY_DSN` is not configured, so every
 * environment (including local dev and CI) stays clean. When configured, it
 * surfaces unhandled exceptions, unhandled promise rejections, and React
 * errors (via `AppErrorBoundary`) with enough context to debug.
 *
 * Environment variables (read from `import.meta.env`):
 *   VITE_SENTRY_DSN                   — enable Sentry if set
 *   VITE_SENTRY_ENVIRONMENT           — production / staging / dev / local
 *   VITE_SENTRY_RELEASE               — git sha or app version
 *   VITE_SENTRY_TRACES_SAMPLE_RATE    — 0.0–1.0, default 0.1
 *   VITE_SENTRY_REPLAYS_SAMPLE_RATE   — 0.0–1.0, default 0.0 (off)
 *
 * Keep this file tiny and dependency-free apart from @sentry/react to avoid
 * bloating the initial bundle when Sentry is disabled.
 */

import * as Sentry from '@sentry/react'

let sentryInitialized = false

function envFloat(name: string, fallback: number): number {
  const raw = (import.meta.env as Record<string, string | undefined>)[name]
  if (!raw) return fallback
  const value = Number.parseFloat(raw)
  return Number.isFinite(value) ? value : fallback
}

function envString(name: string): string | undefined {
  const raw = (import.meta.env as Record<string, string | undefined>)[name]
  return raw && raw.length > 0 ? raw : undefined
}

/** Initialize Sentry exactly once. Returns true iff Sentry is now active. */
export function initSentry(): boolean {
  if (sentryInitialized) return true
  const dsn = envString('VITE_SENTRY_DSN')
  if (!dsn) return false

  try {
    // `Sentry.Integration` is no longer publicly exported from `@sentry/react`;
    // import it directly from `@sentry/core` where it still lives as a public type.
    type SentryIntegration = import('@sentry/core').Integration
    const integrations: SentryIntegration[] = [Sentry.browserTracingIntegration()]
    const replaysRate = envFloat('VITE_SENTRY_REPLAYS_SAMPLE_RATE', 0)
    if (replaysRate > 0) {
      integrations.push(
        Sentry.replayIntegration({
          maskAllText: true,
          blockAllMedia: true,
        }),
      )
    }

    Sentry.init({
      dsn,
      environment: envString('VITE_SENTRY_ENVIRONMENT') ?? 'unknown',
      release: envString('VITE_SENTRY_RELEASE'),
      tracesSampleRate: envFloat('VITE_SENTRY_TRACES_SAMPLE_RATE', 0.1),
      replaysSessionSampleRate: replaysRate,
      replaysOnErrorSampleRate: replaysRate > 0 ? 1.0 : 0,
      integrations,
      // Redact likely-sensitive URL params (?token=..., ?code=...) before send.
      beforeSend: (event) => {
        try {
          const url = event.request?.url
          if (url) {
            event.request = { ...event.request, url: redactQueryParams(url) }
          }
        } catch {
          // never block error reporting
        }
        return event
      },
    })
    sentryInitialized = true
    return true
  } catch (err) {
    console.warn('[observability] Sentry init failed:', err)
    return false
  }
}

function redactQueryParams(url: string): string {
  try {
    const u = new URL(url, window.location.origin)
    const SENSITIVE = new Set([
      'token',
      'code',
      'access_token',
      'refresh_token',
      'password',
      'secret',
    ])
    const redacted: string[] = []
    u.searchParams.forEach((_, key) => {
      if (SENSITIVE.has(key.toLowerCase())) redacted.push(key)
    })
    redacted.forEach((key) => u.searchParams.set(key, '[Filtered]'))
    return u.toString()
  } catch {
    return url
  }
}

/** Attach per-user / per-tenant context once authentication is resolved. */
export function bindUserContext(params: {
  userId?: string | null
  tenantId?: string | null
  email?: string | null
}): void {
  if (!sentryInitialized) return
  try {
    if (params.userId || params.email) {
      Sentry.setUser({
        id: params.userId ?? undefined,
        email: params.email ?? undefined,
      })
    } else {
      Sentry.setUser(null)
    }
    if (params.tenantId) Sentry.setTag('tenant_id', params.tenantId)
  } catch {
    // never break on observability
  }
}

export function isSentryEnabled(): boolean {
  return sentryInitialized
}
