import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowRight } from '@tabler/icons-react'

import { getOpsCounters, type OpsCounters } from '../api/analytics'
import { api } from '../api/client'
import { CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from '../app/crmAppPaths'
import type { CandidatesListInsights } from '../modules/candidates/types'
import { HandoffQueuePanel } from '../modules/workHub/HandoffQueuePanel'
import { MyTasksPanel } from '../modules/workHub/MyTasksPanel'
import { TodayPlannerPanel } from '../modules/workHub/TodayPlannerPanel'
import { ManagerLoadPanel } from '../modules/workHub/ManagerLoadPanel'
import { RiskDigestPanel } from '../modules/workHub/RiskDigestPanel'
import { useWorkHubProfile } from '../modules/workHub/useWorkHubProfile'
import type { WorkHubSection } from '../modules/workHub/profile'
import { usePermissions } from '../hooks/usePermissions'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'

function num(n: number | undefined | null): string {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return String(Math.max(0, Math.floor(Number(n))))
}

const HREF_CANDIDATES_ACTION = `${CRM_APP_PATHS.candidates}?filter=action_required`
const HREF_CANDIDATES_NEW = `${CRM_APP_PATHS.candidates}?stages=new,no_answer`
const HREF_CANDIDATES_DOCS = `${CRM_APP_PATHS.candidates}?stage=waiting_documents`
const HREF_CANDIDATES_INTERVIEW = `${CRM_APP_PATHS.candidates}?stages=contacted,questionnaire_submitted`
const HREF_CANDIDATES_UNASSIGNED = `${CRM_APP_PATHS.candidates}?recruiter_unassigned=true`
const HREF_CANDIDATES_OPS = `${CRM_APP_PATHS.candidates}?ops_mode=in_work`
const HREF_LEADS_STALE = `${CRM_APP_PATHS.leads}?filter=no_first_contact_24h`
const HREF_TASKS_OVERDUE = `${CRM_APP_PATHS.tasks}?tab=tasks&filter=overdue`
const HREF_TASKS_UNLINKED = `${CRM_APP_PATHS.tasks}?tab=tasks&t_layout=by_candidate&t_unlinked=1`

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
      bottleneck_no_contact: Number(o.bottleneck_no_contact) || 0,
      bottleneck_docs_wait: Number(o.bottleneck_docs_wait) || 0,
      bottleneck_interview_pending: Number(o.bottleneck_interview_pending) || 0,
      created_today: Number(o.created_today) || 0,
      stale_no_contact_24h: Number(o.stale_no_contact_24h) || 0,
      oldest_lead_days: o.oldest_lead_days != null ? Number(o.oldest_lead_days) : undefined,
      unassigned_recruiter: Number(o.unassigned_recruiter) || 0,
    }
  } catch {
    return null
  }
}

type Tone = 'rose' | 'amber' | 'slate'

type ActionRow = {
  key: string
  count: number
  titleKey: string
  titleDefault: string
  hintKey?: string
  hintDefault?: string
  href: string
  tone: Tone
}

