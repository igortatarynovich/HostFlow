import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowRight, IconFlame, IconUsersGroup } from '@tabler/icons-react'

import {
  getRiskIntelligenceManagerDigestQueue,
  type OpsCounters,
  type RiskIntelDigestQueueResponse,
} from '../../api/analytics'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

/**
 * G-6 Stage 2d — supervisor / admin-team «what is burning» strip on `/app/work`.
 *
 * Spec: ``docs/specs/operations-loop.md`` — SLA risk digest queue + stale leads +
 * team-wide overdue, single CTA toward the overview (full risk widgets live on
 * ``/app/overview`` today).
 *
 * Data:
 *   - ``GET /analytics/risk-intelligence/manager-digest-queue`` — unread bucket
 *     count + latest bucket volume (``min_band=high`` matches dashboard default).
 *   - ``ops`` prop — same ``OpsCounters`` snapshot Work Hub already loads
 *     (``getOpsCounters``) so we do not duplicate that network round-trip.
 *
 * Wire-in: ``profile.sections`` for ``admin_team`` + ``supervisor`` only, placed
 * after ``todayPlanner`` and before ``managerLoad`` — digest answers «why» before
 * «who owns how many rows».
 */

const HREF_TASKS_TEAM_OVERDUE = `${CRM_APP_PATHS.tasks}?tab=tasks&filter=overdue`
const HREF_TASKS_UNLINKED = `${CRM_APP_PATHS.tasks}?tab=tasks&t_layout=by_candidate&t_unlinked=1`
const HREF_LEADS_STALE = `${CRM_APP_PATHS.leads}?filter=no_first_contact_24h`

type Props = {
  ops: OpsCounters | null
}

