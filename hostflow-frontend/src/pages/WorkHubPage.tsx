import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowRight, IconFlame, IconLock } from '@tabler/icons-react'

import { getOpsCounters, type OpsCounters } from '../api/analytics'
import { getCommunicationsSettings, listCommunicationTimeOffRequests, type CommunicationTimeOffRequest } from '../api/communications'
import { useTeamOverviewNav } from '../contexts/TeamOverviewNavContext'
import { useCommunicationsAccess } from '../hooks/useCommunicationsAccess'
import { usePermissions } from '../hooks/usePermissions'
import { useTeamTierFeatures } from '../hooks/useTeamTierFeatures'
import { usePendingHandoffsCount } from '../hooks/usePendingHandoffsCount'
import { useI18n } from '../i18n'
import {
  type BusinessTypeNav,
  resolveNavPlanFromTeamOverview,
  shouldShowFinanceNavSection,
} from '../nav/financeNavVisibility'
import { CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from '../app/crmAppPaths'
import { api, getOnboardingStatus } from '../api/client'
import { useAuth } from '../store/useAuth'
import type { CandidatesListInsights } from '../modules/candidates/types'

function num(n: number | undefined | null): string {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return String(Math.max(0, Math.floor(Number(n))))
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function intersectsToday(row: CommunicationTimeOffRequest, dayIso: string): boolean {
  const status = String(row.status || '').toLowerCase()
  if (status !== 'approved') return false
  return String(row.start_date || '') <= dayIso && String(row.end_date || '') >= dayIso
}

async function fetchCandidatesInsightsWorkHub(): Promise<CandidatesListInsights | null> {
  try {
    const { data } = await api.get('/candidates', {
      params: { limit: 1, offset: 0, compact: true, include_insights: true },
    })
    const raw = (data as { insights?: unknown })?.insights
    if (!raw || typeof raw !== 'object') return null
    const o = raw as Record<string, unknown>
    return {
      total: Number(o.total) || 0,
      new_count: Number(o.new_count) || 0,
      docs_ready: Number(o.docs_ready) || 0,
      docs_attention: Number(o.docs_attention) || 0,
      docs_ordered: Number(o.docs_ordered) || 0,
      docs_incomplete: Number(o.docs_incomplete) || 0,
      ops_in_work: Number(o.ops_in_work) || 0,
    }
  } catch {
    return null
  }
}

const PATH_CANDIDATES_QV_DOCS = `${CRM_APP_PATHS.candidates}?qv=docs_incomplete`
const PATH_CANDIDATES_OPS_IN_WORK = `${CRM_APP_PATHS.candidates}?ops_mode=in_work`
const PATH_CANDIDATES_HANDOFF_RETURNED = `${CRM_APP_PATHS.candidates}?handoff_status=returned`

export default function WorkHubPage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const { can, isClientTenant } = usePermissions()
  const { allowsTeamFeatures, planLoading: planTierLoading } = useTeamTierFeatures()
  const { canUseCommunicationsFeature } = useCommunicationsAccess()
  const { teamOverview, canLoadTeamOverview } = useTeamOverviewNav()
  const pendingHandoffs = usePendingHandoffsCount()
  const [businessType, setBusinessType] = useState<BusinessTypeNav>('agency')
  const [ops, setOps] = useState<OpsCounters | null>(null)
  const [opsLoading, setOpsLoading] = useState(true)
  const [listInsights, setListInsights] = useState<CandidatesListInsights | null>(null)
  const [insightsLoading, setInsightsLoading] = useState(true)
  const [teamPulse, setTeamPulse] = useState<{
    available: number
    busy: number
    onTimeOffToday: number
    total: number
  } | null>(null)
  const [teamPulseLoading, setTeamPulseLoading] = useState(false)

  useEffect(() => {
    if (!me?.tenant_id) return
    let cancelled = false
    getOnboardingStatus()
      .then((r) => {
        if (!cancelled && r?.business_type) setBusinessType(r.business_type)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [me?.tenant_id])

  const resolvedNavPlan = resolveNavPlanFromTeamOverview(canLoadTeamOverview, teamOverview)
  const showFinance = shouldShowFinanceNavSection({
    isClientTenant,
    businessType,
    resolvedNavPlan,
  })

  const loadOps = useCallback(async () => {
    if (!can('candidates.view') && !can('leads.view')) {
      setOps(null)
      setOpsLoading(false)
      return
    }
    setOpsLoading(true)
    try {
      const data = await getOpsCounters()
      setOps(data)
    } catch {
      setOps(null)
    } finally {
      setOpsLoading(false)
    }
  }, [can])

  const loadInsights = useCallback(async () => {
    if (!can('candidates.view')) {
      setListInsights(null)
      setInsightsLoading(false)
      return
    }
    setInsightsLoading(true)
    try {
      const data = await fetchCandidatesInsightsWorkHub()
      setListInsights(data)
    } catch {
      setListInsights(null)
    } finally {
      setInsightsLoading(false)
    }
  }, [can])

  useEffect(() => {
    void loadOps()
  }, [loadOps])

  useEffect(() => {
    void loadInsights()
  }, [loadInsights])

  const showTeamNav =
    can('notifications.view') &&
    (canUseCommunicationsFeature('teamAvailability') ||
      canUseCommunicationsFeature('myAvailability') ||
      canUseCommunicationsFeature('timeOffRequests'))

  useEffect(() => {
    if (!showTeamNav || !me?.tenant_id) {
      setTeamPulse(null)
      return
    }
    let cancelled = false
    setTeamPulseLoading(true)
    ;(async () => {
      try {
        const [cfg, timeOffRes] = await Promise.all([
          getCommunicationsSettings(),
          listCommunicationTimeOffRequests({ limit: 200, status_filter: ['approved'] }).catch(() => ({
            items: [] as CommunicationTimeOffRequest[],
          })),
        ])
        if (cancelled) return
        const items = cfg.managerQueue?.items || []
        const approvedTimeOff = Array.isArray(timeOffRes.items) ? timeOffRes.items : []
        const today = todayIso()
        const activeTimeOffByUser = new Map<string, CommunicationTimeOffRequest[]>()
        for (const row of approvedTimeOff) {
          if (!intersectsToday(row, today)) continue
          const key = String(row.requester_user_id || '')
          if (!key) continue
          if (!activeTimeOffByUser.has(key)) activeTimeOffByUser.set(key, [])
          activeTimeOffByUser.get(key)!.push(row)
        }
        setTeamPulse({
          total: items.length,
          available: items.filter((x) => x?.enabled && x?.availability?.state === 'available').length,
          busy: items.filter((x) => x?.enabled && ['busy', 'meeting', 'break'].includes(String(x?.availability?.state || '')))
            .length,
          onTimeOffToday: items.filter((x) => activeTimeOffByUser.has(String(x?.managerId || ''))).length,
        })
      } catch {
        if (!cancelled) setTeamPulse(null)
      } finally {
        if (!cancelled) setTeamPulseLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [showTeamNav, me?.tenant_id])

  const showCandidates = can('candidates.view')
  const showCompanies = can('companies.view')
  const showLeads = can('leads.view')

  const sectionTitle = (key: string, fallback: string) => (
    <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t(key, { defaultValue: fallback })}</h2>
  )

  const attentionLoading = opsLoading || (showCandidates && insightsLoading)

  const attentionRows = useMemo(() => {
    const rows: Array<{ key: string; to: string; count: string; title: string; action: string; tone: 'rose' | 'amber' | 'sky' }> = []
    if (showCandidates) {
      rows.push({
        key: 'nna',
        to: CRM_APP_DRILLDOWN_HREFS.candidatesQueueNoNextAction,
        count: num(ops?.no_next_action_candidates),
        title: t('app.work.hub.attention_candidates_no_next', {
          defaultValue: 'Candidates without a next step',
        }),
        action: t('app.work.hub.action_start_processing', { defaultValue: 'Start processing' }),
        tone: 'rose',
      })
    }
    if (can('notifications.view')) {
      rows.push({
        key: 'tasks',
        to: CRM_APP_DRILLDOWN_HREFS.tasksOverdueReminders,
        count: num(ops?.overdue_reminders),
        title: t('app.work.hub.attention_overdue_tasks', { defaultValue: 'Overdue tasks' }),
        action: t('app.work.hub.action_fix_tasks', { defaultValue: 'Fix now' }),
        tone: 'amber',
      })
    }
    if (showLeads) {
      rows.push({
        key: 'leads',
        to: CRM_APP_DRILLDOWN_HREFS.leadsNeedsRouting,
        count: num(ops?.leads_needs_routing),
        title: t('app.work.hub.attention_leads_routing', { defaultValue: 'New leads to triage' }),
        action: t('app.work.hub.action_triage_leads', { defaultValue: 'Triage' }),
        tone: 'sky',
      })
    }
    return rows
  }, [can, ops, showCandidates, showLeads, t])

  const toneBorder = {
    rose: 'border-rose-200 hover:border-rose-300 focus-visible:ring-rose-400',
    amber: 'border-amber-200 hover:border-amber-300 focus-visible:ring-amber-400',
    sky: 'border-sky-200 hover:border-sky-300 focus-visible:ring-sky-400',
  } as const

  const actionCardClass =
    'group flex w-full items-center justify-between gap-4 rounded-2xl border-2 bg-white px-4 py-4 text-left shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2'

  return (
    <div className="mx-auto w-full max-w-4xl space-y-10 py-6 sm:py-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          {t('app.work.hub.operational_title', { defaultValue: 'Work' })}
        </h1>
      </header>

      {!planTierLoading && !allowsTeamFeatures && can('settings.view') && (showCandidates || showLeads) ? (
        <div className="flex flex-wrap items-start gap-3 rounded-xl border border-indigo-200 bg-indigo-50/90 px-4 py-3 text-sm text-indigo-950 shadow-sm">
          <IconLock size={20} className="mt-0.5 shrink-0 text-indigo-600" aria-hidden />
          <div className="min-w-0 flex-1 space-y-1">
            <p className="font-semibold">
              {t('app.work.hub.plan_upgrade_strip_title', { defaultValue: 'Unlock team automation' })}
            </p>
            <p className="text-xs text-indigo-900/90">
              {t('app.work.hub.plan_upgrade_strip_body', {
                defaultValue:
                  'Bulk Meta lead processing, funnel insight actions, and several automations require a Team-tier plan. Solo/Starter still works for day-to-day lists and manual steps.',
              })}
            </p>
            <Link
              to={CRM_APP_PATHS.settingsBilling}
              className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-800 underline decoration-indigo-400 underline-offset-2 hover:text-indigo-950"
            >
              {t('app.work.hub.plan_upgrade_strip_cta', { defaultValue: 'Open billing' })}
              <IconArrowRight size={14} stroke={2} aria-hidden />
            </Link>
          </div>
        </div>
      ) : null}

      {(showCandidates || showLeads || can('notifications.view')) && (
        <section className="space-y-4">
          <div className="flex items-center gap-2">
            <IconFlame size={18} className="text-rose-500" aria-hidden />
            {sectionTitle('app.work.hub.block_attention', 'Needs attention')}
          </div>
          {attentionLoading ? (
            <p className="text-sm text-slate-500">{t('common.loading')}</p>
          ) : attentionRows.length === 0 ? null : (
            <ul className="grid gap-3 sm:grid-cols-1">
              {attentionRows.map((row) => (
                <li key={row.key}>
                  <Link
                    to={row.to}
                    className={`${actionCardClass} ${toneBorder[row.tone]}`}
                  >
                    <div className="min-w-0">
                      <p className="text-3xl font-bold tabular-nums text-slate-900">{row.count}</p>
                      <p className="mt-1 text-sm font-medium text-slate-700">{row.title}</p>
                    </div>
                    <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white group-hover:bg-slate-800">
                      {row.action}
                      <IconArrowRight size={18} stroke={2} aria-hidden />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {showCandidates && (
        <section className="space-y-3">
          {sectionTitle('app.work.hub.block_queue', 'Work queue')}
          <div className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <Link
              to={CRM_APP_DRILLDOWN_HREFS.candidatesQueueNoNextAction}
              className="flex items-center justify-between gap-3 px-4 py-3.5 text-sm transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
            >
              <span className="font-medium text-slate-800">
                {t('app.work.hub.queue_no_next', { defaultValue: 'No next step' })}
              </span>
              <span className="tabular-nums font-semibold text-slate-900">{num(ops?.no_next_action_candidates)}</span>
            </Link>
            <Link
              to={PATH_CANDIDATES_QV_DOCS}
              className="flex items-center justify-between gap-3 px-4 py-3.5 text-sm transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
            >
              <span className="font-medium text-slate-800">
                {t('app.work.hub.queue_docs_incomplete', { defaultValue: 'Awaiting documents' })}
              </span>
              <span className="tabular-nums font-semibold text-slate-900">
                {insightsLoading ? '…' : num(listInsights?.docs_incomplete)}
              </span>
            </Link>
            <Link
              to={PATH_CANDIDATES_OPS_IN_WORK}
              className="flex items-center justify-between gap-3 px-4 py-3.5 text-sm transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
            >
              <span className="font-medium text-slate-800">
                {t('app.work.hub.queue_waiting_reply', { defaultValue: 'Waiting for a reply' })}
              </span>
              <span className="tabular-nums font-semibold text-slate-900">
                {insightsLoading ? '…' : num(listInsights?.ops_in_work)}
              </span>
            </Link>
          </div>
        </section>
      )}

      {showCompanies && (
        <section className="space-y-3">
          {sectionTitle('app.work.hub.block_processing', 'Client processing')}
          <div className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <Link
              to={`${CRM_APP_PATHS.procesowani}?tab=do-procesowania`}
              className="flex items-center justify-between gap-3 px-4 py-3.5 text-sm transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
            >
              <span className="font-medium text-slate-800">
                {t('app.work.hub.processing_needs_decision', { defaultValue: 'Needs your decision' })}
              </span>
              <span className="inline-flex min-w-[2rem] justify-center tabular-nums font-semibold text-slate-900">
                {pendingHandoffs > 0 ? (
                  <span className="rounded-full bg-rose-500 px-2 py-0.5 text-xs text-white">{pendingHandoffs > 99 ? '99+' : pendingHandoffs}</span>
                ) : (
                  '0'
                )}
              </span>
            </Link>
            <Link
              to={`${CRM_APP_PATHS.procesowani}?tab=w-procesie`}
              className="flex items-center justify-between gap-3 px-4 py-3.5 text-sm transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
            >
              <span className="font-medium text-slate-800">
                {t('app.work.hub.processing_client_review', { defaultValue: 'Under client review' })}
              </span>
              <span className="text-slate-400" aria-hidden>
                <IconArrowRight size={18} />
              </span>
            </Link>
            <Link
              to={PATH_CANDIDATES_HANDOFF_RETURNED}
              className="flex items-center justify-between gap-3 px-4 py-3.5 text-sm transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
            >
              <span className="font-medium text-slate-800">
                {t('app.work.hub.processing_returned', { defaultValue: 'Returned from client' })}
              </span>
              <span className="text-slate-400" aria-hidden>
                <IconArrowRight size={18} />
              </span>
            </Link>
          </div>
        </section>
      )}

      {showTeamNav && (
        <section className="space-y-3">
          {sectionTitle('app.work.hub.block_team', 'Team')}
          {teamPulseLoading ? (
            <p className="text-sm text-slate-500">{t('common.loading')}</p>
          ) : teamPulse && teamPulse.total > 0 ? (
            <div className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-3">
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  {t('app.work.hub.team_busy', { defaultValue: 'Busy now: {count}', values: { count: teamPulse.busy } })}
                </div>
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
                  {t('app.work.hub.team_timeoff', {
                    defaultValue: 'Time-off today: {count}',
                    values: { count: teamPulse.onTimeOffToday },
                  })}
                </div>
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
                  {t('app.work.hub.team_available', {
                    defaultValue: 'Available: {count}',
                    values: { count: teamPulse.available },
                  })}
                </div>
              </div>
              <Link
                to={CRM_APP_PATHS.teamAvailability}
                className={`${actionCardClass} border-slate-200 hover:border-brand-300 focus-visible:ring-brand-500`}
              >
                <span className="text-sm font-semibold text-slate-800">
                  {t('app.work.hub.team_open', { defaultValue: 'Open team view' })}
                </span>
                <IconArrowRight size={20} className="text-slate-500" aria-hidden />
              </Link>
            </div>
          ) : (
            <Link
              to={CRM_APP_PATHS.teamAvailability}
              className={`${actionCardClass} border-slate-200 hover:border-brand-300 focus-visible:ring-brand-500`}
            >
              <span className="text-sm font-semibold text-slate-800">
                {t('app.work.hub.team_open', { defaultValue: 'Open team view' })}
              </span>
              <IconArrowRight size={20} className="text-slate-500" aria-hidden />
            </Link>
          )}
        </section>
      )}

      <section className="space-y-3">
        {sectionTitle('app.work.hub.block_quick', 'Quick actions')}
        <div className="flex flex-wrap gap-2">
          {showCandidates ? (
            <Link
              className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700"
              to={CRM_APP_PATHS.candidateNew}
            >
              {t('app.work.hub.action_new_candidate', { defaultValue: 'New candidate' })}
            </Link>
          ) : null}
          {can('notifications.view') ? (
            <Link
              className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:bg-slate-50"
              to={CRM_APP_PATHS.tasks}
            >
              {t('app.work.hub.action_create_task', { defaultValue: 'Add task' })}
            </Link>
          ) : null}
          {canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email') ? (
            <Link
              className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:bg-slate-50"
              to={CRM_APP_PATHS.inbox}
            >
              {t('app.work.hub.action_inbox', { defaultValue: 'Open inbox' })}
            </Link>
          ) : null}
          {showFinance && can('services.view') ? (
            <Link
              className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:bg-slate-50"
              to={CRM_APP_PATHS.orders}
            >
              {t('app.nav.items.orders')}
            </Link>
          ) : null}
        </div>
      </section>
    </div>
  )
}
