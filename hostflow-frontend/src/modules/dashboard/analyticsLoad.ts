import type { TranslateFn } from '../../i18n'

export function isTransientHttpError(e: unknown): boolean {
  const status = (e as { response?: { status?: number } })?.response?.status
  return status === 502 || status === 503 || status === 504
}

/** Prefer soft copy for gateway blips; keep prior dashboard data in the caller. */
export function formatAnalyticsLoadError(e: unknown, t: TranslateFn): string {
  const err = e as { response?: { data?: { detail?: unknown }; status?: number }; message?: string }
  if (isTransientHttpError(e)) {
    return t('app.dashboard.errors.temporarily_unavailable', {
      defaultValue: t('app.dashboard.errors.load_failed'),
    })
  }
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (detail) return JSON.stringify(detail)
  return err?.message || t('app.dashboard.errors.load_failed')
}
