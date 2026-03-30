import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import LeadConversionFunnelPanel from '../components/leads/LeadConversionFunnelPanel'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { leadsNextActionHref } from '../api/nextActions'
import {
  fetchLeadConversionFunnel,
  type LeadConversionFunnelResponse,
  type LeadConversionFunnelSliceQuery,
} from '../api/leadConversionFunnel'
import { fetchLeadNextActions, type LeadNextActionsResponse } from '../api/nextActions'
import type { LeadStage } from '../api/types'
import { useI18n } from '../i18n'
import { useToast } from '../components/Toast'
import { computeFunnelSuggestedInsights } from '../utils/funnelSuggestedInsights'

const STAGE_FILTERS: Array<'' | LeadStage> = ['', 'new', 'contacted', 'qualified', 'converted', 'lost']

/** Preset drill-downs for common lost-reason follow-up (§2.12 management loop). */
const LOST_REASON_LEAD_PRESETS = ['no_response', 'not_qualified', 'budget'] as const

const PRIOR_STAGE_LOST_COMBOS = [
  { lost_from_crm_stage: 'qualified' as const, lost_reason_code: 'no_response' as const },
  { lost_from_crm_stage: 'qualified' as const, lost_reason_code: 'not_qualified' as const },
  { lost_from_crm_stage: 'contacted' as const, lost_reason_code: 'no_response' as const },
] as const

type CohortMode = 'all' | 'rolling7' | 'rolling7_wow'

function formatCohortBound(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString()
}

