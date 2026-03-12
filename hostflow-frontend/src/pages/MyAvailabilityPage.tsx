import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  cancelCommunicationTimeOffRequest,
  createCommunicationTimeOffRequest,
  listCommunicationTimeOffRequests,
  type CommunicationTimeOffRequest,
} from '../api/communications'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useAuth } from '../store/useAuth'
import { useI18n } from '../i18n'

function errorTextFrom(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const msg = detail.map((x) => (typeof x?.msg === 'string' ? x.msg : null)).filter(Boolean).join('; ')
    if (msg) return msg
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.msg === 'string' && detail.msg.trim()) return detail.msg
    try { return JSON.stringify(detail) } catch {}
  }
  if (typeof err?.message === 'string' && err.message.trim()) return err.message
  return fallback
}

export default function MyAvailabilityPage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const [loading, setLoading] = useState(true)
  const [errorText, setErrorText] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [items, setItems] = useState<CommunicationTimeOffRequest[]>([])
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
    setErrorText(null)
    try {
      const res = await listCommunicationTimeOffRequests({ mine_only: true, limit: 100 })
      setItems(Array.isArray(res.items) ? res.items : [])
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to load requests'))
    } finally {
      setLoading(false)
    }
  }, [])

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
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to create request'))
    } finally {
      setBusy(false)
    }
  }, [form, loadMine])

  const handleCancel = useCallback(async (id: string) => {
    setBusy(true)
    try {
      await cancelCommunicationTimeOffRequest(id)
      await loadMine()
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to cancel request'))
    } finally {
      setBusy(false)
    }
  }, [loadMine])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.communications.ia.my_availability_title', { defaultValue: 'My Availability' })}</h1>
        <p className="text-sm text-slate-500">
          {t('app.communications.ia.my_availability_subtitle', { defaultValue: 'Personal work schedule, availability status, breaks, and leave requests. Employee-facing self-service.' })}
        </p>
      </div>
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
        <div>{t('app.profile.labels.user', { defaultValue: 'User' })}: <strong>{me?.full_name || me?.email || me?.id || '—'}</strong></div>
        <div className="mt-2 text-xs text-slate-500">Pending requests: {pendingCount}</div>
        {errorText && (
          <div className="mt-2">
            <ErrorRecoveryBanner
              info={{ title: errorText, hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }) }}
              onRetry={() => void loadMine()}
              retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
              secondaryTo="/app/timeoff"
              secondaryLabel={t('app.communications.ia.timeoff_title', { defaultValue: 'Time-off Requests' })}
              compact
            />
          </div>
        )}
        <form className="mt-3 grid gap-2" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <select value={form.requestType} onChange={(e) => setForm((p) => ({ ...p, requestType: e.target.value }))} className="input">
              <option value="vacation">Vacation</option>
              <option value="day_off">Day off</option>
              <option value="sick_leave">Sick leave</option>
              <option value="other">Other</option>
            </select>
            <select value={form.partialDay} onChange={(e) => setForm((p) => ({ ...p, partialDay: e.target.value }))} className="input">
              <option value="">Full day(s)</option>
              <option value="first_half">First half-day</option>
              <option value="second_half">Second half-day</option>
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
          <textarea rows={3} value={form.reason} onChange={(e) => setForm((p) => ({ ...p, reason: e.target.value }))} className="textarea" placeholder="Reason / comment" />
          <button type="submit" disabled={busy || !form.startDate || !form.endDate} className="btn-primary disabled:opacity-50">
            {busy ? t('common.loading', { defaultValue: 'Loading...' }) : t('common.actions.create', { defaultValue: 'Create' })}
          </button>
        </form>
        <div className="mt-4">
          <div className="mb-2 text-sm font-semibold text-slate-900">{t('app.communications.ia.my_requests', { defaultValue: 'My requests' })}</div>
          <div className="space-y-2">
            {loading && <div className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>}
            {!loading && items.length === 0 && <div className="text-sm text-slate-500">{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</div>}
            {items.map((row) => (
              <div key={row.id} className="rounded border border-slate-200 px-3 py-2">
                <div className="text-sm font-medium text-slate-900">
                  {row.request_type} · {row.start_date} → {row.end_date}
                  {row.partial_day ? ` · ${row.partial_day}` : ''}
                  {row.payload?.time_window?.from && row.payload?.time_window?.to ? ` · ${row.payload.time_window.from}-${row.payload.time_window.to}` : ''}
                </div>
                <div className="mt-1 text-xs text-slate-500">status={row.status} · approver={row.approver_label || row.approver_user_id || '—'}</div>
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
          <Link to="/app/time-off" className="btn-secondary">
            {t('app.communications.ia.open_time_off', { defaultValue: 'Open time-off requests' })}
          </Link>
          <Link to="/app/team-availability" className="btn-secondary">
            {t('app.nav.items.team_availability', { defaultValue: 'Team availability' })}
          </Link>
        </div>
      </div>
    </div>
  )
}
