import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowRight, IconUsersGroup } from '@tabler/icons-react'

import {
  getAnalyticsByManager,
  type AnalyticsByManagerItem,
} from '../../api/analytics'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

/**
 * G-6 Stage 2c — recruiter load distribution on `/app/work`.
 *
 * The admin/supervisor Work Hub profile is supposed to answer
 * "who on the team is over/under-loaded, and where do I need to
 * rebalance?". Before this panel that signal lived only on the
 * dashboard's "Manager load" widget — useful but gated behind a
 * pivot widget picker most operators never open. Surfacing it on
 * the hub puts the team view one scroll away from the calm hero.
 *
 * Scope decisions:
 *   - Wired into `admin_team` and `supervisor` profiles only. Owner-
 *     solo has exactly one recruiter (themself); recruiter/client_
 *     processor views are personal-focus and already have their own
 *     `MyTasksPanel` / `TodayPlannerPanel`; `client_manager` cares
 *     about handoffs, not the agency-side team load.
 *   - Data source: `GET /analytics/by-manager`. Cheaper than the
 *     dashboard's `/analytics/candidate-slices` (returns full
 *     snapshot) — this endpoint aggregates on the DB side and
 *     returns one row per (manager_raw | recruiter_id) key. The
 *     stage 2c backend patch adds `recruiter_id` to each item so
 *     the drill-down can target the canonical URL without a label
 *     lookup round-trip.
 *   - Drill-down precedence: `recruiter_id` wins, legacy
 *     `manager` free-text falls back to `?manager=<label>` (the
 *     `useCandidatesUrlSync` hook recognizes both, see
 *     `hostflow-frontend/src/modules/candidates/hooks/useCandidatesUrlSync.ts`).
 *     Canonical param name on drill-down is `?recruiter_id=` per
 *     G-5 Stage F — the Stage 2c wiring also teaches
 *     `useCandidatesUrlSync` to parse that name (was only reading
 *     `manager_id` / `manager`).
 *
 * Ranking: the response is already sorted by total desc + label,
 * so we render the top N as-is without re-sorting. A visual bar
 * uses the max(total) as the scale — linear so the "who owns the
 * most" signal reads in one glance.
 */

const MAX_ROWS = 6

function num(n: number | undefined | null): string {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return String(Math.max(0, Math.floor(Number(n))))
}

function drilldownHref(item: AnalyticsByManagerItem): string {
  if (item.recruiter_id) {
    return `${CRM_APP_PATHS.candidates}?recruiter_id=${encodeURIComponent(item.recruiter_id)}`
  }
  // Legacy fallback: `Candidate.manager` is a free-text label the old
  // UI wrote. Matches `useCandidatesUrlSync.ts:99` ("manager" alias).
  const label = (item.manager || '').trim()
  if (!label) return CRM_APP_PATHS.candidates
  return `${CRM_APP_PATHS.candidates}?manager=${encodeURIComponent(label)}`
}