export function RiskDigestPanel({ ops }: Props) {
  const { t } = useI18n()
  const [digest, setDigest] = useState<RiskIntelDigestQueueResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await getRiskIntelligenceManagerDigestQueue({
        min_band: 'high',
        limit_buckets: 14,
      })
      setDigest(data)
    } catch {
      setDigest(null)
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const digestUnread = digest?.unread_count ?? 0
  const topUnreadBucket = useMemo(() => {
    const buckets = digest?.buckets ?? []
    return buckets.find((b) => b.unread) ?? buckets[0] ?? null
  }, [digest?.buckets])

  const overdueRem = ops?.overdue_reminders ?? 0
  const unlinkedTasks = ops?.unlinked_tasks ?? 0
  const staleLeads = (ops?.leads_new_untouched_24h ?? 0) + (ops?.draft_intake_stale ?? 0)
  const heatTotal = digestUnread + overdueRem + unlinkedTasks + staleLeads

  if (loading && digest === null && !error) {
    return (
      <section
        aria-busy="true"
        className="h-36 animate-pulse rounded-2xl border border-slate-200 bg-white"
      />
    )
  }

  if (error && digest === null) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-base font-bold text-slate-900">
            {t('app.work.hub.risk_digest.title', { defaultValue: 'Team risk digest' })}
          </h2>
          <button
            type="button"
            className="text-sm font-semibold text-brand-700 hover:text-brand-800"
            onClick={() => void load()}
          >
            {t('app.work.hub.reload', { defaultValue: 'Refresh' })}
          </button>
        </div>
        <p className="mt-2 text-sm text-slate-500">
          {t('app.work.hub.risk_digest.error', {
            defaultValue: 'Could not load the SLA digest. Ops counters below still apply.',
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
            {t('app.work.hub.risk_digest.title', { defaultValue: 'Team risk digest' })}
          </h2>
          <p className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
            <IconFlame size={14} className="shrink-0 text-rose-500 opacity-90" aria-hidden />
            <span>
              {t('app.work.hub.risk_digest.subtitle', {
                defaultValue: 'SLA buckets, overdue work, and stale intake',
              })}
            </span>
          </p>
        </div>
        {heatTotal > 0 ? (
          <span className="shrink-0 rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-800">
            {t('app.work.hub.risk_digest.heat', {
              defaultValue: '{n} hot',
              values: { n: heatTotal },
            })}
          </span>
        ) : null}
      </div>

      <ul className="divide-y divide-slate-100">
        <li className="flex items-start justify-between gap-4 px-6 py-3.5 text-sm">
          <div className="min-w-0">
            <div className="font-semibold text-slate-900">
              {t('app.work.hub.risk_digest.row_sla', { defaultValue: 'SLA digest (high+)' })}
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              {digestUnread > 0
                ? t('app.work.hub.risk_digest.row_sla_unread', {
                    defaultValue: '{unread} unread bucket(s); latest volume ~{vol}',
                    values: {
                      unread: digestUnread,
                      vol: topUnreadBucket?.total_matching ?? 0,
                    },
                  })
                : t('app.work.hub.risk_digest.row_sla_clear', {
                    defaultValue: 'No unread digest buckets for this band.',
                  })}
            </p>
          </div>
          <span className="shrink-0 tabular-nums text-sm font-bold text-slate-900">{digestUnread}</span>
        </li>

        <li>
          <Link
            to={HREF_TASKS_TEAM_OVERDUE}
            className="flex items-start justify-between gap-4 px-6 py-3.5 text-sm transition hover:bg-slate-50/90"
          >
            <div className="min-w-0">
              <div className="font-semibold text-slate-900">
                {t('app.work.hub.risk_digest.row_overdue', { defaultValue: 'Team overdue reminders' })}
              </div>
              <p className="mt-0.5 text-xs text-slate-500">
                {t('app.work.hub.risk_digest.row_overdue_hint', {
                  defaultValue: 'Tasks / reminders past due (tenant scope)',
                })}
              </p>
            </div>
            <span className="shrink-0 tabular-nums text-sm font-bold text-slate-900">{overdueRem}</span>
          </Link>
        </li>

        <li>
          <Link
            to={HREF_LEADS_STALE}
            className="flex items-start justify-between gap-4 px-6 py-3.5 text-sm transition hover:bg-slate-50/90"
          >
            <div className="min-w-0">
              <div className="font-semibold text-slate-900">
                {t('app.work.hub.risk_digest.row_stale', { defaultValue: 'Stale & draft intake' })}
              </div>
              <p className="mt-0.5 text-xs text-slate-500">
                {t('app.work.hub.risk_digest.row_stale_hint', {
                  defaultValue: 'Leads untouched 24h + stale draft rows',
                })}
              </p>
            </div>
            <span className="shrink-0 tabular-nums text-sm font-bold text-slate-900">{staleLeads}</span>
          </Link>
        </li>
        <li>
          <Link
            to={HREF_TASKS_UNLINKED}
            className="flex items-start justify-between gap-4 px-6 py-3.5 text-sm transition hover:bg-slate-50/90"
          >
            <div className="min-w-0">
              <div className="font-semibold text-slate-900">
                {t('app.work.hub.risk_digest.row_unlinked_tasks', {
                  defaultValue: 'Tasks without entity link',
                })}
              </div>
              <p className="mt-0.5 text-xs text-slate-500">
                {t('app.work.hub.risk_digest.row_unlinked_tasks_hint', {
                  defaultValue: 'Rows missing a valid candidate/lead/vacancy/company/thread link',
                })}
              </p>
            </div>
            <span className="shrink-0 tabular-nums text-sm font-bold text-slate-900">{unlinkedTasks}</span>
          </Link>
        </li>
      </ul>

      <div className="border-t border-slate-100 px-6 py-4">
        <Link
          to={CRM_APP_PATHS.overview}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800"
        >
          <IconUsersGroup size={18} className="opacity-90" aria-hidden />
          {t('app.work.hub.risk_digest.cta', { defaultValue: 'Unblock the team — open overview' })}
          <IconArrowRight size={16} className="opacity-80" aria-hidden />
        </Link>
      </div>
    </section>
  )
}
