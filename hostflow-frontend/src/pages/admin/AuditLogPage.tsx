import { useCallback, useEffect, useMemo, useState } from 'react'
import { listAudit } from '../../api/audit'
import type { AuditEntry } from '../../api/audit'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError'
import DeletionRequestsPage from './DeletionRequestsPage'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'

type Tab = 'audit' | 'deletion'

export default function AuditLogPage() {
  const { t, locale } = useI18n()
  const [tab, setTab] = useState<Tab>('audit')
  const [items, setItems] = useState<AuditEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [userIdFilter, setUserIdFilter] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 50

  const emptyLabel = t('common.labels.not_available')

  const load = useCallback(async (overrides?: { offset?: number }) => {
    const off = overrides?.offset ?? offset
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string | number> = { limit, offset: off }
      if (userIdFilter) params.user_id = userIdFilter
      if (actionFilter) params.action = actionFilter
      if (dateFrom) params.from = dateFrom
      if (dateTo) params.to = dateTo
      const res = await listAudit(params)
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      console.error('[AuditLogPage] load error', err)
      setError(t('admin.settings.audit.errors.load'))
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [offset, userIdFilter, actionFilter, dateFrom, dateTo, t])

  useEffect(() => {
    if (tab === 'audit') void load()
  }, [tab, load])

  const handleRefresh = () => void load()

  const auditLogErrorBanner = useMemo<FriendlyErrorInfo | null>(
    () =>
      error
        ? {
            title: error,
            hint: t('app.common.retry_hint'),
          }
        : null,
    [error, t],
  )

  // Cast through a const to defeat TS narrowing inside the branched returns below;
  // both render trees expose tabs that switch between the two values.
  const currentTab: Tab = tab

  const auditTabs = (
    <div className="flex gap-2">
      <button
        type="button"
        className={currentTab === 'audit' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
        onClick={() => setTab('audit')}
      >
        {t('admin.settings.audit.tabs.audit')}
      </button>
      <button
        type="button"
        className={currentTab === 'deletion' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
        onClick={() => setTab('deletion')}
      >
        {t('admin.settings.audit.tabs.deletion')}
      </button>
    </div>
  )

  return (
    <SettingsSubpageHeader
      backLabel={t('admin.settings.subpage.back_all')}
      kicker={t('admin.settings.audit.header_kicker')}
      title={t('admin.settings.audit.page_title')}
      subtitle={t('admin.settings.audit.page_subtitle')}
      actions={
        currentTab === 'audit' ? (
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={handleRefresh}
            disabled={loading}
          >
            {loading ? t('admin.settings.audit.refreshing') : t('admin.settings.audit.refresh')}
          </button>
        ) : undefined
      }
    >
      {auditTabs}
      {currentTab === 'deletion' ? (
        <DeletionRequestsPage />
      ) : (
        <>
          <div className="card p-4 space-y-4">
        <div className="flex flex-wrap gap-3">
          <label className="flex flex-col text-sm gap-1">
            {t('admin.settings.audit.filters.user_id')}
            <input
              type="text"
              className="input w-40"
              placeholder={t('admin.settings.audit.filters.user_id_placeholder')}
              value={userIdFilter}
              onChange={(e) => setUserIdFilter(e.target.value)}
            />
          </label>
          <label className="flex flex-col text-sm gap-1">
            {t('admin.settings.audit.filters.action')}
            <input
              type="text"
              className="input w-32"
              placeholder={t('admin.settings.audit.filters.action_placeholder')}
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
            />
          </label>
          <label className="flex flex-col text-sm gap-1">
            {t('admin.settings.audit.filters.from')}
            <input type="date" className="input w-36" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label className="flex flex-col text-sm gap-1">
            {t('admin.settings.audit.filters.to')}
            <input type="date" className="input w-36" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </label>
          <div className="flex items-end">
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                setOffset(0)
                load({ offset: 0 })
              }}
              disabled={loading}
            >
              {t('admin.settings.audit.apply')}
            </button>
          </div>
        </div>

        {auditLogErrorBanner && (
          <ErrorRecoveryBanner
            info={auditLogErrorBanner}
            onRetry={handleRefresh}
            retryLabel={t('common.actions.refresh')}
            {...friendlyErrorBannerSecondary(
              auditLogErrorBanner,
              CRM_APP_PATHS.settingsAudit,
              t('admin.settings.audit.tabs.audit'),
            )}
            compact
          />
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-slate-500 border-b border-slate-200">
                <th className="py-2 pr-4">{t('admin.settings.audit.table.when')}</th>
                <th className="py-2 pr-4">{t('admin.settings.audit.table.actor')}</th>
                <th className="py-2 pr-4">{t('admin.settings.audit.table.action')}</th>
                <th className="py-2 pr-4">{t('admin.settings.audit.table.subject')}</th>
                <th className="py-2">{t('admin.settings.audit.table.details')}</th>
              </tr>
            </thead>
            <tbody>
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    {t('admin.settings.audit.loading')}
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    {t('admin.settings.audit.empty')}
                  </td>
                </tr>
              ) : (
                items.map((entry) => (
                  <tr key={entry.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-2 pr-4 whitespace-nowrap text-slate-600">
                      {formatDateTime(entry.created_at, locale)}
                    </td>
                    <td className="py-2 pr-4">{entry.actor_label || emptyLabel}</td>
                    <td className="py-2 pr-4 font-medium">{entry.action}</td>
                    <td className="py-2 pr-4">{entry.user_label || entry.user_id || emptyLabel}</td>
                    <td className="py-2">
                      {entry.payload && Object.keys(entry.payload).length > 0 ? (
                        <details className="text-xs">
                          <summary className="cursor-pointer text-slate-500 hover:text-slate-700">
                            {t('admin.settings.audit.details_toggle')}
                          </summary>
                          <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2 text-slate-600 max-w-md">
                            {JSON.stringify(entry.payload, null, 2)}
                          </pre>
                        </details>
                      ) : (
                        emptyLabel
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {total > limit && (
          <div className="flex items-center justify-between text-sm text-slate-600">
            <span>
              {t('admin.settings.audit.pagination', {
                values: {
                  from: offset + 1,
                  to: Math.min(offset + limit, total),
                  total,
                },
              })}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={offset === 0 || loading}
                onClick={() => setOffset((o) => Math.max(0, o - limit))}
              >
                {t('common.actions.prev')}
              </button>
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={offset + limit >= total || loading}
                onClick={() => setOffset((o) => o + limit)}
              >
                {t('common.actions.next')}
              </button>
            </div>
          </div>
        )}
          </div>
        </>
      )}
    </SettingsSubpageHeader>
  )
}
