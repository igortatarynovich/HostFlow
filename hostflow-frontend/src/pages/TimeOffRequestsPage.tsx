import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  cancelCommunicationTimeOffRequest,
  decideCommunicationTimeOffRequest,
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

export default function TimeOffRequestsPage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [errorText, setErrorText] = useState<string | null>(null)
  const [items, setItems] = useState<CommunicationTimeOffRequest[]>([])
  const [statusFilter, setStatusFilter] = useState('')
  const [decisionNotes, setDecisionNotes] = useState<Record<string, string>>({})

  const loadAll = useCallback(async () => {
    setLoading(true)
    setErrorText(null)
    try {
      const res = await listCommunicationTimeOffRequests({
        limit: 200,
        status_filter: statusFilter ? [statusFilter] : undefined,
      })
      setItems(Array.isArray(res.items) ? res.items : [])
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to load time-off requests'))
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  const summary = useMemo(() => ({
    pending: items.filter((x) => x.status === 'pending').length,
    approved: items.filter((x) => x.status === 'approved').length,
    rejected: items.filter((x) => x.status === 'rejected').length,
  }), [items])

  const handleDecision = useCallback(async (id: string, decision: 'approved' | 'rejected') => {
    setBusyId(id)
    try {
      await decideCommunicationTimeOffRequest(id, {
        decision,
        decision_note: decisionNotes[id] || undefined,
      })
      await loadAll()
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to process request'))
    } finally {
      setBusyId(null)
    }
  }, [decisionNotes, loadAll])

  const handleCancel = useCallback(async (id: string) => {
    setBusyId(id)
    try {
      await cancelCommunicationTimeOffRequest(id, { reason: 'Cancelled by manager/admin' })
      await loadAll()
      setErrorText(null)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, 'Failed to cancel request'))
    } finally {
      setBusyId(null)
    }
  }, [loadAll])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{t('app.communications.ia.timeoff_title', { defaultValue: 'Time-off Requests' })}</h1>
        <p className="text-sm text-slate-500">
          {t('app.communications.ia.timeoff_subtitle', { defaultValue: 'Employee requests (vacation / day off / sick leave) and manager approval workflow.' })}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">Pending: <strong>{summary.pending}</strong></div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">Approved: <strong>{summary.approved}</strong></div>
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">Rejected: <strong>{summary.rejected}</strong></div>
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">Reviewer: <strong>{me?.full_name || me?.email || '—'}</strong></div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input">
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <button type="button" onClick={() => void loadAll()} className="btn-secondary">
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
        {errorText && (
          <div className="mb-3">
            <ErrorRecoveryBanner
              info={{ title: errorText, hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }) }}
              onRetry={() => void loadAll()}
              retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
              secondaryTo="/app/my-availability"
              secondaryLabel={t('app.nav.items.my_availability', { defaultValue: 'My availability' })}
              compact
            />
          </div>
        )}
        {loading && <div className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>}
        {!loading && items.length === 0 && <div className="text-sm text-slate-500">{t('app.communications.states.empty', { defaultValue: 'No activity yet' })}</div>}
        <div className="space-y-3">
          {items.map((row) => (
            <div key={row.id} className="rounded border border-slate-200 px-3 py-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-900">
                    {row.request_type} · {row.start_date} → {row.end_date}
                    {row.partial_day ? ` · ${row.partial_day}` : ''}
                    {row.payload?.time_window?.from && row.payload?.time_window?.to ? ` · ${row.payload.time_window.from}-${row.payload.time_window.to}` : ''}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    requester={row.requester_label || row.requester_user_id} · status={row.status} · approver={row.approver_label || row.approver_user_id || '—'}
                  </div>
                  {row.reason && <div className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{row.reason}</div>}
                  {row.decision_note && <div className="mt-2 text-xs text-slate-500">Decision note: {row.decision_note}</div>}
                </div>
                {row.status === 'pending' && (
                  <div className="w-full max-w-sm space-y-2">
                    <textarea
                      rows={2}
                      value={decisionNotes[row.id] || ''}
                      onChange={(e) => setDecisionNotes((p) => ({ ...p, [row.id]: e.target.value }))}
                      className="textarea"
                      placeholder="Decision note (optional)"
                    />
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={() => void handleDecision(row.id, 'approved')} disabled={busyId === row.id} className="btn-primary btn-sm disabled:opacity-50">
                        {busyId === row.id ? t('common.loading', { defaultValue: 'Loading...' }) : 'Approve'}
                      </button>
                      <button type="button" onClick={() => void handleDecision(row.id, 'rejected')} disabled={busyId === row.id} className="btn-danger btn-sm disabled:opacity-50">
                        {busyId === row.id ? t('common.loading', { defaultValue: 'Loading...' }) : 'Reject'}
                      </button>
                      <button type="button" onClick={() => void handleCancel(row.id)} disabled={busyId === row.id} className="btn-secondary btn-sm disabled:opacity-50">
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
