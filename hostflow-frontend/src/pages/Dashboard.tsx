// src/pages/Dashboard.tsx
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import api, { withTenant } from '../api/client'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { useCurrentTenantId } from '../contexts/CurrentTenant'
import { useTenantInfo } from '../contexts/TenantInfo'
import { OnboardingWizard } from '../components/OnboardingWizard'
import { PostWizardWelcomePanel } from '../components/onboarding/PostWizardWelcomePanel'
import { isOnboardingWizardEnabled } from '../utils/featureFlags'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { DashboardAnalyticsHubLinks } from '../components/dashboard/DashboardAnalyticsHubLinks'
import { DashboardLeadAutoFixCard } from '../components/dashboard/DashboardLeadAutoFixCard'
import { DashboardSectionCollapsible } from '../components/dashboard/DashboardSectionCollapsible'

const AnalyticsLeadConversionFunnelPageLazy = lazy(() => import('./AnalyticsLeadConversionFunnelPage'))
import {
  getAnalyticsProfileSummary,
  getHandoffStats,
  getContactAttemptStats,
  getDocumentStats,
  getDocumentRuntimeKpis,
} from '../api/analytics'
import { listTenantManagers } from '../api/users'
import { listCandidateStages } from '../api/candidate_stages'
import { usePermissions } from '../hooks/usePermissions'
import { isPostRecruitmentStageCode } from '../constants/recruitmentStageBoundary'
import { DAY_MS, QUICK_RANGE_OPTIONS, DIMENSION_OPTIONS, DEFAULT_STAGE_CODES } from '../modules/dashboard/constants'
import type {
  ListResp,
  NamedCount,
  StageBreakdownItem,
  CandidateSnapshot,
  CandidateSlicesResponse,
  PivotDimension,
  QuickRange,
  LoadOverrides,
  StageLabelConfig,
  StageOutcome,
  DashboardPreset,
  DashboardWidgetId,
} from '../modules/dashboard/types'
import { formatDateInput, calcRange, calcPrevPeriod, formatDelta, normalizeKey, normalizeTotal } from '../modules/dashboard/utils'
import {
  CRM_APP_DRILLDOWN_HREFS,
  CRM_APP_PATHS,
  dashboardInvoiceOpsDrilldownPath,
} from '../app/crmAppPaths'
import { servicesOrdersTabPath } from '../modules/services/utils'

// Stage/reason normalisation maps + helpers, moved to modules/dashboard/stageNormalize
import {
  DEFAULT_STAGE_LABELS,
  STAGE_HIGHLIGHT_CODES,
  STAGE_STACK_COLORS,
  canonicalStageKey,
  determineStageOutcome,
  NORMALIZED_REASON_LABEL_ALIASES,
  NORMALIZED_STAGE_CODE_ALIASES,
  NORMALIZED_STAGE_LABEL_ALIASES,
  normalizeStageCounts,
  stageHighlights,
} from '../modules/dashboard/stageNormalize'
import { useDashboardKpiLoaders } from '../modules/dashboard/hooks/useDashboardKpiLoaders'
import { useDashboardRiskOps } from '../modules/dashboard/hooks/useDashboardRiskOps'
import { useDashboardRetention } from '../modules/dashboard/hooks/useDashboardRetention'
import { useDashboardLayoutPrefs } from '../modules/dashboard/hooks/useDashboardLayoutPrefs'
import { useDashboardDerivedAnalytics } from '../modules/dashboard/hooks/useDashboardDerivedAnalytics'
import { DashboardFiltersBar } from '../modules/dashboard/components/DashboardFiltersBar'
import { DashboardExecutiveOverview } from '../modules/dashboard/components/DashboardExecutiveOverview'
import { DashboardPivotPanels } from '../modules/dashboard/components/DashboardPivotPanels'
import { DashboardAnalysisPanel } from '../modules/dashboard/components/DashboardAnalysisPanel'
import { DashboardRetentionCenter } from '../modules/dashboard/components/DashboardRetentionCenter'
import { DashboardOpsOverviewPanels } from '../modules/dashboard/components/DashboardOpsOverviewPanels'
import { DashboardPortfolioPanels } from '../modules/dashboard/components/DashboardPortfolioPanels'

