const STATUS_LABELS_PL: Record<string, string> = {
  not_sent: 'Ankieta niewysłana',
  sent: 'Oczekujemy na odpowiedź',
  opened: 'Oczekujemy na odpowiedź',
  in_progress: 'Oczekujemy na odpowiedź',
  submitted: 'Wypełniona',
  expired: 'Wygasła',
}

const STATUS_LABELS_EN: Record<string, string> = {
  not_sent: 'Questionnaire not sent',
  sent: 'Waiting for response',
  opened: 'Waiting for response',
  in_progress: 'Waiting for response',
  submitted: 'Response received',
  expired: 'Expired',
}

const STATUS_LABELS_RU: Record<string, string> = {
  not_sent: 'Анкета не отправлена',
  sent: 'Ожидаем ответ',
  opened: 'Ожидаем ответ',
  in_progress: 'Ожидаем ответ',
  submitted: 'Ответ получен',
  expired: 'Истекла',
}

export type SalesQuestionnaireStatus = keyof typeof STATUS_LABELS_EN

export function isWaitingForQuestionnaireResponse(status: string | null | undefined): boolean {
  return status === 'sent' || status === 'opened' || status === 'in_progress' || status === 'waiting_for_response'
}

export function readSalesQuestionnaireStatus(lead: { normalized?: Record<string, unknown> | null }): SalesQuestionnaireStatus | null {
  const raw = lead.normalized?.sales_questionnaire_status
  if (typeof raw !== 'string' || !raw.trim()) return null
  return raw in STATUS_LABELS_EN ? (raw as SalesQuestionnaireStatus) : null
}

type StatusLabelOptions = {
  locale?: string
  fallback?: string
}

function statusLabelsForLocale(locale?: string): Record<string, string> {
  const code = String(locale || 'en').slice(0, 2).toLowerCase()
  if (code === 'pl') return STATUS_LABELS_PL
  if (code === 'ru') return STATUS_LABELS_RU
  return STATUS_LABELS_EN
}

export function salesQuestionnaireStatusLabel(
  lead: { normalized?: Record<string, unknown> | null },
  options?: StatusLabelOptions,
): string {
  const labels = statusLabelsForLocale(options?.locale)
  const fallback = options?.fallback ?? labels.not_sent ?? 'Questionnaire not sent'
  const status = readSalesQuestionnaireStatus(lead)
  if (!status) return fallback
  return labels[status] ?? fallback
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
