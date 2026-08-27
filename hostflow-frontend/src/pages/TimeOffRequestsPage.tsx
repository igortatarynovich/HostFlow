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
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader, Toolbar } from '../components/layout'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../utils/friendlyError'

export default function TimeOffRequestsPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const { me } = useAuth()
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [items, setItems] = useState<CommunicationTimeOffRequest[]>([])
  const [statusFilter, setStatusFilter] = useState('')
  const [decisionNotes, setDecisionNotes] = useState<Record<string, string>>({})

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listCommunicationTimeOffRequests({
        limit: 200,
        status_filter: statusFilter ? [statusFilter] : undefined,
      })
      setItems(Array.isArray(res.items) ? res.items : [])
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.timeoff.errors.load', { defaultValue: 'Failed to load time-off requests' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('app.communications.timeoff.errors.load', { defaultValue: 'Failed to load time-off requests' }),
            t,
          ),
        )
      }
    } finally {
      setLoading(false)
    }
  }, [planLimitModal, statusFilter, t])

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
      setError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.timeoff.errors.process', { defaultValue: 'Failed to process request' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('app.communications.timeoff.errors.process', { defaultValue: 'Failed to process request' }),
            t,
          ),
        )
      }
    } finally {
      setBusyId(null)
    }
  }, [decisionNotes, loadAll, planLimitModal, t])

  const handleCancel = useCallback(async (id: string) => {
    setBusyId(id)
    try {
      await cancelCommunicationTimeOffRequest(id, { reason: 'Cancelled by manager/admin' })
      await loadAll()
      setError(null)
    } catch (err: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications.timeoff.errors.cancel', { defaultValue: 'Failed to cancel request' }),
        )
      ) {
        setError(
          getFriendlyErrorInfo(
            err,
            t('app.communications.timeoff.errors.cancel', { defaultValue: 'Failed to cancel request' }),
            t,
          ),
        )
      }
    } finally {
      setBusyId(null)
    }
  }, [loadAll, planLimitModal, t])

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.communications.ia.timeoff_title', { defaultValue: 'Time-off Requests' })}
          subtitle={t('app.communications.ia.timeoff_subtitle', {
            defaultValue: 'Employee requests (vacation / day off / sick leave) and manager approval workflow.',
          })}
          kind="browse"
          secondaryActions={
            <button type="button" className="btn-secondary btn-sm" onClick={() => void loadAll()} disabled={loading}>
              {t('common.actions.refresh')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pb-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{t('app.communications.timeoff.stats.pending', { defaultValue: 'Pending: {count}', values: { count: summary.pending } })}</div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{t('app.communications.timeoff.stats.approved', { defaultValue: 'Approved: {count}', values: { count: summary.approved } })}</div>
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{t('app.communications.timeoff.stats.rejected', { defaultValue: 'Rejected: {count}', values: { count: summary.rejected } })}</div>
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">
          {t('app.communications.timeoff.stats.reviewer', { defaultValue: 'Reviewer: {name}', values: { name: me?.full_name || me?.email || '—' } })}
        </div>
      </div>

      <Toolbar>
        <div className="flex flex-wrap items-center gap-2">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input">
            <option value="">{t('app.communications.timeoff.filters.all_statuses', { defaultValue: 'All statuses' })}</option>
            <option value="pending">{t('app.communications.timeoff.status.pending', { defaultValue: 'Pending' })}</option>
            <option value="approved">{t('app.communications.timeoff.status.approved', { defaultValue: 'Approved' })}</option>
            <option value="rejected">{t('app.communications.timeoff.status.rejected', { defaultValue: 'Rejected' })}</option>
            <option value="cancelled">{t('app.communications.timeoff.status.cancelled', { defaultValue: 'Cancelled' })}</option>
          </select>
        </div>
      </Toolbar>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        {error && (
          <div className="mb-3">
            <ErrorRecoveryBanner
              info={error}
              onRetry={() => void loadAll()}
              retryLabel={t('common.actions.refresh')}
              {...friendlyErrorBannerSecondary(
                error,
                CRM_APP_PATHS.myAvailability,
                t('app.nav.items.my_availability', { defaultValue: 'My availability' }),
              )}
              compact
            />
          </div>
        )}
        {loading && <div className="text-sm text-slate-500">{t('common.loading')}</div>}
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
                      placeholder={t('app.communications.timeoff.decision_note_optional', { defaultValue: 'Decision note (optional)' })}
                    />
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={() => void handleDecision(row.id, 'approved')} disabled={busyId === row.id} className="btn-primary btn-sm disabled:opacity-50">
                        {busyId === row.id ? t('common.loading') : t('app.communications.timeoff.actions.approve', { defaultValue: 'Approve' })}
                      </button>
                      <button type="button" onClick={() => void handleDecision(row.id, 'rejected')} disabled={busyId === row.id} className="btn-danger btn-sm disabled:opacity-50">
                        {busyId === row.id ? t('common.loading') : t('app.communications.timeoff.actions.reject', { defaultValue: 'Reject' })}
                      </button>
                      <button type="button" onClick={() => void handleCancel(row.id)} disabled={busyId === row.id} className="btn-secondary btn-sm disabled:opacity-50">
                        {t('app.communications.timeoff.actions.cancel', { defaultValue: 'Cancel' })}
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
    </PageShell>
  )
}