export default function WorkHubPage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const { can } = usePermissions()
  const profile = useWorkHubProfile()
  const [ops, setOps] = useState<OpsCounters | null>(null)
  const [opsLoading, setOpsLoading] = useState(true)
  const [listInsights, setListInsights] = useState<CandidatesListInsights | null>(null)
  const [insightsLoading, setInsightsLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)

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
      setLoadError(false)
    } catch {
      setOps(null)
      setLoadError(true)
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
      setLoadError(false)
    } catch {
      setListInsights(null)
      setLoadError(true)
    } finally {
      setInsightsLoading(false)
    }
  }, [can])

  const reload = useCallback(() => {
    setLoadError(false)
    void loadOps()
    void loadInsights()
  }, [loadOps, loadInsights])

  useEffect(() => {
    void loadOps()
  }, [loadOps])

  useEffect(() => {
    void loadInsights()
  }, [loadInsights])

  const showCandidates = can('candidates.view')
  const showLeads = can('leads.view')
  const showTasks = can('notifications.view')
  const showRiskDigest = useMemo(() => {
    const r = String((me as { role?: string })?.role ?? '').toLowerCase()
    return r === 'superadmin' || r === 'administrator' || r === 'supervisor'
  }, [(me as { role?: string })?.role])
  const dataLoading = opsLoading || (showCandidates && insightsLoading)

  const bottleneckSum = useMemo(() => {
    if (!listInsights) return 0
    return (
      (listInsights.bottleneck_no_contact ?? 0) +
      (listInsights.bottleneck_docs_wait ?? 0) +
      (listInsights.bottleneck_interview_pending ?? 0) +
      (listInsights.ops_in_work ?? 0)
    )
  }, [listInsights])

  const heroNeedCount = useMemo(() => {
    const nna = ops?.no_next_action_candidates ?? 0
    return Math.max(nna, bottleneckSum)
  }, [ops?.no_next_action_candidates, bottleneckSum])

  const bottlenecks = useMemo((): ActionRow[] => {
    if (!listInsights) return []
    const rows: ActionRow[] = [
      {
        key: 'docs',
        count: listInsights.bottleneck_docs_wait ?? 0,
        titleKey: 'app.work.hub.bn_docs_wait',
        titleDefault: 'Waiting for documents',
        hintKey: 'app.work.hub.bn_docs_hint',
        hintDefault: 'Open list filtered by document stage',
        href: HREF_CANDIDATES_DOCS,
        tone: 'amber',
      },
      {
        key: 'contact',
        count: listInsights.bottleneck_no_contact ?? 0,
        titleKey: 'app.work.hub.bn_no_contact',
        titleDefault: 'No first contact yet',
        href: HREF_CANDIDATES_NEW,
        tone: 'amber',
      },
      {
        key: 'interview',
        count: listInsights.bottleneck_interview_pending ?? 0,
        titleKey: 'app.work.hub.bn_interview',
        titleDefault: 'Interview not scheduled',
        href: HREF_CANDIDATES_INTERVIEW,
        tone: 'amber',
      },
      {
        key: 'reply',
        count: listInsights.ops_in_work ?? 0,
        titleKey: 'app.work.hub.bn_waiting_reply',
        titleDefault: 'Waiting for a reply',
        href: HREF_CANDIDATES_OPS,
        tone: 'slate',
      },
    ]
    return rows.filter((r) => r.count > 0).sort((a, b) => b.count - a.count).slice(0, 5)
  }, [listInsights])

  const topBottleneck = bottlenecks[0]

  const criticalRows = useMemo((): ActionRow[] => {
    const rows: ActionRow[] = []
    if (showLeads && (ops?.leads_new_untouched_24h ?? 0) > 0) {
      rows.push({
        key: 'leads_stale',
        count: ops!.leads_new_untouched_24h!,
        titleKey: 'app.work.hub.crit_leads_stale',
        titleDefault: 'Leads with no first touch for over 24 hours',
        href: HREF_LEADS_STALE,
        tone: 'rose',
      })
    }
    if (showTasks && (ops?.overdue_reminders ?? 0) > 0) {
      rows.push({
        key: 'tasks_od',
        count: ops!.overdue_reminders!,
        titleKey: 'app.work.hub.crit_tasks_overdue',
        titleDefault: 'Overdue tasks',
        href: HREF_TASKS_OVERDUE,
        tone: 'rose',
      })
    }
    if (showTasks && (ops?.unlinked_tasks ?? 0) > 0) {
      rows.push({
        key: 'tasks_unlinked',
        count: ops!.unlinked_tasks!,
        titleKey: 'app.work.hub.crit_tasks_unlinked',
        titleDefault: 'Tasks without entity link',
        href: HREF_TASKS_UNLINKED,
        tone: 'amber',
      })
    }
    if (showCandidates && (ops?.no_next_action_candidates ?? 0) > 0) {
      rows.push({
        key: 'nna',
        count: ops!.no_next_action_candidates!,
        titleKey: 'app.work.hub.crit_no_next',
        titleDefault: 'Candidates without a next step',
        href: HREF_CANDIDATES_ACTION,
        tone: 'amber',
      })
    }
    if (showCandidates && (listInsights?.unassigned_recruiter ?? 0) > 0) {
      rows.push({
        key: 'unass',
        count: listInsights!.unassigned_recruiter!,
        titleKey: 'app.work.hub.crit_unassigned',
        titleDefault: 'Candidates without an assigned recruiter',
        href: HREF_CANDIDATES_UNASSIGNED,
        tone: 'amber',
      })
    }
    if (showLeads && (ops?.leads_needs_routing ?? 0) > 0) {
      rows.push({
        key: 'route',
        count: ops!.leads_needs_routing!,
        titleKey: 'app.work.hub.crit_leads_route',
        titleDefault: 'New leads awaiting triage',
        href: CRM_APP_DRILLDOWN_HREFS.leadsNeedsRouting,
        tone: 'slate',
      })
    }
    return rows.slice(0, 5)
  }, [showCandidates, showLeads, showTasks, ops, listInsights])

  const hasProblems = useMemo(() => {
    if (criticalRows.length > 0) return true
    if (bottlenecks.length > 0) return true
    if (heroNeedCount > 0) return true
    return false
  }, [criticalRows.length, bottlenecks.length, heroNeedCount])

  const calm = !dataLoading && !loadError && !hasProblems

  const heroSubtitle = useMemo(() => {
    if (!listInsights || dataLoading) return null
    if (topBottleneck) {
      return t('app.work.hub.hero_sub_most_stuck', {
        defaultValue: 'Largest backlog: {stage}',
        values: { stage: t(topBottleneck.titleKey, { defaultValue: topBottleneck.titleDefault }) },
      })
    }
    const od = listInsights.oldest_lead_days
    if (od != null && od >= 1) {
      return t('app.work.hub.hero_sub_oldest', {
        defaultValue: 'Longest wait in early pipeline: {days} days',
        values: { days: od },
      })
    }
    return null
  }, [listInsights, dataLoading, topBottleneck, t])

  const toneBar: Record<Tone, string> = {
    rose: 'bg-rose-500',
    amber: 'bg-amber-500',
    slate: 'bg-slate-400',
  }

  const Skeleton = () => (
    <div className="space-y-6" aria-busy="true">
      <div className="h-10 w-48 animate-pulse rounded-lg bg-slate-200" />
      <div className="h-40 animate-pulse rounded-2xl border border-slate-200 bg-white" />
      <div className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white" />
    </div>
  )

  // Hero copy varies by role profile. Counter and CTA logic stay shared so we
  // don't fork data flow per role — only the framing changes.
  const calmHeroCopy = (() => {
    switch (profile.hero.variant) {
      case 'calm_team':
        return {
          title: t('app.work.profile.calm_team.title', { defaultValue: 'Team is on track' }),
          body: t('app.work.profile.calm_team.body', {
            defaultValue: 'No overdue work for the team right now.',
          }),
        }
      case 'calm_solo':
        return {
          title: t('app.work.profile.calm_solo.title', { defaultValue: 'All quiet' }),
          body: t('app.work.profile.calm_solo.body', {
            defaultValue: 'Nothing demands your attention — a good time to plan ahead.',
          }),
        }
      case 'calm_client':
        return {
          title: t('app.work.profile.calm_client.title', { defaultValue: 'Inbox is empty' }),
          body: t('app.work.profile.calm_client.body', {
            defaultValue: 'No handoffs from the agency need a decision right now.',
          }),
        }
      case 'viewer':
        return {
          title: t('app.work.profile.viewer.title', { defaultValue: 'Browse-only access' }),
          body: t('app.work.profile.viewer.body_short', {
            defaultValue: 'Use the menu to browse data. You cannot make changes here.',
          }),
        }
      case 'calm_personal':
      default:
        return {
          title: t('app.work.hub.hero_all_ok', { defaultValue: 'Everything is under control' }),
          body: t('app.work.hub.hero_calm_body', {
            defaultValue: 'No candidates are waiting on your action right now',
          }),
        }
    }
  })()

  const renderHero = () => (
    <section
      key="hero"
      className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm sm:p-8"
    >
      <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 space-y-3 lg:max-w-[70%]">
          {calm ? (
            <>
              <p className="text-xl font-bold text-slate-900 sm:text-2xl">{calmHeroCopy.title}</p>
              <p className="text-[15px] text-slate-600">{calmHeroCopy.body}</p>
              <p className="text-[15px] text-slate-500">
                {t('app.work.hub.hero_new_today', {
                  defaultValue: 'New leads today: {count}',
                  values: { count: num(listInsights?.created_today ?? 0) },
                })}
              </p>
            </>
          ) : (
            <>
              <p className="text-[3.25rem] font-bold leading-none tracking-tight text-slate-900 tabular-nums">
                {num(heroNeedCount)}
              </p>
              <p className="text-xl font-bold text-slate-900 sm:text-2xl">
                {t(profile.hero.needHeadlineKey, {
                  defaultValue: profile.hero.needHeadlineDefault,
                })}
              </p>
              {heroSubtitle ? <p className="text-[15px] text-slate-600">{heroSubtitle}</p> : null}
            </>
          )}
        </div>
        <div className="flex shrink-0 flex-col gap-3 sm:flex-row lg:flex-col lg:items-end">
          <Link
            to={HREF_CANDIDATES_ACTION}
            className="inline-flex h-12 min-w-[11rem] items-center justify-center rounded-xl bg-brand-600 px-5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
          >
            {t('app.work.hub.cta_open_candidates', { defaultValue: 'Open candidates' })}
          </Link>
          {calm ? (
            <Link
              to={CRM_APP_PATHS.candidateNew}
              className="inline-flex h-12 min-w-[11rem] items-center justify-center rounded-xl border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
            >
              {t('app.work.hub.cta_create_candidate', { defaultValue: 'Create candidate' })}
            </Link>
          ) : (
            <>
              {showLeads && ((ops?.leads_needs_routing ?? 0) > 0 || (ops?.leads_new_untouched_24h ?? 0) > 0) ? (
                <Link
                  to={
                    (ops?.leads_needs_routing ?? 0) > 0
                      ? CRM_APP_DRILLDOWN_HREFS.leadsNeedsRouting
                      : HREF_LEADS_STALE
                  }
                  className="inline-flex h-12 min-w-[11rem] items-center justify-center rounded-xl border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
                >
                  {t('app.work.hub.cta_open_leads', { defaultValue: 'Open leads' })}
                  <IconArrowRight size={18} className="ml-1 opacity-60" aria-hidden />
                </Link>
              ) : null}
              {showTasks && (ops?.overdue_reminders ?? 0) > 0 ? (
                <Link
                  to={HREF_TASKS_OVERDUE}
                  className="inline-flex h-12 min-w-[11rem] items-center justify-center rounded-xl border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
                >
                  {t('app.work.hub.cta_open_tasks', { defaultValue: 'Open tasks' })}
                  <IconArrowRight size={18} className="ml-1 opacity-60" aria-hidden />
                </Link>
              ) : null}
            </>
          )}
        </div>
      </div>
    </section>
  )

  const renderCritical = () => (
    <section
      key="critical"
      className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
    >
      <div className="border-b border-slate-100 px-6 py-4">
        <h2 className="text-base font-bold text-slate-900">
          {t('app.work.hub.block_critical', { defaultValue: 'Needs attention' })}
        </h2>
      </div>
      <ul>
        {criticalRows.map((row) => (
          <li key={row.key} className="group border-b border-slate-100 last:border-b-0">
            <Link to={row.href} className="flex items-stretch gap-0 transition hover:bg-slate-50/90">
              <div className={`w-1 shrink-0 ${toneBar[row.tone]}`} aria-hidden />
              <div className="flex min-w-0 flex-1 items-center justify-between gap-4 px-5 py-4">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900">
                    <span className="tabular-nums">{num(row.count)}</span>{' '}
                    {t(row.titleKey, { defaultValue: row.titleDefault })}
                  </p>
                  {row.hintKey ? (
                    <p className="mt-0.5 text-xs text-slate-500">
                      {t(row.hintKey, { defaultValue: row.hintDefault || '' })}
                    </p>
                  ) : null}
                </div>
                <span className="shrink-0 text-sm font-semibold text-brand-700 group-hover:text-brand-800">
                  {t('app.work.hub.row_open', { defaultValue: 'Open' })}
                  <IconArrowRight size={16} className="ml-1 inline align-text-bottom opacity-70" aria-hidden />
                </span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )

  const renderBottlenecks = () => (
    <section
      key="bottlenecks"
      className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
    >
      <div className="border-b border-slate-100 px-6 py-4">
        <h2 className="text-base font-bold text-slate-900">
          {t('app.work.hub.block_bottlenecks', { defaultValue: 'Bottlenecks' })}
        </h2>
      </div>
      <ul>
        {bottlenecks.map((row) => (
          <li key={row.key} className="border-b border-slate-100 last:border-b-0">
            <Link
              to={row.href}
              className="group flex items-stretch gap-0 transition hover:bg-slate-50/90"
            >
              <div className={`w-1 shrink-0 ${toneBar[row.tone]}`} aria-hidden />
              <div className="flex min-w-0 flex-1 items-center justify-between gap-4 px-5 py-3.5">
                <span className="truncate text-sm font-medium text-slate-800">
                  {t(row.titleKey, { defaultValue: row.titleDefault })}
                </span>
                <span className="tabular-nums text-sm font-bold text-slate-900">{num(row.count)}</span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )

  const renderQuickActions = (): JSX.Element | null => null

  // Sections are rendered in the order defined by the active role profile.
  // Each section may be skipped (returns null) if the underlying data isn't
  // visible to this user — section order is the layout, not the visibility.
  const renderSection = (section: WorkHubSection): JSX.Element | null => {
    switch (section) {
      case 'hero':
        return showCandidates ? renderHero() : null
      case 'critical':
        return !calm && criticalRows.length > 0 ? renderCritical() : null
      case 'bottlenecks':
        return profile.showBottlenecks && !calm && bottlenecks.length > 0
          ? renderBottlenecks()
          : null
      case 'handoffQueue':
        return profile.showHandoffQueue ? <HandoffQueuePanel key="handoffQueue" /> : null
      case 'myTasks':
        // Panel fetches `assignee_scope=mine` — gate on the caller's
        // notification permission (same as the `tasks` drilldown in the
        // critical block). Without `notifications.view` the backend
        // would 403 on every fetch; rendering an error card feels worse
        // than silently skipping the section.
        return showTasks ? <MyTasksPanel key="myTasks" /> : null
      case 'todayPlanner':
        // Planner events live behind the same `notifications.view`
        // permission gate as reminders (see `/api/v1/communications/
        // planner/events` ACL). Gating on `showTasks` keeps behaviour
        // symmetric with MyTasksPanel and avoids a guaranteed 403 for
        // viewer-like roles that land on a non-viewer profile.
        return showTasks ? <TodayPlannerPanel key="todayPlanner" /> : null
      case 'riskDigest':
        // Same role gate as Dashboard risk / SLA digest (`canViewRiskOpsUi`).
        // Panel uses Work Hub `ops` snapshot + manager digest queue API.
        return showRiskDigest ? <RiskDigestPanel key="riskDigest" ops={ops} /> : null
      case 'managerLoad':
        // G-6 Stage 2c — team load distribution. Panel fetches
        // `/analytics/by-manager`, which already requires a visibility
        // scope that admin/supervisor have by virtue of being on an
        // `admin_team` / `supervisor` profile (see `resolveWorkHubProfile`).
        // Gate on `candidates.view` as a defensive alignment with the
        // drill-down target (`/app/candidates?recruiter_id=…`) so a role
        // without list access never sees the panel it can't action.
        return showCandidates ? <ManagerLoadPanel key="managerLoad" /> : null
      case 'quickActions':
        return renderQuickActions()
      case 'viewerSummary':
        // Viewer profile has no actionable data; rely on critical block below it
        // and show a one-line read-only note so the screen isn't empty.
        return (
          <section
            key="viewerSummary"
            className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm"
          >
            {t('app.work.profile.viewer.body', {
              defaultValue:
                'Read-only access. Open candidates, leads or vacancies from the side menu to browse data.',
            })}
          </section>
        )
      default:
        return null
    }
  }

  return (
    <div className="min-h-[calc(100vh-5rem)] bg-slate-50">
      <div className="mx-auto max-w-[1200px] space-y-6 px-8 py-10">
        <header className="space-y-1 pb-2">
          <h1 className="text-[2.25rem] font-bold leading-tight tracking-tight text-slate-900">
            {t('app.work.hub.operational_title', { defaultValue: 'Work' })}
          </h1>
          <p className="text-[15px] text-slate-500">
            {t('app.work.hub.page_kicker', { defaultValue: 'Everything that needs attention right now' })}
          </p>
        </header>

        {loadError && !dataLoading ? (
          <div className="rounded-2xl border border-rose-200 bg-white px-6 py-5 text-sm text-rose-950 shadow-sm">
            <p className="font-medium">{t('app.work.hub.load_error', { defaultValue: 'Could not load the work panel' })}</p>
            <button
              type="button"
              className="mt-3 inline-flex h-11 items-center rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800"
              onClick={() => reload()}
            >
              {t('app.work.hub.reload', { defaultValue: 'Refresh' })}
            </button>
          </div>
        ) : null}

        {dataLoading ? (
          <Skeleton />
        ) : (
          <>
            {profile.sections.map((section) => {
              const node = renderSection(section)
              return node ? <Fragment key={section}>{node}</Fragment> : null
            })}
          </>
        )}
      </div>
    </div>
  )
}
