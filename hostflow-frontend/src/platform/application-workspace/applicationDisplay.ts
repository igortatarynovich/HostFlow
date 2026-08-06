import type { Application, ApplicationStatus, ApplicationTab } from '../../api/types/application'
import type { LocaleCode, TranslateFn } from '../../i18n'

export const APPLICATION_STATUS_BADGE: Record<ApplicationStatus, string> = {
  new: 'bg-emerald-50 text-emerald-700',
  in_progress: 'bg-amber-50 text-amber-700',
  waiting: 'bg-blue-50 text-blue-700',
  questionnaire_submitted: 'bg-violet-50 text-violet-700',
  completed: 'bg-slate-100 text-slate-600',
  rejected: 'bg-rose-50 text-rose-700',
}

const STATUS_FALLBACK: Record<ApplicationStatus, string> = {
  new: 'New',
  in_progress: 'In progress',
  waiting: 'Awaiting reply',
  questionnaire_submitted: 'Reply received',
  completed: 'Completed',
  rejected: 'Rejected',
}

export function applicationStatusLabel(status: ApplicationStatus, t: TranslateFn): string {
  return t(`app.application_workspace.status.${status}`, { defaultValue: STATUS_FALLBACK[status] })
}

function localeTag(locale: LocaleCode | string | undefined): string {
  if (locale === 'ru' || locale === 'ru-RU') return 'ru-RU'
  if (locale === 'pl' || locale === 'pl-PL') return 'pl-PL'
  return 'en-US'
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
  t?: TranslateFn,
  locale?: LocaleCode | string,
): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const diffMs = Date.now() - d.getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) {
    return t?.('app.application_workspace.time.just_now', { defaultValue: 'just now' }) ?? 'just now'
  }
  if (mins < 60) {
    return (
      t?.('app.application_workspace.time.minutes_ago', {
        defaultValue: '{count} min ago',
        values: { count: mins },
      }) ?? `${mins} min ago`
    )
  }
  const hours = Math.floor(mins / 60)
  if (hours < 24) {
    return (
      t?.('app.application_workspace.time.hours_ago', {
        defaultValue: '{count} h ago',
        values: { count: hours },
      }) ?? `${hours} h ago`
    )
  }
  return d.toLocaleString(localeTag(locale), {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
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
