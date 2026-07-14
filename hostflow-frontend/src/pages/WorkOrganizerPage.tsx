import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import CommunicationsCalendarPage from './CommunicationsCalendarPage'
import { MyTasksPanel } from '../modules/workHub/MyTasksPanel'
import { TodayPlannerPanel } from '../modules/workHub/TodayPlannerPanel'
import { HandoffQueuePanel } from '../modules/workHub/HandoffQueuePanel'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { getOpsCounters, type OpsCounters } from '../api/analytics'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { useI18n } from '../i18n'

export default function WorkOrganizerPage() {
  const { t } = useI18n()
  const [calendarFullscreen, setCalendarFullscreen] = useState(false)
  const [ops, setOps] = useState<OpsCounters | null>(null)
  const [loadingOps, setLoadingOps] = useState(true)

  const loadOps = useCallback(async () => {
    setLoadingOps(true)
    try {
      const data = await getOpsCounters()
      setOps(data)
    } catch {
      setOps(null)
    } finally {
      setLoadingOps(false)
    }
  }, [])

  useEffect(() => {
    void loadOps()
  }, [loadOps])

  const summaryRows = useMemo(() => {
    return [
      {
        key: 'nna',
        count: Number(ops?.no_next_action_candidates || 0),
        label: t('app.work.hub.crit_no_next', { defaultValue: 'Candidates without next step' }),
        href: `${CRM_APP_PATHS.candidates}?filter=action_required`,
        severity: 'amber' as const,
        priority: 30,
      },
      {
        key: 'od',
        count: Number(ops?.overdue_reminders || 0),
        label: t('app.work.hub.crit_tasks_overdue', { defaultValue: 'Overdue tasks' }),
        href: `${CRM_APP_PATHS.tasks}?tab=tasks&filter=overdue`,
        severity: 'red' as const,
        priority: 100,
      },
      {
        key: 'lead_stale',
        count: Number(ops?.leads_new_untouched_24h || 0),
        label: t('app.work.hub.crit_leads_stale', { defaultValue: 'Leads untouched 24h+' }),
        href: `${CRM_APP_PATHS.leads}?filter=no_first_contact_24h`,
        severity: 'red' as const,
        priority: 90,
      },
      {
        key: 'route',
        count: Number(ops?.leads_needs_routing || 0),
        label: t('app.work.hub.crit_leads_route', { defaultValue: 'Leads waiting triage' }),
        href: `${CRM_APP_PATHS.leads}?filter=needs_routing`,
        severity: 'amber' as const,
        priority: 60,
      },
      {
        key: 'failed',
        count: Number(ops?.leads_failed || 0),
        label: t('app.work.hub.problems.failed', { defaultValue: 'Failed leads / incidents' }),
        href: CRM_APP_PATHS.leads,
        severity: 'red' as const,
        priority: 80,
      },
    ]
      .filter((x) => x.count > 0)
      .sort((a, b) => {
        if (b.priority !== a.priority) return b.priority - a.priority
        if (b.count !== a.count) return b.count - a.count
        return a.label.localeCompare(b.label)
      })
  }, [ops, t])

  const severityClass = (severity: 'red' | 'amber' | 'slate') => {
    if (severity === 'red') return 'border-rose-200 bg-rose-50 text-rose-800'
    if (severity === 'amber') return 'border-amber-200 bg-amber-50 text-amber-800'
    return 'border-slate-200 bg-slate-50 text-slate-800'
  }

  return (
    <PageShell className="bg-slate-50">
      <PageShellHeader>
        <PageHeader
          title={t('app.work.hub.operational_title', { defaultValue: 'Work' })}
          subtitle={t('app.work.hub.page_kicker', { defaultValue: 'Everything that needs attention right now' })}
          kind="browse"
          secondaryActions={
            <button type="button" className="btn-secondary btn-sm" onClick={() => void loadOps()}>
              {t('common.actions.refresh', { defaultValue: 'Refresh' })}
            </button>
          }
        />
      </PageShellHeader>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 pb-4">
      <section className="sticky top-0 z-20 rounded-xl border border-slate-200 bg-white/95 p-3 backdrop-blur">
        <div className="mb-2 text-sm font-semibold text-slate-900">
          {t('app.work.organizer.top.problems_title', { defaultValue: 'Critical counters' })}
        </div>
        {loadingOps ? (
          <div className="text-xs text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>
        ) : summaryRows.length === 0 ? (
          <div className="text-xs text-slate-500">
            {t('app.work.organizer.right.no_problems', { defaultValue: 'No critical issues right now.' })}
          </div>
        ) : (
          <div className="grid gap-2 md:grid-cols-3 xl:grid-cols-5">
            {summaryRows.map((row) => (
              <Link
                key={row.key}
                to={row.href}
                className={`flex items-center justify-between rounded border px-2 py-1.5 text-xs hover:opacity-90 ${severityClass(row.severity)}`}
              >
                <span className="truncate">{row.label}</span>
                <span className="ml-2 rounded bg-white/80 px-1.5 py-0.5 font-semibold">{row.count}</span>
              </Link>
            ))}
          </div>
        )}
      </section>

      <div className="mb-3 flex items-center justify-end">
        <button
          type="button"
          className="btn-secondary"
          onClick={() => setCalendarFullscreen((v) => !v)}
        >
          {calendarFullscreen
            ? t('common.actions.close', { defaultValue: 'Close' })
            : t('app.communications.calendar.actions.open', { defaultValue: 'Open' })}{' '}
          {t('app.communications.calendar.views.month', { defaultValue: 'Calendar' })}
        </button>
      </div>
      <div className={calendarFullscreen ? '' : 'grid gap-4 xl:grid-cols-[1.55fr_0.45fr]'}>
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <CommunicationsCalendarPage embedded />
        </div>
        {!calendarFullscreen && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <MyTasksPanel />
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <TodayPlannerPanel />
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <HandoffQueuePanel />
            </div>
          </div>
        )}
      </div>
      </div>
    </PageShell>
  )
}
