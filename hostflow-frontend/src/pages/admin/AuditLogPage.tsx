import { useCallback, useEffect, useState } from 'react'
import { listAudit } from '../../api/audit'
import type { AuditEntry } from '../../api/audit'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import DeletionRequestsPage from './DeletionRequestsPage'

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
      setError(t('admin.settings.audit.errors.load', { defaultValue: 'Не удалось загрузить аудит' }))
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

  if (tab === 'deletion') {
    return (
      <div className="space-y-4">
        <div className="flex gap-2">
          <button
            type="button"
            className={tab === 'audit' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => setTab('audit')}
          >
            {t('admin.settings.audit.tabs.audit', { defaultValue: 'Аудит-лог' })}
          </button>
          <button
            type="button"
            className={tab === 'deletion' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => setTab('deletion')}
          >
            {t('admin.settings.audit.tabs.deletion', { defaultValue: 'Очередь удаления' })}
          </button>
        </div>
        <DeletionRequestsPage />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex gap-2">
          <button
            type="button"
            className={tab === 'audit' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => setTab('audit')}
          >
            {t('admin.settings.audit.tabs.audit', { defaultValue: 'Аудит-лог' })}
          </button>
          <button
            type="button"
            className={tab === 'deletion' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
            onClick={() => setTab('deletion')}
          >
            {t('admin.settings.audit.tabs.deletion', { defaultValue: 'Очередь удаления' })}
          </button>
        </div>
        <button
          type="button"
          className="btn-secondary btn-sm"
          onClick={handleRefresh}
          disabled={loading}
        >
          {loading ? t('admin.settings.audit.refreshing', { defaultValue: 'Загрузка…' }) : t('admin.settings.audit.refresh', { defaultValue: 'Обновить' })}
        </button>
      </div>

      <div className="card p-4 space-y-4">
        <div className="flex flex-wrap gap-3">
          <label className="flex flex-col text-sm gap-1">
            {t('admin.settings.audit.filters.user_id', { defaultValue: 'Пользователь (ID)' })}
            <input
              type="text"
              className="input w-40"
              placeholder="UUID"
              value={userIdFilter}
              onChange={(e) => setUserIdFilter(e.target.value)}
            />
          </label>
          <label className="flex flex-col text-sm gap-1">
            {t('admin.settings.audit.filters.action', { defaultValue: 'Действие' })}
            <input
              type="text"
              className="input w-32"
              placeholder="action"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
            />
          </label>
          <label className="flex flex-col text-sm gap-1">
            {t('admin.settings.audit.filters.from', { defaultValue: 'От' })}
            <input type="date" className="input w-36" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label className="flex flex-col text-sm gap-1">
            {t('admin.settings.audit.filters.to', { defaultValue: 'До' })}
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
              {t('admin.settings.audit.apply', { defaultValue: 'Применить' })}
            </button>
          </div>
        </div>

        {error && (
          <ErrorRecoveryBanner
            info={{
              title: error,
              hint: t('app.common.retry_hint', { defaultValue: 'Повторите действие или обновите страницу.' }),
            }}
            onRetry={handleRefresh}
            retryLabel={t('common.actions.refresh', { defaultValue: 'Обновить' })}
            secondaryTo="/app/settings/audit"
            secondaryLabel={t('admin.settings.audit.tabs.audit', { defaultValue: 'Аудит-лог' })}
            compact
          />
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-slate-500 border-b border-slate-200">
                <th className="py-2 pr-4">{t('admin.settings.audit.table.when', { defaultValue: 'Когда' })}</th>
                <th className="py-2 pr-4">{t('admin.settings.audit.table.actor', { defaultValue: 'Кто' })}</th>
                <th className="py-2 pr-4">{t('admin.settings.audit.table.action', { defaultValue: 'Действие' })}</th>
                <th className="py-2 pr-4">{t('admin.settings.audit.table.subject', { defaultValue: 'Объект' })}</th>
                <th className="py-2">{t('admin.settings.audit.table.details', { defaultValue: 'Детали' })}</th>
              </tr>
            </thead>
            <tbody>
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    {t('admin.settings.audit.loading', { defaultValue: 'Загрузка…' })}
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    {t('admin.settings.audit.empty', { defaultValue: 'Нет записей аудита' })}
                  </td>
                </tr>
              ) : (
                items.map((entry) => (
                  <tr key={entry.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-2 pr-4 whitespace-nowrap text-slate-600">
                      {formatDateTime(entry.created_at, locale)}
                    </td>
                    <td className="py-2 pr-4">{entry.actor_label || '—'}</td>
                    <td className="py-2 pr-4 font-medium">{entry.action}</td>
                    <td className="py-2 pr-4">{entry.user_label || entry.user_id || '—'}</td>
                    <td className="py-2">
                      {entry.payload && Object.keys(entry.payload).length > 0 ? (
                        <details className="text-xs">
                          <summary className="cursor-pointer text-slate-500 hover:text-slate-700">
                            {t('admin.settings.audit.details', { defaultValue: 'Подробнее' })}
                          </summary>
                          <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2 text-slate-600 max-w-md">
                            {JSON.stringify(entry.payload, null, 2)}
                          </pre>
                        </details>
                      ) : (
                        '—'
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
                defaultValue: 'Показано {from}–{to} из {total}',
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
                {t('common.actions.prev', { defaultValue: 'Назад' })}
              </button>
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={offset + limit >= total || loading}
                onClick={() => setOffset((o) => o + limit)}
              >
                {t('common.actions.next', { defaultValue: 'Далее' })}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
