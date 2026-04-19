/**
 * toastFromError — turn an axios / API error into a consistent error toast.
 *
 * Contract (see docs/specs/ux/error_handling.md):
 *   1. Network and timeout errors → red toast, long TTL, generic retry CTA.
 *   2. 5xx and unexpected (non-HTTP) errors → red toast + report to Sentry.
 *   3. 400 captcha_failed / 401 / 403 / 404 / 409 → red toast, actionable hint.
 *   4. 402 plan-limit / 403 billing-gate → red toast with "Open Billing" action
 *      when we know where to send the user.
 *   5. 429 rate-limit → red toast, include `Please retry in N seconds` when the
 *      backend reported `retry_after`.
 *
 * The toast is explicit (always visible to the user). If you additionally need
 * an inline banner with retry button, use `ErrorRecoveryBanner` with the same
 * `FriendlyErrorInfo` — call `getFriendlyErrorInfo` yourself and feed both UIs.
 */

import type { ReactNode } from 'react'
import * as Sentry from '@sentry/react'
import {
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
  type FriendlyErrorTranslateFn,
} from './friendlyError'

type ToastNotify = (message: {
  title: string
  description?: ReactNode
  variant?: 'info' | 'success' | 'error' | 'warning'
  action?: { label: string; onClick: () => void }
  ttlMs?: number
}) => string

export type ToastFromErrorOptions = {
  /** Fallback title used when friendly mapping has no status-specific label. */
  fallbackTitle: string
  /** Optional translator (usually `useTranslation().t`). */
  t?: FriendlyErrorTranslateFn
  /** When provided, the toast shows a Retry button that calls this handler. */
  onRetry?: () => void
  /** Default label for the Retry button. */
  retryLabel?: string
  /**
   * If false, do not forward this error to Sentry even for 5xx/unknown cases.
   * Use for expected background failures you purposefully surface via toast
   * (e.g. optimistic undo flows that can fail).
   */
  reportToSentry?: boolean
  /**
   * Extra Sentry tags / extras merged into the reported event.
   * Useful for binding feature tags (e.g. { feature: 'leads.bulk_move' }).
   */
  sentryTags?: Record<string, string>
}

/**
 * Returns `true` if this error is "user-visible expected" — no need to report
 * to Sentry (it's a plan gate, quota, validation, 404 by user intent, etc.).
 */
function isExpectedUserError(info: FriendlyErrorInfo): boolean {
  const status = info.status ?? 0
  if (status === 0) return false // network / unknown → report
  if (status >= 500) return false
  // Plan-limit / quota / billing / captcha / validation / rate-limit are user-facing.
  return true
}

function buildDescription(info: FriendlyErrorInfo): string | undefined {
  const lines = [info.hint, info.detail && info.detail !== info.hint ? info.detail : null]
  const out = lines.filter(Boolean).join(' ')
  return out.trim() || undefined
}

/**
 * Render a unified error toast from any thrown error. Returns the toast id so
 * callers can dismiss it early (e.g. when retrying succeeds).
 */
export function toastFromError(
  notify: ToastNotify,
  err: unknown,
  opts: ToastFromErrorOptions,
): string {
  const info = getFriendlyErrorInfo(err, opts.fallbackTitle, opts.t)
  const description = buildDescription(info)
  const shouldReport =
    opts.reportToSentry !== false && !isExpectedUserError(info)

  if (shouldReport) {
    try {
      Sentry.withScope((scope) => {
        if (info.status) scope.setTag('http.status', String(info.status))
        if (info.code) scope.setTag('error.code', info.code)
        if (opts.sentryTags) {
          for (const [k, v] of Object.entries(opts.sentryTags)) scope.setTag(k, v)
        }
        scope.setExtra('friendly_title', info.title)
        Sentry.captureException(err)
      })
    } catch {
      // never let observability break the UI
    }
  }

  return notify({
    title: info.title,
    description,
    variant: 'error',
    action: opts.onRetry
      ? { label: opts.retryLabel ?? 'Retry', onClick: opts.onRetry }
      : undefined,
  })
}

