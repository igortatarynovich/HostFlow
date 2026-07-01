import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listManagers } from '../api/client'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import {
  createCommunicationPlannerEvent,
  getMyWorkingHours,
  listCommunicationPlannerEvents,
  patchCommunicationPlannerEvent,
  type CommunicationPlannerEvent,
  type WorkingHoursSchedule,
} from '../api/communications'
import { useI18n } from '../i18n'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageBreadcrumb } from '../components/nav/PageBreadcrumb'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { friendlyErrorBannerSecondary, friendlyFormHintError, getFriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'

function toLocalInput(dt?: string | null): string {
  if (!dt) return ''
  const d = new Date(dt)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatDateTime(dt?: string | null): string {
  if (!dt) return '—'
  const d = new Date(dt)
  if (Number.isNaN(d.getTime())) return dt
  return new Intl.DateTimeFormat(undefined, { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(d)
}

export default function CommunicationsPlannerPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [busy, setBusy] = useState(false)
  const [items, setItems] = useState<CommunicationPlannerEvent[]>([])
  const [workingHours, setWorkingHours] = useState<WorkingHoursSchedule | null>(null)
  const [allowOutsideHours, setAllowOutsideHours] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [kindFilter, setKindFilter] = useState('')
  const [managers, setManagers] = useState<Array<{ id: string; label: string }>>([])
  const [labels, setLabels] = useState<Map<string, string>>(new Map())
  const [form, setForm] = useState({
    title: '',
    kind: 'task',
    priority: 'normal',
    assigneeId: '',
    startAt: toLocalInput(new Date(Date.now() + 30 * 60_000).toISOString()),
    endAt: toLocalInput(new Date(Date.now() + 90 * 60_000).toISOString()),
    allDay: false,
    description: '',
  })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [eventsRes, mgrs, wh] = await Promise.all([
        listCommunicationPlannerEvents({
          limit: 200,
          status_filter: statusFilter ? [statusFilter] : undefined,
          kind: kindFilter || undefined,
        }),
        listManagers().catch(() => []),
        getMyWorkingHours().catch(() => null),
      ])
      const normalized = (Array.isArray(mgrs) ? mgrs : []).map((m: any) => ({ id: String(m.id), label: String(m.label || m.full_name || m.email || m.id) }))
      setManagers(normalized)
      setLabels(new Map(normalized.map((m) => [m.id, m.label])))
      setItems(Array.isArray(eventsRes.items) ? eventsRes.items : [])
      if (wh) setWorkingHours(wh)
    } catch (err: any) {
      setError(getFriendlyErrorInfo(err, t('app.communications.planner.errors.load', { defaultValue: 'Failed to load planner' }), t))
    } finally {
      setLoading(false)
    }
  }, [kindFilter, statusFilter, t])

  useEffect(() => {
    void load()
  }, [load])

  const stats = useMemo(() => ({
    total: items.length,
    planned: items.filter((x) => x.status === 'planned').length,
    inProgress: items.filter((x) => x.status === 'in_progress').length,
    done: items.filter((x) => x.status === 'done').length,
  }), [items])

  const handleCreate = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (!form.title.trim() || !form.startAt) return
    if (!form.allDay && workingHours?.days?.length && !allowOutsideHours) {
      const d = new Date(form.startAt)
      const jsDay = d.getDay() // 0=Sun..6=Sat
      const weekday = (jsDay + 6) % 7 // 0=Mon..6=Sun
      const day = workingHours.days.find((x) => x.weekday === weekday)
      if (day?.enabled && Array.isArray(day.windows) && day.windows.length) {
        const hhmm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
        const toMin = (v: string) => {
          const [h, m] = v.split(':').map((x) => Number(x))
          return h * 60 + m
        }
        const mNow = toMin(hhmm)
        const inAny = day.windows.some((w) => mNow >= toMin(w.from) && mNow < toMin(w.to))
        if (!inAny) {
          setError(
            friendlyFormHintError(
              t('app.communications.planner.errors.outside_hours', {
                defaultValue: 'Selected start time is outside your working hours. Update My Availability or enable "Create outside hours".',
              }),
              t,
            ),
          )
          return
        }
      }
    }
    setBusy(true)
    try {
      await createCommunicationPlannerEvent({
        title: form.title.trim(),
        kind: form.kind,
        priority: form.priority,
        assignee_id: form.assigneeId || undefined,
        start_at: new Date(form.startAt).toISOString(),
        end_at: form.allDay || !form.endAt ? undefined : new Date(form.endAt).toISOString(),
        all_day: form.allDay,
        description: form.description.trim() || undefined,
      })
      setForm((p) => ({ ...p, title: '', description: '' }))
      await load()
      setError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.planner.errors.create', { defaultValue: 'Failed to create planner event' }),
        )
      ) {
        setError(getFriendlyErrorInfo(err, t('app.communications.planner.errors.create', { defaultValue: 'Failed to create planner event' }), t))
      }
    } finally {
      setBusy(false)
    }
  }, [allowOutsideHours, form, load, planLimitModal, t, workingHours])

  const setEventStatus = useCallback(async (id: string, status: string) => {
    setBusy(true)
    try {
      await patchCommunicationPlannerEvent(id, { status })
      await load()
      setError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.planner.errors.update', { defaultValue: 'Failed to update planner event' }),
        )
      ) {
        setError(getFriendlyErrorInfo(err, t('app.communications.planner.errors.update', { defaultValue: 'Failed to update planner event' }), t))
      }
    } finally {
      setBusy(false)
    }
  }, [load, planLimitModal, t])

  return (
    <div className="space-y-4">
      <WorkspaceTopNav active="calendar" />
      <PageBreadcrumb className="max-w-4xl" />
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.communications.ia.planner_title', { defaultValue: 'Planner' })}</h1>
        <p className="text-sm text-slate-500">
          {t('app.communications.ia.planner_subtitle', { defaultValue: 'Operational planning for managers and tasks. Separate from email/messages inboxes.' })}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">{t('app.communications.planner.stats.total', { defaultValue: 'Total' })}: <strong>{stats.total}</strong></div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{t('app.communications.planner.stats.planned', { defaultValue: 'Planned' })}: <strong>{stats.planned}</strong></div>
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-800">{t('app.communications.planner.stats.in_progress', { defaultValue: 'In progress' })}: <strong>{stats.inProgress}</strong></div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{t('app.communications.planner.stats.done', { defaultValue: 'Done' })}: <strong>{stats.done}</strong></div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1.2fr]">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 text-sm font-semibold text-slate-900">{t('app.communications.planner.form.title', { defaultValue: 'New planner event' })}</div>
          {error && (
            <div className="mb-3">
              <ErrorRecoveryBanner
                info={error}
                onRetry={() => void load()}
                retryLabel={t('common.actions.refresh')}
                {...friendlyErrorBannerSecondary(
                  error,
                  CRM_APP_PATHS.calendar,
                  t('app.nav.items.calendar', { defaultValue: 'Calendar' }),
                )}
                compact
              />
            </div>
          )}
          <form className="space-y-2" onSubmit={handleCreate}>
            <input value={form.title} onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))} className="input" placeholder={t('app.communications.planner.form.fields.title', { defaultValue: 'Title' })} />
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <select value={form.kind} onChange={(e) => setForm((p) => ({ ...p, kind: e.target.value }))} className="input">
                <option value="task">{t('app.communications.planner.kind.task', { defaultValue: 'Task' })}</option>
                <option value="call">{t('app.communications.planner.kind.call', { defaultValue: 'Call' })}</option>
                <option value="meeting">{t('app.communications.planner.kind.meeting', { defaultValue: 'Meeting' })}</option>
                <option value="followup">{t('app.communications.planner.kind.followup', { defaultValue: 'Follow-up' })}</option>
                <option value="shift">{t('app.communications.planner.kind.shift', { defaultValue: 'Shift' })}</option>
              </select>
              <select value={form.priority} onChange={(e) => setForm((p) => ({ ...p, priority: e.target.value }))} className="input">
                <option value="low">{t('app.communications.planner.priority.low', { defaultValue: 'Low' })}</option>
                <option value="normal">{t('app.communications.planner.priority.normal', { defaultValue: 'Normal' })}</option>
                <option value="high">{t('app.communications.planner.priority.high', { defaultValue: 'High' })}</option>
              </select>
            </div>
            <select value={form.assigneeId} onChange={(e) => setForm((p) => ({ ...p, assigneeId: e.target.value }))} className="input">
              <option value="">{t('app.communications.planner.assignee.unassigned', { defaultValue: 'Unassigned' })}</option>
              {managers.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
            </select>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.allDay} onChange={(e) => setForm((p) => ({ ...p, allDay: e.target.checked }))} />
              {t('app.communications.planner.form.fields.all_day', { defaultValue: 'All day' })}
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={allowOutsideHours} onChange={(e) => setAllowOutsideHours(e.target.checked)} />
              {t('app.communications.planner.form.fields.outside_hours', { defaultValue: 'Create outside working hours' })}
            </label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <input type={form.allDay ? 'date' : 'datetime-local'} value={form.startAt} onChange={(e) => setForm((p) => ({ ...p, startAt: e.target.value }))} className="input" />
              <input type={form.allDay ? 'date' : 'datetime-local'} value={form.endAt} onChange={(e) => setForm((p) => ({ ...p, endAt: e.target.value }))} className="input" />
            </div>
            <textarea rows={3} value={form.description} onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))} className="textarea" placeholder={t('app.communications.planner.form.fields.description', { defaultValue: 'Description' })} />
            <button type="submit" disabled={busy || !form.title.trim() || !form.startAt} className="btn-primary disabled:opacity-50">
              {busy ? t('common.loading') : t('common.actions.create', { defaultValue: 'Create' })}
            </button>
          </form>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to={CRM_APP_PATHS.calendar} className="btn-secondary">
              {t('app.nav.items.calendar', { defaultValue: 'Calendar' })}
            </Link>
            <Link to={CRM_APP_PATHS.myAvailability} className="btn-secondary">
              {t('app.nav.items.my_availability', { defaultValue: 'My availability' })}
            </Link>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input">
              <option value="">{t('app.communications.planner.filters.all_statuses', { defaultValue: 'All statuses' })}</option>
              <option value="planned">{t('app.communications.planner.status.planned', { defaultValue: 'Planned' })}</option>
              <option value="in_progress">{t('app.communications.planner.status.in_progress', { defaultValue: 'In progress' })}</option>
              <option value="done">{t('app.communications.planner.status.done', { defaultValue: 'Done' })}</option>
              <option value="cancelled">{t('app.communications.planner.status.cancelled', { defaultValue: 'Cancelled' })}</option>
            </select>
            <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value)} className="input">
              <option value="">{t('app.communications.planner.filters.all_kinds', { defaultValue: 'All kinds' })}</option>
              <option value="task">{t('app.communications.planner.kind.task', { defaultValue: 'Task' })}</option>
              <option value="call">{t('app.communications.planner.kind.call', { defaultValue: 'Call' })}</option>
              <option value="meeting">{t('app.communications.planner.kind.meeting', { defaultValue: 'Meeting' })}</option>
              <option value="followup">{t('app.communications.planner.kind.followup', { defaultValue: 'Follow-up' })}</option>
              <option value="shift">{t('app.communications.planner.kind.shift', { defaultValue: 'Shift' })}</option>
            </select>
            <button type="button" onClick={() => void load()} className="btn-secondary">
              {t('common.actions.refresh')}
            </button>
          </div>

          {loading && <div className="text-sm text-slate-500">{t('common.loading')}</div>}
          {!loading && items.length === 0 && <div className="text-sm text-slate-500">{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</div>}
          <div className="space-y-2">
            {items.map((row) => (
              <div key={row.id} className="rounded border border-slate-200 px-3 py-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-slate-900">{row.title}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {t(`app.communications.planner.kind.${row.kind}`, { defaultValue: row.kind })} · {t(`app.communications.planner.status.${row.status}`, { defaultValue: row.status })} · {t(`app.communications.planner.priority.${row.priority}`, { defaultValue: row.priority })} · {formatDateTime(row.start_at)}{row.end_at ? ` → ${formatDateTime(row.end_at)}` : ''}
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      {t('app.communications.planner.assignee.label', { defaultValue: 'Assignee' })}={row.assignee_id ? (labels.get(String(row.assignee_id)) || row.assignee_id) : '—'}
                    </div>
                    {row.description && <div className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{row.description}</div>}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {row.status !== 'in_progress' && (
                      <button type="button" onClick={() => void setEventStatus(row.id, 'in_progress')} disabled={busy} className="btn-secondary btn-xs disabled:opacity-50">{t('app.communications.planner.actions.start', { defaultValue: 'Start' })}</button>
                    )}
                    {row.status !== 'done' && (
                      <button type="button" onClick={() => void setEventStatus(row.id, 'done')} disabled={busy} className="btn-secondary btn-xs disabled:opacity-50">{t('app.communications.planner.status.done', { defaultValue: 'Done' })}</button>
                    )}
                    {row.status !== 'cancelled' && (
                      <button type="button" onClick={() => void setEventStatus(row.id, 'cancelled')} disabled={busy} className="btn-danger btn-xs disabled:opacity-50">{t('common.actions.cancel', { defaultValue: 'Cancel' })}</button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