export default function AnalyticsLeadConversionFunnelPage({ embedded = false }: { embedded?: boolean } = {}) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [leadNba, setLeadNba] = useState<LeadNextActionsResponse | null>(null)
  const [funnelData, setFunnelData] = useState<LeadConversionFunnelResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [cohortMode, setCohortMode] = useState<CohortMode>('all')
  const [funnelSliceDraft, setFunnelSliceDraft] = useState({
    source: '',
    vacancyId: '',
    funnelId: '',
    assigneeUserId: '',
  })
  const [funnelSliceQuery, setFunnelSliceQuery] = useState<LeadConversionFunnelSliceQuery>({})

  const applyFunnelSlices = useCallback(() => {
    const next: LeadConversionFunnelSliceQuery = {}
    if (funnelSliceDraft.source.trim()) next.source = funnelSliceDraft.source.trim()
    if (funnelSliceDraft.vacancyId.trim()) next.vacancyId = funnelSliceDraft.vacancyId.trim()
    if (funnelSliceDraft.funnelId.trim()) next.funnelId = funnelSliceDraft.funnelId.trim()
    if (funnelSliceDraft.assigneeUserId.trim()) next.assigneeUserId = funnelSliceDraft.assigneeUserId.trim()
    setFunnelSliceQuery(next)
  }, [funnelSliceDraft])

  const clearFunnelSlices = useCallback(() => {
    setFunnelSliceDraft({ source: '', vacancyId: '', funnelId: '', assigneeUserId: '' })
    setFunnelSliceQuery({})
  }, [])

  const buildFunnelRequest = useCallback((): LeadConversionFunnelSliceQuery | null => {
    const hasSlices = Boolean(
      funnelSliceQuery.source?.trim() ||
        funnelSliceQuery.vacancyId?.trim() ||
        funnelSliceQuery.funnelId?.trim() ||
        funnelSliceQuery.assigneeUserId?.trim(),
    )
    const cohortOn = cohortMode !== 'all'
    if (!hasSlices && !cohortOn) return null
    const next: LeadConversionFunnelSliceQuery = { ...funnelSliceQuery }
    if (cohortOn) {
      next.cohortWindowDays = 7
      next.cohortComparePrior = cohortMode === 'rolling7_wow'
    }
    return next
  }, [cohortMode, funnelSliceQuery])

  const refresh = useCallback(() => {
    setLoading(true)
    void fetchLeadNextActions()
      .then((r) => setLeadNba(r))
      .catch(() => setLeadNba(null))
    const payload = buildFunnelRequest()
    void fetchLeadConversionFunnel(payload)
      .then((r) => setFunnelData(r))
      .catch((err: unknown) => {
        const detail = (err as { response?: { data?: { detail?: { code?: string } } } })?.response?.data?.detail
        if (detail && typeof detail === 'object' && detail.code === 'plan_requires_team') {
          setCohortMode('all')
          notify({
            title: t('app.leads.conversion_funnel.slices_team_required_title'),
            description: t('app.leads.conversion_funnel.slices_team_required_desc'),
            variant: 'error',
          })
        }
        setFunnelData(null)
      })
      .finally(() => setLoading(false))
  }, [buildFunnelRequest, notify, t])

  useEffect(() => {
    refresh()
  }, [refresh])

  const stageLabels = useMemo(() => {
    const map: Record<string, string> = {}
    STAGE_FILTERS.forEach((value) => {
      if (!value) return
      map[value] = t(`app.leads.stages.${value}`)
    })
    ;(['lead', 'qualified', 'active', 'final'] as const).forEach((value) => {
      map[value] = t(`app.leads.conversion_funnel.roots.${value}`)
    })
    return map
  }, [t])

  const funnelSuggested = useMemo(() => computeFunnelSuggestedInsights(funnelData), [funnelData])

  const shellClass = embedded ? 'w-full' : 'w-full max-w-6xl px-4 py-6 sm:px-6'

  return (
    <div className={shellClass}>
      {!embedded ? (
        <>
          <h1 className="text-xl font-semibold text-slate-900">{t('app.analytics.lead_conversion.title')}</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">{t('app.analytics.lead_conversion.subtitle')}</p>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            <Link
              to={CRM_APP_PATHS.settingsFunnels}
              className="font-medium text-brand-700 hover:text-brand-800 hover:underline"
            >
              {t('app.analytics.lead_conversion.configure_funnels')}
            </Link>
            {' · '}
            <Link to={CRM_APP_PATHS.leads} className="font-medium text-brand-700 hover:text-brand-800 hover:underline">
              {t('app.analytics.lead_conversion.open_leads_workspace')}
            </Link>
          </p>
        </>
      ) : (
        <p className="mb-4 max-w-3xl text-xs text-slate-600">
          <Link
            to={CRM_APP_PATHS.settingsFunnels}
            className="font-medium text-brand-700 hover:text-brand-800 hover:underline"
          >
            {t('app.analytics.lead_conversion.configure_funnels')}
          </Link>
          {' · '}
          <Link to={CRM_APP_PATHS.leads} className="font-medium text-brand-700 hover:text-brand-800 hover:underline">
            {t('app.analytics.lead_conversion.open_leads_workspace')}
          </Link>
        </p>
      )}

      {!loading ? (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold text-slate-800">
            {t('app.analytics.lead_conversion.management_chain_title')}
          </div>
          <p className="mt-1 text-sm text-slate-600">{t('app.analytics.lead_conversion.management_chain_intro')}</p>
          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-sm font-medium">
            <li>
              <Link
                to={CRM_APP_PATHS.settingsFunnels}
                className="text-brand-700 hover:text-brand-800 hover:underline"
              >
                {t('app.analytics.lead_conversion.management_chain_pipelines')}
              </Link>
            </li>
            <li>
              <Link
                to={CRM_APP_PATHS.automationRules}
                className="text-brand-700 hover:text-brand-800 hover:underline"
              >
                {t('app.analytics.lead_conversion.management_chain_automation')}
              </Link>
            </li>
            <li>
              <Link to={CRM_APP_PATHS.leads} className="text-brand-700 hover:text-brand-800 hover:underline">
                {t('app.analytics.lead_conversion.management_chain_leads')}
              </Link>
            </li>
            <li>
              {embedded ? (
                <a href="#lead-conversion" className="text-brand-700 hover:text-brand-800 hover:underline">
                  {t('app.analytics.lead_conversion.management_chain_nba')}
                </a>
              ) : (
                <Link to={CRM_APP_PATHS.overview} className="text-brand-700 hover:text-brand-800 hover:underline">
                  {t('app.analytics.lead_conversion.management_chain_nba')}
                </Link>
              )}
            </li>
          </ul>
          <p className="mt-2 text-xs text-slate-500">{t('app.analytics.lead_conversion.management_chain_automation_hint')}</p>
          <div className="mt-3 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            {t('app.analytics.lead_conversion.management_chain_presets_title')}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-2 text-sm">
            {LOST_REASON_LEAD_PRESETS.map((code) => (
              <Link
                key={code}
                to={leadsNextActionHref({
                  status: 'processed',
                  stage: 'lost',
                  lost_reason_code: code,
                })}
                className="text-brand-700 hover:text-brand-800 hover:underline"
              >
                {t(`app.leads.lost_reason.codes.${code}`)}
              </Link>
            ))}
          </div>
          <div className="mt-3 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            {t('app.analytics.lead_conversion.management_chain_combo_title')}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-2 text-sm">
            {PRIOR_STAGE_LOST_COMBOS.map((combo) => (
              <Link
                key={`${combo.lost_from_crm_stage}-${combo.lost_reason_code}`}
                to={leadsNextActionHref({
                  status: 'processed',
                  stage: 'lost',
                  lost_from_crm_stage: combo.lost_from_crm_stage,
                  lost_reason_code: combo.lost_reason_code,
                })}
                className="text-brand-700 hover:text-brand-800 hover:underline"
              >
                {t('app.analytics.lead_conversion.management_chain_combo_item', {
                  values: {
                    stage:
                      stageLabels[combo.lost_from_crm_stage] ?? combo.lost_from_crm_stage,
                    reason: t(`app.leads.lost_reason.codes.${combo.lost_reason_code}`),
                  },
                })}
              </Link>
            ))}
          </div>
        </div>
      ) : null}

      {loading ? (
        <div className="mt-10 text-sm text-slate-500">{t('common.loading')}</div>
      ) : funnelData && funnelData.stages.length > 0 ? (
        <>
          {funnelSuggested.weak || funnelSuggested.slow ? (
            <div className="mt-8 rounded-xl border border-brand-200/80 bg-brand-50/40 p-4 text-sm text-slate-700">
              <div className="text-xs font-semibold uppercase tracking-wide text-brand-900/80">
                {t('app.analytics.lead_conversion.suggested_title')}
              </div>
              <p className="mt-1 text-slate-600">{t('app.analytics.lead_conversion.suggested_intro')}</p>
              <ul className="mt-2 list-inside list-disc space-y-1 text-slate-700">
                {funnelSuggested.weak ? (
                  <li>
                    {t('app.analytics.lead_conversion.suggested_weak', {
                      values: {
                        rootLabel: stageLabels[funnelSuggested.weak.conversionRoot] ?? funnelSuggested.weak.conversionRoot,
                        pct: funnelSuggested.weak.progressedPct,
                        drop: funnelSuggested.weak.drop,
                      },
                    })}
                  </li>
                ) : null}
                {funnelSuggested.slow ? (
                  <li>
                    {t('app.analytics.lead_conversion.suggested_slow', {
                      values: {
                        rootLabel: stageLabels[funnelSuggested.slow.conversionRoot] ?? funnelSuggested.slow.conversionRoot,
                        days: Math.round(funnelSuggested.slow.dwellDays * 10) / 10,
                        count: funnelSuggested.slow.bucketCount,
                      },
                    })}
                  </li>
                ) : null}
              </ul>
              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm font-medium">
                <Link
                  to={CRM_APP_PATHS.overview}
                  className="text-brand-700 hover:text-brand-800 hover:underline"
                >
                  {t('app.analytics.lead_conversion.suggested_dashboard')}
                </Link>
                {funnelSuggested.weak ? (
                  <Link
                    to={leadsNextActionHref({
                      status: 'processed',
                      conversion_root: funnelSuggested.weak.conversionRoot,
                    })}
                    className="text-brand-700 hover:text-brand-800 hover:underline"
                  >
                    {t('app.analytics.lead_conversion.suggested_open_weak')}
                  </Link>
                ) : null}
                {funnelSuggested.slow ? (
                  <Link
                    to={leadsNextActionHref({
                      status: 'processed',
                      conversion_root: funnelSuggested.slow.conversionRoot,
                    })}
                    className="text-brand-700 hover:text-brand-800 hover:underline"
                  >
                    {t('app.analytics.lead_conversion.suggested_open_slow')}
                  </Link>
                ) : null}
              </div>
            </div>
          ) : null}
          <div className="mt-8 rounded-xl border border-slate-200 bg-slate-50/50 p-4">
            <div className="mb-4 rounded-lg border border-slate-200 bg-white/80 p-3">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                {t('app.analytics.lead_conversion.cohort_title')}
              </div>
              <p className="mt-1 text-xs text-slate-600">{t('app.analytics.lead_conversion.cohort_intro')}</p>
              <div
                className="mt-2 inline-flex flex-wrap gap-1 rounded-lg border border-slate-200 bg-slate-100 p-0.5"
                role="group"
                aria-label={t('app.analytics.lead_conversion.cohort_aria')}
              >
                {(
                  [
                    { mode: 'all' as const, labelKey: 'app.analytics.lead_conversion.cohort_all' },
                    { mode: 'rolling7' as const, labelKey: 'app.analytics.lead_conversion.cohort_7d' },
                    { mode: 'rolling7_wow' as const, labelKey: 'app.analytics.lead_conversion.cohort_7d_wow' },
                  ] as const
                ).map(({ mode, labelKey }) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setCohortMode(mode)}
                    className={`rounded-md px-2.5 py-1 text-xs font-medium ${
                      cohortMode === mode ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {t(labelKey)}
                  </button>
                ))}
              </div>
              {leadNba && leadNba.nba_tier !== 'team' ? (
                <p className="mt-2 text-[11px] text-slate-500">{t('app.analytics.lead_conversion.cohort_team_only')}</p>
              ) : null}
              {funnelData?.cohort_created_after && funnelData?.cohort_created_before_exclusive ? (
                <p className="mt-2 text-[11px] text-slate-500">
                  {t('app.analytics.lead_conversion.cohort_window_label', {
                    values: {
                      from: formatCohortBound(funnelData.cohort_created_after),
                      to: formatCohortBound(funnelData.cohort_created_before_exclusive),
                    },
                  })}
                </p>
              ) : null}
            </div>
            <LeadConversionFunnelPanel
            data={funnelData}
            teamTierSlices={leadNba?.nba_tier === 'team'}
            funnelSliceDraft={funnelSliceDraft}
            setFunnelSliceDraft={setFunnelSliceDraft}
            onApplySlices={applyFunnelSlices}
            onClearSlices={clearFunnelSlices}
            stageLabels={stageLabels}
            layout="vertical"
          />
            {funnelData.cohort_prior_window ? (
              <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white p-3">
                <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.analytics.lead_conversion.cohort_wow_title')}
                </div>
                <p className="mt-1 text-xs text-slate-600">{t('app.analytics.lead_conversion.cohort_wow_intro')}</p>
                <p className="mt-1 text-[11px] text-slate-500">
                  {t('app.analytics.lead_conversion.cohort_prior_window_label', {
                    values: {
                      from: formatCohortBound(funnelData.cohort_prior_window.cohort_created_at_min),
                      to: formatCohortBound(funnelData.cohort_prior_window.cohort_created_at_max_exclusive),
                    },
                  })}
                </p>
                <table className="mt-2 w-full min-w-[280px] border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-[10px] uppercase tracking-wide text-slate-500">
                      <th className="py-1.5 pr-2 font-semibold">{t('app.analytics.lead_conversion.cohort_metric')}</th>
                      <th className="py-1.5 pr-2 font-semibold">{t('app.analytics.lead_conversion.cohort_current')}</th>
                      <th className="py-1.5 pr-2 font-semibold">{t('app.analytics.lead_conversion.cohort_prior')}</th>
                      <th className="py-1.5 font-semibold">{t('app.analytics.lead_conversion.cohort_delta')}</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-800">
                    {(
                      [
                        {
                          key: 'win',
                          cur: funnelData.total_win_path_processed,
                          prev: funnelData.cohort_prior_window.total_win_path_processed,
                          label: t('app.analytics.lead_conversion.cohort_m_win_path'),
                        },
                        {
                          key: 'lost',
                          cur: funnelData.lost_processed_count,
                          prev: funnelData.cohort_prior_window.lost_processed_count,
                          label: t('app.analytics.lead_conversion.cohort_m_lost'),
                        },
                        {
                          key: 'new',
                          cur: funnelData.status_new_count,
                          prev: funnelData.cohort_prior_window.status_new_count,
                          label: t('app.analytics.lead_conversion.cohort_m_new'),
                        },
                      ] as const
                    ).map((row) => {
                      const delta = row.cur - row.prev
                      return (
                        <tr key={row.key} className="border-b border-slate-100">
                          <td className="py-1.5 pr-2">{row.label}</td>
                          <td className="py-1.5 pr-2 tabular-nums">{row.cur}</td>
                          <td className="py-1.5 pr-2 tabular-nums">{row.prev}</td>
                          <td className={`py-1.5 tabular-nums ${delta > 0 ? 'text-emerald-700' : delta < 0 ? 'text-rose-700' : 'text-slate-600'}`}>
                            {delta > 0 ? `+${delta}` : String(delta)}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        </>
      ) : (
        <div className="mt-10 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-600">
          {t('app.analytics.lead_conversion.empty')}
        </div>
      )}
    </div>
  )
}
