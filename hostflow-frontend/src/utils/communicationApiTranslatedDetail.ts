/** Mirrors backend `detail.code` for mandatory outbound link (see `communications.py`). */
export const COMMUNICATION_API_CODE_THREAD_UNLINKED_OUTBOUND = 'communication_thread_unlinked_outbound_blocked' as const

/** When API returns this code, show i18n instead of English `detail.msg`. */
export function communicationApiTranslatedDetail(
  err: unknown,
  t: (key: string, options?: { defaultValue?: string; values?: Record<string, string | number> }) => string,
): string | null {
  const d = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (d && typeof d === 'object' && !Array.isArray(d)) {
    const code = String((d as { code?: string }).code || '').trim()
    if (code === COMMUNICATION_API_CODE_THREAD_UNLINKED_OUTBOUND) {
      return t('app.communications_api.thread_unlinked_outbound_blocked')
    }
  }
  return null
}
