import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconChecklist } from '@tabler/icons-react'
import { addDays, startOfDay } from 'date-fns'

import { completeReminder, listReminders, updateReminder } from '../../api/client'
import type { ReminderRecord } from '../../api/types/notification'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { usePermissions } from '../../hooks/usePermissions'
import { useI18n } from '../../i18n'

const PEEK_LIMIT = 5
const FETCH_LIMIT = 100

/**
 * Phase 4 (taskbar): compact peek at open reminders due through end of tomorrow —
 * same window as Work Hub `MyTasksPanel`, without leaving the current page.
 */
export function TodayTasksPeek() {
  const { can } = usePermissions()
  const { t, locale } = useI18n()
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [rows, setRows] = useState<ReminderRecord[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [busyId, setBusyId] = useState<string | null>(null)
  const rootRef = useRef<HTMLDivElement | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const now = new Date()
      const dueTo = addDays(startOfDay(now), 2)
      const data = await listReminders({
        assigneeScope: 'mine',
        status: ['new', 'pending', 'overdue'],
        dueTo: dueTo.toISOString(),
        limit: FETCH_LIMIT,
      })
      const items: ReminderRecord[] = Array.isArray(data?.items) ? (data.items as ReminderRecord[]) : []
      setTotalCount(items.length)
      setRows(items.slice(0, PEEK_LIMIT))
    } catch {
      setTotalCount(0)
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  const handleComplete = useCallback(
    async (id: string) => {
      if (!id) return
      setBusyId(id)
      try {
        await completeReminder(id)
        await load()
      } finally {
        setBusyId(null)
      }
    },
    [load],
  )

  const handleSnoozeHour = useCallback(
    async (row: ReminderRecord) => {
      if (!row?.id) return
      const dueTs = Date.parse(String(row.due_at || ''))
      const nextRemindAt = Number.isNaN(dueTs)
        ? new Date(Date.now() + 60 * 60 * 1000).toISOString()
        : new Date(dueTs + 60 * 60 * 1000).toISOString()
      setBusyId(row.id)
      try {
        await updateReminder(row.id, { remind_at: nextRemindAt })
        await load()
      } finally {
        setBusyId(null)
      }
    },
    [load],
  )

  useEffect(() => {
    if (!open) return
    void load()
  }, [open, load])

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  if (!can('notifications.view')) return null

  const loc = locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US'

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className="relative rounded-full border border-slate-200 p-1.5 text-slate-700 transition hover:bg-slate-50"
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={t('app.topbar.tasks_peek.label', { defaultValue: 'Today’s tasks' })}
        title={t('app.topbar.tasks_peek.label', { defaultValue: 'Today’s tasks' })}
        onClick={() => setOpen((v) => !v)}
      >
        <IconChecklist size={20} stroke={1.8} />
        {totalCount > 0 ? (
          <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-brand-600 px-1 text-[11px] font-semibold text-white">
            {totalCount > 99 ? '99+' : totalCount}
          </span>
        ) : null}
      </button>
      {open ? (
        <div
          className="absolute right-0 top-11 z-50 w-[min(92vw,22rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
          role="dialog"
          aria-label={t('app.topbar.tasks_peek.title', { defaultValue: 'Tasks due soon' })}
        >
          <div className="border-b border-slate-100 px-4 py-3">
            <p className="text-sm font-semibold text-slate-900">
              {t('app.topbar.tasks_peek.title', { defaultValue: 'Tasks due soon' })}
            </p>
            <p className="text-xs text-slate-500">
              {t('app.topbar.tasks_peek.subtitle', { defaultValue: 'Overdue, today & tomorrow' })}
            </p>
          </div>
          <div className="max-h-[min(50vh,20rem)] space-y-1 overflow-auto p-2">
            {loading ? (
              <p className="px-2 py-3 text-sm text-slate-500">{t('common.loading')}</p>
            ) : rows.length === 0 ? (
              <p className="px-2 py-3 text-sm text-slate-500">{t('app.reminders.states.empty')}</p>
            ) : (
              rows.map((r) => {
                const due = r.due_at ? new Date(r.due_at) : null
                const dueLabel =
                  due && !Number.isNaN(due.getTime())
                    ? due.toLocaleString(loc, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                    : '—'
                const title = String(r.title || r.type || t('app.reminders.fallback_title')).trim()
                const href = `${CRM_APP_PATHS.tasks}?t_id=${encodeURIComponent(String(r.id))}`
                return (
                  <div key={r.id} className="rounded-lg px-2 py-2 transition hover:bg-slate-50">
                    <Link to={href} className="block text-left text-sm" onClick={() => setOpen(false)}>
                      <span className="line-clamp-2 font-medium text-slate-900">{title}</span>
                      <span className="mt-0.5 block text-[11px] text-slate-500">{dueLabel}</span>
                    </Link>
                    <div className="mt-1.5 flex items-center gap-2">
                      <button
                        type="button"
                        className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 disabled:opacity-50"
                        disabled={busyId === r.id}
                        onClick={() => void handleComplete(String(r.id))}
                      >
                        {t('app.topbar.tasks_peek.complete')}
                      </button>
                      <button
                        type="button"
                        className="text-[11px] font-semibold text-slate-600 hover:text-slate-800 disabled:opacity-50"
                        disabled={busyId === r.id}
                        onClick={() => void handleSnoozeHour(r)}
                      >
                        {t('app.topbar.tasks_peek.snooze_hour')}
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
          <div className="border-t border-slate-100 px-3 py-2">
            <Link
              to={CRM_APP_PATHS.tasks}
              className="text-xs font-semibold text-brand-700 hover:text-brand-800"
              onClick={() => setOpen(false)}
            >
              {t('app.topbar.tasks_peek.open_all', { defaultValue: 'Open tasks' })}
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  )
}
