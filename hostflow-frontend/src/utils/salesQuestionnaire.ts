import type { TranslateFn } from '../i18n'

const STATUS_LABEL_DEFAULTS_EN: Record<string, string> = {
  not_sent: 'Questionnaire not sent',
  sent: 'Waiting for response',
  opened: 'Waiting for response',
  in_progress: 'Waiting for response',
  submitted: 'Response received',
  expired: 'Expired',
}

export type SalesQuestionnaireStatus = keyof typeof STATUS_LABEL_DEFAULTS_EN

export function isWaitingForQuestionnaireResponse(status: string | null | undefined): boolean {
  return status === 'sent' || status === 'opened' || status === 'in_progress'
}

export function readSalesQuestionnaireStatus(lead: {
  normalized?: Record<string, unknown> | null
}): SalesQuestionnaireStatus | null {
  const raw = lead.normalized?.sales_questionnaire_status
  if (typeof raw !== 'string' || !raw.trim()) return null
  return raw in STATUS_LABEL_DEFAULTS_EN ? (raw as SalesQuestionnaireStatus) : null
}

type StatusLabelOptions = {
  /** Preferred: CRM UI translate function. */
  t?: TranslateFn
  /** @deprecated Prefer `t` — kept for callers that only have a locale code. */
  locale?: string
  fallback?: string
}

export function salesQuestionnaireStatusLabel(
  lead: { normalized?: Record<string, unknown> | null },
  options?: StatusLabelOptions,
): string {
  const status = readSalesQuestionnaireStatus(lead)
  const t = options?.t
  const fallback =
    options?.fallback ??
    (t
      ? t('app.sales_questionnaire.status.not_sent', {
          defaultValue: STATUS_LABEL_DEFAULTS_EN.not_sent,
        })
      : STATUS_LABEL_DEFAULTS_EN.not_sent)

  if (!status) return fallback

  if (t) {
    return t(`app.sales_questionnaire.status.${status}`, {
      defaultValue: STATUS_LABEL_DEFAULTS_EN[status] ?? fallback,
    })
  }

  return STATUS_LABEL_DEFAULTS_EN[status] ?? fallback
}

export function readSalesQuestionnaireSummary(lead: {
  normalized?: Record<string, unknown> | null
}): Record<string, unknown> {
  const block = lead.normalized?.sales_questionnaire
  return block && typeof block === 'object' && !Array.isArray(block)
    ? (block as Record<string, unknown>)
    : {}
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
