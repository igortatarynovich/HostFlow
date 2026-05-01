import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowRight } from '@tabler/icons-react'

import { getHandoffStats, type HandoffStatsResponse } from '../../api/analytics'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

/**
 * Handoff queue summary for client_manager / client_processor.
 *
 * Pending = total_requested − accepted − rejected − returned (the dashboard
 * "handoff.pending" metric — see `docs/specs/operational-metrics.md` §3.2).
 * The drilldown URLs match the canonical entries from the same spec so
 * counter ↔ list parity is preserved (G-3).
 */
export function HandoffQueuePanel() {
  const { t } = useI18n()
  const [stats, setStats] = useState<HandoffStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(false)
    getHandoffStats()
      .then((data) => {
        if (mounted) setStats(data)
      })
      .catch(() => {
        if (mounted) setError(true)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  if (loading) {
    return (
      <section
        aria-busy="true"
        className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white"
      />
    )
  }

  if (error || !stats) {
    return null
  }

  const requested = stats.total_requested ?? 0
  const accepted = stats.total_accepted ?? 0
  const rejected = stats.total_rejected ?? 0
  const returned = stats.total_returned ?? 0
  const pending = Math.max(0, requested - accepted - rejected - returned)

  if (requested === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-bold text-slate-900">
          {t('app.work.handoff.title', { defaultValue: 'Incoming handoffs' })}
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.work.handoff.empty', {
            defaultValue: 'No handoffs from the agency yet.',
          })}
        </p>
      </section>
    )
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
        <h2 className="text-base font-bold text-slate-900">
          {t('app.work.handoff.title', { defaultValue: 'Incoming handoffs' })}
        </h2>
        <Link
          to={`${CRM_APP_PATHS.candidates}?handoff_status=any`}
          className="inline-flex items-center text-sm font-semibold text-brand-700 hover:text-brand-800"
        >
          {t('app.work.handoff.open_all', { defaultValue: 'Open all' })}
          <IconArrowRight size={16} className="ml-1 opacity-70" aria-hidden />
        </Link>
      </div>
      <ul className="divide-y divide-slate-100">
        <HandoffRow
          countLabel={t('app.work.handoff.pending', {
            defaultValue: 'Awaiting your decision',
          })}
          count={pending}
          tone="amber"
          href={`${CRM_APP_PATHS.candidates}?handoff_status=pending`}
        />
        <HandoffRow
          countLabel={t('app.work.handoff.returned', {
            defaultValue: 'Returned to the agency',
          })}
          count={returned}
          tone="slate"
          href={`${CRM_APP_PATHS.candidates}?handoff_status=returned`}
        />
        <HandoffRow
          countLabel={t('app.work.handoff.accepted', {
            defaultValue: 'Accepted (in your pipeline)',
          })}
          count={accepted}
          tone="emerald"
          href={`${CRM_APP_PATHS.candidates}?handoff_status=accepted`}
        />
      </ul>
    </section>
  )
}

type RowTone = 'amber' | 'slate' | 'emerald'

const TONE_BAR: Record<RowTone, string> = {
  amber: 'bg-amber-500',
  slate: 'bg-slate-400',
  emerald: 'bg-emerald-500',
}

function HandoffRow({
  countLabel,
  count,
  tone,
  href,
}: {
  countLabel: string
  count: number
  tone: RowTone
  href: string
}) {
  return (
    <li>
      <Link
        to={href}
        className="group flex items-stretch gap-0 transition hover:bg-slate-50/90"
      >
        <div className={`w-1 shrink-0 ${TONE_BAR[tone]}`} aria-hidden />
        <div className="flex min-w-0 flex-1 items-center justify-between gap-4 px-5 py-3.5">
          <span className="truncate text-sm font-medium text-slate-800">{countLabel}</span>
          <span className="tabular-nums text-sm font-bold text-slate-900">{count}</span>
        </div>
      </Link>
    </li>
  )
}