export function ManagerLoadPanel() {
  const { t } = useI18n()
  const [items, setItems] = useState<AnalyticsByManagerItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await getAnalyticsByManager()
      const rows = Array.isArray(data?.items) ? data.items : []
      setItems(rows)
    } catch {
      setItems(null)
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const visible = useMemo(() => (items ?? []).slice(0, MAX_ROWS), [items])
  const overflow = Math.max(0, (items?.length ?? 0) - visible.length)
  const maxTotal = useMemo(
    () => visible.reduce((acc, item) => Math.max(acc, item.total || 0), 1),
    [visible],
  )

  if (loading && items === null) {
    return (
      <section
        aria-busy="true"
        className="h-40 animate-pulse rounded-2xl border border-slate-200 bg-white"
      />
    )
  }

  if (error && items === null) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            {t('app.work.hub.manager_load.title', { defaultValue: 'Team load' })}
          </h2>
          <button
            type="button"
            className="text-sm font-semibold text-brand-700 hover:text-brand-800"
            onClick={() => void load()}
          >
            {t('app.work.hub.reload', { defaultValue: 'Refresh' })}
          </button>
        </div>
        <p className="mt-3 text-sm text-slate-500">
          {t('app.work.hub.manager_load.error', {
            defaultValue: 'Could not load team distribution. Try again.',
          })}
        </p>
      </section>
    )
  }

  if (!items || items.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            {t('app.work.hub.manager_load.title', { defaultValue: 'Team load' })}
          </h2>
          <Link
            to={CRM_APP_PATHS.candidates}
            className="inline-flex items-center text-sm font-semibold text-brand-700 hover:text-brand-800"
          >
            {t('app.work.hub.manager_load.open_all', { defaultValue: 'Open candidates' })}
            <IconArrowRight size={16} className="ml-1 opacity-70" aria-hidden />
          </Link>
        </div>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.work.hub.manager_load.empty', {
            defaultValue: 'No candidates are assigned to anyone yet.',
          })}
        </p>
      </section>
    )
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-6 py-4">
        <div className="min-w-0">
          <h2 className="text-base font-bold text-slate-900">
            {t('app.work.hub.manager_load.title', { defaultValue: 'Team load' })}
          </h2>
          <p className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
            <IconUsersGroup size={14} className="opacity-70" aria-hidden />
            <span>
              {t('app.work.hub.manager_load.subtitle', {
                defaultValue: 'Candidates owned by each recruiter',
              })}
            </span>
          </p>
        </div>
        <Link
          to={CRM_APP_PATHS.candidates}
          className="inline-flex items-center text-sm font-semibold text-brand-700 hover:text-brand-800"
        >
          {t('app.work.hub.manager_load.open_all', { defaultValue: 'Open candidates' })}
          <IconArrowRight size={16} className="ml-1 opacity-70" aria-hidden />
        </Link>
      </div>
      <ul className="divide-y divide-slate-100">
        {visible.map((item) => (
          <LoadRow key={item.recruiter_id ?? item.manager} item={item} maxTotal={maxTotal} t={t} />
        ))}
        {overflow > 0 ? (
          <li>
            <Link
              to={CRM_APP_PATHS.candidates}
              className="group flex items-stretch gap-0 transition hover:bg-slate-50/90"
            >
              <div className="w-1 shrink-0 bg-slate-300" aria-hidden />
              <div className="flex min-w-0 flex-1 items-center justify-between gap-4 px-5 py-3 text-xs text-slate-500">
                <span>
                  {t('app.work.hub.manager_load.more', {
                    defaultValue: '+{count} more on the team',
                    values: { count: overflow },
                  })}
                </span>
                <span className="shrink-0 font-semibold text-brand-700 group-hover:text-brand-800">
                  {t('app.work.hub.row_open', { defaultValue: 'Open' })}
                </span>
              </div>
            </Link>
          </li>
        ) : null}
      </ul>
    </section>
  )
}

function LoadRow({
  item,
  maxTotal,
  t,
}: {
  item: AnalyticsByManagerItem
  maxTotal: number
  t: ReturnType<typeof useI18n>['t']
}) {
  const href = drilldownHref(item)
  const label = (item.manager || '').trim() || t('app.work.hub.manager_load.unknown', { defaultValue: 'Unassigned' })
  const total = Math.max(0, Math.floor(Number(item.total) || 0))
  const hired = Math.max(0, Math.floor(Number(item.hired) || 0))
  const barWidth = maxTotal > 0 ? `${Math.min(100, Math.round((total / maxTotal) * 100))}%` : '0%'
  return (
    <li>
      <Link to={href} className="group flex items-stretch gap-0 transition hover:bg-slate-50/90">
        <div className="w-1 shrink-0 bg-slate-300" aria-hidden />
        <div className="flex min-w-0 flex-1 items-center justify-between gap-4 px-5 py-3.5">
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-3">
              <p className="truncate text-sm font-semibold text-slate-900">{label}</p>
              <span className="shrink-0 tabular-nums text-sm font-bold text-slate-900">{num(total)}</span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden>
              <div className="h-full rounded-full bg-brand-500" style={{ width: barWidth }} />
            </div>
            <p className="mt-1.5 flex items-center gap-3 text-xs text-slate-500">
              <span>
                {t('app.work.hub.manager_load.hired_count', {
                  defaultValue: '{count} hired',
                  values: { count: hired },
                })}
              </span>
              {!item.recruiter_id ? (
                <span className="text-amber-700">
                  {t('app.work.hub.manager_load.legacy_label', {
                    defaultValue: 'legacy label',
                  })}
                </span>
              ) : null}
            </p>
          </div>
          <span className="shrink-0 text-sm font-semibold text-brand-700 group-hover:text-brand-800">
            {t('app.work.hub.row_open', { defaultValue: 'Open' })}
            <IconArrowRight size={16} className="ml-1 inline align-text-bottom opacity-70" aria-hidden />
          </span>
        </div>
      </Link>
    </li>
  )
}
