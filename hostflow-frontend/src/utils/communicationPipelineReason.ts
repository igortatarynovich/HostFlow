/** Translate C5 Communication Pipeline deny / dispatch reason codes for inbox UI. */
export function communicationPipelineReasonMessage(
  reason: string | null | undefined,
  t: (key: string, options?: { defaultValue?: string; values?: Record<string, string | number> }) => string,
): string {
  const code = String(reason || '').trim()
  if (!code) {
    return t('app.communications.email.dispatch_failed')
  }
  const key = `app.communications_api.pipeline.${code}`
  const translated = t(key, { defaultValue: '' })
  if (translated && translated !== key) return translated
  return t('app.communications.email.dispatch_failed_reason', {
    defaultValue: 'Send blocked: {reason}',
    values: { reason: code },
  })
}