export default function Dashboard() {
  const { t, locale } = useI18n()
  const { me } = useAuth()
  const { can, role, isClientTenant } = usePermissions()
  const canServicesOpsWidgets = useMemo(() => can('services.view'), [can])
  const canVacanciesOpenWidget = useMemo(() => can('vacancies.view'), [can])
  const tenant = useTenantInfo()
  const currentTenantId = useCurrentTenantId()
  const tenantId = (currentTenantId ?? (me as { tenant_id?: string })?.tenant_id) ?? 'default'
  const scopeTid = currentTenantId ?? (me as { tenant_id?: string })?.tenant_id
  const canViewRiskOpsUi = useMemo(() => {
    const r = String((me as { role?: string })?.role ?? '').toLowerCase()
    return r === 'superadmin' || r === 'administrator' || r === 'supervisor'
  }, [(me as { role?: string })?.role])
  const myUserId = useMemo(() => String((me as { sub?: string })?.sub || '').trim(), [(me as { sub?: string })?.sub])
  const dashUserBase = useMemo(() => {
    const safe = (myUserId || 'anon').replace(/[^a-zA-Z0-9-]/g, '').slice(0, 80)
    return `hf:dashboard:${tenantId}:u:${safe || 'anon'}`
  }, [tenantId, myUserId])
  const location = useLocation()

  useEffect(() => {
    const id = location.hash?.replace(/^#/, '').trim()
    if (id !== 'lead-conversion') return
    const run = () => document.getElementById('lead-conversion')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    const t = window.setTimeout(run, 120)
    return () => window.clearTimeout(t)
  }, [location.hash])

  const initialRange = calcRange('90d')
  const [dateFrom, setDateFrom] = useState<string>(initialRange.from)
  const [dateTo, setDateTo] = useState<string>(initialRange.to)
  const [activeRange, setActiveRange] = useState<QuickRange | 'custom'>('90d')
  const [dateField, setDateField] = useState<'created' | 'updated'>('created')

  const [loading, setLoading] = useState(true)
  const [errText, setErrText] = useState<string | null>(null)

  const {
    opsCounters,
    opsCountersLoading,
    vacanciesOpenLoading,
    vacanciesOpenSummary,
    invoiceMoney,
    invoiceMoneyLoading,
    stageMetrics,
    stageMetricsLoading,
    loadOpsCounters,
    loadInvoiceMoneyWidget: _loadInvoiceMoneyWidget,
    loadStageMetrics: _loadStageMetrics,
  } = useDashboardKpiLoaders({ canVacanciesOpenWidget, canServicesOpsWidgets })
  void _loadInvoiceMoneyWidget
  void _loadStageMetrics
  const {
    riskIntel,
    riskTrends,
    riskValidation,
    riskShadowSnapshot,
    riskDigestQueue,
    riskDigestMinBand,
    setRiskDigestMinBand,
    riskDigestQueueReadFilter,
    setRiskDigestQueueReadFilter,
    riskShadowBucketStart,
    setRiskShadowBucketStart,
    riskIntelLoading,
    riskIntelShadowLoading,
    digestAckLoading,
    digestHandoffBusyId,
    digestReminderAssigneePick,
    setDigestReminderAssigneePick,
    digestBulkSelected,
    digestBulkReminderAssignee,
    setDigestBulkReminderAssignee,
    digestBulkBusy,
    digestBulkResultReport,
    digestBulkHeadRef,
    digestBulkRowIds,
    filteredDigestBuckets,
    latestDigestBucketStart,
    loadRiskOpsCore,
    loadRiskShadow,
    refreshRiskOpsIntel,
    onManagerDigestAck,
    onManagerDigestAckLatest,
    onShadowDigestReminder,
    onShadowDigestClaim,
    toggleDigestBulkRow,
    toggleDigestBulkAll,
    onShadowDigestBulkRemind,
    onShadowDigestBulkClaim,
  } = useDashboardRiskOps({ canViewRiskOpsUi, myUserId, t })


  const [globalCounts, setGlobalCounts] = useState({ candidates: 0, companies: 0, vacancies: 0 })
  const [periodTotal, setPeriodTotal] = useState(0)
  const [slices, setSlices] = useState<CandidateSlicesResponse | null>(null)
  const isClientRole = isClientTenant && role !== 'administrator'
  const isTrialTenant = String(tenant?.status || '').trim().toLowerCase() === 'trial'
  const canManageBilling = role === 'administrator' || role === 'supervisor'
  const {
    trialEndsAt: _trialEndsAt,
    billingGate,
    retentionStatus,
    retentionDismissed: _retentionDismissed,
    retentionReport,
    retentionReportLoading,
    trialDaysLeft,
    trialTone,
    showTrialPanel,
    trialCenterClasses,
    retentionReportRows,
    trialAgeDays: _trialAgeDays,
    retentionDay,
    retentionNextHref,
    retentionStepKey,
    retentionNudge,
    dismissRetentionNudge,
    trackRetentionEvent,
  } = useDashboardRetention({ canManageBilling, isTrialTenant, tenant, tenantId, t })
  void _trialEndsAt
  void _retentionDismissed
  void _trialAgeDays
  const [stageView, setStageView] = useState<'all' | 'agency' | 'client'>(() =>
    isClientRole ? 'client' : 'all',
  )

  const [pivotPrimary, setPivotPrimary] = useState<PivotDimension>('company')
  const [pivotSecondary, setPivotSecondary] = useState<PivotDimension | 'none'>('stage')
  const [breakdownGroup, setBreakdownGroup] = useState<PivotDimension>('source')
  const [breakdownMetric, setBreakdownMetric] = useState<'count' | 'conversion' | 'time' | 'dropoff'>(
    'conversion',
  )
  const [vacancyFilter, setVacancyFilter] = useState<string>('')
  const [vacancyOptions, setVacancyOptions] = useState<{ id: string; label: string }[]>([])
  const [companyFilter, setCompanyFilter] = useState<string>('')
  const [companyOptions, setCompanyOptions] = useState<{ id: string; label: string }[]>([])
  const [managerFilter, setManagerFilter] = useState<string>('')
  const [managerOptions, setManagerOptions] = useState<{ id: string; label: string }[]>([])
  const [candidateFilter, setCandidateFilter] = useState<string>('')
  const [stagesFilter, setStagesFilter] = useState<string[]>([])
  const [stageOptions, setStageOptions] = useState<{ code: string; label: string }[]>([])
  const [handoffStats, setHandoffStats] = useState<Awaited<ReturnType<typeof getHandoffStats>> | null>(null)
  const [contactStats, setContactStats] = useState<Awaited<ReturnType<typeof getContactAttemptStats>> | null>(null)
  const [documentStats, setDocumentStats] = useState<Awaited<ReturnType<typeof getDocumentStats>> | null>(null)
  const [documentRuntimeKpis, setDocumentRuntimeKpis] = useState<
    Awaited<ReturnType<typeof getDocumentRuntimeKpis>> | null
  >(null)
  const [profileSummary, setProfileSummary] = useState<Awaited<ReturnType<typeof getAnalyticsProfileSummary>> | null>(null)
  const [compareWithPrevious, setCompareWithPrevious] = useState(false)
  const [prevPeriodTotal, setPrevPeriodTotal] = useState<number | null>(null)
  const [prevHandoffStats, setPrevHandoffStats] = useState<Awaited<ReturnType<typeof getHandoffStats>> | null>(null)
  const pivotChartContainerRef = useRef<HTMLDivElement | null>(null)
  const [isPivotChartContainerReady, setIsPivotChartContainerReady] = useState(false)

  const {
    visibleWidgetsKey,
    visibleFiltersKey,
    dashboardPresetKey,
    visibleWidgets,
    setVisibleWidgets,
    visibleFilters,
    setVisibleFilters,
    isWidgetVisible,
    isFilterVisible,
    toggleWidget,
    toggleFilter,
    savedPreset,
    setSavedPreset,
  } = useDashboardLayoutPrefs({ dashUserBase, tenantId })

  const numberFormatter = useMemo(() => {
    switch (locale) {
      case 'pl':
        return new Intl.NumberFormat('pl-PL')
      case 'ru':
        return new Intl.NumberFormat('ru-RU')
      default:
        return new Intl.NumberFormat('en-US')
    }
  }, [locale])
  const formatNumber = useCallback((value?: number) => numberFormatter.format(value ?? 0), [numberFormatter])

  const quickRangeOptions = useMemo(
    () => QUICK_RANGE_OPTIONS.map((value) => ({ value, label: t(`app.dashboard.ranges.${value}`) })),
    [t],
  )

  const dimensionOptions = useMemo(
    () => DIMENSION_OPTIONS.map((value) => ({ value, label: t(`app.dashboard.dimensions.${value}`) })),
    [t],
  )

  const stageLabels = useMemo<StageLabelConfig>(() => STAGE_HIGHLIGHT_CODES, [])
  const untitledLabel = t('app.dashboard.labels.no_title')
  const notAvailableLabel = t('common.labels.not_available')
  const startStageLabel = t('app.dashboard.stage_metrics.start_stage')

  const translateStageLabel = useCallback(
    (code?: string | null, fallback?: string | null) => {
      const normalizedCode = normalizeKey(code)
      const canonicalFromCode = normalizedCode
        ? NORMALIZED_STAGE_CODE_ALIASES[normalizedCode] ??
          NORMALIZED_STAGE_LABEL_ALIASES[normalizedCode] ??
          normalizedCode
        : null
      const fallbackKey = normalizeKey(fallback)
      const canonicalFromFallback = fallbackKey
        ? NORMALIZED_STAGE_LABEL_ALIASES[fallbackKey] ?? fallbackKey
        : null
      const finalKey = canonicalFromCode ?? canonicalFromFallback
      if (finalKey) {
        // Use candidate stage labels so statuses are consistent across list, card and analytics.
        const candidatesKey = `app.candidates.stage_labels.${finalKey}`
        const translatedFromCandidates = t(candidatesKey)
        if (translatedFromCandidates !== candidatesKey) {
          return translatedFromCandidates
        }
      }
      if (fallback && fallback.trim()) return fallback
      if (code && code.trim()) return code
      return notAvailableLabel
    },
    [t, notAvailableLabel],
  )

  const translateReasonLabel = useCallback(
    (code?: string | null, fallback?: string | null) => {
      const normalizedCode = normalizeKey(code)
      const canonicalCode = normalizedCode ? NORMALIZED_REASON_LABEL_ALIASES[normalizedCode] ?? normalizedCode : null
      const fallbackKey = normalizeKey(fallback)
      const finalKey =
        canonicalCode ?? (fallbackKey ? NORMALIZED_REASON_LABEL_ALIASES[fallbackKey] ?? fallbackKey : null)
      if (finalKey) {
        if (finalKey === 'no_reason') {
          return t('app.dashboard.labels.no_reason')
        }
        const translationKey = `app.dashboard.reason_codes.${finalKey}`
        const translated = t(translationKey)
        if (translated !== translationKey) {
          return translated
        }
      }
      return fallback ?? code ?? ''
    },
    [t],
  )

  const getDimensionValues = useCallback(
    (row: CandidateSnapshot, dimension: PivotDimension): string[] => {
      switch (dimension) {
        case 'stage': {
          const label = translateStageLabel(row.stage, row.stage_label)
          return [label || notAvailableLabel]
        }
        case 'company':
          return [row.company || notAvailableLabel]
        case 'vacancy':
          return [row.vacancy || row.company || notAvailableLabel]
        case 'source':
          return [row.source || notAvailableLabel]
        case 'citizenship':
          return [row.citizenship || notAvailableLabel]
        case 'country':
          return [row.country || notAvailableLabel]
        case 'manager':
          return [row.manager_name || row.manager_short || row.manager || notAvailableLabel]
        case 'reason': {
          const stageLabel = translateStageLabel(row.reason_stage, row.reason_stage_label)
          const codes = row.status_reason_codes ?? []
          const fallbackReasons = row.status_reason_labels ?? []
          const translatedReasons =
            codes.length > 0
              ? codes.map((code, index) => translateReasonLabel(code, fallbackReasons[index]))
              : []
          const reasons = translatedReasons.length > 0 ? translatedReasons : fallbackReasons
          if (stageLabel && reasons.length) {
            return reasons.map((label) => `${stageLabel}: ${label}`)
          }
          if (stageLabel) {
            return [`${stageLabel}: ${t('app.dashboard.labels.no_reason')}`]
          }
          return reasons.length ? reasons : []
        }
        default:
          return [notAvailableLabel]
      }
    },
    [t, translateStageLabel, translateReasonLabel, notAvailableLabel],
  )

  const load = async (overrides?: LoadOverrides) => {
    const from = overrides?.from ?? dateFrom
    const to = overrides?.to ?? dateTo
    const field = overrides?.field ?? dateField
    const vacancyId =
      overrides && 'vacancyId' in overrides ? (overrides.vacancyId ?? '') : vacancyFilter
    const companyId =
      overrides && 'companyId' in overrides ? (overrides.companyId ?? '') : companyFilter
    const managerId =
      overrides && 'managerId' in overrides ? (overrides.managerId ?? '') : managerFilter
    const candidateIdRaw =
      overrides && 'candidateId' in overrides ? (overrides.candidateId ?? '') : candidateFilter
    const candidateId = String(candidateIdRaw || '').trim()
    const stages =
      overrides && 'stages' in overrides ? (overrides.stages ?? []) : stagesFilter
    const doCompare = overrides?.compare ?? compareWithPrevious

    if (from && to && from > to) {
      setErrText(t('app.dashboard.errors.range_invalid'))
      return
    }

    setLoading(true)
    setErrText(null)
    try {
      const params: Record<string, any> = { limit: 40, by: field, stage_view: stageView }
      if (from) params.from = from
      if (to) params.to = to
      if (vacancyId) params.vacancy_id = vacancyId
      if (companyId) params.company_id = companyId
      if (managerId) params.manager_id = managerId
      if (candidateId) params.candidate_id = candidateId
      if (stages.length > 0) params.stages = stages
      if (scopeTid) params.scope_tenant_id = scopeTid

      const candParams: Record<string, any> = { limit: 1, offset: 0 }
      if (scopeTid) candParams.scope_tenant_id = scopeTid
      const candidatesClient = scopeTid ? withTenant(scopeTid) : api

      const periodParams = from && to ? { from, to } : {}
      const prevPeriod = from && to ? calcPrevPeriod(from, to) : null
      const shouldCompare = doCompare && prevPeriod

      const [cand, comps, vacs, sliceResp, handoffResp, contactResp, docResp, docRuntimeKpisResp, profileResp] =
        await Promise.all([
        candidatesClient.get<ListResp<any>>('/candidates', { params: candParams }),
        api.get<ListResp<any>>('/companies/', { params: { limit: 50, offset: 0 } }),
        api.get<ListResp<any>>('/vacancies/', { params: { limit: 50, offset: 0 } }),
        candidatesClient.get<CandidateSlicesResponse>('/analytics/candidate-slices', { params }),
        getHandoffStats(periodParams).catch(() => null),
        getContactAttemptStats(periodParams).catch(() => null),
        getDocumentStats(periodParams).catch(() => null),
        getDocumentRuntimeKpis(periodParams).catch(() => null),
        getAnalyticsProfileSummary().catch(() => null),
      ])

      let prevTotal: number | null = null
      let prevHandoff: Awaited<ReturnType<typeof getHandoffStats>> | null = null
      if (shouldCompare && prevPeriod) {
        const [prevSliceRes, prevHandoffRes] = await Promise.all([
          candidatesClient.get<CandidateSlicesResponse>('/analytics/candidate-slices', {
            params: { ...params, from: prevPeriod.from, to: prevPeriod.to },
          }),
          getHandoffStats({ from: prevPeriod.from, to: prevPeriod.to }).catch(() => null),
        ])
        prevTotal = prevSliceRes.data?.total ?? 0
        prevHandoff = prevHandoffRes
      }

      const slicesData = sliceResp.data
      setGlobalCounts({
        candidates: slicesData?.total ?? normalizeTotal(cand.data),
        companies: slicesData?.companies_total ?? normalizeTotal(comps.data),
        vacancies: slicesData?.vacancies_total ?? normalizeTotal(vacs.data),
      })
      setSlices(slicesData)
      setPeriodTotal(slicesData?.total ?? 0)
      setHandoffStats(handoffResp)
      setContactStats(contactResp)
      setDocumentStats(docResp)
      setDocumentRuntimeKpis(docRuntimeKpisResp)
      setProfileSummary(profileResp)
      setPrevPeriodTotal(prevTotal)
      setPrevHandoffStats(prevHandoff)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      const fallback = t('app.dashboard.errors.load_failed')
      const asText =
        typeof detail === 'string'
          ? detail
          : detail
            ? JSON.stringify(detail)
            : e?.message || fallback
      setErrText(asText)
      setSlices(null)
      setPeriodTotal(0)
      setHandoffStats(null)
      setContactStats(null)
      setDocumentStats(null)
      setProfileSummary(null)
      console.error('Dashboard load error:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageView])

  useEffect(() => {
    ;(async () => {
      try {
        const { data } = await api.get('/vacancies/', { params: { limit: 200, offset: 0 } })
        const list: any[] = Array.isArray(data)
          ? data
          : Array.isArray((data as any)?.items)
            ? (data as any).items
            : []
        const mapped = list
          .map((item: any) => {
            const id = item?.id
            if (!id) return null
            const title = item?.title || item?.vacancy_title || untitledLabel
            const companyName = item?.company_name || item?.company?.name || ''
            const label = companyName ? `${title} • ${companyName}` : title
            return { id, label }
          })
          .filter(Boolean) as { id: string; label: string }[]
        setVacancyOptions(mapped)
      } catch (error) {
        console.error('Failed to load vacancy options', error)
      }
    })()
  }, [untitledLabel])

  useEffect(() => {
    ;(async () => {
      try {
        const { data } = await api.get('/companies/', { params: { limit: 200, offset: 0 } })
        const list: any[] = Array.isArray(data)
          ? data
          : Array.isArray((data as any)?.items)
            ? (data as any).items
            : []
        const mapped = list
          .map((item: any) => {
            const id = item?.id
            if (!id) return null
            const label = item?.name || item?.label || id
            return { id, label }
          })
          .filter(Boolean) as { id: string; label: string }[]
        setCompanyOptions(mapped)
      } catch (error) {
        console.error('Failed to load company options', error)
      }
    })()
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        const managers = await listTenantManagers()
        setManagerOptions(
          managers.map((m) => ({ id: m.id, label: m.label || m.full_name || m.email || m.id }))
        )
      } catch (error) {
        console.error('Failed to load manager options', error)
      }
    })()
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        const stages = await listCandidateStages({ active: true })
        if (stages.length > 0) {
          setStageOptions(
            stages
              .filter((s) => !isPostRecruitmentStageCode(s.code))
              .map((s) => ({ code: s.code, label: s.label || s.code })),
          )
        } else {
          setStageOptions(
            DEFAULT_STAGE_CODES.map((code) => ({
              code,
              label: t(`app.candidates.stage_labels.${code}`, { defaultValue: code }),
            }))
          )
        }
      } catch (error) {
        console.error('Failed to load stage options', error)
        setStageOptions(
          DEFAULT_STAGE_CODES.map((code) => ({
            code,
            label: t(`app.dashboard.stage_labels.${code}`) || code,
          }))
        )
      }
    })()
  }, [t])

  useEffect(() => {
    if (!vacancyFilter) return
    if (vacancyOptions.some((option) => option.id === vacancyFilter)) return
    setVacancyFilter('')
  }, [vacancyFilter, vacancyOptions])

  useEffect(() => {
    if (!companyFilter) return
    if (companyOptions.some((option) => option.id === companyFilter)) return
    setCompanyFilter('')
  }, [companyFilter, companyOptions])

  useEffect(() => {
    if (!managerFilter) return
    if (managerOptions.some((option) => option.id === managerFilter)) return
    setManagerFilter('')
  }, [managerFilter, managerOptions])

  useEffect(() => {
    if (!stagesFilter.length) return
    const allowed = new Set(stageOptions.map((option) => option.code))
    const next = stagesFilter.filter((code) => allowed.has(code))
    if (next.length !== stagesFilter.length) {
      setStagesFilter(next)
    }
  }, [stagesFilter, stageOptions])

  const applyQuickRange = (range: QuickRange) => {
    const next = calcRange(range)
    setDateFrom(next.from)
    setDateTo(next.to)
    setActiveRange(range)
    // immediately refresh data for the new range
    load({ from: next.from, to: next.to })
  }

  const handleVacancyChange = (value: string) => {
    setVacancyFilter(value)
    load({ vacancyId: value })
  }

  const handleCompanyChange = (value: string) => {
    setCompanyFilter(value)
    load({ companyId: value })
  }

  const handleManagerChange = (value: string) => {
    setManagerFilter(value)
    load({ managerId: value })
  }

  const handleCandidateFilterApply = (raw: string) => {
    const v = raw.trim()
    setCandidateFilter(v)
    load({ candidateId: v || null })
  }

  const handleStagesChange = (codes: string[]) => {
    setStagesFilter(codes)
    load({ stages: codes })
  }

  const handleResetFilters = () => {
    setVacancyFilter('')
    setCompanyFilter('')
    setManagerFilter('')
    setCandidateFilter('')
    setStagesFilter([])
    setCompareWithPrevious(false)
    const next = calcRange('90d')
    setDateFrom(next.from)
    setDateTo(next.to)
    setActiveRange('90d')
    setDateField('created')
    load({
      from: next.from,
      to: next.to,
      vacancyId: null,
      companyId: null,
      managerId: null,
      candidateId: null,
      stages: [],
      compare: false,
    })
  }

  const handleSavePreset = () => {
    const preset: DashboardPreset = {
      dateFrom,
      dateTo,
      activeRange,
      dateField,
      vacancyFilter,
      companyFilter,
      managerFilter,
      candidateFilter,
      stagesFilter: [...stagesFilter],
      compareWithPrevious,
      visibleWidgets: [...visibleWidgets],
      visibleFilters: [...visibleFilters],
      pivotPrimary,
      pivotSecondary,
    }
    try {
      localStorage.setItem(dashboardPresetKey, JSON.stringify(preset))
      setSavedPreset(preset)
    } catch (e) {
      console.error('Failed to save preset', e)
    }
  }

  const handleLoadPreset = () => {
    try {
      const raw = localStorage.getItem(dashboardPresetKey)
      if (!raw) return
      const preset = JSON.parse(raw) as DashboardPreset
      setDateFrom(preset.dateFrom || '')
      setDateTo(preset.dateTo || '')
      setActiveRange((preset.activeRange as QuickRange) || '90d')
      setDateField(preset.dateField || 'created')
      setVacancyFilter(preset.vacancyFilter || '')
      setCompanyFilter(preset.companyFilter || '')
      setManagerFilter(preset.managerFilter || '')
      setCandidateFilter(preset.candidateFilter || '')
      setStagesFilter(Array.isArray(preset.stagesFilter) ? preset.stagesFilter : [])
      setCompareWithPrevious(Boolean(preset.compareWithPrevious))
      if (Array.isArray(preset.visibleWidgets)) {
        setVisibleWidgets(new Set(preset.visibleWidgets))
        try {
          localStorage.setItem(visibleWidgetsKey, JSON.stringify(preset.visibleWidgets))
        } catch {
          /* ignore */
        }
      }
      if (Array.isArray(preset.visibleFilters)) {
        setVisibleFilters(new Set(preset.visibleFilters))
        try {
          localStorage.setItem(visibleFiltersKey, JSON.stringify(preset.visibleFilters))
        } catch {
          /* ignore */
        }
      }
      if (preset.pivotPrimary) setPivotPrimary(preset.pivotPrimary as PivotDimension)
      if (preset.pivotSecondary) setPivotSecondary(preset.pivotSecondary as PivotDimension | 'none')
      load({
        from: preset.dateFrom,
        to: preset.dateTo,
        field: preset.dateField,
        vacancyId: preset.vacancyFilter || null,
        companyId: preset.companyFilter || null,
        managerId: preset.managerFilter || null,
        candidateId: preset.candidateFilter || null,
        stages: preset.stagesFilter,
        compare: preset.compareWithPrevious,
      })
    } catch (e) {
      console.error('Failed to load preset', e)
    }
  }

  const selectedVacancyLabel = useMemo(() => {
    if (!vacancyFilter) return ''
    const match = vacancyOptions.find((option) => option.id === vacancyFilter)
    return match?.label ?? notAvailableLabel
  }, [vacancyFilter, vacancyOptions, notAvailableLabel])

  const pivotData = useMemo(() => {
    if (!slices?.snapshot?.length) return { rows: [] as { key: string; total: number; breakdown: Record<string, number>; filterParams: Record<string, string> }[], secondaryKeys: [] as string[] }

    const totals = new Map<string, { total: number; breakdown: Map<string, number>; filterParams: Record<string, string> }>()
    const secondaryTotals = new Map<string, number>()
    const pivotSecondaryDimension = pivotSecondary === 'none' ? null : pivotSecondary
    const secondaryEnabled = Boolean(pivotSecondaryDimension)

    // Для reason dimension каждый кандидат может иметь несколько значений (несколько причин)
    // Для остальных измерений каждый кандидат считается один раз
    const isReasonPrimary = pivotPrimary === 'reason'
    const isReasonSecondary = pivotSecondaryDimension === 'reason'

    for (const row of slices.snapshot) {
      const primaryValues = getDimensionValues(row, pivotPrimary)
      const normalizedPrimary = primaryValues.length ? primaryValues : [notAvailableLabel]

      const secondaryValues = secondaryEnabled && pivotSecondaryDimension
        ? getDimensionValues(row, pivotSecondaryDimension as PivotDimension)
        : []
      const normalizedSecondary = secondaryEnabled
        ? (secondaryValues.length ? secondaryValues : [notAvailableLabel])
        : []

      // Если нет значений в primary, пропускаем эту строку
      if (!normalizedPrimary.length) continue

      for (const primary of normalizedPrimary) {
        const key = primary || notAvailableLabel
        const existing = totals.get(key)
        const entry = existing ?? {
          total: 0,
          breakdown: new Map<string, number>(),
          filterParams: (() => {
            const p: Record<string, string> = {}
            if (pivotPrimary === 'stage' && row.stage) p.stage = row.stage
            else if (pivotPrimary === 'company' && row.company_id) p.company_id = row.company_id
            else if (pivotPrimary === 'vacancy' && row.vacancy_id) p.vacancy_id = row.vacancy_id
            else if (pivotPrimary === 'source' && row.source) p.source = row.source
            else if (pivotPrimary === 'citizenship' && row.citizenship) p.citizenship = row.citizenship
            else if (pivotPrimary === 'country' && row.country) p.country = row.country
            else if (pivotPrimary === 'manager' && row.manager_id) p.manager_id = row.manager_id
            else if (pivotPrimary === 'reason' && row.reason_stage && row.status_reason_codes?.[0]) {
              p.stage = row.reason_stage
              p.status_reason = row.status_reason_codes[0]
            }
            return p
          })(),
        }
        
        if (secondaryEnabled) {
          // Если есть secondary значения, считаем каждую комбинацию
          if (normalizedSecondary.length > 0) {
            for (const secondary of normalizedSecondary) {
              const secKey = secondary || notAvailableLabel
              entry.breakdown.set(secKey, (entry.breakdown.get(secKey) ?? 0) + 1)
              secondaryTotals.set(secKey, (secondaryTotals.get(secKey) ?? 0) + 1)
            }
            // Для reason dimension считаем количество комбинаций (каждая причина отдельно)
            // Для остальных измерений - один кандидат независимо от количества secondary значений
            if (isReasonPrimary || isReasonSecondary) {
              // Если reason - считаем каждую комбинацию отдельно
              entry.total += normalizedSecondary.length
            } else {
              // Для остальных измерений - один кандидат считается один раз
              entry.total += 1
            }
          } else {
            // Если нет secondary значений, считаем как один кандидат
            entry.total += 1
          }
        } else {
          // Без secondary dimension каждый кандидат считается один раз
          entry.total += 1
        }
        totals.set(key, entry)
      }
    }

    const secondaryKeys = secondaryEnabled
      ? Array.from(secondaryTotals.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, 8)
          .map(([key]) => key)
      : []

  const rows = Array.from(totals.entries())
      .map(([key, entry]) => ({
        key,
        total: entry.total,
        breakdown: Object.fromEntries(entry.breakdown),
        filterParams: entry.filterParams || {},
      }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 30)

    return { rows, secondaryKeys }
  }, [getDimensionValues, pivotPrimary, pivotSecondary, slices?.snapshot, notAvailableLabel])

  useEffect(() => {
    if (!isWidgetVisible('pivotChart') || pivotData.rows.length === 0) {
      setIsPivotChartContainerReady(false)
      return
    }
    const node = pivotChartContainerRef.current
    if (!node) {
      setIsPivotChartContainerReady(false)
      return
    }

    let rafId = 0
    const updateReadyState = () => {
      const rect = node.getBoundingClientRect()
      setIsPivotChartContainerReady(rect.width > 0 && rect.height > 0)
    }

    updateReadyState()

    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver(() => {
        cancelAnimationFrame(rafId)
        rafId = requestAnimationFrame(updateReadyState)
      })
      observer.observe(node)
      return () => {
        cancelAnimationFrame(rafId)
        observer.disconnect()
      }
    }

    const intervalId = window.setInterval(updateReadyState, 200)
    return () => window.clearInterval(intervalId)
  }, [isWidgetVisible, pivotData.rows.length])

  const {
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
    executiveStageCountMap: _executiveStageCountMap,
    executiveHighlights,
    executiveKpis,
    funnelSteps,
  } = useDashboardDerivedAnalytics({
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
  })
  void _executiveStageCountMap

  const businessCardHref = useCallback((key: string): string => {
    switch (key) {
      case 'service_orders_in_progress':
        return servicesOrdersTabPath({ status: 'in_progress' })
      case 'service_orders_delivered':
        return servicesOrdersTabPath({ status: 'completed' })
      case 'clients_total':
      case 'counterparties_total':
      case 'companies_total':
        return CRM_APP_PATHS.clientsDirectory
      case 'vacancies_active':
        return CRM_APP_PATHS.vacancies
      case 'candidates_total':
        return CRM_APP_PATHS.candidates
      case 'leads_total':
        return CRM_APP_PATHS.leads
      default:
        return CRM_APP_PATHS.overview
    }
  }, [])

  const documentQuickFilterHref = useCallback((statusKey: string): string => {
    const base = CRM_APP_PATHS.documents
    const key = String(statusKey || '').toLowerCase()
    if (['missing', 'not_uploaded'].includes(key)) return `${base}?quick=missing`
    if (['requested'].includes(key)) return `${base}?quick=requested`
    if (['approved', 'ready', 'received', 'delivered', 'completed'].includes(key)) return `${base}?quick=ready`
    if (['in_progress', 'uploaded', 'submitted', 'pending_verification'].includes(key)) return `${base}?quick=in_progress`
    return `${base}?status=${encodeURIComponent(key)}`
  }, [])

  const makeCandidatesHref = useCallback((params: Record<string, string | null | undefined>) => {
    const sp = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      const value = String(v || '').trim()
      if (value) sp.set(k, value)
    })
    const qs = sp.toString()
    const base = CRM_APP_PATHS.candidates
    return qs ? `${base}?${qs}` : base
  }, [])
  const drilldownTitle = t('app.dashboard.ops.drilldown')
  const drillInlineClass = 'cursor-pointer hover:underline underline-offset-2 decoration-dotted'

  const rangeInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo)
  const primaryLabel = dimensionOptions.find((opt) => opt.value === pivotPrimary)?.label ?? ''
  const secondaryLabel =
    pivotSecondary === 'none'
      ? t('app.dashboard.labels.no_subgroup')
      : dimensionOptions.find((opt) => opt.value === pivotSecondary)?.label ?? ''
  type BreakdownRow = {
    label: string
    total: number
    hired: number
    lost: number
    conversion: number
    dropoff: number
    avgDaysInStage: number | null
    filterParams: Record<string, string>
  }

  const breakdownRows = useMemo((): BreakdownRow[] => {
    if (!slices?.snapshot?.length) return []
    const m = new Map<
      string,
      {
        label: string
        total: number
        hired: number
        lost: number
        sumDays: number
        timeN: number
        filterParams: Record<string, string>
      }
    >()
    for (const row of slices.snapshot) {
      const label = (getDimensionValues(row, breakdownGroup)[0] || notAvailableLabel).trim() || notAvailableLabel
      const canonical = canonicalStageKey(row.stage, row.stage_label)
      const outcome = determineStageOutcome(canonical, stageLabels)
      let e = m.get(label)
      if (!e) {
        e = { label, total: 0, hired: 0, lost: 0, sumDays: 0, timeN: 0, filterParams: {} }
        m.set(label, e)
      }
      e.total += 1
      if (outcome === 'hired') e.hired += 1
      if (outcome === 'rejected' || outcome === 'declined') e.lost += 1
      if (outcome === 'pipeline' && row.updated_at) {
        const days = (Date.now() - new Date(row.updated_at).getTime()) / DAY_MS
        if (Number.isFinite(days) && days >= 0 && days < 3650) {
          e.sumDays += days
          e.timeN += 1
        }
      }
      if (Object.keys(e.filterParams).length === 0) {
        if (breakdownGroup === 'source' && row.source) e.filterParams = { preferred_channel: row.source }
        else if (breakdownGroup === 'manager' && row.manager_id) e.filterParams = { manager_id: row.manager_id }
        else if (breakdownGroup === 'vacancy' && row.vacancy_id) e.filterParams = { vacancy: row.vacancy_id }
        else if (breakdownGroup === 'company' && row.company_id) e.filterParams = { company_id: row.company_id }
        else if (breakdownGroup === 'country' && row.country) e.filterParams = { country: row.country }
        else if (breakdownGroup === 'stage' && row.stage) e.filterParams = { stage: row.stage }
        else if (breakdownGroup === 'citizenship' && row.citizenship) e.filterParams = { citizenship: row.citizenship }
      }
    }
    return Array.from(m.values())
      .map((e) => ({
        label: e.label,
        total: e.total,
        hired: e.hired,
        lost: e.lost,
        conversion: e.total > 0 ? (e.hired / e.total) * 100 : 0,
        dropoff: e.total > 0 ? (e.lost / e.total) * 100 : 0,
        avgDaysInStage: e.timeN > 0 ? e.sumDays / e.timeN : null,
        filterParams: e.filterParams,
      }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 24)
  }, [breakdownGroup, getDimensionValues, notAvailableLabel, slices?.snapshot, stageLabels])

  const breakdownGroupOptions = useMemo(
    () =>
      (['source', 'manager', 'vacancy', 'country', 'stage'] as const).map((value) => ({
        value: value as PivotDimension,
        label: t(`app.dashboard.dimensions.${value}`),
      })),
    [t],
  )

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.dashboard.title')}
          subtitle={t('app.dashboard.page_subtitle')}
          kind="browse"
          secondaryActions={
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => load()}
              disabled={loading || rangeInvalid}
            >
              {loading ? t('app.dashboard.refresh.loading') : t('app.dashboard.refresh.action')}
            </button>
          }
        />
      </PageShellHeader>
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        {tenantId && retentionStatus?.onboarding_required === true && <OnboardingWizard tenantId={tenantId} />}
        {isOnboardingWizardEnabled() ? <PostWizardWelcomePanel /> : null}
        <DashboardLeadAutoFixCard opsCounters={opsCounters} onRefreshOps={loadOpsCounters} />

        <DashboardFiltersBar
          t={t}
          isFilterVisible={isFilterVisible}
          quickRangeOptions={quickRangeOptions}
          activeRange={activeRange}
          applyQuickRange={applyQuickRange}
          dateFrom={dateFrom}
          setDateFrom={setDateFrom}
          dateTo={dateTo}
          setDateTo={setDateTo}
          setActiveRange={setActiveRange}
          dateField={dateField}
          setDateField={setDateField}
          load={load}
          vacancyFilter={vacancyFilter}
          vacancyOptions={vacancyOptions}
          handleVacancyChange={handleVacancyChange}
          companyFilter={companyFilter}
          companyOptions={companyOptions}
          handleCompanyChange={handleCompanyChange}
          managerFilter={managerFilter}
          managerOptions={managerOptions}
          handleManagerChange={handleManagerChange}
          candidateFilter={candidateFilter}
          setCandidateFilter={setCandidateFilter}
          handleCandidateFilterApply={handleCandidateFilterApply}
          stagesFilter={stagesFilter}
          stageOptions={stageOptions}
          handleStagesChange={handleStagesChange}
          stageView={stageView}
          setStageView={setStageView}
          isClientRole={isClientRole}
          compareWithPrevious={compareWithPrevious}
          setCompareWithPrevious={setCompareWithPrevious}
          handleResetFilters={handleResetFilters}
          handleSavePreset={handleSavePreset}
          handleLoadPreset={handleLoadPreset}
          savedPreset={savedPreset}
          visibleWidgets={visibleWidgets}
          toggleWidget={toggleWidget}
          visibleFilters={visibleFilters}
          toggleFilter={toggleFilter}
          loading={loading}
          periodTotal={periodTotal}
          formatNumber={formatNumber}
        />

        <DashboardExecutiveOverview
          t={t}
          locale={locale}
          formatNumber={formatNumber}
          periodTotal={periodTotal}
          executiveKpis={executiveKpis}
          stageLabels={stageLabels}
          makeCandidatesHref={makeCandidatesHref}
        />

        <DashboardAnalysisPanel
          t={t}
          formatNumber={formatNumber}
          makeCandidatesHref={makeCandidatesHref}
          funnelSteps={funnelSteps}
          breakdownGroup={breakdownGroup}
          setBreakdownGroup={setBreakdownGroup}
          breakdownGroupOptions={breakdownGroupOptions}
          breakdownMetric={breakdownMetric}
          setBreakdownMetric={setBreakdownMetric}
          breakdownRows={breakdownRows}
          opsCounters={opsCounters}
          documentBlockerAnalytics={documentBlockerAnalytics}
        />

        {!can('leads.view') && can('manager.tools') ? (
          <DashboardSectionCollapsible
            storagePrefix={dashUserBase}
            sectionKey="shortcutsHub"
            title={t('app.dashboard.sections.shortcuts.title')}
            subtitle={t('app.dashboard.sections.shortcuts.subtitle')}
            defaultOpen={false}
          >
            <div className="p-4">
              <DashboardAnalyticsHubLinks />
            </div>
          </DashboardSectionCollapsible>
        ) : null}

        {can('leads.view') ? (
          <DashboardSectionCollapsible
            id="lead-conversion"
            storagePrefix={dashUserBase}
            sectionKey="leadFunnel"
            title={t('app.dashboard.sections.lead_funnel.title')}
            subtitle={t('app.dashboard.sections.lead_funnel.subtitle')}
            defaultOpen={false}
          >
            <div className="p-4">
              <Suspense fallback={<div className="px-2 py-4 text-sm text-slate-500">{t('common.loading')}</div>}>
                <AnalyticsLeadConversionFunnelPageLazy embedded />
              </Suspense>
            </div>
          </DashboardSectionCollapsible>
        ) : null}

        <DashboardSectionCollapsible
          storagePrefix={dashUserBase}
          sectionKey="workspaceSlices"
          title={t('app.dashboard.sections.slices.title')}
          subtitle={t('app.dashboard.sections.slices.subtitle')}
          defaultOpen
        >
          <div className="space-y-4 px-1 pb-2 pt-1 sm:px-2">

        <DashboardPivotPanels
          t={t}
          formatNumber={formatNumber}
          isWidgetVisible={isWidgetVisible}
          pivotPrimary={pivotPrimary}
          pivotSecondary={pivotSecondary}
          setPivotPrimary={setPivotPrimary}
          setPivotSecondary={setPivotSecondary}
          pivotData={pivotData}
          dimensionOptions={dimensionOptions}
          primaryLabel={primaryLabel}
          secondaryLabel={secondaryLabel}
          pivotChartContainerRef={pivotChartContainerRef}
          isPivotChartContainerReady={isPivotChartContainerReady}
        />

        <DashboardOpsOverviewPanels
          t={t}
          locale={locale}
          formatNumber={formatNumber}
          makeCandidatesHref={makeCandidatesHref}
          documentQuickFilterHref={documentQuickFilterHref}
          drilldownTitle={drilldownTitle}
          isWidgetVisible={isWidgetVisible}
          handoffStats={handoffStats}
          contactStats={contactStats}
          documentStats={documentStats}
          documentRuntimeKpis={documentRuntimeKpis}
          documentBlockerAnalytics={documentBlockerAnalytics}
          profileSummary={profileSummary}
          stageStackSegments={stageStackSegments}
          errText={errText}
          rangeInvalid={rangeInvalid}
          globalCounts={globalCounts}
          periodTotal={periodTotal}
          dateField={dateField}
          dashboardCompanyLabels={dashboardCompanyLabels}
          businessProfileCards={businessProfileCards}
          businessTypeLabel={businessTypeLabel}
          businessCardHref={businessCardHref}
          groupedStages={groupedStages}
          groupedRejectedReasons={groupedRejectedReasons}
          groupedDeclinedReasons={groupedDeclinedReasons}
          drillInlineClass={drillInlineClass}
        />

        <DashboardPortfolioPanels
          t={t}
          formatNumber={formatNumber}
          makeCandidatesHref={makeCandidatesHref}
          drilldownTitle={drilldownTitle}
          drillInlineClass={drillInlineClass}
          isWidgetVisible={isWidgetVisible}
          slices={slices}
          stageLabels={stageLabels}
          dashboardCompanyLabels={dashboardCompanyLabels}
          sourceStageRows={sourceStageRows}
          docStageStats={docStageStats}
          stageVelocityRows={stageVelocityRows}
          managerLoadRows={managerLoadRows}
          countryHeatmapRows={countryHeatmapRows}
        />
          </div>
        </DashboardSectionCollapsible>
        <DashboardRetentionCenter
          t={t}
          canManageBilling={canManageBilling}
          isTrialTenant={isTrialTenant}
          billingGate={billingGate}
          retentionNudge={retentionNudge}
          dismissRetentionNudge={dismissRetentionNudge}
          trackRetentionEvent={trackRetentionEvent}
          showTrialPanel={showTrialPanel}
          trialCenterClasses={trialCenterClasses}
          trialDaysLeft={trialDaysLeft}
          trialTone={trialTone}
          retentionReport={retentionReport}
          retentionReportLoading={retentionReportLoading}
          retentionReportRows={retentionReportRows}
        />
      </div>
    </PageShell>
  )
}
