import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  cancelCommunicationTimeOffRequest,
  createCommunicationTimeOffRequest,
  getMyWorkingHours,
  listCommunicationTimeOffRequests,
  upsertMyWorkingHours,
  type CommunicationTimeOffRequest,
  type WorkingHoursDay,
  type WorkingHoursSchedule,
} from '../api/communications'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useAuth } from '../store/useAuth'
import { useI18n } from '../i18n'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../utils/friendlyError'

export default function MyAvailabilityPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const { me } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [busy, setBusy] = useState(false)
  const [items, setItems] = useState<CommunicationTimeOffRequest[]>([])
  const [workingHours, setWorkingHours] = useState<WorkingHoursSchedule | null>(null)
  const [workingBusy, setWorkingBusy] = useState(false)
  const [form, setForm] = useState({
    requestType: 'vacation',
    startDate: '',
    endDate: '',
    partialDay: '',
    partialFrom: '09:00',
    partialTo: '13:00',
    reason: '',
  })

  const loadMine = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [res, wh] = await Promise.all([
        listCommunicationTimeOffRequests({ mine_only: true, limit: 100 }),
        getMyWorkingHours().catch(() => null),
      ])
      setItems(Array.isArray(res.items) ? res.items : [])
      if (wh) setWorkingHours(wh)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.my_availability.errors.load_requests', { defaultValue: 'Failed to load requests' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('app.communications.my_availability.errors.load_requests', { defaultValue: 'Failed to load requests' }),
            t,
          ),
        )
      }
    } finally {
      setLoading(false)
    }
  }, [planLimitModal, t])
  const defaultDays = useMemo<WorkingHoursDay[]>(() => {
    const weekdays = [0, 1, 2, 3, 4]
    return weekdays.map((weekday) => ({
      weekday,
      enabled: true,
      windows: [{ from: '09:00', to: '17:00' }],
    }))
  }, [])

  const effectiveWorkingHours = workingHours ?? { tz: null, days: defaultDays }
  const browserTz = useMemo(() => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || null
    } catch {
      return null
    }
  }, [])

  const updateDay = useCallback((weekday: number, patch: Partial<WorkingHoursDay>) => {
    setWorkingHours((prev) => {
      const base = prev ?? { tz: null, days: defaultDays }
      const days = Array.isArray(base.days) ? base.days : []
      const nextDays = days.map((d) => (d.weekday === weekday ? { ...d, ...patch } : d))
      return { ...base, days: nextDays }
    })
  }, [defaultDays])

  const updateWindow = useCallback((weekday: number, idx: number, patch: Partial<WorkingHoursDay['windows'][number]>) => {
    setWorkingHours((prev) => {
      const base = prev ?? { tz: null, days: defaultDays }
      const days = Array.isArray(base.days) ? base.days : []
      const nextDays = days.map((d) => {
        if (d.weekday !== weekday) return d
        const windows = Array.isArray(d.windows) ? d.windows : []
        const nextWindows = windows.map((w, i) => (i === idx ? { ...w, ...patch } : w))
        return { ...d, windows: nextWindows }
      })
      return { ...base, days: nextDays }
    })
  }, [defaultDays])

  const addWindow = useCallback((weekday: number) => {
    setWorkingHours((prev) => {
      const base = prev ?? { tz: null, days: defaultDays }
      const days = Array.isArray(base.days) ? base.days : []
      const nextDays = days.map((d) => {
        if (d.weekday !== weekday) return d
        const windows = Array.isArray(d.windows) ? d.windows : []
        if (windows.length >= 3) return d
        return { ...d, windows: [...windows, { from: '13:00', to: '17:00' }] }
      })
      return { ...base, days: nextDays }
    })
  }, [defaultDays])

  const removeWindow = useCallback((weekday: number, idx: number) => {
    setWorkingHours((prev) => {
      const base = prev ?? { tz: null, days: defaultDays }
      const days = Array.isArray(base.days) ? base.days : []
      const nextDays = days.map((d) => {
        if (d.weekday !== weekday) return d
        const windows = Array.isArray(d.windows) ? d.windows : []
        const nextWindows = windows.filter((_, i) => i !== idx)
        return { ...d, windows: nextWindows }
      })
      return { ...base, days: nextDays }
    })
  }, [defaultDays])

  const handleSaveWorkingHours = useCallback(async () => {
    setWorkingBusy(true)
    try {
      const saved = await upsertMyWorkingHours(effectiveWorkingHours)
      setWorkingHours(saved)
      setError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.my_availability.errors.save_working_hours', { defaultValue: 'Failed to save working hours' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('app.communications.my_availability.errors.save_working_hours', { defaultValue: 'Failed to save working hours' }),
            t,
          ),
        )
      }
    } finally {
      setWorkingBusy(false)
    }
  }, [effectiveWorkingHours, planLimitModal, t])

  useEffect(() => {
    void loadMine()
  }, [loadMine])

  const pendingCount = useMemo(() => items.filter((x) => String(x.status || '').toLowerCase() === 'pending').length, [items])

  const handleSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (!form.startDate || !form.endDate) return
    setBusy(true)
    try {
      await createCommunicationTimeOffRequest({
        request_type: form.requestType,
        start_date: form.startDate,
        end_date: form.endDate,
        partial_day: form.partialDay || undefined,
        reason: form.reason || undefined,
        payload: form.partialDay
          ? {
              time_window:
                form.partialFrom && form.partialTo
                  ? { from: form.partialFrom, to: form.partialTo }
                  : undefined,
            }
          : undefined,
      })
      setForm((p) => ({ ...p, reason: '' }))
      await loadMine()
      setError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.my_availability.errors.create_request', { defaultValue: 'Failed to create request' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('app.communications.my_availability.errors.create_request', { defaultValue: 'Failed to create request' }),
            t,
          ),
        )
      }
    } finally {
      setBusy(false)
    }
  }, [form, loadMine, planLimitModal, t])

  const handleCancel = useCallback(async (id: string) => {
    setBusy(true)
    try {
      await cancelCommunicationTimeOffRequest(id)
      await loadMine()
      setError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.my_availability.errors.cancel_request', { defaultValue: 'Failed to cancel request' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('app.communications.my_availability.errors.cancel_request', { defaultValue: 'Failed to cancel request' }),
            t,
          ),
        )
      }
    } finally {
      setBusy(false)
    }
  }, [loadMine, planLimitModal, t])

  return (
    <PageShell>
      <WorkspaceTopNav active="calendar" />
      <PageShellHeader>
        <PageHeader
          title={t('app.communications.ia.my_availability_title', { defaultValue: 'My Availability' })}
          subtitle={t('app.communications.ia.my_availability_subtitle', {
            defaultValue: 'Personal work schedule, availability status, breaks, and leave requests. Employee-facing self-service.',
          })}
          kind="browse"
          secondaryActions={
            <button type="button" className="btn-secondary btn-sm" onClick={() => void loadMine()} disabled={loading}>
              {t('common.actions.refresh')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pb-4">
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
        <div>{t('app.profile.labels.user', { defaultValue: 'User' })}: <strong>{me?.full_name || me?.email || me?.id || '—'}</strong></div>
        <div className="mt-2 text-xs text-slate-500">
          {t('app.communications.my_availability.pending_requests', { values: { count: pendingCount } })}
        </div>
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="text-sm font-semibold text-slate-900">
            {t('app.communications.ia.working_hours_title', { defaultValue: 'Working hours' })}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {t('app.communications.ia.working_hours_subtitle', {
              defaultValue: 'Set your weekly working schedule. Planner and calendar will use it as baseline availability.',
            })}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <label className="text-xs font-medium text-slate-700">
              {t('app.profile.labels.timezone', { defaultValue: 'Timezone' })}
            </label>
            <input
              className="input h-8 w-[240px] px-2 py-1 text-xs"
              placeholder={browserTz || 'Europe/Warsaw'}
              value={effectiveWorkingHours.tz || ''}
              onChange={(e) => setWorkingHours((prev) => ({ ...(prev ?? { tz: null, days: defaultDays }), tz: e.target.value || null }))}
            />
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => setWorkingHours((prev) => ({ ...(prev ?? { tz: null, days: defaultDays }), tz: browserTz }))}
              disabled={!browserTz}
            >
              {t('app.profile.actions.use_browser_timezone', { defaultValue: 'Use browser timezone' })}
            </button>
          </div>
          <div className="mt-3 grid gap-2">
            {effectiveWorkingHours.days
              .slice()
              .sort((a, b) => a.weekday - b.weekday)
              .map((d) => (
                <div key={d.weekday} className="rounded border border-slate-200 bg-white px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2">
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={Boolean(d.enabled)}
                      onChange={(e) => updateDay(d.weekday, { enabled: e.target.checked })}
                    />
                    {t(`app.communications.my_availability.weekday.${d.weekday}`)}
                  </label>
                  <button type="button" className="btn-secondary btn-sm" disabled={!d.enabled} onClick={() => void addWindow(d.weekday)}>
                    {t('common.actions.add', { defaultValue: 'Add' })}
                  </button>
                  </div>
                  <div className="mt-2 space-y-2">
                    {(Array.isArray(d.windows) ? d.windows : [{ from: '09:00', to: '17:00' }]).map((w, idx) => (
                      <div key={`${d.weekday}:${idx}`} className="flex flex-wrap items-center gap-2">
                        <input
                          type="time"
                          className="input h-8 px-2 py-1 text-xs"
                          value={w.from || '09:00'}
                          disabled={!d.enabled}
                          onChange={(e) => void updateWindow(d.weekday, idx, { from: e.target.value })}
                        />
                        <span className="text-xs text-slate-500">→</span>
                        <input
                          type="time"
                          className="input h-8 px-2 py-1 text-xs"
                          value={w.to || '17:00'}
                          disabled={!d.enabled}
                          onChange={(e) => void updateWindow(d.weekday, idx, { to: e.target.value })}
                        />
                        {idx > 0 && (
                          <button type="button" className="btn-danger btn-sm" disabled={!d.enabled} onClick={() => void removeWindow(d.weekday, idx)}>
                            {t('common.actions.remove', { defaultValue: 'Remove' })}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
          </div>
          <div className="mt-3">
            <button type="button" onClick={() => void handleSaveWorkingHours()} disabled={workingBusy} className="btn-secondary btn-sm disabled:opacity-50">
              {workingBusy ? t('common.saving', { defaultValue: 'Saving…' }) : t('common.save', { defaultValue: 'Save' })}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-2">
            <ErrorRecoveryBanner
              info={error}
              onRetry={() => void loadMine()}
              retryLabel={t('common.actions.refresh')}
              {...friendlyErrorBannerSecondary(
                error,
                CRM_APP_PATHS.timeOff,
                t('app.communications.ia.timeoff_title', { defaultValue: 'Time-off Requests' }),
              )}
              compact
            />
          </div>
        )}
        <form className="mt-3 grid gap-2" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <select value={form.requestType} onChange={(e) => setForm((p) => ({ ...p, requestType: e.target.value }))} className="input">
              <option value="vacation">{t('app.communications.my_availability.request_type.vacation', { defaultValue: 'Vacation' })}</option>
              <option value="day_off">{t('app.communications.my_availability.request_type.day_off', { defaultValue: 'Day off' })}</option>
              <option value="sick_leave">{t('app.communications.my_availability.request_type.sick_leave', { defaultValue: 'Sick leave' })}</option>
              <option value="other">{t('app.communications.my_availability.request_type.other', { defaultValue: 'Other' })}</option>
            </select>
            <select value={form.partialDay} onChange={(e) => setForm((p) => ({ ...p, partialDay: e.target.value }))} className="input">
              <option value="">{t('app.communications.my_availability.partial_day.full', { defaultValue: 'Full day(s)' })}</option>
              <option value="first_half">{t('app.communications.my_availability.partial_day.first_half', { defaultValue: 'First half-day' })}</option>
              <option value="second_half">{t('app.communications.my_availability.partial_day.second_half', { defaultValue: 'Second half-day' })}</option>
            </select>
          </div>
          {form.partialDay && (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <input type="time" value={form.partialFrom} onChange={(e) => setForm((p) => ({ ...p, partialFrom: e.target.value }))} className="input" />
              <input type="time" value={form.partialTo} onChange={(e) => setForm((p) => ({ ...p, partialTo: e.target.value }))} className="input" />
            </div>
          )}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <input type="date" value={form.startDate} onChange={(e) => setForm((p) => ({ ...p, startDate: e.target.value }))} className="input" />
            <input type="date" value={form.endDate} onChange={(e) => setForm((p) => ({ ...p, endDate: e.target.value }))} className="input" />
          </div>
          <textarea
            rows={3}
            value={form.reason}
            onChange={(e) => setForm((p) => ({ ...p, reason: e.target.value }))}
            className="textarea"
            placeholder={t('app.communications.my_availability.reason_placeholder', { defaultValue: 'Reason / comment' })}
          />
          <button type="submit" disabled={busy || !form.startDate || !form.endDate} className="btn-primary disabled:opacity-50">
            {busy ? t('common.loading') : t('common.actions.create', { defaultValue: 'Create' })}
          </button>
        </form>
        <div className="mt-4">
          <div className="mb-2 text-sm font-semibold text-slate-900">{t('app.communications.ia.my_requests', { defaultValue: 'My requests' })}</div>
          <div className="space-y-2">
            {loading && <div className="text-sm text-slate-500">{t('common.loading')}</div>}
            {!loading && items.length === 0 && <div className="text-sm text-slate-500">{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</div>}
            {items.map((row) => (
              <div key={row.id} className="rounded border border-slate-200 px-3 py-2">
                <div className="text-sm font-medium text-slate-900">
                  {row.request_type} · {row.start_date} → {row.end_date}
                  {row.partial_day ? ` · ${row.partial_day}` : ''}
                  {row.payload?.time_window?.from && row.payload?.time_window?.to ? ` · ${row.payload.time_window.from}-${row.payload.time_window.to}` : ''}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {t('app.communications.my_availability.row_meta', {
                    values: {
                      status: row.status,
                      approver: row.approver_label || row.approver_user_id || t('common.labels.not_available'),
                    },
                  })}
                </div>
                {row.reason && <div className="mt-1 text-sm text-slate-700 whitespace-pre-wrap">{row.reason}</div>}
                {row.status === 'pending' && (
                  <div className="mt-2">
                    <button type="button" onClick={() => void handleCancel(row.id)} disabled={busy} className="btn-secondary btn-xs disabled:opacity-50">
                      {t('common.actions.cancel', { defaultValue: 'Cancel' })}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link to={CRM_APP_PATHS.timeOff} className="btn-secondary">
            {t('app.communications.ia.open_time_off', { defaultValue: 'Open time-off requests' })}
          </Link>
          <Link to={CRM_APP_PATHS.teamAvailability} className="btn-secondary">
            {t('app.nav.items.team_availability', { defaultValue: 'Team availability' })}
          </Link>
        </div>
      </div>
      </div>
    </PageShell>
  )
}
