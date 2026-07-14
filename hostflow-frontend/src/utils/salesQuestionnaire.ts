const STATUS_LABELS_PL: Record<string, string> = {
  not_sent: 'Ankieta niewysłana',
  sent: 'Ankieta wysłana',
  opened: 'Ankieta otwarta',
  in_progress: 'W trakcie wypełniania',
  submitted: 'Wypełniona',
  expired: 'Wygasła',
}

export type SalesQuestionnaireStatus = keyof typeof STATUS_LABELS_PL

export function readSalesQuestionnaireStatus(lead: { normalized?: Record<string, unknown> | null }): SalesQuestionnaireStatus | null {
  const raw = lead.normalized?.sales_questionnaire_status
  if (typeof raw !== 'string' || !raw.trim()) return null
  return raw in STATUS_LABELS_PL ? (raw as SalesQuestionnaireStatus) : null
}

export function salesQuestionnaireStatusLabel(
  lead: { normalized?: Record<string, unknown> | null },
  inviteStatus?: string | null,
  fallback = 'Ankieta niewysłana',
): string {
  const status = readSalesQuestionnaireStatus(lead) || (inviteStatus && inviteStatus in STATUS_LABELS_PL ? (inviteStatus as SalesQuestionnaireStatus) : null)
  if (!status) return fallback
  return STATUS_LABELS_PL[status] ?? fallback
}

export function formatSalesQuestionnaireTimestamp(iso: string | null | undefined, locale = 'pl'): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  const localeTag = locale === 'pl' ? 'pl-PL' : locale === 'ru' ? 'ru-RU' : 'en-US'
  return date.toLocaleString(localeTag, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function readSalesQuestionnaireSummary(lead: { normalized?: Record<string, unknown> | null }): Record<string, unknown> {
  const block = lead.normalized?.sales_questionnaire
  return block && typeof block === 'object' && !Array.isArray(block) ? (block as Record<string, unknown>) : {}
}

export function absoluteApplyUrl(applyUrl: string): string {
  if (/^https?:\/\//i.test(applyUrl)) return applyUrl
  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}${applyUrl.startsWith('/') ? applyUrl : `/${applyUrl}`}`
  }
  return applyUrl
}

export function whatsAppShareUrl(phone: string | null | undefined, message: string): string | null {
  const digits = String(phone || '').replace(/\D/g, '')
  if (!digits) return null
  return `https://wa.me/${digits}?text=${encodeURIComponent(message)}`
}
