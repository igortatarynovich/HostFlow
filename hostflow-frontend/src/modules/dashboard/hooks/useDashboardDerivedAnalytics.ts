import { useMemo } from 'react'
import type { LocaleCode, TranslateFn } from '../../../i18n'
import type {
  AnalyticsProfileSummary,
  ContactAttemptStatsResponse,
  DocumentStatsResponse,
  OpsCounters,
  StageMetricsResponse,
} from '../../../api/analytics'
import { getRegionDisplayName } from '../../../utils/catalogLocale'
import { DAY_MS } from '../constants'
import {
  canonicalStageKey,
  determineStageOutcome,
  DOC_STAGE_CATEGORY,
  stageHighlights,
} from '../stageNormalize'
import type {
  CandidateSlicesResponse,
  StageLabelConfig,
  StageOutcome,
} from '../types'

export interface UseDashboardDerivedAnalyticsOptions {
  slices: CandidateSlicesResponse | null
  profileSummary: AnalyticsProfileSummary | null
  documentStats: DocumentStatsResponse | null
  contactStats: ContactAttemptStatsResponse | null
  opsCounters: OpsCounters | null
  stageMetrics: StageMetricsResponse | null
  periodTotal: number
  stageLabels: StageLabelConfig
  translateStageLabel: (code?: string | null, fallback?: string | null) => string
  translateReasonLabel: (code?: string | null, fallback?: string | null) => string
  notAvailableLabel: string
  locale: LocaleCode
  t: TranslateFn
}

export interface SourceStageRow {
  label: string
  total: number
  highlight: ReturnType<typeof stageHighlights>
}

export interface DocStageStats {
  waiting: number
  ready: number
  attention: number
  total: number
}

export interface DocumentBlockerAnalytics {
  total: number
  missingOrRequested: number
  awaitingReview: number
  problematic: number
  estimatedBlockedRevenue: number
}

export interface StageVelocityRow {
  stageCode: string
  label: string
  total: number
  avgDays: number
  p90: number
  intensity: number
}

export interface BusinessProfileCard {
  key: string
  label: string
  value: number
}

export interface ManagerLoadRow {
  label: string
  total: number
  pipeline: number
  managerIdForFilter: string | null
}

export interface CountryHeatmapRow {
  label: string
  count: number
  intensity: number
}

export interface GroupedStage {
  label: string
  count: number
  keys: string[]
}

export interface StageStackSegment {
  label: string
  value: number
  percent: number
  outcome: StageOutcome
  stageKeyForFilter: string
}

export interface GroupedReason {
  label: string
  count: number
  codes: Set<string>
}

export interface ExecutiveKpis {
  hired: number
  conversionPct: number
  avgDaysToEmploy: number | null
  pctNoNextQueue: number
  slaProxyPct: number
  noReplyProxyPct: number | null
  leadCost: number | null
}

export interface FunnelStep {
  key: string
  label: string
  count: number
  stepConv: number | null
  avgDays: number | null
}

export interface UseDashboardDerivedAnalyticsResult {
  sourceStageRows: SourceStageRow[]
  docStageStats: DocStageStats
  documentBlockerAnalytics: DocumentBlockerAnalytics
  stageVelocityRows: StageVelocityRow[]
  businessProfileCards: BusinessProfileCard[]
  dashboardCompanyLabels: { plural: string; singular: string }
  businessTypeLabel: string
  managerLoadRows: ManagerLoadRow[]
  countryHeatmapRows: CountryHeatmapRow[]
  groupedStages: GroupedStage[]
  stageStackSegments: StageStackSegment[]
  groupedRejectedReasons: GroupedReason[]
  groupedDeclinedReasons: GroupedReason[]
  executiveStageCountMap: Record<string, number>
  executiveHighlights: ReturnType<typeof stageHighlights>
  executiveKpis: ExecutiveKpis
  funnelSteps: FunnelStep[]
}

/**
 * Derived analytics for the dashboard page (pure useMemo derivations from
 * loaded slices / KPI / stats objects). No state, no effects.
 */
