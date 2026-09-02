import type { Application, ApplicationStatus, ApplicationTab } from '../../api/types/application'
import type { TranslateFn } from '../../i18n'

export const APPLICATION_STATUS_BADGE: Record<ApplicationStatus, string> = {
  new: 'bg-emerald-50 text-emerald-700',
  in_progress: 'bg-amber-50 text-amber-700',
  waiting: 'bg-blue-50 text-blue-700',
  questionnaire_submitted: 'bg-violet-50 text-violet-700',
  completed: 'bg-slate-100 text-slate-600',
  rejected: 'bg-rose-50 text-rose-700',
}

/** Call-outcome activity codes shown in the application table filter. Not ticket statuses. */
export const APPLICATION_CALL_OUTCOME_CODES = [
  'interested',
  'not_interested',
  'callback_requested',
  'answered',
  'no_answer',
  'unavailable',
  'wrong_number',
] as const

export function applicationCallOutcome(application: Application): string | null {
  const raw = application.extensions?.call_result_v1
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const result = String((raw as { result?: unknown }).result || '').trim()
  return result || null
}

export function applicationCallOutcomeLabel(code: string, t: TranslateFn): string {
  const key = `app.recruitment_inquiry.call_result.results.${code}`
  const translated = t(key)
  return translated === key ? code : translated
}

export function applicationMatchesSearch(application: Application, q: string): boolean {
  const needle = q.trim().toLowerCase()
  if (!needle) return true
  const haystack = [
    application.title,
    application.contact.name,
    application.contact.phone,
    application.contact.email,
    application.source,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return haystack.includes(needle)
}

export function applicationStatusLabel(status: string, t: TranslateFn): string {
  const key = `app.sales_inquiry.status.${status}`
  const translated = t(key)
  return translated === key ? status : translated
}

/** @deprecated Prefer applicationStatusLabel(status, t) */
export const APPLICATION_STATUS_TEXT: Record<ApplicationStatus, string> = {
  new: 'New',
  in_progress: 'In progress',
  waiting: 'Waiting for a reply',
  questionnaire_submitted: 'Reply received',
  completed: 'Completed',
  rejected: 'Rejected',
}

export function applicationTabBucket(app: Application): ApplicationTab {
  if (app.tab_bucket && app.tab_bucket !== 'all') return app.tab_bucket
  if (app.status === 'rejected') return 'completed'
  if (app.status === 'questionnaire_submitted') return 'in_progress'
  return app.status === 'new' || app.status === 'in_progress' || app.status === 'waiting' || app.status === 'completed'
    ? app.status
    : 'all'
}

export function applicationNeedsFirstContact(app: Application): boolean {
  return app.status === 'new'
}

export function formatApplicationRelativeTime(
  iso: string | null | undefined,
  t: TranslateFn,
  locale?: string,
): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const diffMs = Date.now() - d.getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return t('app.sales_inquiry.time.just_now')
  if (mins < 60) return t('app.sales_inquiry.time.minutes_ago', { values: { count: mins } })
  const hours = Math.floor(mins / 60)
  if (hours < 24) return t('app.sales_inquiry.time.hours_ago', { values: { count: hours } })
  return d.toLocaleString(locale, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function applicationInitial(app: Application): string {
  const name = app.contact.name || app.title
  return name.charAt(0).toUpperCase() || '?'
}

export function applicationWhatsappHref(phone: string | null | undefined): string | null {
  if (!phone) return null
  const digits = phone.replace(/[^\d+]/g, '').replace(/^\+/, '')
  return digits ? `https://wa.me/${digits}` : null
}

export function sortApplicationsByCreatedDesc(a: Application, b: Application): number {
  const ta = a.created_at ? new Date(a.created_at).getTime() : 0
  const tb = b.created_at ? new Date(b.created_at).getTime() : 0
  return tb - ta
}
