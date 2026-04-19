// src/pages/Dashboard.tsx
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import api, { withTenant } from '../api/client'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { useCurrentTenantId } from '../contexts/CurrentTenant'
import { useTenantInfo } from '../contexts/TenantInfo'
import { OnboardingWizard } from '../components/OnboardingWizard'
import { PageBreadcrumb } from '../components/nav/PageBreadcrumb'
import { DashboardAnalyticsHubLinks } from '../components/dashboard/DashboardAnalyticsHubLinks'
import { DashboardLeadAutoFixCard } from '../components/dashboard/DashboardLeadAutoFixCard'
import { DashboardSectionCollapsible } from '../components/dashboard/DashboardSectionCollapsible'

const AnalyticsLeadConversionFunnelPageLazy = lazy(() => import('./AnalyticsLeadConversionFunnelPage'))
import {
  getAnalyticsProfileSummary,
  getHandoffStats,
  getContactAttemptStats,
  getDocumentStats,
} from '../api/analytics'
import { listTenantManagers } from '../api/users'
import { listCandidateStages } from '../api/candidate_stages'
import { usePermissions } from '../hooks/usePermissions'
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

      const [cand, comps, vacs, sliceResp, handoffResp, contactResp, docResp, profileResp] = await Promise.all([
        candidatesClient.get<ListResp<any>>('/candidates', { params: candParams }),
        api.get<ListResp<any>>('/companies/', { params: { limit: 50, offset: 0 } }),
        api.get<ListResp<any>>('/vacancies/', { params: { limit: 50, offset: 0 } }),
        candidatesClient.get<CandidateSlicesResponse>('/analytics/candidate-slices', { params }),
        getHandoffStats(periodParams).catch(() => null),
        getContactAttemptStats(periodParams).catch(() => null),
        getDocumentStats(periodParams).catch(() => null),
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
            stages.map((s) => ({ code: s.code, label: s.label || s.code }))
          )
        } else {
          setStageOptions(
            DEFAULT_STAGE_CODES.map((code) => ({
              code,
              label: t(`app.dashboard.stage_labels.${code}`) || code,
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
    <section className="h-full min-h-0 w-full flex flex-col">
      <div className="min-h-0 flex-1 space-y-0 gap-0 overflow-auto px-0 py-0">
        {tenantId && retentionStatus?.onboarding_required === true && <OnboardingWizard tenantId={tenantId} />}
        <DashboardLeadAutoFixCard opsCounters={opsCounters} onRefreshOps={loadOpsCounters} />
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">{t('app.dashboard.title')}</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600">{t('app.dashboard.page_subtitle')}</p>
          </div>
          <div className="flex items-center gap-2">
            <button className="btn-secondary" onClick={() => load()} disabled={loading || rangeInvalid}>
              {loading ? t('app.dashboard.refresh.loading') : t('app.dashboard.refresh.action')}
            </button>
          </div>
        </div>

        <PageBreadcrumb className="mb-1" />

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

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-6">
          <div>
            <div className="text-sm font-semibold text-slate-900">{t('app.dashboard.analytics.analysis.title')}</div>
            <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.analytics.analysis.subtitle')}</p>
          </div>

          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.dashboard.analytics.funnel.badge')}
            </div>
            <p className="mt-1 text-xs text-slate-500">{t('app.dashboard.analytics.funnel.hint')}</p>
            {funnelSteps.length === 0 ? (
              <div className="mt-3 text-sm text-slate-500">{t('app.dashboard.analytics.funnel.empty')}</div>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-slate-500">
                      <th className="py-2 pr-4">{t('app.dashboard.analytics.funnel.col_stage')}</th>
                      <th className="py-2 pr-4 text-right">{t('app.dashboard.analytics.funnel.col_count')}</th>
                      <th className="py-2 pr-4 text-right">{t('app.dashboard.analytics.funnel.col_step_conv')}</th>
                      <th className="py-2 text-right">{t('app.dashboard.analytics.funnel.col_avg_days')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {funnelSteps.map((step) => (
                      <tr key={step.key} className="border-t border-slate-100">
                        <td className="py-2 pr-4">
                          <Link
                            to={makeCandidatesHref({ stage: step.key })}
                            className="font-medium text-brand-700 hover:underline"
                          >
                            {step.label}
                          </Link>
                        </td>
                        <td className="py-2 pr-4 text-right">{formatNumber(step.count)}</td>
                        <td className="py-2 pr-4 text-right text-slate-600">
                          {step.stepConv != null ? `${step.stepConv.toFixed(1)}%` : '—'}
                        </td>
                        <td className="py-2 text-right text-slate-600">
                          {step.avgDays != null ? `${step.avgDays}d` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.dashboard.analytics.breakdown.badge')}
                </div>
                <p className="mt-1 text-xs text-slate-500">{t('app.dashboard.analytics.breakdown.hint')}</p>
              </div>
              <div className="flex flex-wrap gap-3 text-sm">
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-slate-500">{t('app.dashboard.analytics.breakdown.group')}</span>
                  <select
                    className="input text-sm"
                    value={breakdownGroup}
                    onChange={(e) => setBreakdownGroup(e.target.value as PivotDimension)}
                  >
                    {breakdownGroupOptions.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-slate-500">{t('app.dashboard.analytics.breakdown.metric')}</span>
                  <select
                    className="input text-sm"
                    value={breakdownMetric}
                    onChange={(e) =>
                      setBreakdownMetric(e.target.value as 'count' | 'conversion' | 'time' | 'dropoff')
                    }
                  >
                    <option value="count">{t('app.dashboard.analytics.breakdown.metric_count')}</option>
                    <option value="conversion">{t('app.dashboard.analytics.breakdown.metric_conversion')}</option>
                    <option value="time">{t('app.dashboard.analytics.breakdown.metric_time')}</option>
                    <option value="dropoff">{t('app.dashboard.analytics.breakdown.metric_dropoff')}</option>
                  </select>
                </label>
              </div>
            </div>
            {breakdownRows.length === 0 ? (
              <div className="mt-3 text-sm text-slate-500">{t('app.dashboard.analytics.breakdown.empty')}</div>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-slate-500">
                      <th className="py-2 pr-4">{t('app.dashboard.analytics.breakdown.col_segment')}</th>
                      <th className="py-2 text-right">{t('app.dashboard.analytics.breakdown.col_value')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {breakdownRows.map((row) => {
                      const href =
                        Object.keys(row.filterParams).length > 0
                          ? makeCandidatesHref(row.filterParams)
                          : CRM_APP_PATHS.candidates
                      let valueCell: string
                      if (breakdownMetric === 'count') valueCell = formatNumber(row.total)
                      else if (breakdownMetric === 'conversion') valueCell = `${row.conversion.toFixed(1)}%`
                      else if (breakdownMetric === 'dropoff') valueCell = `${row.dropoff.toFixed(1)}%`
                      else valueCell = row.avgDaysInStage != null ? `${Math.round(row.avgDaysInStage)}d` : '—'
                      return (
                        <tr key={row.label} className="border-t border-slate-100">
                          <td className="py-2 pr-4">
                            <Link to={href} className="font-medium text-brand-700 hover:underline">
                              {row.label}
                            </Link>
                          </td>
                          <td className="py-2 text-right text-slate-800">{valueCell}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.dashboard.analytics.problems.badge')}
            </div>
            <p className="mt-1 text-xs text-slate-500">{t('app.dashboard.analytics.problems.hint')}</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <Link
                to={CRM_APP_DRILLDOWN_HREFS.tasksOverdueReminders}
                className="flex items-center justify-between rounded-lg border border-rose-100 bg-rose-50/60 px-3 py-2 text-sm hover:border-rose-200"
              >
                <span>{t('app.dashboard.analytics.problems.overdue_tasks')}</span>
                <span className="font-semibold text-rose-800">{formatNumber(opsCounters?.overdue_reminders ?? 0)}</span>
              </Link>
              <Link
                to={CRM_APP_DRILLDOWN_HREFS.candidatesQueueNoNextAction}
                className="flex items-center justify-between rounded-lg border border-amber-100 bg-amber-50/60 px-3 py-2 text-sm hover:border-amber-200"
              >
                <span>{t('app.dashboard.analytics.problems.no_next_candidate')}</span>
                <span className="font-semibold text-amber-900">
                  {formatNumber(opsCounters?.no_next_action_candidates ?? 0)}
                </span>
              </Link>
              <Link
                to={CRM_APP_DRILLDOWN_HREFS.leadsProcessedStuck}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm hover:border-brand-200"
              >
                <span>{t('app.dashboard.analytics.problems.stuck_leads')}</span>
                <span className="font-semibold">{formatNumber(opsCounters?.leads_sla_stuck_stage_reminders ?? 0)}</span>
              </Link>
              <Link
                to={CRM_APP_DRILLDOWN_HREFS.tasksLeadsSlaNudges}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm hover:border-brand-200"
              >
                <span>{t('app.dashboard.analytics.problems.sla_leads')}</span>
                <span className="font-semibold">{formatNumber(opsCounters?.leads_sla_no_next_action_reminders ?? 0)}</span>
              </Link>
              <Link
                to={`${CRM_APP_PATHS.documents}?quick=missing`}
                className="flex items-center justify-between rounded-lg border border-blue-100 bg-blue-50/60 px-3 py-2 text-sm hover:border-blue-200"
              >
                <span>{t('app.dashboard.analytics.problems.docs_missing')}</span>
                <span className="font-semibold text-blue-900">
                  {formatNumber(documentBlockerAnalytics.missingOrRequested)}
                </span>
              </Link>
            </div>
          </div>
        </div>

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

        {((isWidgetVisible('handoff') && handoffStats) || (isWidgetVisible('contact') && contactStats) || (isWidgetVisible('documents') && documentStats)) && (
          <div className="grid gap-4 md:grid-cols-3">
            {isWidgetVisible('handoff') && handoffStats && (
              <div className="card p-4">
                <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.widgets.handoff.title')}</div>
                <div className="text-xs text-slate-500 mt-0.5">{t('app.dashboard.widgets.handoff.subtitle')}</div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <Link
                    to={makeCandidatesHref({ handoff_status: 'pending' })}
                    className="rounded-lg bg-slate-50 p-2 hover:bg-slate-100"
                    title={drilldownTitle}
                  >
                    <span className="text-slate-500">{t('app.dashboard.widgets.handoff.requested')}</span>
                    <div className="font-semibold">{formatNumber(handoffStats.total_requested)}</div>
                  </Link>
                  <Link
                    to={makeCandidatesHref({ handoff_status: 'accepted' })}
                    className="rounded-lg bg-emerald-50 p-2 hover:bg-emerald-100"
                    title={drilldownTitle}
                  >
                    <span className="text-slate-500">{t('app.dashboard.widgets.handoff.accepted')}</span>
                    <div className="font-semibold text-emerald-700">{formatNumber(handoffStats.total_accepted)}</div>
                  </Link>
                  <Link
                    to={makeCandidatesHref({ handoff_status: 'rejected' })}
                    className="rounded-lg bg-rose-50 p-2 hover:bg-rose-100"
                    title={drilldownTitle}
                  >
                    <span className="text-slate-500">{t('app.dashboard.widgets.handoff.rejected')}</span>
                    <div className="font-semibold text-rose-700">{formatNumber(handoffStats.total_rejected)}</div>
                  </Link>
                  <Link
                    to={makeCandidatesHref({ handoff_status: 'returned' })}
                    className="rounded-lg bg-amber-50 p-2 hover:bg-amber-100"
                    title={drilldownTitle}
                  >
                    <span className="text-slate-500">{t('app.dashboard.widgets.handoff.returned')}</span>
                    <div className="font-semibold text-amber-700">{formatNumber(handoffStats.total_returned)}</div>
                  </Link>
                </div>
              </div>
            )}
            {isWidgetVisible('contact') && contactStats && (
              <div className="card p-4">
                <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.widgets.contact_attempts.title')}</div>
                <div className="text-xs text-slate-500 mt-0.5">{t('app.dashboard.widgets.contact_attempts.subtitle')}</div>
                <div className="mt-3 space-y-2 text-sm">
                  <Link
                    to={makeCandidatesHref({ contact_attempts: 'some' })}
                    className="flex justify-between rounded px-1 py-0.5 hover:bg-slate-50"
                    title={drilldownTitle}
                  >
                    <span className="text-slate-500">{t('app.dashboard.widgets.contact_attempts.total')}</span>
                    <span className="font-semibold">{formatNumber(contactStats.total_attempts)}</span>
                  </Link>
                  <Link
                    to={makeCandidatesHref({ contact_attempts: 'some' })}
                    className="flex justify-between rounded px-1 py-0.5 hover:bg-slate-50"
                    title={drilldownTitle}
                  >
                    <span className="text-slate-500">{t('app.dashboard.widgets.contact_attempts.avg')}</span>
                    <span className="font-semibold">{contactStats.avg_per_candidate.toFixed(1)}</span>
                  </Link>
                  <Link
                    to={makeCandidatesHref({ contact_attempts: 'limit_reached' })}
                    className="flex justify-between rounded px-1 py-0.5 hover:bg-slate-50"
                    title={drilldownTitle}
                  >
                    <span className="text-slate-500">{t('app.dashboard.widgets.contact_attempts.limit_reached')}</span>
                    <span className="font-semibold">{formatNumber(contactStats.limit_reached_count)}</span>
                  </Link>
                </div>
              </div>
            )}
            {isWidgetVisible('documents') && documentStats && (
              <div className="card p-4">
                <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.widgets.documents.title')}</div>
                <div className="text-xs text-slate-500 mt-0.5">{t('app.dashboard.widgets.documents.subtitle')}</div>
                <div className="mt-3 space-y-2 text-sm">
                  <Link
                    to={CRM_APP_PATHS.documents}
                    title={drilldownTitle}
                    className="flex justify-between rounded px-1 py-0.5 hover:bg-slate-50"
                  >
                    <span className="text-slate-500">{t('app.dashboard.widgets.documents.total')} <span className="text-[10px]">↗</span></span>
                    <span className="font-semibold">{formatNumber(documentStats.total_docs)}</span>
                  </Link>
                  <Link
                    to={`${CRM_APP_PATHS.documents}?quick=ready`}
                    title={drilldownTitle}
                    className="flex justify-between rounded px-1 py-0.5 hover:bg-slate-50"
                  >
                    <span className="text-slate-500">{t('app.dashboard.widgets.documents.complete')} <span className="text-[10px]">↗</span></span>
                    <span className="font-semibold">{formatNumber(documentStats.candidates_with_complete_docs)}</span>
                  </Link>
                  {Object.keys(documentStats.by_status || {}).length > 0 && (
                    <div className="mt-2 pt-2 border-t border-slate-100">
                      <span className="text-xs text-slate-500">{t('app.dashboard.widgets.documents.by_status')}</span>
                      <ul className="mt-1 space-y-0.5 text-xs">
                        {Object.entries(documentStats.by_status || {}).slice(0, 5).map(([status, count]) => (
                          <li key={status} className="flex justify-between">
                            <Link className="hover:underline" to={documentQuickFilterHref(status)}>{status}</Link>
                            <span>{formatNumber(count)}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="mt-2 pt-2 border-t border-slate-100">
                    <div className="text-xs text-slate-500">
                      {t('app.dashboard.widgets.documents.blockers_title')}
                    </div>
                    <div className="mt-1 grid grid-cols-1 gap-1.5 text-xs">
                      <Link
                        to={`${CRM_APP_PATHS.documents}?quick=missing`}
                        className="flex items-center justify-between rounded bg-blue-50 px-2 py-1 text-blue-800 hover:bg-blue-100"
                      >
                        <span>{t('app.dashboard.widgets.documents.blockers_missing')}</span>
                        <span className="font-semibold">{formatNumber(documentBlockerAnalytics.missingOrRequested)}</span>
                      </Link>
                      <Link
                        to={`${CRM_APP_PATHS.documents}?quick=in_progress`}
                        className="flex items-center justify-between rounded bg-amber-50 px-2 py-1 text-amber-800 hover:bg-amber-100"
                      >
                        <span>{t('app.dashboard.widgets.documents.blockers_review')}</span>
                        <span className="font-semibold">{formatNumber(documentBlockerAnalytics.awaitingReview)}</span>
                      </Link>
                      <Link
                        to={`${CRM_APP_PATHS.documents}?status=rejected`}
                        className="flex items-center justify-between rounded bg-rose-50 px-2 py-1 text-rose-800 hover:bg-rose-100"
                      >
                        <span>{t('app.dashboard.widgets.documents.blockers_problematic')}</span>
                        <span className="font-semibold">{formatNumber(documentBlockerAnalytics.problematic)}</span>
                      </Link>
                    </div>
                    {documentBlockerAnalytics.total > 0 ? (
                      <div className="mt-2 text-[11px] text-slate-600">
                        {t('app.dashboard.widgets.documents.blockers_total_hint', { values: { count: formatNumber(documentBlockerAnalytics.total) } })}
                      </div>
                    ) : null}
                    {profileSummary?.business_type === 'services' && documentBlockerAnalytics.estimatedBlockedRevenue > 0 ? (
                      <div className="mt-2 rounded border border-rose-200 bg-rose-50 px-2 py-1.5 text-[11px] text-rose-800">
                        {t('app.dashboard.widgets.documents.blockers_cost_hint', { values: {
                            amount: new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US', {
                              style: 'currency',
                              currency: 'EUR',
                              maximumFractionDigits: 0,
                            }).format(documentBlockerAnalytics.estimatedBlockedRevenue),
                          } })}
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {isWidgetVisible('stageStack') && stageStackSegments.length > 0 && (
          <div className="card p-4 space-y-3">
            <div>
              <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.stages.stack_title')}</div>
              <div className="text-xs text-slate-500">{t('app.dashboard.stages.stack_subtitle')}</div>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100 flex">
              {stageStackSegments.map((segment) => (
                <div
                  key={`stack-${segment.label}`}
                  className={['h-full', STAGE_STACK_COLORS[segment.outcome]].join(' ')}
                  style={{ width: `${segment.percent}%` }}
                  title={`${segment.label}: ${formatNumber(segment.value)} (${segment.percent}%)`}
                />
              ))}
            </div>
            <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2 lg:grid-cols-3">
              {stageStackSegments.slice(0, 6).map((segment) => (
                <Link
                  key={`legend-${segment.label}`}
                  to={makeCandidatesHref({ stage: segment.stageKeyForFilter })}
                  className="flex items-center gap-2 rounded px-1 py-0.5 hover:bg-slate-50"
                >
                  <span className={`h-2 w-2 rounded-full ${STAGE_STACK_COLORS[segment.outcome]}`} />
                  <span className="truncate">
                    {segment.label} · {segment.percent}%
                  </span>
                </Link>
              ))}
            </div>
          </div>
        )}

        {errText && (
          <div className="text-sm text-red-600 whitespace-pre-wrap break-words">
            {errText}
          </div>
        )}

        {rangeInvalid && (
          <div className="text-sm text-red-600">{t('app.dashboard.errors.range_invalid')}</div>
        )}

        {isWidgetVisible('globalStats') && (
        <div className="grid w-full gap-4 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
          <Link to={CRM_APP_PATHS.candidates} className="card block p-4 hover:border-brand-200">
            <div className="text-slate-500 text-sm mb-1">{t('app.dashboard.stats.candidates_total')}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.candidates)}</div>
          </Link>
          <Link to={CRM_APP_PATHS.clientsDirectory} className="card block p-4 hover:border-brand-200">
            <div className="text-slate-500 text-sm mb-1">{dashboardCompanyLabels.plural}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.companies)}</div>
          </Link>
          <Link to={CRM_APP_PATHS.vacancies} className="card block p-4 hover:border-brand-200">
            <div className="text-slate-500 text-sm mb-1">{t('app.dashboard.stats.vacancies')}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.vacancies)}</div>
          </Link>
          <Link
            to={CRM_APP_PATHS.candidates}
            className="card block p-4 border border-brand-100 hover:border-brand-200"
          >
            <div className="text-slate-500 text-sm mb-1">{t('app.dashboard.stats.period')}</div>
            <div className="text-2xl font-semibold">{formatNumber(periodTotal)}</div>
            <div className="text-xs text-slate-500 mt-1">
              {dateField === 'created'
                ? t('app.dashboard.stats.period_suffix_created')
                : t('app.dashboard.stats.period_suffix_updated')}
            </div>
          </Link>
        </div>
        )}

        {businessProfileCards.length > 0 && (
          <div className="card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold">
                {t('app.dashboard.business.title')}
              </div>
              <div className="text-xs text-slate-500">
                {t('app.dashboard.business.type_label')}: {businessTypeLabel}
              </div>
            </div>
            <div className="grid w-full gap-3 grid-cols-[repeat(auto-fill,minmax(180px,1fr))]">
              {businessProfileCards.map((card) => (
                <Link key={card.key} to={businessCardHref(card.key)} className="block rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 hover:border-brand-200">
                  <div className="text-xs text-slate-500">{card.label}</div>
                  <div className="mt-1 text-xl font-semibold text-slate-900">{formatNumber(card.value)}</div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {(isWidgetVisible('stages') || isWidgetVisible('reasons')) && (
        <div className="grid gap-4 lg:grid-cols-3">
          {isWidgetVisible('stages') && (
          <div className="card p-4 lg:col-span-2">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-sm font-semibold">{t('app.dashboard.stages.title')}</div>
                <div className="text-xs text-slate-500">{t('app.dashboard.stages.subtitle')}</div>
              </div>
            </div>
            {slices?.stages?.length ? (
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('app.dashboard.stages.table.status')}</th>
                    <th className="text-right">{t('app.dashboard.stages.table.count')}</th>
                  </tr>
                </thead>
                <tbody>
                {groupedStages.map((stage, index) => (
                  <tr key={`grouped-stage-${index}-${stage.keys.join('-')}`}>
                    <td>
                          <Link to={makeCandidatesHref({ stage: stage.keys[0] })} title={drilldownTitle} className={drillInlineClass}>
                        {stage.label}
                      </Link>
                    </td>
                    <td className="text-right font-medium">{formatNumber(stage.count)}</td>
                  </tr>
                ))}
                </tbody>
              </table>
            ) : (
              <div className="text-sm text-slate-500">{t('app.dashboard.stages.empty')}</div>
            )}
          </div>
          )}
          {isWidgetVisible('reasons') && (
          <div className="card p-4 space-y-4">
            <div>
              <div className="text-sm font-semibold mb-2">{t('app.dashboard.reasons.rejected_title')}</div>
              {groupedRejectedReasons.length ? (
                <ul className="space-y-1 text-sm">
                  {groupedRejectedReasons.slice(0, 8).map((item, index) => (
                    <li key={`rejected-grouped-${index}-${Array.from(item.codes).join('-') || item.label}`} className="flex justify-between gap-2">
                      <Link
                        to={makeCandidatesHref({ stage: 'rejected', status_reason: Array.from(item.codes)[0] || item.label })}
                        className="truncate hover:underline"
                      >
                        {item.label}
                      </Link>
                      <span className="font-medium">{formatNumber(item.count)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.reasons.rejected_empty')}</div>
              )}
            </div>
            <div>
              <div className="text-sm font-semibold mb-2">{t('app.dashboard.reasons.declined_title')}</div>
              {groupedDeclinedReasons.length ? (
                <ul className="space-y-1 text-sm">
                  {groupedDeclinedReasons.slice(0, 8).map((item, index) => (
                    <li key={`declined-grouped-${index}-${Array.from(item.codes).join('-') || item.label}`} className="flex justify-between gap-2">
                      <Link
                        to={makeCandidatesHref({ stage: 'declined', status_reason: Array.from(item.codes)[0] || item.label })}
                        className="truncate hover:underline"
                      >
                        {item.label}
                      </Link>
                      <span className="font-medium">{formatNumber(item.count)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.reasons.declined_empty')}</div>
              )}
            </div>
          </div>
          )}
        </div>
        )}

        {(isWidgetVisible('companies') || isWidgetVisible('vacancies')) && (
        <div className="grid gap-4 lg:grid-cols-2">
          {isWidgetVisible('companies') && (
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold">
                {t('app.dashboard.companies.title', { values: { label: dashboardCompanyLabels.plural } })}
              </div>
              <div className="text-xs text-slate-500">
                {t('app.dashboard.companies.subtitle', { values: { label: dashboardCompanyLabels.plural.toLowerCase() } })}
              </div>
            </div>
            {slices?.companies?.length ? (
              <table className="table">
                <thead>
                  <tr>
                    <th>{dashboardCompanyLabels.singular}</th>
                    <th className="text-right">{t('app.dashboard.companies.table.total')}</th>
                    <th className="text-right">{t('app.dashboard.companies.table.in_pipeline')}</th>
                    <th className="text-right">{t('app.dashboard.companies.table.hired')}</th>
                    <th className="text-right">{t('app.dashboard.companies.table.rejected')}</th>
                  </tr>
                </thead>
                <tbody>
                  {slices.companies.map((item) => {
                    const highlight = stageHighlights(item.by_stage, stageLabels)
                    return (
                      <tr key={`company-${item.key}`}>
                        <td className="truncate">
                          <Link to={makeCandidatesHref({ q: item.label })} title={drilldownTitle} className={drillInlineClass}>
                            {item.label}
                          </Link>
                        </td>
                        <td className="text-right font-medium">
                          <Link to={makeCandidatesHref({ q: item.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(item.count)}
                          </Link>
                        </td>
                        <td className="text-right">
                          <Link to={makeCandidatesHref({ q: item.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(highlight.pipeline)}
                          </Link>
                        </td>
                        <td className="text-right text-emerald-600">
                          <Link to={makeCandidatesHref({ q: item.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(highlight.hired)}
                          </Link>
                        </td>
                        <td className="text-right text-red-600">
                          <Link to={makeCandidatesHref({ q: item.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(highlight.rejected + highlight.declined)}
                          </Link>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            ) : (
              <div className="text-sm text-slate-500">
                {t('app.dashboard.companies.empty', { values: { label: dashboardCompanyLabels.singular.toLowerCase() } })}
              </div>
            )}
          </div>
          )}
          {isWidgetVisible('vacancies') && (
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold">{t('app.dashboard.vacancies.title')}</div>
              <div className="text-xs text-slate-500">{t('app.dashboard.vacancies.subtitle')}</div>
            </div>
            {slices?.vacancies?.length ? (
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('app.dashboard.vacancies.table.vacancy')}</th>
                    <th className="text-right">{t('app.dashboard.vacancies.table.total')}</th>
                    <th className="text-right">{t('app.dashboard.vacancies.table.in_pipeline')}</th>
                    <th className="text-right">{t('app.dashboard.vacancies.table.hired')}</th>
                    <th className="text-right">{t('app.dashboard.vacancies.table.rejected')}</th>
                  </tr>
                </thead>
                <tbody>
                  {slices.vacancies.map((item) => {
                    const highlight = stageHighlights(item.by_stage, stageLabels)
                    return (
                      <tr key={`vacancy-${item.key}`}>
                        <td className="truncate">
                          <Link to={makeCandidatesHref({ vacancy: item.key || item.label })} title={drilldownTitle} className={drillInlineClass}>
                            {item.label}
                          </Link>
                        </td>
                        <td className="text-right font-medium">
                          <Link to={makeCandidatesHref({ vacancy: item.key || item.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(item.count)}
                          </Link>
                        </td>
                        <td className="text-right">
                          <Link to={makeCandidatesHref({ vacancy: item.key || item.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(highlight.pipeline)}
                          </Link>
                        </td>
                        <td className="text-right text-emerald-600">
                          <Link to={makeCandidatesHref({ vacancy: item.key || item.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(highlight.hired)}
                          </Link>
                        </td>
                        <td className="text-right text-red-600">
                          <Link to={makeCandidatesHref({ vacancy: item.key || item.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(highlight.rejected + highlight.declined)}
                          </Link>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            ) : (
              <div className="text-sm text-slate-500">{t('app.dashboard.vacancies.empty')}</div>
            )}
          </div>
          )}
        </div>
        )}

        {(isWidgetVisible('sources') || isWidgetVisible('docsRisk') || isWidgetVisible('velocity')) && (sourceStageRows.length > 0 || docStageStats.total > 0 || stageVelocityRows.length > 0) && (
          <div className="grid gap-4 lg:grid-cols-3">
            {isWidgetVisible('sources') && (
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold">{t('app.dashboard.sources.detail_title')}</div>
                <div className="text-xs text-slate-500">{t('app.dashboard.sources.detail_subtitle')}</div>
              </div>
              {sourceStageRows.length ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t('app.dashboard.sources.table.source')}</th>
                      <th className="text-right">{t('app.dashboard.sources.table.pipeline')}</th>
                      <th className="text-right">{t('app.dashboard.sources.table.hired')}</th>
                      <th className="text-right">{t('app.dashboard.sources.table.rejected')}</th>
                      <th className="text-right">{t('app.dashboard.sources.table.total')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sourceStageRows.map((row) => (
                      <tr key={`source-${row.label}`}>
                        <td className="truncate">
                          <Link
                            to={makeCandidatesHref({ preferred_channel: row.label })}
                            title={drilldownTitle}
                            className={drillInlineClass}
                          >
                            {row.label}
                          </Link>
                        </td>
                        <td className="text-right">
                          <Link
                            to={makeCandidatesHref({ preferred_channel: row.label })}
                            title={drilldownTitle}
                            className={drillInlineClass}
                          >
                            {formatNumber(row.highlight.pipeline)}
                          </Link>
                        </td>
                        <td className="text-right text-emerald-600">
                          <Link
                            to={makeCandidatesHref({ preferred_channel: row.label })}
                            title={drilldownTitle}
                            className={drillInlineClass}
                          >
                            {formatNumber(row.highlight.hired)}
                          </Link>
                        </td>
                        <td className="text-right text-rose-600">
                          <Link
                            to={makeCandidatesHref({ preferred_channel: row.label })}
                            title={drilldownTitle}
                            className={drillInlineClass}
                          >
                            {formatNumber(row.highlight.rejected + row.highlight.declined)}
                          </Link>
                        </td>
                        <td className="text-right font-semibold">
                          <Link
                            to={makeCandidatesHref({ preferred_channel: row.label })}
                            title={drilldownTitle}
                            className={drillInlineClass}
                          >
                            {formatNumber(row.total)}
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.sources.empty')}</div>
              )}
            </div>
            )}
            {isWidgetVisible('docsRisk') && (
            <div className="card p-4 space-y-3">
              <div>
                <div className="text-sm font-semibold">{t('app.dashboard.docs_risk.title')}</div>
                <div className="text-xs text-slate-500">{t('app.dashboard.docs_risk.subtitle')}</div>
              </div>
              {docStageStats.total ? (
                <div className="space-y-3">
                  {(['waiting', 'attention', 'ready'] as const).map((bucket) => {
                    const value = docStageStats[bucket]
                    const percent = docStageStats.total ? Math.round((value / docStageStats.total) * 100) : 0
                    const barColor =
                      bucket === 'ready'
                        ? 'bg-emerald-400'
                        : bucket === 'attention'
                          ? 'bg-amber-400'
                          : 'bg-brand-400'
                    return (
                      <div key={bucket} className="space-y-1">
                        <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
                          <Link
                            to={
                              bucket === 'ready'
                                ? `${CRM_APP_PATHS.documents}?quick=ready`
                                : bucket === 'attention'
                                  ? `${CRM_APP_PATHS.documents}?status=rejected`
                                  : `${CRM_APP_PATHS.documents}?quick=requested`
                            }
                            className="hover:underline"
                          >
                            {t(`app.dashboard.docs_risk.${bucket}`)}
                          </Link>
                          <span>{percent}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-100">
                          <div
                            className={`h-full rounded-full ${barColor}`}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                        <div className="text-xs text-slate-500">
                          {t('app.dashboard.docs_risk.count', { values: { count: formatNumber(value) } })}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.docs_risk.empty')}</div>
              )}
            </div>
            )}
            {isWidgetVisible('velocity') && (
            <div className="card p-4 space-y-3">
              <div>
                <div className="text-sm font-semibold">{t('app.dashboard.velocity.title')}</div>
                <div className="text-xs text-slate-500">{t('app.dashboard.velocity.subtitle')}</div>
              </div>
              {stageVelocityRows.length ? (
                <div className="space-y-2">
                  {stageVelocityRows.map((row) => (
                    <div key={row.stageCode} className="relative overflow-hidden rounded-xl border border-brand-50">
                      <div
                        className="absolute inset-y-0 left-0 bg-brand-500/20"
                        style={{ width: `${Math.max(row.intensity * 100, 8)}%` }}
                      />
                      <Link
                        to={makeCandidatesHref({ stage: row.stageCode })}
                        className="relative flex items-center justify-between px-3 py-2 text-sm"
                        title={drilldownTitle}
                      >
                        <div>
                          <div className="font-medium">{row.label}</div>
                          <div className="text-xs text-slate-500">
                            {t('app.dashboard.velocity.avg', { values: { value: Math.round(row.avgDays) } })}
                            {' · '}
                            {t('app.dashboard.velocity.p90', { values: { value: Math.round(row.p90) } })}
                          </div>
                        </div>
                        <div className="text-xs text-slate-500">
                          {t('app.dashboard.velocity.count', { values: { value: formatNumber(row.total) } })}
                        </div>
                      </Link>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.velocity.empty')}</div>
              )}
            </div>
            )}
          </div>
        )}

        {(isWidgetVisible('managerLoad') || isWidgetVisible('countries')) && (
        <div className="grid gap-4 lg:grid-cols-2">
          {isWidgetVisible('managerLoad') && (
          <div className="card p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold">{t('app.dashboard.manager_load.title')}</div>
              <div className="text-xs text-slate-500">{t('app.dashboard.manager_load.subtitle')}</div>
            </div>
            {managerLoadRows.length ? (
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('app.dashboard.manager_load.manager')}</th>
                    <th className="text-right">{t('app.dashboard.manager_load.pipeline')}</th>
                    <th className="text-right">{t('app.dashboard.manager_load.total')}</th>
                  </tr>
                </thead>
                <tbody>
                  {managerLoadRows.map((row) => (
                    <tr key={row.label}>
                      <td>
                        {row.managerIdForFilter ? (
                          <Link
                            to={makeCandidatesHref({ manager_id: row.managerIdForFilter })}
                            title={drilldownTitle}
                            className={drillInlineClass}
                          >
                            {row.label}
                          </Link>
                        ) : (
                          <span>{row.label}</span>
                        )}
                      </td>
                      <td className="text-right font-semibold">
                        {row.managerIdForFilter ? (
                          <Link
                            to={makeCandidatesHref({ manager_id: row.managerIdForFilter })}
                            title={drilldownTitle}
                            className={drillInlineClass}
                          >
                            {formatNumber(row.pipeline)}
                          </Link>
                        ) : (
                          <span>{formatNumber(row.pipeline)}</span>
                        )}
                      </td>
                      <td className="text-right text-slate-600">
                        {row.managerIdForFilter ? (
                          <Link
                            to={makeCandidatesHref({ manager_id: row.managerIdForFilter })}
                            title={drilldownTitle}
                            className={drillInlineClass}
                          >
                            {formatNumber(row.total)}
                          </Link>
                        ) : (
                          <span>{formatNumber(row.total)}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-sm text-slate-500">{t('app.dashboard.manager_load.empty')}</div>
            )}
          </div>
          )}
          {isWidgetVisible('countries') && (
          <div className="card p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold">{t('app.dashboard.country_heatmap.title')}</div>
              <div className="text-xs text-slate-500">{t('app.dashboard.country_heatmap.subtitle')}</div>
            </div>
            {countryHeatmapRows.length ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {countryHeatmapRows.map((row) => (
                  <div
                    key={`country-heat-${row.label}`}
                    className="rounded-2xl p-3 text-sm font-medium text-white shadow-inner"
                    style={{
                      background: `linear-gradient(135deg, rgba(59,130,246,${
                        0.35 + row.intensity * 0.45
                      }), rgba(99,102,241,${0.45 + row.intensity * 0.35}))`,
                    }}
                  >
                    <div>{row.label}</div>
                    <div className="text-xs text-white/80">{formatNumber(row.count)}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-slate-500">{t('app.dashboard.country_heatmap.empty')}</div>
            )}
          </div>
          )}
        </div>
        )}
          </div>
        </DashboardSectionCollapsible>
        {retentionNudge && (
          <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">
                  {t('app.dashboard.retention.badge')}
                </p>
                <h2 className="text-sm font-semibold text-brand-950">
                  {retentionNudge.activationDone
                    ? t('app.dashboard.retention.post_activation.title')
                    : t(`app.dashboard.retention.${retentionNudge.dayKey}.title`)}
                </h2>
                <p className="text-xs text-brand-900/90">
                  {retentionNudge.activationDone
                    ? t('app.dashboard.retention.post_activation.subtitle')
                    : t(`app.dashboard.retention.${retentionNudge.dayKey}.subtitle`)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  to={retentionNudge.href}
                  className="btn-secondary btn-sm"
                  onClick={() =>
                    trackRetentionEvent('cta_click', {
                      day: retentionNudge.day,
                      stepKey: retentionNudge.stepKey,
                      href: retentionNudge.href,
                      activationDone: retentionNudge.activationDone,
                    })
                  }
                >
                  {retentionNudge.activationDone
                    ? t('app.dashboard.retention.cta_billing')
                    : (() => {
                        const full = `app.dashboard.retention.cta_step.${retentionNudge.stepKey}`
                        const out = t(full as any)
                        return out === full ? t('app.dashboard.retention.cta_step.fallback') : out
                      })()}
                </Link>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => {
                    trackRetentionEvent('dismiss', {
                      day: retentionNudge.day,
                      stepKey: retentionNudge.stepKey,
                      href: retentionNudge.href,
                      activationDone: retentionNudge.activationDone,
                    })
                    dismissRetentionNudge()
                  }}
                >
                  {t('app.dashboard.retention.dismiss')}
                </button>
              </div>
            </div>
          </div>
        )}
        {billingGate?.side_effects_blocked && canManageBilling && (
          <div className="rounded-xl border border-rose-400 bg-rose-50 p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-rose-900">
                  {t('app.dashboard.billing_gate.badge')}
                </p>
                <h2 className="text-sm font-semibold text-rose-950">
                  {t('app.dashboard.billing_gate.blocked_title')}
                </h2>
                <p className="text-xs text-rose-900/90">
                  {billingGate.block_reason === 'past_due'
                    ? t('app.dashboard.billing_gate.blocked_subtitle_past_due')
                    : t('app.dashboard.billing_gate.blocked_subtitle_trial_expired')}
                </p>
              </div>
              <Link to={CRM_APP_PATHS.settingsBilling} className="btn-secondary">
                {t('app.dashboard.billing_gate.cta')}
              </Link>
            </div>
          </div>
        )}
        {showTrialPanel && (
          <div className={trialCenterClasses.wrapper}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className={trialCenterClasses.badge}>
                  {t('app.dashboard.trial_center.badge')}
                </p>
                <h2 className={trialCenterClasses.title}>
                  {billingGate?.trial_grace_active
                    ? t('app.dashboard.trial_center.grace_title')
                    : trialDaysLeft != null
                      ? t('app.dashboard.trial_center.title_with_days', { values: { days: trialDaysLeft } })
                      : t('app.dashboard.trial_center.title')}
                </h2>
                <p className={trialCenterClasses.subtitle}>
                  {billingGate?.trial_grace_active
                    ? t('app.dashboard.trial_center.grace_subtitle', {
                        values: {
                          hours:
                            billingGate.side_effect_grace_hours_remaining != null
                              ? Math.max(0, Math.ceil(billingGate.side_effect_grace_hours_remaining))
                              : 0,
                        },
                      })
                    : t('app.dashboard.trial_center.subtitle')}
                </p>
                {trialTone === 'critical' && (
                  <span className={trialCenterClasses.urgency}>
                    {t('app.dashboard.trial_center.urgency_critical')}
                  </span>
                )}
                {trialTone === 'warning' && (
                  <span className={trialCenterClasses.urgency}>
                    {t('app.dashboard.trial_center.urgency_warning')}
                  </span>
                )}
              </div>
              {canManageBilling && (
                <Link to={CRM_APP_PATHS.settingsBilling} className="btn-secondary">
                  {t('app.dashboard.trial_center.open_billing')}
                </Link>
              )}
            </div>
            <p className={trialCenterClasses.legal}>
              {t('app.dashboard.trial_center.legal_prefix')}{' '}
              <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
                {t('app.dashboard.trial_center.legal_terms')}
              </a>
              {', '}
              <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
                {t('app.dashboard.trial_center.legal_privacy')}
              </a>
              {', '}
              <a href="/legal/cookies.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
                {t('app.dashboard.trial_center.legal_cookies')}
              </a>
              .
            </p>
            {canManageBilling && isTrialTenant && (
              <div className="mt-3 rounded-lg border border-slate-200 bg-white/80 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-700">
                    {t('app.dashboard.trial_center.retention.title')}
                  </p>
                  {retentionReportLoading && (
                    <span className="text-[11px] text-slate-500">
                      {t('app.dashboard.trial_center.retention.loading')}
                    </span>
                  )}
                </div>
                <div className="overflow-x-auto">
                  <table className="table table-sm">
                    <thead>
                      <tr>
                        <th>{t('app.dashboard.trial_center.retention.columns.day')}</th>
                        <th>{t('app.dashboard.trial_center.retention.columns.impression')}</th>
                        <th>{t('app.dashboard.trial_center.retention.columns.click')}</th>
                        <th>{t('app.dashboard.trial_center.retention.columns.dismiss')}</th>
                        <th>{t('app.dashboard.trial_center.retention.columns.ctr')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {retentionReportRows.map((row) => (
                        <tr key={row.key}>
                          <td>{row.label}</td>
                          <td>{row.impression}</td>
                          <td>{row.ctaClick}</td>
                          <td>{row.dismiss}</td>
                          <td>{row.ctr.toFixed(2)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-2 text-xs text-slate-600">
                  {t('app.dashboard.trial_center.retention.summary', { values: {
                      impression: retentionReport?.totals?.impression ?? 0,
                      click: retentionReport?.totals?.cta_click ?? 0,
                      dismiss: retentionReport?.totals?.dismiss ?? 0,
                      ctr: Number(retentionReport?.totals?.ctr_percent ?? 0).toFixed(2),
                    } })}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
