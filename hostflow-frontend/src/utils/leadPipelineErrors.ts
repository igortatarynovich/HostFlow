import type { TranslateFn } from '../i18n'

/** Map backend lead processing error codes to i18n (§2.10). */
export function formatLeadPipelineError(code: string | null | undefined, t: TranslateFn): string {
  if (code == null || !String(code).trim()) return '—'
  const c = String(code).trim()
  const key = `app.leads.pipeline_errors.${c}`
  const translated = t(key)
  return translated === key ? c : translated
}
