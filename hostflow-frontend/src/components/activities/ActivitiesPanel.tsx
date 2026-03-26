import clsx from 'clsx'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { completeActivity, listActivities } from '../../api/client'
import type { ReminderListResponse, ReminderRecord } from '../../api/types'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { buildInboxThreadPath } from '../../utils/inboxDeepLinks'

type LoadState = 'idle' | 'loading' | 'error'
type StatusFilter = 'active' | 'all' | 'done'

function isClosedStatus(status?: string | null): boolean {
  const normalized = String(status || '').trim().toLowerCase()
  return normalized === 'done' || normalized === 'completed' || normalized === 'cancelled'
}

function reminderEntityHref(item: ReminderRecord): string | null {
  const entityId = String(item.entity_id || '')
  if (!entityId) return null
  switch (item.entity_type) {
    case 'candidate':
      return `${CRM_APP_PATHS.candidates}/${entityId}`
    case 'vacancy':
      return `${CRM_APP_PATHS.vacancies}/${entityId}`
    case 'lead':
      return CRM_APP_PATHS.leads
    case 'company':
      return `${CRM_APP_PATHS.agencyClients}/${entityId}`
    case 'communication_thread':
      return buildInboxThreadPath(entityId)
    default:
      return null
  }
}

type ActivitiesPanelProps = {
  /** Tighter spacing for modal embedding */
  compact?: boolean
  /** Show link to full tasks workspace (Reminders, same as **`tasksWorkspace`**) */
  showFullPageLink?: boolean
  /** When true, reload list whenever this value changes (e.g. modal open counter) */
  refreshToken?: number
  /** Strip outer chrome when already inside a modal/card */
  embedded?: boolean
}

/**
 * Shared activities list + filters (used on Activities page and in modals).
 */
export function ActivitiesPanel({ compact, showFullPageLink, refreshToken, embedded }: ActivitiesPanelProps) {
  const { t } = useI18n()
  const [items, setItems] = useState<ReminderRecord[]>([])
  const [state, setState] = useState<LoadState>('idle')
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const [status, setStatus] = useState<StatusFilter>('active')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [search, setSearch] = useState<string>('')

  const statusList = useMemo(() => {
    if (status === 'active') return ['pending', 'new', 'overdue', 'sent']
    if (status === 'done') return ['done', 'cancelled']
    return undefined
  }, [status])

  const load = useCallback(async () => {
    setState('loading')
    setError(null)
    try {
      const data = (await listActivities({
        status: statusList,
        types: typeFilter ? [typeFilter] : undefined,
        assigneeScope: 'mine',
      })) as ReminderListResponse
      setItems(Array.isArray(data?.items) ? data.items : [])
      setState('idle')
    } catch (err: any) {
      setState('error')
      setError(getFriendlyErrorInfo(err, t('app.activities.errors.load')))
    }
  }, [statusList, t, typeFilter])

  useEffect(() => {
    void load()
  }, [load, refreshToken])

  const typeOptions = useMemo(() => {
    return Array.from(new Set(items.map((i) => i.type).filter(Boolean))).sort()
  }, [items])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return items
      .filter((item) => {
        if (!q) return true
        const hay = [item.title, item.description, item.type, item.entity_type, item.entity_id]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
        return hay.includes(q)
      })
      .sort((a, b) => Date.parse(a.due_at || '') - Date.parse(b.due_at || ''))
  }, [items, search])

  const handleComplete = useCallback(
    async (id: string) => {
      setBusyId(id)
      setError(null)
      try {
        const updated = (await completeActivity(id)) as ReminderRecord
        setItems((prev) => prev.map((r) => (r.id === id ? updated : r)))
      } catch (err: any) {
        setError(getFriendlyErrorInfo(err, t('app.activities.errors.complete')))
      } finally {
        setBusyId(null)
      }
    },
    [t],
  )

  const pad = embedded ? 'space-y-3' : compact ? 'p-3 space-y-3' : 'p-4 space-y-4'

  return (
    <section
      className={clsx(
        !embedded && 'rounded-2xl border border-slate-200 bg-white shadow-sm',
        embedded && 'bg-transparent',
        pad,
      )}
    >
      <div className={clsx('flex flex-wrap items-center gap-2', compact && 'gap-1.5')}>
        <input
          className={clsx('input min-w-[180px] flex-1', compact && 'text-sm')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('app.activities.filters.search')}
        />
        <select className={clsx('input', compact && 'text-sm')} value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="">{t('app.activities.filters.type_all')}</option>
          {typeOptions.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        <div className="flex flex-wrap gap-1.5">
          {(['active', 'all', 'done'] as StatusFilter[]).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setStatus(value)}
              className={clsx(
                'rounded-md border px-2.5 py-1 text-xs font-medium transition',
                compact && 'px-2 py-0.5 text-[11px]',
                status === value
                  ? 'border-brand-600 bg-brand-600 text-white'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
              )}
            >
              {value === 'active' && t('app.activities.filters.active')}
              {value === 'all' && t('app.activities.filters.all')}
              {value === 'done' && t('app.activities.filters.done')}
            </button>
          ))}
        </div>
        <button type="button" className={clsx('btn-secondary btn-sm', compact && 'btn-xs')} onClick={() => void load()}>
          {t('common.actions.refresh')}
        </button>
      </div>

      {state === 'loading' && <div className="text-sm text-slate-500">{t('common.loading')}</div>}
      {state === 'error' && error && (
        <ErrorRecoveryBanner
          compact
          info={error}
          onRetry={() => void load()}
          retryLabel={t('common.retry')}
          secondaryTo={CRM_APP_PATHS.leads}
          secondaryLabel={t('app.reminders.states.empty_cta_leads')}
        />
      )}

      {state !== 'loading' && filtered.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
          {t('app.activities.states.empty')}
        </div>
      )}

      {filtered.length > 0 && (
        <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 max-h-[min(60vh,520px)] overflow-y-auto">
          {filtered.map((item) => {
            const href = reminderEntityHref(item)
            const closed = isClosedStatus(item.status)
            const busy = busyId === item.id
            return (
              <div key={item.id} className="flex flex-wrap items-start justify-between gap-2 bg-white p-2.5 sm:p-3">
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{item.type}</span>
                    <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{item.entity_type}</span>
                    <span className="text-[11px] text-slate-500">{new Date(item.due_at).toLocaleString()}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-semibold text-slate-900">{item.title || '—'}</p>
                    {href && (
                      <Link to={href} className="text-xs font-medium text-brand-700 hover:underline">
                        {t('app.activities.actions.open')}
                      </Link>
                    )}
                  </div>
                  {item.description && <p className="text-xs text-slate-600 whitespace-pre-wrap">{item.description}</p>}
                </div>
                <div className="flex items-center gap-2">
                  {!closed && (
                    <button
                      type="button"
                      className="btn-primary btn-xs"
                      onClick={() => void handleComplete(item.id)}
                      disabled={busy}
                    >
                      {busy ? t('common.loading') : t('app.activities.actions.complete')}
                    </button>
                  )}
                  {closed && (
                    <span className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
                      {t('app.activities.states.completed')}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showFullPageLink ? (
        <div className="flex justify-end border-t border-slate-100 pt-3">
          <Link to={CRM_APP_PATHS.tasks} className="btn-secondary btn-sm">
            {t('app.candidates.activities_modal.open_full_page')}
          </Link>
        </div>
      ) : null}
    </section>
  )
}
