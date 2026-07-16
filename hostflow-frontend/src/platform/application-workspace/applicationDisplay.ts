import type { Application, ApplicationStatus, ApplicationTab } from '../../api/types/application'

export const APPLICATION_STATUS_BADGE: Record<ApplicationStatus, string> = {
  new: 'bg-emerald-50 text-emerald-700',
  in_progress: 'bg-amber-50 text-amber-700',
  waiting: 'bg-blue-50 text-blue-700',
  questionnaire_submitted: 'bg-violet-50 text-violet-700',
  completed: 'bg-slate-100 text-slate-600',
  rejected: 'bg-rose-50 text-rose-700',
}

export const APPLICATION_STATUS_TEXT: Record<ApplicationStatus, string> = {
  new: 'Новое',
  in_progress: 'В работе',
  waiting: 'Ожидаем ответ',
  questionnaire_submitted: 'Ответ получен',
  completed: 'Завершено',
  rejected: 'Отклонено',
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

export function formatApplicationRelativeTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const diffMs = Date.now() - d.getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин назад`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} ч назад`
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
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
