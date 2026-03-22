import { useCallback, useEffect, useMemo, useState } from 'react'
import { listAutomationLog, type AutomationLogEntry } from '../api/automationLog'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useI18n } from '../i18n'
import { formatDateTime } from '../utils/dateFormat'

export default function AutomationLogPage() {
  const { t, locale } = useI18n()
  const [items, setItems] = useState<AutomationLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [targetType, setTargetType] = useState('candidate')
  const [targetId, setTargetId] = useState('')
  const [actionPrefix, setActionPrefix] = useState('automation.')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 100

  const load = useCallback(
    async (overrides?: { offset?: number }) => {
      const off = overrides?.offset ?? offset
      setLoading(true)
      setError(null)
      try {
        const res = await listAutomationLog({
          target_type: targetType || undefined,
          target_id: targetId || undefined,
          action_prefix: actionPrefix || undefined,
          from: dateFrom || undefined,
          to: dateTo || undefined,
          limit,
          offset: off,
        })
        setItems(res.items || [])
        setTotal(res.total || 0)
      } catch (err: any) {
        console.error('[AutomationLogPage] load error', err)
        setError(t('app.automation_log.errors.load', { defaultValue: 'Failed to load automation log' }))
        setItems([])
        setTotal(0)
      } finally {
        setLoading(false)
      }
    },
    [actionPrefix, dateFrom, dateTo, offset, t, targetId, targetType],
  )

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const shownTo = useMemo(() => Math.min(offset + limit, total), [limit, offset, total])

  return (
    <div className="space-y-4">
      <header className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              {t('app.automation_log.title', { defaultValue: 'Automation log' })}
            </h1>
            <p className="text-xs text-slate-500">
              {t('app.automation_log.subtitle', {
                defaultValue: 'Why did something happen? Shows automation-triggered actions (v1).',
              })}
            </p>
          </div>
          <button type="button" className="btn-secondary btn-sm" onClick={() => load()} disabled={loading}>
            {loading ? t('common.loading', { defaultValue: 'Loading…' }) : t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
      </header>

      <div className="card p-4 space-y-4">
        <div className="flex flex-wrap gap-3">
          <label className="flex flex-col text-sm gap-1">
            {t('app.automation_log.filters.target_type', { defaultValue: 'Target type' })}
            <input className="input w-40" value={targetType} onChange={(e) => setTargetType(e.target.value)} />
          </label>
          <label className="flex flex-col text-sm gap-1">
            {t('app.automation_log.filters.target_id', { defaultValue: 'Target id' })}
            <input
              className="input w-64"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              placeholder={t('app.automation_log.filters.target_id_placeholder', { defaultValue: 'UUID' })}
            />
          </label>
          <label className="flex flex-col text-sm gap-1">
            {t('app.automation_log.filters.action_prefix', { defaultValue: 'Action prefix' })}
            <input
              className="input w-40"
              value={actionPrefix}
              onChange={(e) => setActionPrefix(e.target.value)}
              placeholder={t('app.automation_log.filters.action_prefix_placeholder', { defaultValue: 'automation.' })}
            />
          </label>
          <label className="flex flex-col text-sm gap-1">
            {t('app.automation_log.filters.from', { defaultValue: 'From' })}
            <input type="date" className="input w-36" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label className="flex flex-col text-sm gap-1">
            {t('app.automation_log.filters.to', { defaultValue: 'To' })}
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
              {t('common.apply', { defaultValue: 'Apply' })}
            </button>
          </div>
        </div>

        {error && (
          <ErrorRecoveryBanner
            info={{
              title: error,
              hint: t('app.common.retry_hint', { defaultValue: 'Repeat the action or refresh the page.' }),
            }}
            onRetry={() => load()}
            retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
            secondaryTo="/app/automation-log"
            secondaryLabel={t('app.automation_log.title', { defaultValue: 'Automation log' })}
            compact
          />
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-slate-500 border-b border-slate-200">
                <th className="py-2 pr-4">{t('app.automation_log.table.when', { defaultValue: 'When' })}</th>
                <th className="py-2 pr-4">{t('app.automation_log.table.action', { defaultValue: 'Action' })}</th>
                <th className="py-2 pr-4">{t('app.automation_log.table.target', { defaultValue: 'Target' })}</th>
                <th className="py-2">{t('app.automation_log.table.payload', { defaultValue: 'Payload' })}</th>
              </tr>
            </thead>
            <tbody>
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500">
                    {t('common.loading')}
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500">
                    {t('app.automation_log.empty', { defaultValue: 'No automation events yet.' })}
                  </td>
                </tr>
              ) : (
                items.map((entry) => (
                  <tr key={entry.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-2 pr-4 whitespace-nowrap text-slate-600">{formatDateTime(entry.created_at, locale)}</td>
                    <td className="py-2 pr-4 font-medium">{entry.action}</td>
                    <td className="py-2 pr-4 text-slate-700">
                      {(entry.target_type || '—') + (entry.target_id ? `:${entry.target_id}` : '')}
                    </td>
                    <td className="py-2">
                      {entry.payload && Object.keys(entry.payload).length > 0 ? (
                        <details className="text-xs">
                          <summary className="cursor-pointer text-slate-500 hover:text-slate-700">
                            {t('admin.settings.audit.details', { defaultValue: 'Details' })}
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
              {t('app.automation_log.pagination', {
                defaultValue: 'Shown {from}–{to} of {total}',
                values: { from: offset + 1, to: shownTo, total },
              })}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={offset === 0 || loading}
                onClick={() => {
                  const next = Math.max(0, offset - limit)
                  setOffset(next)
                  load({ offset: next })
                }}
              >
                {t('common.actions.prev', { defaultValue: 'Prev' })}
              </button>
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={offset + limit >= total || loading}
                onClick={() => {
                  const next = offset + limit
                  setOffset(next)
                  load({ offset: next })
                }}
              >
                {t('common.actions.next', { defaultValue: 'Next' })}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
