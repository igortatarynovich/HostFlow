import clsx from 'clsx'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { completeActivity, listActivities } from '../api/client'
import type { ReminderListResponse, ReminderRecord } from '../api/types'
import { useI18n } from '../i18n'
import WorkspaceTopNav from '../components/communications/WorkspaceTopNav'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'

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
      return `/app/candidates/${entityId}`
    case 'vacancy':
      return `/app/vacancies/${entityId}`
    case 'lead':
      return `/app/leads`
    case 'company':
      return `/app/companies/${entityId}`
    default:
      return null
  }
}

export default function ActivitiesPage() {
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
      })) as ReminderListResponse
      setItems(Array.isArray(data?.items) ? data.items : [])
      setState('idle')
    } catch (err: any) {
      setState('error')
      setError(getFriendlyErrorInfo(err, t('app.activities.errors.load', { defaultValue: 'Failed to load activities' })))
    }
  }, [statusList, t, typeFilter])

  useEffect(() => {
    void load()
  }, [load])

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
        setError(getFriendlyErrorInfo(err, t('app.activities.errors.complete', { defaultValue: 'Failed to complete activity' })))
      } finally {
        setBusyId(null)
      }
    },
    [t],
  )

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <WorkspaceTopNav active="activities" />

      <header className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.activities.title', { defaultValue: 'Activities' })}
            </p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-900">
              {t('app.activities.subtitle', { defaultValue: 'Planned work for you' })}
            </h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary btn-sm" onClick={() => void load()}>
              {t('common.actions.refresh', { defaultValue: 'Refresh' })}
            </button>
          </div>
        </div>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <input
            className="input min-w-[220px] flex-1"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('app.activities.filters.search', { defaultValue: 'Search title, type, entity...' })}
          />
          <select className="input" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="">{t('app.activities.filters.type_all', { defaultValue: 'All types' })}</option>
            {typeOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
          <div className="flex flex-wrap gap-2">
            {(['active', 'all', 'done'] as StatusFilter[]).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatus(value)}
                className={clsx(
                  'rounded-md border px-3 py-1.5 text-xs font-medium transition',
                  status === value
                    ? 'border-brand-600 bg-brand-600 text-white'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
                )}
              >
                {value === 'active' && t('app.activities.filters.active', { defaultValue: 'Active' })}
                {value === 'all' && t('app.activities.filters.all', { defaultValue: 'All' })}
                {value === 'done' && t('app.activities.filters.done', { defaultValue: 'Done' })}
              </button>
            ))}
          </div>
        </div>

        {state === 'loading' && <div className="text-sm text-slate-500">{t('common.loading')}</div>}
        {state === 'error' && error && (
          <ErrorRecoveryBanner
            compact
            info={error}
            onRetry={() => void load()}
            retryLabel={t('common.retry', { defaultValue: 'Retry' })}
            secondaryTo="/app/leads"
            secondaryLabel={t('app.reminders.states.empty_cta_leads', { defaultValue: 'Open leads' })}
          />
        )}

        {state !== 'loading' && filtered.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
            {t('app.activities.states.empty', { defaultValue: 'No activities yet' })}
          </div>
        )}

        {filtered.length > 0 && (
          <div className="divide-y divide-slate-100 rounded-xl border border-slate-200">
            {filtered.map((item) => {
              const href = reminderEntityHref(item)
              const closed = isClosedStatus(item.status)
              const busy = busyId === item.id
              return (
                <div key={item.id} className="flex flex-wrap items-start justify-between gap-3 bg-white p-3">
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{item.type}</span>
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                        {item.entity_type}
                      </span>
                      <span className="text-xs text-slate-500">{new Date(item.due_at).toLocaleString()}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-semibold text-slate-900">{item.title || '—'}</p>
                      {href && (
                        <Link to={href} className="text-xs font-medium text-brand-700 hover:underline">
                          {t('app.activities.actions.open', { defaultValue: 'Open' })}
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
                        {busy ? t('common.loading') : t('app.activities.actions.complete', { defaultValue: 'Complete' })}
                      </button>
                    )}
                    {closed && (
                      <span className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
                        {t('app.activities.states.completed', { defaultValue: 'Done' })}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}

