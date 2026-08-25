import { useCallback, useEffect, useMemo, useState } from 'react'
import { approveDeleteRequest, listDeleteRequests, rejectDeleteRequest } from '../../api/deletionRequests'
import type { DeletionRequest } from '../../api/types'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { usePermissions } from '../../hooks/usePermissions'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError'

type FilterStatus = 'all' | 'pending' | 'approved' | 'rejected'

type DeletionRequestsPageProps = {
  embedded?: boolean
}

export default function DeletionRequestsPage({ embedded = false }: DeletionRequestsPageProps) {
  const { t } = useI18n()
  const { can } = usePermissions()
  const canViewQueue = can('admin.deletionQueue') || can('candidates.deleteQueue')

  const [requests, setRequests] = useState<DeletionRequest[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<FilterStatus>('pending')
  const [savingId, setSavingId] = useState<string | null>(null)

  const loadRequests = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = filter === 'all' ? undefined : { status: filter }
      const data = await listDeleteRequests(params)
      setRequests(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('[DeletionRequestsPage] load error', err)
      setError(t('app.admin.deletion_requests.errors.load'))
    } finally {
      setLoading(false)
    }
  }, [filter, t])

  useEffect(() => {
    if (!canViewQueue) return
    void loadRequests()
  }, [canViewQueue, loadRequests])

  const pendingRequests = useMemo(() => requests.filter((item) => item.status === 'pending'), [requests])

  const handleDecision = useCallback(
    async (request: DeletionRequest, approve: boolean) => {
      if (!approve) {
        const reason = window.prompt(t('app.admin.deletion_requests.prompts.reject_reason')) || undefined
        setSavingId(request.id)
        setError(null)
        try {
          await rejectDeleteRequest(request.id, { comment: reason })
          await loadRequests()
        } catch (err) {
          console.error('[DeletionRequestsPage] reject error', err)
          setError(t('app.admin.deletion_requests.errors.reject'))
        } finally {
          setSavingId(null)
        }
        return
      }

      setSavingId(request.id)
      setError(null)
      try {
        await approveDeleteRequest(request.id)
        await loadRequests()
      } catch (err) {
        console.error('[DeletionRequestsPage] approve error', err)
        setError(t('app.admin.deletion_requests.errors.approve'))
      } finally {
        setSavingId(null)
      }
    },
    [loadRequests, t],
  )

  if (!canViewQueue) {
    return (
      <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        {t('app.admin.deletion_requests.messages.no_access')}
      </div>
    )
  }

  const deletionQueueErrorBanner: FriendlyErrorInfo | null = error
    ? {
        title: error,
        hint: t('app.common.retry_hint'),
      }
    : null

  const filterControls = (
    <div className="flex items-center gap-2">
      <select
        className="input"
        value={filter}
        onChange={(event) => setFilter(event.target.value as FilterStatus)}
      >
        <option value="pending">{t('app.admin.deletion_requests.filters.pending')}</option>
        <option value="approved">{t('app.admin.deletion_requests.filters.approved')}</option>
        <option value="rejected">{t('app.admin.deletion_requests.filters.rejected')}</option>
        <option value="all">{t('app.admin.deletion_requests.filters.all')}</option>
      </select>
      <button className="btn-secondary" onClick={() => void loadRequests()} disabled={loading}>
        {loading ? t('common.loading') : t('common.actions.refresh')}
      </button>
    </div>
  )

  const body = (
    <>
      {embedded ? (
        <div className="flex flex-wrap items-center justify-end gap-4">{filterControls}</div>
      ) : null}

      {deletionQueueErrorBanner && (
        <ErrorRecoveryBanner
          info={deletionQueueErrorBanner}
          onRetry={() => void loadRequests()}
          retryLabel={t('common.actions.refresh')}
          {...friendlyErrorBannerSecondary(
            deletionQueueErrorBanner,
            CRM_APP_PATHS.settingsAudit,
            t('admin.settings.audit.tabs.deletion'),
          )}
          compact
        />
      )}

      {loading ? (
        <div className="text-sm text-slate-500">{t('common.loading')}</div>
      ) : requests.length === 0 ? (
        <div className="text-sm text-slate-500">{t('app.admin.deletion_requests.messages.empty')}</div>
      ) : (
        <ul className="space-y-3">
          {requests.map((request) => {
            const isPending = request.status === 'pending'
            const saving = savingId === request.id
            return (
              <li key={request.id} className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold text-slate-900">
                      {t('app.admin.deletion_requests.labels.candidate')}: {request.candidate?.first_name}{' '}
                      {request.candidate?.last_name}
                    </div>
                    <div className="text-xs text-slate-500">
                      {t('common.labels.id')}: {request.candidate_id}
                    </div>
                  </div>
                  <div className="text-xs text-slate-500">
                    {t('common.labels.status')}:{' '}
                    <span className="font-medium text-slate-900">
                      {t(`app.admin.deletion_requests.status.${request.status}`, { defaultValue: request.status })}
                    </span>
                  </div>
                </div>

                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  <div>
                    <div className="text-xs uppercase text-slate-400">
                      {t('app.admin.deletion_requests.labels.recruiter')}
                    </div>
                    <div>{request.requested_by_user?.email || request.requested_by}</div>
                  </div>
                  <div>
                    <div className="text-xs uppercase text-slate-400">
                      {t('app.admin.deletion_requests.labels.supervisor')}
                    </div>
                    <div>{request.supervisor_user?.email || request.supervisor_id}</div>
                  </div>
                </div>

                {request.reason && (
                  <div className="mt-2 text-xs text-slate-500">
                    {t('app.admin.deletion_requests.labels.reason')}: {request.reason}
                  </div>
                )}

                {request.status !== 'pending' && request.resolved_by && (
                  <div className="mt-2 text-xs text-slate-500">
                    {t('app.admin.deletion_requests.labels.resolution')}:{' '}
                    {t(`app.admin.deletion_requests.status.${request.status}`, { defaultValue: request.status })} ·{' '}
                    {request.resolved_at ? new Date(request.resolved_at).toLocaleString() : ''}
                  </div>
                )}

                {isPending && (
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={saving}
                      onClick={() => void handleDecision(request, true)}
                    >
                      {saving ? t('common.saving') : t('app.admin.deletion_requests.actions.approve')}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={saving}
                      onClick={() => void handleDecision(request, false)}
                    >
                      {t('app.admin.deletion_requests.actions.reject')}
                    </button>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {filter !== 'pending' && pendingRequests.length > 0 && (
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-700">
          {t('app.admin.deletion_requests.messages.pending_hint', { values: { count: pendingRequests.length } })}
        </div>
      )}
    </>
  )

  if (embedded) {
    return <div className="space-y-4">{body}</div>
  }

  return (
    <SettingsSubpageHeader
      backLabel={t('admin.settings.subpage.back_all')}
      title={t('app.admin.deletion_requests.title')}
      subtitle={t('app.admin.deletion_requests.subtitle')}
      actions={filterControls}
    >
      {body}
    </SettingsSubpageHeader>
  )
}