export function useDashboardDerivedAnalytics({
  slices,
  profileSummary,
  documentStats,
  contactStats,
  opsCounters,
  stageMetrics,
  periodTotal,
  stageLabels,
  translateStageLabel,
  translateReasonLabel,
  notAvailableLabel,
  locale,
  t,
}: UseDashboardDerivedAnalyticsOptions): UseDashboardDerivedAnalyticsResult {
  const sourceStageRows = useMemo<SourceStageRow[]>(() => {
    if (!slices?.snapshot?.length) return []
    const grouped = new Map<string, { label: string; total: number; byStage: Record<string, number> }>()
    slices.snapshot.forEach((row) => {
      const label = row.source?.trim() || notAvailableLabel
      const entry = grouped.get(label) ?? { label, total: 0, byStage: {} }
      const canonical = canonicalStageKey(row.stage, row.stage_label) ?? 'unknown'
      entry.total += 1
      entry.byStage[canonical] = (entry.byStage[canonical] ?? 0) + 1
      grouped.set(label, entry)
    })
    return Array.from(grouped.values())
      .map((entry) => ({
        label: entry.label,
        total: entry.total,
        highlight: stageHighlights(entry.byStage, stageLabels),
      }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 6)
  }, [slices?.snapshot, notAvailableLabel, stageLabels])

  const docStageStats = useMemo<DocStageStats>(() => {
    if (!slices?.snapshot?.length) return { waiting: 0, ready: 0, attention: 0, total: 0 }
    const counts: { waiting: number; ready: number; attention: number } = {
      waiting: 0,
      ready: 0,
      attention: 0,
    }
    slices.snapshot.forEach((row) => {
      const canonical = canonicalStageKey(row.stage, row.stage_label)
      if (!canonical) return
      let bucket: keyof typeof counts | null =
        DOC_STAGE_CATEGORY[canonical] ??
        (canonical.includes('permit') || canonical.includes('visa') || canonical.includes('doc')
          ? 'waiting'
          : null)
      if (!bucket && canonical.includes('problem')) bucket = 'attention'
      if (!bucket) return
      counts[bucket] += 1
    })
    const total = counts.waiting + counts.ready + counts.attention
    return { ...counts, total }
  }, [slices?.snapshot])

  const documentBlockerAnalytics = useMemo<DocumentBlockerAnalytics>(() => {
    if (!documentStats) {
      return {
        total: 0,
        missingOrRequested: 0,
        awaitingReview: 0,
        problematic: 0,
        estimatedBlockedRevenue: 0,
      }
    }
    const byStatus = Object.entries(documentStats.by_status || {}).reduce<Record<string, number>>(
      (acc, [k, v]) => {
        acc[String(k || '').toLowerCase()] = Number(v || 0)
        return acc
      },
      {},
    )
    const sumBy = (keys: string[]) => keys.reduce((sum, key) => sum + (byStatus[key] || 0), 0)
    const missingOrRequested = sumBy(['missing', 'requested', 'not_uploaded'])
    const awaitingReview = sumBy(['in_progress', 'uploaded', 'submitted', 'pending_verification'])
    const problematic = sumBy(['rejected', 'expired', 'invalid', 'problematic', 'needs_attention'])
    const total = missingOrRequested + awaitingReview + problematic

    const serviceOrdersInProgress = Number(profileSummary?.kpis?.service_orders_in_progress || 0)
    const avgOrderRevenue = Number(
      profileSummary?.kpis?.avg_order_revenue ||
        profileSummary?.kpis?.service_order_avg_revenue ||
        0,
    )
    const docsTotal = Math.max(Number(documentStats.total_docs || 0), 1)
    const blockedShare = total > 0 ? Math.min(total / docsTotal, 1) : 0
    const estimatedBlockedRevenue =
      serviceOrdersInProgress > 0 && avgOrderRevenue > 0
        ? blockedShare * serviceOrdersInProgress * avgOrderRevenue
        : 0

    return {
      total,
      missingOrRequested,
      awaitingReview,
      problematic,
      estimatedBlockedRevenue,
    }
  }, [documentStats, profileSummary?.kpis])

  const stageVelocityRows = useMemo<StageVelocityRow[]>(() => {
    if (!slices?.snapshot?.length) return []
    // eslint-disable-next-line react-hooks/purity -- stage velocity is an analytics snapshot; `now` is captured at recompute time (when `slices` change), not on every render
    const now = Date.now()
    const store = new Map<string, { label: string; values: number[] }>()
    slices.snapshot.forEach((row) => {
      if (!row.created_at) return
      const ts = Date.parse(row.created_at)
      if (Number.isNaN(ts)) return
      const days = Math.max((now - ts) / DAY_MS, 0)
      const canonical = canonicalStageKey(row.stage, row.stage_label) || String(row.stage || '')
      if (!canonical) return
      const label = translateStageLabel(row.stage, row.stage_label) || notAvailableLabel
      const entry = store.get(canonical)
      if (entry) entry.values.push(days)
      else store.set(canonical, { label, values: [days] })
    })
    const rows = Array.from(store.entries())
      .map(([stageCode, payload]) => {
        const values = payload.values
        const total = values.length
        const avgDays = values.reduce((sum, value) => sum + value, 0) / total
        const sorted = values.slice().sort((a, b) => a - b)
        const index = Math.min(sorted.length - 1, Math.max(0, Math.floor(0.9 * (sorted.length - 1))))
        const p90 = sorted[index] ?? avgDays
        return { stageCode, label: payload.label, total, avgDays, p90 }
      })
      .sort((a, b) => b.total - a.total)
      .slice(0, 6)
    const maxAvg = rows.reduce((max, row) => Math.max(max, row.avgDays), 0)
    return rows.map((row) => ({
      ...row,
      intensity: maxAvg ? Math.min(row.avgDays / maxAvg, 1) : 0,
    }))
  }, [slices?.snapshot, translateStageLabel, notAvailableLabel])

  const businessProfileCards = useMemo<BusinessProfileCard[]>(() => {
    if (!profileSummary) return []
    const kpis = profileSummary.kpis || {}
    const businessType = profileSummary.business_type
    if (businessType === 'services') {
      return [
        { key: 'clients_total', label: t('app.dashboard.business.services.clients_total'), value: Number(kpis.clients_total || 0) },
        { key: 'counterparties_total', label: t('app.dashboard.business.services.counterparties_total'), value: Number(kpis.counterparties_total || 0) },
        { key: 'service_orders_in_progress', label: t('app.dashboard.business.services.orders_in_progress'), value: Number(kpis.service_orders_in_progress || 0) },
        { key: 'service_orders_delivered', label: t('app.dashboard.business.services.orders_delivered'), value: Number(kpis.service_orders_delivered || 0) },
      ]
    }
    if (businessType === 'employer') {
      return [
        { key: 'vacancies_active', label: t('app.dashboard.business.employer.vacancies_active'), value: Number(kpis.vacancies_active || 0) },
        { key: 'candidates_total', label: t('app.dashboard.business.employer.candidates_total'), value: Number(kpis.candidates_total || 0) },
        { key: 'leads_total', label: t('app.dashboard.business.employer.leads_total'), value: Number(kpis.leads_total || 0) },
        { key: 'companies_total', label: t('app.dashboard.business.employer.companies_total'), value: Number(kpis.companies_total || 0) },
      ]
    }
    return [
      { key: 'companies_total', label: t('app.dashboard.business.agency.companies_total'), value: Number(kpis.companies_total || 0) },
      { key: 'vacancies_active', label: t('app.dashboard.business.agency.vacancies_active'), value: Number(kpis.vacancies_active || 0) },
      { key: 'candidates_total', label: t('app.dashboard.business.agency.candidates_total'), value: Number(kpis.candidates_total || 0) },
      { key: 'leads_total', label: t('app.dashboard.business.agency.leads_total'), value: Number(kpis.leads_total || 0) },
    ]
  }, [profileSummary, t])

  const dashboardCompanyLabels = useMemo(() => {
    const bt = profileSummary?.business_type
    if (bt === 'employer') {
      return {
        plural: t('app.dashboard.terms.companies_plural'),
        singular: t('app.dashboard.terms.companies_singular'),
      }
    }
    return {
      plural: t('app.dashboard.terms.clients_plural'),
      singular: t('app.dashboard.terms.clients_singular'),
    }
  }, [profileSummary?.business_type, t])

  const businessTypeLabel = useMemo(() => {
    const bt = profileSummary?.business_type
    if (bt === 'services') return t('app.dashboard.business.type.services')
    if (bt === 'employer') return t('app.dashboard.business.type.employer')
    if (bt === 'agency') return t('app.dashboard.business.type.agency')
    return t('common.labels.not_available')
  }, [profileSummary?.business_type, t])

  const managerLoadRows = useMemo<ManagerLoadRow[]>(() => {
    if (!slices?.snapshot?.length) return []
    const rows = new Map<
      string,
      { label: string; total: number; pipeline: number; managerIdForFilter: string | null }
    >()
    slices.snapshot.forEach((row) => {
      const label =
        row.manager_name ||
        row.manager ||
        row.manager_short ||
        t('app.dashboard.manager_load.unknown')
      const managerIdForFilter = String(row.manager || row.manager_short || '').trim() || null
      const canonical = canonicalStageKey(row.stage, row.stage_label)
      const outcome = determineStageOutcome(canonical, stageLabels)
      const entry = rows.get(label) ?? { label, total: 0, pipeline: 0, managerIdForFilter }
      entry.total += 1
      if (outcome === 'pipeline') entry.pipeline += 1
      rows.set(label, entry)
    })
    return Array.from(rows.values())
      .sort((a, b) => b.pipeline - a.pipeline || b.total - a.total)
      .slice(0, 6)
  }, [slices?.snapshot, stageLabels, t])

  const countryHeatmapRows = useMemo<CountryHeatmapRow[]>(() => {
    const list = slices?.countries ?? []
    if (!list.length) return []
    const max = list.reduce((acc, item) => Math.max(acc, item.count), 0) || 1
    return list
      .map((item) => {
        const code = item.key || ''
        const label = /^[A-Z]{2}$/.test(String(code))
          ? getRegionDisplayName(code, locale)
          : item.label || code || notAvailableLabel
        return {
          label: label || notAvailableLabel,
          count: item.count,
          intensity: Math.min(item.count / max, 1),
        }
      })
      .slice(0, 12)
  }, [slices?.countries, notAvailableLabel, locale])

  const groupedStages = useMemo<GroupedStage[]>(() => {
    if (!slices?.stages?.length) return []
    const grouped = new Map<string, { label: string; count: number; keys: string[] }>()
    slices.stages.forEach((stage) => {
      const translatedLabel = translateStageLabel(stage.key, stage.label) || stage.label
      if (grouped.has(translatedLabel)) {
        const existing = grouped.get(translatedLabel)!
        existing.count += stage.count ?? 0
        existing.keys.push(stage.key)
      } else {
        grouped.set(translatedLabel, {
          label: translatedLabel,
          count: stage.count ?? 0,
          keys: [stage.key],
        })
      }
    })
    return Array.from(grouped.values()).sort((a, b) => b.count - a.count)
  }, [slices?.stages, translateStageLabel])

  const stageStackSegments = useMemo<StageStackSegment[]>(() => {
    if (!groupedStages.length) return []
    const total = groupedStages.reduce((acc, stage) => acc + stage.count, 0)
    if (!total) return []
    return groupedStages.map((stage) => {
      const firstOriginalStage = slices?.stages?.find(
        (s) => (translateStageLabel(s.key, s.label) || s.label) === stage.label,
      )
      const stageKeyForFilter = firstOriginalStage?.key || stage.keys[0] || ''
      const canonical = firstOriginalStage
        ? canonicalStageKey(firstOriginalStage.key, firstOriginalStage.label)
        : null
      const outcome = determineStageOutcome(canonical, stageLabels)
      const value = stage.count
      const percent = total ? Math.round((value / total) * 1000) / 10 : 0
      return { label: stage.label, value, percent, outcome, stageKeyForFilter }
    })
  }, [groupedStages, slices?.stages, stageLabels, translateStageLabel])

  const groupedRejectedReasons = useMemo<GroupedReason[]>(() => {
    if (!slices?.snapshot?.length) return []
    const grouped = new Map<string, { label: string; count: number; codes: Set<string> }>()
    const noReasonLabel = t('app.dashboard.labels.no_reason')

    slices.snapshot.forEach((row) => {
      if (row.stage !== 'rejected') return

      const codes = row.status_reason_codes ?? []
      const fallbackLabels = row.status_reason_labels ?? []

      if (codes.length === 0 && fallbackLabels.length === 0) return

      const reasonsToProcess = codes.length > 0 ? codes : fallbackLabels
      reasonsToProcess.forEach((codeOrLabel, index) => {
        const code = codes.length > 0 ? codeOrLabel : null
        const fallback = fallbackLabels[index] || codeOrLabel
        const translatedLabel = translateReasonLabel(code, fallback)

        if (translatedLabel === noReasonLabel) return

        if (grouped.has(translatedLabel)) {
          const existing = grouped.get(translatedLabel)!
          existing.count += 1
          if (code) existing.codes.add(code)
        } else {
          grouped.set(translatedLabel, {
            label: translatedLabel,
            count: 1,
            codes: code ? new Set([code]) : new Set(),
          })
        }
      })
    })

    return Array.from(grouped.values()).sort((a, b) => b.count - a.count)
  }, [slices?.snapshot, translateReasonLabel, t])

  const groupedDeclinedReasons = useMemo<GroupedReason[]>(() => {
    if (!slices?.snapshot?.length) return []
    const grouped = new Map<string, { label: string; count: number; codes: Set<string> }>()
    const noReasonLabel = t('app.dashboard.labels.no_reason')

    slices.snapshot.forEach((row) => {
      if (row.stage !== 'declined') return

      const codes = row.status_reason_codes ?? []
      const fallbackLabels = row.status_reason_labels ?? []

      if (codes.length === 0 && fallbackLabels.length === 0) return

      const reasonsToProcess = codes.length > 0 ? codes : fallbackLabels
      reasonsToProcess.forEach((codeOrLabel, index) => {
        const code = codes.length > 0 ? codeOrLabel : null
        const fallback = fallbackLabels[index] || codeOrLabel
        const translatedLabel = translateReasonLabel(code, fallback)

        if (translatedLabel === noReasonLabel) return

        if (grouped.has(translatedLabel)) {
          const existing = grouped.get(translatedLabel)!
          existing.count += 1
          if (code) existing.codes.add(code)
        } else {
          grouped.set(translatedLabel, {
            label: translatedLabel,
            count: 1,
            codes: code ? new Set([code]) : new Set(),
          })
        }
      })
    })

    return Array.from(grouped.values()).sort((a, b) => b.count - a.count)
  }, [slices?.snapshot, translateReasonLabel, t])

  const executiveStageCountMap = useMemo<Record<string, number>>(() => {
    const m: Record<string, number> = {}
    for (const s of slices?.stages ?? []) {
      m[s.key] = (m[s.key] ?? 0) + (s.count ?? 0)
    }
    return m
  }, [slices?.stages])

  const executiveHighlights = useMemo(
    () => stageHighlights(executiveStageCountMap, stageLabels),
    [executiveStageCountMap, stageLabels],
  )

  const executiveKpis = useMemo<ExecutiveKpis>(() => {
    const hired = executiveHighlights.hired
    const conversionPct = periodTotal > 0 ? (hired / periodTotal) * 100 : 0
    const hiredTimes = (stageMetrics?.stage_time || []).filter((st) => {
      const c = canonicalStageKey(st.stage, st.stage)
      return c && (stageLabels.hired ?? []).includes(c)
    })
    const avgDaysToEmploy =
      hiredTimes.length > 0
        ? hiredTimes.reduce((a, st) => a + st.avg_days, 0) / hiredTimes.length
        : null
    const pipelineDen = Math.max(executiveHighlights.pipeline, opsCounters?.overview_pipeline_total ?? 0, 1)
    const noNext = opsCounters?.no_next_action_candidates ?? 0
    const pctNoNextQueue = Math.round(Math.min(100, (noNext / pipelineDen) * 100))
    const overdue = opsCounters?.overdue_reminders ?? 0
    const slaProxyPct = Math.max(0, Math.round(100 - Math.min(100, (overdue / pipelineDen) * 100)))
    const limitReached = contactStats?.limit_reached_count ?? 0
    const noReplyProxyPct =
      periodTotal > 0 ? Math.round(Math.min(100, (limitReached / periodTotal) * 100)) : null
    const kpi = profileSummary?.kpis
    const costRaw = kpi ? kpi['lead_cost'] ?? kpi['cost_per_lead'] : undefined
    const leadCost =
      typeof costRaw === 'number' && Number.isFinite(costRaw) ? costRaw : null
    return {
      hired,
      conversionPct,
      avgDaysToEmploy,
      pctNoNextQueue,
      slaProxyPct,
      noReplyProxyPct,
      leadCost,
    }
  }, [
    contactStats?.limit_reached_count,
    executiveHighlights.hired,
    executiveHighlights.pipeline,
    opsCounters?.no_next_action_candidates,
    opsCounters?.overdue_reminders,
    opsCounters?.overview_pipeline_total,
    periodTotal,
    profileSummary?.kpis,
    stageLabels.hired,
    stageMetrics?.stage_time,
  ])

  const funnelSteps = useMemo<FunnelStep[]>(() => {
    if (!slices?.stages?.length) return []
    let prev: number | null = null
    return slices.stages.map((s) => {
      const label = translateStageLabel(s.key, s.label) || s.label
      const cnt = s.count ?? 0
      const stepConv = prev != null && prev > 0 ? (cnt / prev) * 100 : null
      prev = cnt
      const avgDays = stageMetrics?.stage_time?.find((x) => x.stage === s.key)?.avg_days ?? null
      return { key: s.key, label, count: cnt, stepConv, avgDays }
    })
  }, [slices?.stages, stageMetrics?.stage_time, translateStageLabel])

  return {
    sourceStageRows,
    docStageStats,
    documentBlockerAnalytics,
    stageVelocityRows,
    businessProfileCards,
    dashboardCompanyLabels,
    businessTypeLabel,
    managerLoadRows,
    countryHeatmapRows,
    groupedStages,
    stageStackSegments,
    groupedRejectedReasons,
    groupedDeclinedReasons,
    executiveStageCountMap,
    executiveHighlights,
    executiveKpis,
    funnelSteps,
  }
}
