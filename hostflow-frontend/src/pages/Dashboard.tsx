// src/pages/Dashboard.tsx
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import api, { getOnboardingStatus, type OnboardingStatus, withTenant } from '../api/client'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { useCurrentTenantId } from '../contexts/CurrentTenant'
import { useTenantInfo } from '../contexts/TenantInfo'
import { OnboardingWizard } from '../components/OnboardingWizard'
import {
  getTrialRetentionReport,
  getAnalyticsProfileSummary,
  getHandoffStats,
  getContactAttemptStats,
  getDocumentStats,
  recordTrialRetentionEvent,
  type TrialRetentionReport,
} from '../api/analytics'
import { listTenantManagers } from '../api/users'
import { getBillingSubscription } from '../api/billing'
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
import { DEFAULT_VISIBLE_WIDGETS, DEFAULT_VISIBLE_FILTERS, type DashboardFilterId } from '../modules/dashboard/types'
import { formatDateInput, calcRange, calcPrevPeriod, formatDelta, normalizeKey, normalizeTotal } from '../modules/dashboard/utils'
import { getRegionDisplayName } from '../utils/catalogLocale'
import { toCSV } from '../modules/candidates/candidateUtils'
import { ACTIVATION_PATHS, getRetentionNextPath, getRetentionStepKey } from '../app/activationRoutes'

// StageLabelConfig, normalizeKey are now imported from modules/dashboard

const DEFAULT_STAGE_LABELS: StageLabelConfig = {
  hired: [],
  rejected: [],
  declined: [],
}

const STAGE_CODE_ALIASES: Record<string, string> = {
  hired: 'employed',
  employeed: 'employed',
  employment: 'employed',
  probation: 'probation_ok',
  probation_done: 'probation_ok',
  probation_ok: 'probation_ok',
  hired_stage: 'employed',
}

const STAGE_LABEL_ALIASES: Record<string, string> = {
  new: 'new',
  new_lead: 'new',
  новый: 'new',
  nowy: 'new',
  nowy_: 'new',
  nowy_lead: 'new',
  contacted: 'contacted',
  contact_established: 'contacted',
  контакт_установлен: 'contacted',
  kontakt_nawiązany: 'contacted',
  kontakt_nawiazany: 'contacted',
  kontakt_nawiązany_: 'contacted',
  interview: 'contacted',
  questionnaire_submitted: 'questionnaire_submitted',
  анкета_заполнена: 'questionnaire_submitted',
  kwestionariusz_wysłany: 'questionnaire_submitted',
  kwestionariusz_wyslany: 'questionnaire_submitted',
  waiting_for_documents: 'docs_wait',
  awaiting_documents: 'docs_wait',
  ожидаем_документы: 'docs_wait',
  czekamy_na_dokumenty: 'docs_wait',
  czekamy_na_dokumenty_: 'docs_wait',
  documents_received: 'docs_got',
  документы_получены: 'docs_got',
  dokumenty_otrzymane: 'docs_got',
  dokumenty_otrzymane_: 'docs_got',
  work_permit_ordered: 'permit_ordered',
  заказ_разрешения: 'permit_ordered',
  zamowiono_zezwolenie: 'permit_ordered',
  work_permit_received: 'permit_received',
  разрешение_получено: 'permit_received',
  zezwolenie_odebrane: 'permit_received',
  visa_in_progress: 'visa',
  виза: 'visa',
  red_paper_ordered: 'red_paper',
  красная_бумага_заказана: 'red_paper',
  trip_planned: 'trip_plan',
  plan_trip: 'trip_plan',
  планируем_приезд: 'trip_plan',
  planowany_przyjazd: 'trip_plan',
  at_client_base: 'at_client',
  на_базе_клиента: 'at_client',
  na_bazie_klienta: 'at_client',
  employed: 'employed',
  hired: 'employed',
  трудоустроен: 'employed',
  zatrudniony: 'employed',
  on_trip: 'on_trip',
  в_рейсе: 'on_trip',
  probation_passed: 'probation_ok',
  probation_completed: 'probation_ok',
  probation_ok: 'probation_ok',
  прошёл_пробный_период: 'probation_ok',
  okres_próbny_zakończony: 'probation_ok',
  rejected: 'rejected',
  отклонён: 'rejected',
  odrzucony: 'rejected',
  odrzucony_: 'rejected',
  declined: 'declined',
  candidate_declined: 'declined',
  отказался: 'declined',
  kandydat_zrezygnował: 'declined',
  kandydat_zrezygnowal: 'declined',
  no_answer: 'no_answer',
  не_отвечает: 'no_answer',
  brak_kontaktu: 'no_answer',
  brak_kontaktu_: 'no_answer',
}

const STAGE_HIGHLIGHT_CODES: StageLabelConfig = {
  hired: ['employed', 'probation_ok', 'probation_done', 'hired'],
  rejected: ['rejected'],
  declined: ['declined'],
}

const REASON_LABEL_ALIASES: Record<string, string> = {
  schedule_mismatch: 'schedule',
  schedule: 'schedule',
  недоступен_график: 'schedule',
  bez_dopasowania_grafiku: 'schedule',
  salary_expectations: 'salary',
  salary_expectations_: 'salary',
  salary_expectation: 'salary',
  'salary expectations': 'salary',
  salary: 'salary',
  зарплата: 'salary',
  не_устраивает_зарплата: 'salary',
  oczekiwania_płacowe: 'salary',
  oczekiwania_placowe: 'salary',
  base_location_not_suitable: 'location',
  location_mismatch: 'location',
  расположение_не_подходит: 'location',
  lokalizacja_nie_odpowiada: 'location',
  trailer_type_mismatch: 'trailer_type',
  trailer_type: 'trailer_type',
  не_устраивает_тип_полуприцепа: 'trailer_type',
  typ_naczepy: 'trailer_type',
  no_night_driving: 'night_driving',
  night_driving: 'night_driving',
  bonus_scheme_mismatch: 'bonus_scheme',
  bonus_scheme: 'bonus_scheme',
  cab_sleep: 'cab_overnight',
  does_not_want_to_sleep_in_cab: 'cab_overnight',
  не_хочет_спать_в_кабине: 'cab_overnight',
  nie_chce_spać_w_kabinie: 'cab_overnight',
  negative_company_reviews: 'company_reviews',
  poor_company_reviews: 'company_reviews',
  негативные_отзывы: 'company_reviews',
  słabe_opinie: 'company_reviews',
  eu_experience_less_than_1_year: 'eu_exp_lt_1y',
  eu_exp_lt_one_year: 'eu_exp_lt_1y',
  опыт_по_ес_менее_1_года: 'eu_exp_lt_1y',
  eu_experience_less_than_6_months: 'eu_exp_lt_6m',
  опыт_по_ес_менее_6_месяцев: 'eu_exp_lt_6m',
  awaiting_residence_permit: 'awaiting_residence',
  waiting_for_residence: 'awaiting_residence',
  ожидает_внж: 'awaiting_residence',
  czeka_na_kartę_pobytu: 'awaiting_residence',
  czeka_na_karte_pobytu: 'awaiting_residence',
  language_barrier: 'language',
  missing_language: 'language',
  нет_языка: 'language',
  no_visa_or_residence_permit: 'no_visa',
  no_visa_residence_permit: 'no_visa',
  no_residence_permit: 'no_visa',
  no_visa: 'no_visa',
  нет_визы_внж: 'no_visa',
  нет_визы: 'no_visa',
  no_ce_experience: 'no_ce_experience',
  lacks_ce_experience: 'no_ce_experience',
  нет_опыта_ce: 'no_ce_experience',
  нет_опыта_по_ce: 'no_ce_experience',
  no_code_95: 'no_code95',
  missing_code_95: 'no_code95',
  нет_95_кода: 'no_code95',
  no_tachograph_card: 'no_chip',
  missing_tachograph_card: 'no_chip',
  нет_карты_тахографа: 'no_chip',
  нет_чипа: 'no_chip',
  age_restrictions: 'age',
  age: 'age',
  возраст: 'age',
  blacklisted: 'blacklist',
  чёрный_список: 'blacklist',
  wrong_phone: 'wrong_phone',
  incorrect_phone_number: 'wrong_phone',
  wrong_phone_number: 'wrong_phone',
  wrong_number: 'wrong_phone',
  invalid_phone: 'wrong_phone',
  неверно_указан_номер: 'wrong_phone',
  неверный_номер: 'wrong_phone',
  неверный_номер_телефона: 'wrong_phone',
  nieprawidlowy_numer: 'wrong_phone',
  nieprawidlowy_numer_telefonu: 'wrong_phone',
  bez_przyczyny: 'no_reason',
  без_причины: 'no_reason',
}

const buildNormalizedMap = (source: Record<string, string>) =>
  Object.fromEntries(
    Object.entries(source)
      .map(([key, value]) => [normalizeKey(key), value])
      .filter(([key]) => Boolean(key)),
  )

const NORMALIZED_STAGE_CODE_ALIASES = buildNormalizedMap(STAGE_CODE_ALIASES)
const NORMALIZED_STAGE_LABEL_ALIASES = buildNormalizedMap(STAGE_LABEL_ALIASES)
const NORMALIZED_REASON_LABEL_ALIASES = buildNormalizedMap(REASON_LABEL_ALIASES)

const canonicalStageKey = (code?: string | null, fallback?: string | null): string | null => {
  const normalized = normalizeKey(code)
  if (normalized) {
    return (
      NORMALIZED_STAGE_CODE_ALIASES[normalized] ??
      NORMALIZED_STAGE_LABEL_ALIASES[normalized] ??
      normalized
    )
  }
  const fallbackKey = normalizeKey(fallback)
  if (fallbackKey) {
    return NORMALIZED_STAGE_LABEL_ALIASES[fallbackKey] ?? fallbackKey
  }
  return null
}

const DOC_STAGE_CATEGORY: Record<string, 'waiting' | 'ready' | 'attention'> = {
  docs_wait: 'waiting',
  permit_ordered: 'waiting',
  permit_received: 'ready',
  docs_got: 'ready',
  visa: 'waiting',
  red_paper: 'waiting',
  docs_problem: 'attention',
  documents_issue: 'attention',
}

const determineStageOutcome = (
  canonical: string | null | undefined,
  labels: StageLabelConfig = DEFAULT_STAGE_LABELS,
): 'hired' | 'rejected' | 'declined' | 'pipeline' => {
  if (!canonical) return 'pipeline'
  if ((labels.hired ?? []).includes(canonical)) return 'hired'
  if ((labels.rejected ?? []).includes(canonical)) return 'rejected'
  if ((labels.declined ?? []).includes(canonical)) return 'declined'
  return 'pipeline'
}

type StageOutcome = 'hired' | 'rejected' | 'declined' | 'pipeline'

const normalizeStageCounts = (input?: Record<string, number>): Record<string, number> => {
  if (!input) return {}
  const result: Record<string, number> = {}
  Object.entries(input).forEach(([key, value]) => {
    const numeric = Number(value) || 0
    if (!numeric) return
    const canonical = canonicalStageKey(key, key) || key
    result[canonical] = (result[canonical] ?? 0) + numeric
  })
  return result
}

const stageHighlights = (
  map?: Record<string, number>,
  labels: StageLabelConfig = DEFAULT_STAGE_LABELS,
) => {
  const normalized = normalizeStageCounts(map)
  if (!Object.keys(normalized).length) {
    return { hired: 0, rejected: 0, declined: 0, pipeline: 0 }
  }
  const hiredKeys = labels.hired ?? []
  const rejectedKeys = labels.rejected ?? []
  const declinedKeys = labels.declined ?? []
  const hired = hiredKeys.reduce((acc, key) => acc + (normalized[key] ?? 0), 0)
  const rejected = rejectedKeys.reduce((acc, key) => acc + (normalized[key] ?? 0), 0)
  const declined = declinedKeys.reduce((acc, key) => acc + (normalized[key] ?? 0), 0)
  const total = Object.values(normalized).reduce((acc, val) => acc + (val ?? 0), 0)
  const pipeline = Math.max(total - hired - rejected - declined, 0)
  return { hired, rejected, declined, pipeline }
}

const STAGE_STACK_COLORS: Record<StageOutcome, string> = {
  hired: 'bg-emerald-400',
  rejected: 'bg-rose-400',
  declined: 'bg-amber-400',
  pipeline: 'bg-brand-400',
}

type TrialRetentionDay = 1 | 2 | 3 | 7

// normalizeTotal is now imported from modules/dashboard/utils

export default function Dashboard() {
  const { t, locale } = useI18n()
  const { me } = useAuth()
  const tenant = useTenantInfo()
  const currentTenantId = useCurrentTenantId()
  const tenantId = (currentTenantId ?? (me as { tenant_id?: string })?.tenant_id) ?? 'default'
  const scopeTid = currentTenantId ?? (me as { tenant_id?: string })?.tenant_id
  const initialRange = calcRange('90d')
  const [dateFrom, setDateFrom] = useState<string>(initialRange.from)
  const [dateTo, setDateTo] = useState<string>(initialRange.to)
  const [activeRange, setActiveRange] = useState<QuickRange | 'custom'>('90d')
  const [dateField, setDateField] = useState<'created' | 'updated'>('created')

  const [loading, setLoading] = useState(true)
  const [errText, setErrText] = useState<string | null>(null)

  const [globalCounts, setGlobalCounts] = useState({ candidates: 0, companies: 0, vacancies: 0 })
  const [periodTotal, setPeriodTotal] = useState(0)
  const [slices, setSlices] = useState<CandidateSlicesResponse | null>(null)
  const { role, isClientTenant } = usePermissions()
  const isClientRole = isClientTenant && role !== 'administrator'
  const isTrialTenant = String(tenant?.status || '').trim().toLowerCase() === 'trial'
  const canManageBilling = role === 'administrator' || role === 'supervisor'
  const [trialEndsAt, setTrialEndsAt] = useState<string | null>(null)
  const [retentionStatus, setRetentionStatus] = useState<OnboardingStatus | null>(null)
  const [retentionDismissed, setRetentionDismissed] = useState(false)
  const retentionImpressionRef = useRef<string | null>(null)
  const [retentionReport, setRetentionReport] = useState<TrialRetentionReport | null>(null)
  const [retentionReportLoading, setRetentionReportLoading] = useState(false)
  const [stageView, setStageView] = useState<'all' | 'agency' | 'client'>(() =>
    isClientRole ? 'client' : 'all',
  )

  const [pivotPrimary, setPivotPrimary] = useState<PivotDimension>('company')
  const [pivotSecondary, setPivotSecondary] = useState<PivotDimension | 'none'>('stage')
  const [vacancyFilter, setVacancyFilter] = useState<string>('')
  const [vacancyOptions, setVacancyOptions] = useState<{ id: string; label: string }[]>([])
  const [companyFilter, setCompanyFilter] = useState<string>('')
  const [companyOptions, setCompanyOptions] = useState<{ id: string; label: string }[]>([])
  const [managerFilter, setManagerFilter] = useState<string>('')
  const [managerOptions, setManagerOptions] = useState<{ id: string; label: string }[]>([])
  const [stagesFilter, setStagesFilter] = useState<string[]>([])
  const [stageOptions, setStageOptions] = useState<{ code: string; label: string }[]>([])
  const [handoffStats, setHandoffStats] = useState<Awaited<ReturnType<typeof getHandoffStats>> | null>(null)
  const [contactStats, setContactStats] = useState<Awaited<ReturnType<typeof getContactAttemptStats>> | null>(null)
  const [documentStats, setDocumentStats] = useState<Awaited<ReturnType<typeof getDocumentStats>> | null>(null)
  const [profileSummary, setProfileSummary] = useState<Awaited<ReturnType<typeof getAnalyticsProfileSummary>> | null>(null)
  const [compareWithPrevious, setCompareWithPrevious] = useState(false)
  const [prevPeriodTotal, setPrevPeriodTotal] = useState<number | null>(null)
  const [prevHandoffStats, setPrevHandoffStats] = useState<Awaited<ReturnType<typeof getHandoffStats>> | null>(null)
  const [savedPreset, setSavedPreset] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    if (!isTrialTenant || !canManageBilling) {
      setTrialEndsAt(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const subscription = await getBillingSubscription()
        if (!cancelled) {
          setTrialEndsAt(subscription?.trial_ends_at || null)
        }
      } catch {
        if (!cancelled) {
          setTrialEndsAt(null)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [canManageBilling, isTrialTenant])

  const trialDaysLeft = useMemo(() => {
    if (!trialEndsAt) return null
    const ends = new Date(trialEndsAt)
    if (Number.isNaN(ends.getTime())) return null
    const diffMs = ends.getTime() - Date.now()
    return Math.max(0, Math.ceil(diffMs / DAY_MS))
  }, [trialEndsAt])

  const trialTone = useMemo<'normal' | 'warning' | 'critical'>(() => {
    if (trialDaysLeft == null) return 'normal'
    if (trialDaysLeft <= 2) return 'critical'
    if (trialDaysLeft <= 7) return 'warning'
    return 'normal'
  }, [trialDaysLeft])

  const trialCenterClasses = useMemo(() => {
    if (trialTone === 'critical') {
      return {
        wrapper: 'rounded-xl border border-rose-300 bg-rose-50 p-4 shadow-sm',
        badge: 'text-xs font-semibold uppercase tracking-wide text-rose-800',
        title: 'text-sm font-semibold text-rose-950',
        subtitle: 'text-xs text-rose-900/90',
        legal: 'mt-2 text-xs text-rose-900/90',
        urgency: 'inline-flex items-center rounded-md border border-rose-300 bg-rose-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-rose-800',
      } as const
    }
    if (trialTone === 'warning') {
      return {
        wrapper: 'rounded-xl border border-amber-300 bg-amber-50 p-4 shadow-sm',
        badge: 'text-xs font-semibold uppercase tracking-wide text-amber-800',
        title: 'text-sm font-semibold text-amber-950',
        subtitle: 'text-xs text-amber-900/90',
        legal: 'mt-2 text-xs text-amber-900/90',
        urgency: 'inline-flex items-center rounded-md border border-amber-300 bg-amber-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-800',
      } as const
    }
    return {
      wrapper: 'rounded-xl border border-emerald-300 bg-emerald-50 p-4 shadow-sm',
      badge: 'text-xs font-semibold uppercase tracking-wide text-emerald-800',
      title: 'text-sm font-semibold text-emerald-950',
      subtitle: 'text-xs text-emerald-900/90',
      legal: 'mt-2 text-xs text-emerald-900/90',
      urgency: 'inline-flex items-center rounded-md border border-emerald-300 bg-emerald-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-800',
    } as const
  }, [trialTone])

  const retentionReportRows = useMemo(() => {
    const source = retentionReport?.buckets ?? []
    const order: Array<'d1' | 'd2' | 'd3' | 'd7'> = ['d1', 'd2', 'd3', 'd7']
    const labels: Record<string, string> = {
      d1: t('app.dashboard.trial_center.retention.day1', { defaultValue: 'Day 1' }),
      d2: t('app.dashboard.trial_center.retention.day2', { defaultValue: 'Day 2' }),
      d3: t('app.dashboard.trial_center.retention.day3', { defaultValue: 'Day 3' }),
      d7: t('app.dashboard.trial_center.retention.day7', { defaultValue: 'Day 7' }),
    }
    const map = new Map(source.map((row) => [row.day_bucket, row]))
    return order.map((key) => {
      const row = map.get(key)
      return {
        key,
        label: labels[key],
        impression: row?.impression ?? 0,
        ctaClick: row?.cta_click ?? 0,
        dismiss: row?.dismiss ?? 0,
        ctr: row?.ctr_percent ?? 0,
      }
    })
  }, [retentionReport?.buckets, t])

  useEffect(() => {
    if (!isTrialTenant) {
      setRetentionStatus(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const data = await getOnboardingStatus()
        if (!cancelled) {
          setRetentionStatus(data)
        }
      } catch {
        if (!cancelled) {
          setRetentionStatus(null)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isTrialTenant])

  useEffect(() => {
    if (!isTrialTenant || !canManageBilling) {
      setRetentionReport(null)
      setRetentionReportLoading(false)
      return
    }
    let cancelled = false
    setRetentionReportLoading(true)
    ;(async () => {
      try {
        const data = await getTrialRetentionReport({ days: 30 })
        if (!cancelled) {
          setRetentionReport(data)
        }
      } catch {
        if (!cancelled) {
          setRetentionReport(null)
        }
      } finally {
        if (!cancelled) {
          setRetentionReportLoading(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [canManageBilling, isTrialTenant])

  const trialAgeDays = useMemo(() => {
    const createdAtRaw = String(tenant?.created_at || '').trim()
    if (!createdAtRaw) return null
    const createdAt = new Date(createdAtRaw)
    if (Number.isNaN(createdAt.getTime())) return null
    const diffMs = Date.now() - createdAt.getTime()
    return Math.max(0, Math.floor(diffMs / DAY_MS))
  }, [tenant?.created_at])

  const retentionDay = useMemo<TrialRetentionDay | null>(() => {
    if (trialAgeDays == null) return null
    if (trialAgeDays >= 7) return 7
    if (trialAgeDays >= 3) return 3
    if (trialAgeDays >= 2) return 2
    if (trialAgeDays >= 1) return 1
    return null
  }, [trialAgeDays])

  const retentionDismissKey = useMemo(() => {
    if (!tenantId || retentionDay == null) return null
    return `hf:trial-retention:${tenantId}:d${retentionDay}`
  }, [tenantId, retentionDay])

  useEffect(() => {
    if (!retentionDismissKey) {
      setRetentionDismissed(false)
      return
    }
    try {
      const raw = localStorage.getItem(retentionDismissKey)
      setRetentionDismissed(raw === '1')
    } catch {
      setRetentionDismissed(false)
    }
  }, [retentionDismissKey])

  const dismissRetentionNudge = useCallback(() => {
    if (!retentionDismissKey) return
    try {
      localStorage.setItem(retentionDismissKey, '1')
    } catch {
      /* ignore */
    }
    setRetentionDismissed(true)
  }, [retentionDismissKey])

  const retentionNextHref = useMemo(() => getRetentionNextPath(retentionStatus), [retentionStatus])

  const retentionStepKey = useMemo(() => getRetentionStepKey(retentionStatus), [retentionStatus])

  const retentionNudge = useMemo(() => {
    if (!isTrialTenant || retentionDay == null || retentionDismissed) return null
    const activationDone = Boolean(
      retentionStatus && !retentionStatus.onboarding_required && !retentionStatus.activation_required,
    )
    const dayKey = `d${retentionDay}` as const
    return {
      day: retentionDay,
      dayKey,
      activationDone,
      href: retentionNextHref,
      stepKey: retentionStepKey,
    }
  }, [isTrialTenant, retentionDay, retentionDismissed, retentionStatus, retentionNextHref, retentionStepKey])

  const trackRetentionEvent = useCallback(
    (
      action: 'impression' | 'cta_click' | 'dismiss',
      payload?: { day?: TrialRetentionDay; stepKey?: string; href?: string; activationDone?: boolean },
    ) => {
      const dayBucket = payload?.day != null ? (`d${payload.day}` as 'd1' | 'd2' | 'd3' | 'd7') : null
      if (typeof window !== 'undefined') {
        const dataLayer = (window as typeof window & { dataLayer?: unknown[] }).dataLayer
        if (Array.isArray(dataLayer)) {
          dataLayer.push({
            event: 'trial_retention_nudge',
            action,
            day: payload?.day ?? null,
            step_key: payload?.stepKey ?? null,
            target_href: payload?.href ?? null,
            activation_done: payload?.activationDone ?? null,
            tenant_id: tenantId,
          })
        }
      }
      if (dayBucket) {
        void recordTrialRetentionEvent({
          event: 'trial_retention_nudge',
          action,
          day_bucket: dayBucket,
          step_key: payload?.stepKey ?? null,
          target_href: payload?.href ?? null,
          activation_done: payload?.activationDone ?? null,
        }).catch(() => undefined)
      }
    },
    [tenantId],
  )

  useEffect(() => {
    if (!retentionNudge) {
      retentionImpressionRef.current = null
      return
    }
    const impressionKey = `${tenantId}:${retentionNudge.day}:${retentionNudge.stepKey}`
    if (retentionImpressionRef.current === impressionKey) return
    retentionImpressionRef.current = impressionKey
    trackRetentionEvent('impression', {
      day: retentionNudge.day,
      stepKey: retentionNudge.stepKey,
      href: retentionNudge.href,
      activationDone: retentionNudge.activationDone,
    })
  }, [retentionNudge, tenantId, trackRetentionEvent])

  const visibleWidgetsKey = useMemo(() => `hf:dashboard:${tenantId}:visibleWidgets`, [tenantId])
  const visibleFiltersKey = useMemo(() => `hf:dashboard:${tenantId}:visibleFilters`, [tenantId])
  const loadVisibleWidgets = useCallback((): Set<string> => {
    try {
      const raw = localStorage.getItem(visibleWidgetsKey)
      if (raw) {
        const arr = JSON.parse(raw)
        if (Array.isArray(arr)) return new Set(arr)
      }
    } catch {
      /* ignore */
    }
    return new Set(DEFAULT_VISIBLE_WIDGETS)
  }, [visibleWidgetsKey])
  const loadVisibleFilters = useCallback((): Set<string> => {
    try {
      const raw = localStorage.getItem(visibleFiltersKey)
      if (raw) {
        const arr = JSON.parse(raw)
        if (Array.isArray(arr)) return new Set(arr)
      }
    } catch {
      /* ignore */
    }
    return new Set(DEFAULT_VISIBLE_FILTERS)
  }, [visibleFiltersKey])
  const [visibleWidgets, setVisibleWidgets] = useState<Set<string>>(loadVisibleWidgets)
  const [visibleFilters, setVisibleFilters] = useState<Set<string>>(loadVisibleFilters)
  useEffect(() => {
    setVisibleWidgets(loadVisibleWidgets())
    setVisibleFilters(loadVisibleFilters())
  }, [tenantId, loadVisibleWidgets, loadVisibleFilters])
  const isWidgetVisible = useCallback(
    (id: DashboardWidgetId) => visibleWidgets.has(id),
    [visibleWidgets],
  )
  const isFilterVisible = useCallback(
    (id: DashboardFilterId) => visibleFilters.has(id),
    [visibleFilters],
  )
  const toggleWidget = useCallback((id: DashboardWidgetId) => {
    setVisibleWidgets((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      try {
        localStorage.setItem(visibleWidgetsKey, JSON.stringify([...next]))
      } catch {
        /* ignore */
      }
      return next
    })
  }, [visibleWidgetsKey])
  const toggleFilter = useCallback((id: DashboardFilterId) => {
    setVisibleFilters((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      try {
        localStorage.setItem(visibleFiltersKey, JSON.stringify([...next]))
      } catch {
        /* ignore */
      }
      return next
    })
  }, [visibleFiltersKey])

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

  const dashboardPresetKey = useMemo(() => `hf:dashboard:${tenantId}:preset`, [tenantId])

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

  const handleStagesChange = (codes: string[]) => {
    setStagesFilter(codes)
    load({ stages: codes })
  }

  const handleResetFilters = () => {
    setVacancyFilter('')
    setCompanyFilter('')
    setManagerFilter('')
    setStagesFilter([])
    setCompareWithPrevious(false)
    const next = calcRange('90d')
    setDateFrom(next.from)
    setDateTo(next.to)
    setActiveRange('90d')
    setDateField('created')
    load({ from: next.from, to: next.to, vacancyId: null, companyId: null, managerId: null, stages: [], compare: false })
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
        stages: preset.stagesFilter,
        compare: preset.compareWithPrevious,
      })
    } catch (e) {
      console.error('Failed to load preset', e)
    }
  }

  useEffect(() => {
    try {
      const raw = localStorage.getItem(dashboardPresetKey)
      if (raw) setSavedPreset(JSON.parse(raw) as Record<string, unknown>)
    } catch {
      // ignore
    }
  }, [dashboardPresetKey])

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

  const sourceStageRows = useMemo(() => {
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

  const docStageStats = useMemo(() => {
    if (!slices?.snapshot?.length) return { waiting: 0, ready: 0, attention: 0, total: 0 }
    const counts = { waiting: 0, ready: 0, attention: 0 }
    slices.snapshot.forEach((row) => {
      const canonical = canonicalStageKey(row.stage, row.stage_label)
      if (!canonical) return
      let bucket =
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

  const stageVelocityRows = useMemo(() => {
    if (!slices?.snapshot?.length) return []
    const now = Date.now()
    const store = new Map<string, number[]>()
    slices.snapshot.forEach((row) => {
      if (!row.created_at) return
      const ts = Date.parse(row.created_at)
      if (Number.isNaN(ts)) return
      const days = Math.max((now - ts) / DAY_MS, 0)
      const label = translateStageLabel(row.stage, row.stage_label) || notAvailableLabel
      const list = store.get(label)
      if (list) list.push(days)
      else store.set(label, [days])
    })
    const rows = Array.from(store.entries())
      .map(([label, values]) => {
        const total = values.length
        const avgDays = values.reduce((sum, value) => sum + value, 0) / total
        const sorted = values.slice().sort((a, b) => a - b)
        const index = Math.min(sorted.length - 1, Math.max(0, Math.floor(0.9 * (sorted.length - 1))))
        const p90 = sorted[index] ?? avgDays
        return { label, total, avgDays, p90 }
      })
      .sort((a, b) => b.total - a.total)
      .slice(0, 6)
    const maxAvg = rows.reduce((max, row) => Math.max(max, row.avgDays), 0)
    return rows.map((row) => ({
      ...row,
      intensity: maxAvg ? Math.min(row.avgDays / maxAvg, 1) : 0,
    }))
  }, [slices?.snapshot, translateStageLabel, notAvailableLabel])

  const businessProfileCards = useMemo(() => {
    if (!profileSummary) return []
    const kpis = profileSummary.kpis || {}
    const businessType = profileSummary.business_type
    if (businessType === 'services') {
      return [
        { key: 'clients_total', label: t('app.dashboard.business.services.clients_total', { defaultValue: 'Clients' }), value: Number(kpis.clients_total || 0) },
        { key: 'counterparties_total', label: t('app.dashboard.business.services.counterparties_total', { defaultValue: 'Counterparties' }), value: Number(kpis.counterparties_total || 0) },
        { key: 'service_orders_in_progress', label: t('app.dashboard.business.services.orders_in_progress', { defaultValue: 'Orders in progress' }), value: Number(kpis.service_orders_in_progress || 0) },
        { key: 'service_orders_delivered', label: t('app.dashboard.business.services.orders_delivered', { defaultValue: 'Delivered orders' }), value: Number(kpis.service_orders_delivered || 0) },
      ]
    }
    if (businessType === 'employer') {
      return [
        { key: 'vacancies_active', label: t('app.dashboard.business.employer.vacancies_active', { defaultValue: 'Active vacancies' }), value: Number(kpis.vacancies_active || 0) },
        { key: 'candidates_total', label: t('app.dashboard.business.employer.candidates_total', { defaultValue: 'Candidates' }), value: Number(kpis.candidates_total || 0) },
        { key: 'leads_total', label: t('app.dashboard.business.employer.leads_total', { defaultValue: 'Leads' }), value: Number(kpis.leads_total || 0) },
        { key: 'companies_total', label: t('app.dashboard.business.employer.companies_total', { defaultValue: 'Companies' }), value: Number(kpis.companies_total || 0) },
      ]
    }
    return [
      { key: 'companies_total', label: t('app.dashboard.business.agency.companies_total', { defaultValue: 'Clients' }), value: Number(kpis.companies_total || 0) },
      { key: 'vacancies_active', label: t('app.dashboard.business.agency.vacancies_active', { defaultValue: 'Active vacancies' }), value: Number(kpis.vacancies_active || 0) },
      { key: 'candidates_total', label: t('app.dashboard.business.agency.candidates_total', { defaultValue: 'Candidates' }), value: Number(kpis.candidates_total || 0) },
      { key: 'leads_total', label: t('app.dashboard.business.agency.leads_total', { defaultValue: 'Leads' }), value: Number(kpis.leads_total || 0) },
    ]
  }, [profileSummary, t])

  const dashboardCompanyLabels = useMemo(() => {
    const bt = profileSummary?.business_type
    if (bt === 'employer') {
      return {
        plural: t('app.dashboard.terms.companies_plural', { defaultValue: 'Companies' }),
        singular: t('app.dashboard.terms.companies_singular', { defaultValue: 'Company' }),
      }
    }
    return {
      plural: t('app.dashboard.terms.clients_plural', { defaultValue: 'Clients' }),
      singular: t('app.dashboard.terms.clients_singular', { defaultValue: 'Client' }),
    }
  }, [profileSummary?.business_type, t])

  const businessTypeLabel = useMemo(() => {
    const bt = profileSummary?.business_type
    if (bt === 'services') return t('app.dashboard.business.type.services', { defaultValue: 'Services' })
    if (bt === 'employer') return t('app.dashboard.business.type.employer', { defaultValue: 'Employer' })
    if (bt === 'agency') return t('app.dashboard.business.type.agency', { defaultValue: 'Agency' })
    return t('common.labels.not_available')
  }, [profileSummary?.business_type, t])

  const managerLoadRows = useMemo(() => {
    if (!slices?.snapshot?.length) return []
    const rows = new Map<
      string,
      { label: string; total: number; pipeline: number; managerLabel: string }
    >()
    slices.snapshot.forEach((row) => {
      const label =
        row.manager_name ||
        row.manager ||
        row.manager_short ||
        t('app.dashboard.manager_load.unknown')
      const canonical = canonicalStageKey(row.stage, row.stage_label)
      const outcome = determineStageOutcome(canonical, stageLabels)
      const entry = rows.get(label) ?? { label, total: 0, pipeline: 0, managerLabel: label }
      entry.total += 1
      if (outcome === 'pipeline') entry.pipeline += 1
      rows.set(label, entry)
    })
    return Array.from(rows.values())
      .sort((a, b) => b.pipeline - a.pipeline || b.total - a.total)
      .slice(0, 6)
  }, [slices?.snapshot, stageLabels, t])

  const countryHeatmapRows = useMemo(() => {
    const list = slices?.countries ?? []
    if (!list.length) return []
    const max = list.reduce((acc, item) => Math.max(acc, item.count), 0) || 1
    return list
      .map((item) => {
        const code = item.key || ''
        const label = /^[A-Z]{2}$/.test(String(code)) ? getRegionDisplayName(code, locale) : (item.label || code || notAvailableLabel)
        return {
          label: label || notAvailableLabel,
          count: item.count,
          intensity: Math.min(item.count / max, 1),
        }
      })
      .slice(0, 12)
  }, [slices?.countries, notAvailableLabel, locale])

  const rangeInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo)
  const primaryLabel = dimensionOptions.find((opt) => opt.value === pivotPrimary)?.label ?? ''
  const secondaryLabel =
    pivotSecondary === 'none'
      ? t('app.dashboard.labels.no_subgroup')
      : dimensionOptions.find((opt) => opt.value === pivotSecondary)?.label ?? ''
  // Группируем статусы по переведенному названию
  const groupedStages = useMemo(() => {
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

  const stageStackSegments = useMemo(() => {
    if (!groupedStages.length) return []
    const total = groupedStages.reduce((acc, stage) => acc + stage.count, 0)
    if (!total) return []
    return groupedStages.map((stage) => {
      // Находим первый исходный stage для определения outcome
      const firstOriginalStage = slices?.stages?.find(
        (s) => (translateStageLabel(s.key, s.label) || s.label) === stage.label
      )
      const canonical = firstOriginalStage
        ? canonicalStageKey(firstOriginalStage.key, firstOriginalStage.label)
        : null
      const outcome = determineStageOutcome(canonical, stageLabels)
      const value = stage.count
      const percent = total ? Math.round((value / total) * 1000) / 10 : 0
      return { label: stage.label, value, percent, outcome }
    })
  }, [groupedStages, slices?.stages, stageLabels, translateStageLabel])

  // Группируем причины отказа по переведенному названию
  // Используем snapshot данные напрямую, чтобы учесть все причины из карточек кандидатов
  const groupedRejectedReasons = useMemo(() => {
    if (!slices?.snapshot?.length) return []
    const grouped = new Map<string, { label: string; count: number; codes: Set<string> }>()
    const noReasonLabel = t('app.dashboard.labels.no_reason')
    
    // Обрабатываем все кандидаты со стадией rejected
    slices.snapshot.forEach((row) => {
      // Проверяем, что стадия rejected (reason_stage может быть не установлен, но stage должен быть)
      if (row.stage !== 'rejected') return
      
      const codes = row.status_reason_codes ?? []
      const fallbackLabels = row.status_reason_labels ?? []
      
      if (codes.length === 0 && fallbackLabels.length === 0) {
        // Нет причин - пропускаем
        return
      }
      
      // Обрабатываем каждую причину
      const reasonsToProcess = codes.length > 0 ? codes : fallbackLabels
      reasonsToProcess.forEach((codeOrLabel, index) => {
        const code = codes.length > 0 ? codeOrLabel : null
        const fallback = fallbackLabels[index] || codeOrLabel
        const translatedLabel = translateReasonLabel(code, fallback)
        
        // Пропускаем "Без причины"
        if (translatedLabel === noReasonLabel) {
          return
        }
        
        if (grouped.has(translatedLabel)) {
          const existing = grouped.get(translatedLabel)!
          existing.count += 1
          if (code) {
            existing.codes.add(code)
          }
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

  // Группируем причины отмены по переведенному названию
  // Используем snapshot данные напрямую, чтобы учесть все причины из карточек кандидатов
  const groupedDeclinedReasons = useMemo(() => {
    if (!slices?.snapshot?.length) return []
    const grouped = new Map<string, { label: string; count: number; codes: Set<string> }>()
    const noReasonLabel = t('app.dashboard.labels.no_reason')
    
    // Обрабатываем все кандидаты со стадией declined
    slices.snapshot.forEach((row) => {
      // Проверяем, что стадия declined (reason_stage может быть не установлен, но stage должен быть)
      if (row.stage !== 'declined') return
      
      const codes = row.status_reason_codes ?? []
      const fallbackLabels = row.status_reason_labels ?? []
      
      if (codes.length === 0 && fallbackLabels.length === 0) {
        // Нет причин - пропускаем
        return
      }
      
      // Обрабатываем каждую причину
      const reasonsToProcess = codes.length > 0 ? codes : fallbackLabels
      reasonsToProcess.forEach((codeOrLabel, index) => {
        const code = codes.length > 0 ? codeOrLabel : null
        const fallback = fallbackLabels[index] || codeOrLabel
        const translatedLabel = translateReasonLabel(code, fallback)
        
        // Пропускаем "Без причины"
        if (translatedLabel === noReasonLabel) {
          return
        }
        
        if (grouped.has(translatedLabel)) {
          const existing = grouped.get(translatedLabel)!
          existing.count += 1
          if (code) {
            existing.codes.add(code)
          }
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

  return (
    <section className="h-full min-h-0 w-full flex flex-col">
      <div className="flex-1 min-h-0 overflow-auto px-6 py-4 space-y-4">
        {tenantId && retentionStatus?.onboarding_required === true && <OnboardingWizard tenantId={tenantId} />}
        {retentionNudge && (
          <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">
                  {t('app.dashboard.retention.badge', { defaultValue: 'Trial next step' })}
                </p>
                <h2 className="text-sm font-semibold text-brand-950">
                  {t(`app.dashboard.retention.${retentionNudge.dayKey}.title`, {
                    defaultValue: retentionNudge.activationDone
                      ? 'Keep momentum during trial'
                      : 'Finish activation and get first value',
                  })}
                </h2>
                <p className="text-xs text-brand-900/90">
                  {t(`app.dashboard.retention.${retentionNudge.dayKey}.subtitle`, {
                    defaultValue: retentionNudge.activationDone
                      ? 'Your base setup is done. Keep using the workspace and prepare billing before trial ends.'
                      : 'Complete the next guided step now to keep progress and avoid drop-off during trial.',
                  })}
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
                    ? t('app.dashboard.retention.cta_billing', { defaultValue: 'Open billing' })
                    : t(`app.dashboard.retention.cta_step.${retentionNudge.stepKey}`, {
                        defaultValue: 'Continue setup',
                      })}
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
                  {t('app.dashboard.retention.dismiss', { defaultValue: 'Hide for now' })}
                </button>
              </div>
            </div>
          </div>
        )}
        {isTrialTenant && (
          <div className={trialCenterClasses.wrapper}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className={trialCenterClasses.badge}>
                  {t('app.dashboard.trial_center.badge', { defaultValue: 'Trial Center' })}
                </p>
                <h2 className={trialCenterClasses.title}>
                  {trialDaysLeft != null
                    ? t('app.dashboard.trial_center.title_with_days', {
                        defaultValue: 'Your trial is active: {days} day(s) left',
                        values: { days: trialDaysLeft },
                      })
                    : t('app.dashboard.trial_center.title', {
                        defaultValue: 'Your trial is active',
                      })}
                </h2>
                <p className={trialCenterClasses.subtitle}>
                  {t('app.dashboard.trial_center.subtitle', {
                    defaultValue:
                      'Review billing and legal terms now to avoid interruption when trial ends.',
                  })}
                </p>
                {trialTone === 'critical' && (
                  <span className={trialCenterClasses.urgency}>
                    {t('app.dashboard.trial_center.urgency_critical', { defaultValue: 'Action required now' })}
                  </span>
                )}
                {trialTone === 'warning' && (
                  <span className={trialCenterClasses.urgency}>
                    {t('app.dashboard.trial_center.urgency_warning', { defaultValue: 'Trial ending soon' })}
                  </span>
                )}
              </div>
              {canManageBilling && (
                <Link to="/app/settings/billing" className="btn-secondary">
                  {t('app.dashboard.trial_center.open_billing', { defaultValue: 'Open billing' })}
                </Link>
              )}
            </div>
            <p className={trialCenterClasses.legal}>
              {t('app.dashboard.trial_center.legal_prefix', { defaultValue: 'Legal:' })}{' '}
              <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
                {t('app.dashboard.trial_center.legal_terms', { defaultValue: 'Terms' })}
              </a>
              {', '}
              <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
                {t('app.dashboard.trial_center.legal_privacy', { defaultValue: 'Privacy' })}
              </a>
              {', '}
              <a href="/legal/cookies.html" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">
                {t('app.dashboard.trial_center.legal_cookies', { defaultValue: 'Cookies' })}
              </a>
              .
            </p>
            {canManageBilling && (
              <div className="mt-3 rounded-lg border border-slate-200 bg-white/80 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-700">
                    {t('app.dashboard.trial_center.retention.title', { defaultValue: 'Retention events (30d)' })}
                  </p>
                  {retentionReportLoading && (
                    <span className="text-[11px] text-slate-500">
                      {t('app.dashboard.trial_center.retention.loading', { defaultValue: 'Loading…' })}
                    </span>
                  )}
                </div>
                <div className="overflow-x-auto">
                  <table className="table table-sm">
                    <thead>
                      <tr>
                        <th>{t('app.dashboard.trial_center.retention.columns.day', { defaultValue: 'Day' })}</th>
                        <th>{t('app.dashboard.trial_center.retention.columns.impression', { defaultValue: 'Impressions' })}</th>
                        <th>{t('app.dashboard.trial_center.retention.columns.click', { defaultValue: 'CTA clicks' })}</th>
                        <th>{t('app.dashboard.trial_center.retention.columns.dismiss', { defaultValue: 'Dismiss' })}</th>
                        <th>{t('app.dashboard.trial_center.retention.columns.ctr', { defaultValue: 'CTR' })}</th>
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
                  {t('app.dashboard.trial_center.retention.summary', {
                    defaultValue: 'Total impressions: {impression}, clicks: {click}, dismiss: {dismiss}, CTR: {ctr}%.',
                    values: {
                      impression: retentionReport?.totals?.impression ?? 0,
                      click: retentionReport?.totals?.cta_click ?? 0,
                      dismiss: retentionReport?.totals?.dismiss ?? 0,
                      ctr: Number(retentionReport?.totals?.ctr_percent ?? 0).toFixed(2),
                    },
                  })}
                </p>
              </div>
            )}
          </div>
        )}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-xl font-semibold">{t('app.dashboard.title')}</h1>
          <div className="flex items-center gap-2">
            <button className="btn-secondary" onClick={() => load()} disabled={loading || rangeInvalid}>
              {loading ? t('app.dashboard.refresh.loading') : t('app.dashboard.refresh.action')}
            </button>
          </div>
        </div>

        <div className="card p-4 space-y-4">
          <div className="flex flex-wrap items-end gap-3 gap-y-2">
            {isFilterVisible('period') && (
              <label className="flex flex-col text-xs gap-0.5">
                <span className="text-slate-500">{t('app.dashboard.filters.period')}</span>
                <div className="flex gap-1">
                  {quickRangeOptions.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      className={`px-2 py-1 rounded text-xs ${
                        activeRange === option.value ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                      onClick={() => applyQuickRange(option.value)}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </label>
            )}
            {isFilterVisible('dateRange') && (
              <>
                <label className="flex flex-col text-xs gap-0.5">
                  <span className="text-slate-500">{t('app.dashboard.filters.from')}</span>
                  <input type="date" className="input input-sm w-32" autoComplete="off" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setActiveRange('custom') }} />
                </label>
                <label className="flex flex-col text-xs gap-0.5">
                  <span className="text-slate-500">{t('app.dashboard.filters.to')}</span>
                  <input type="date" className="input input-sm w-32" autoComplete="off" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setActiveRange('custom') }} />
                </label>
              </>
            )}
            {isFilterVisible('dateField') && (
              <label className="flex flex-col text-xs gap-0.5">
                <span className="text-slate-500">{t('app.dashboard.filters.date_field')}</span>
                <select className="input input-sm w-28" value={dateField} onChange={(e) => { const next = e.target.value === 'updated' ? 'updated' : 'created'; setDateField(next); load({ field: next }) }}>
                  <option value="created">{t('app.dashboard.filters.field_created')}</option>
                  <option value="updated">{t('app.dashboard.filters.field_updated')}</option>
                </select>
              </label>
            )}
            {isFilterVisible('vacancy') && (
              <label className="flex flex-col text-xs gap-0.5">
                <span className="text-slate-500">{t('app.dashboard.filters.vacancy')}</span>
                <select className="input input-sm w-40" value={vacancyFilter} onChange={(e) => handleVacancyChange(e.target.value)}>
                  <option value="">{t('app.dashboard.filters.all_vacancies')}</option>
                  {vacancyOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>{opt.label}</option>
                  ))}
                </select>
              </label>
            )}
            {isFilterVisible('company') && (
              <label className="flex flex-col text-xs gap-0.5">
                <span className="text-slate-500">{t('app.dashboard.filters.company')}</span>
                <select className="input input-sm w-40" value={companyFilter} onChange={(e) => handleCompanyChange(e.target.value)}>
                  <option value="">{t('app.dashboard.filters.all_companies')}</option>
                  {companyOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>{opt.label}</option>
                  ))}
                </select>
              </label>
            )}
            {isFilterVisible('manager') && (
              <label className="flex flex-col text-xs gap-0.5">
                <span className="text-slate-500">{t('app.dashboard.filters.manager')}</span>
                <select className="input input-sm w-40" value={managerFilter} onChange={(e) => handleManagerChange(e.target.value)}>
                  <option value="">{t('app.dashboard.filters.all_managers')}</option>
                  {managerOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>{opt.label}</option>
                  ))}
                </select>
              </label>
            )}
            {isFilterVisible('stages') && (
              <label className="flex flex-col text-xs gap-0.5">
                <span className="text-slate-500">{t('app.dashboard.filters.stages')}</span>
                <select
                  className="input input-sm w-32"
                  multiple
                  size={2}
                  value={stagesFilter}
                  onChange={(e) => {
                    const selected = Array.from(e.target.selectedOptions, (o) => o.value)
                    handleStagesChange(selected)
                  }}
                >
                  {stageOptions.map((opt) => (
                    <option key={opt.code} value={opt.code}>{opt.label}</option>
                  ))}
                </select>
              </label>
            )}
            <label className="flex flex-col text-xs gap-0.5">
              <span className="text-slate-500">
                {t('app.dashboard.filters.stage_view')}
              </span>
              <select
                className="input input-sm w-32"
                value={stageView}
                onChange={(e) => setStageView((e.target.value as 'all' | 'agency' | 'client') || 'all')}
              >
                {!isClientRole && (
                  <option value="all">{t('app.dashboard.filters.stage_view_all')}</option>
                )}
                {!isClientRole && (
                  <option value="agency">{t('app.dashboard.filters.stage_view_agency')}</option>
                )}
                <option value="client">
                  {t('app.dashboard.filters.stage_view_client')}
                </option>
                {isClientRole && (
                  <option value="all">{t('app.dashboard.filters.stage_view_all')}</option>
                )}
              </select>
            </label>
            {isFilterVisible('compare') && (
              <label className="flex items-center gap-2 text-xs cursor-pointer py-1">
                <input
                  type="checkbox"
                  checked={compareWithPrevious}
                  onChange={(e) => {
                    const v = e.target.checked
                    setCompareWithPrevious(v)
                    load({ compare: v })
                  }}
                />
                <span className="text-slate-600">{t('app.dashboard.filters.compare_previous')}</span>
              </label>
            )}
            {isFilterVisible('presets') && (
              <div className="flex items-center gap-1 ml-2">
                <button type="button" className="btn-secondary btn-sm text-xs" onClick={handleResetFilters}>
                  {t('app.dashboard.filters.reset')}
                </button>
                <button type="button" className="btn-secondary btn-sm text-xs" onClick={handleSavePreset}>
                  {t('app.dashboard.filters.save_preset')}
                </button>
                <button
                  type="button"
                  className="btn-secondary btn-sm text-xs"
                  onClick={handleLoadPreset}
                  disabled={!savedPreset}
                  title={savedPreset ? '' : t('app.dashboard.filters.no_preset')}
                >
                  {t('app.dashboard.filters.load_preset')}
                </button>
              </div>
            )}
            {isFilterVisible('widgets') && (
              <details className="relative group ml-auto">
                <summary className="btn-secondary btn-sm cursor-pointer list-none text-xs">
                  {t('app.dashboard.filters.widgets')}
                </summary>
                <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-slate-200 rounded-lg shadow-lg py-2 min-w-[180px] max-h-[280px] overflow-y-auto">
                  {(DEFAULT_VISIBLE_WIDGETS as string[]).map((id) => (
                    <label
                      key={id}
                      className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-50 cursor-pointer text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={visibleWidgets.has(id)}
                        onChange={() => toggleWidget(id)}
                      />
                      {t(`app.dashboard.widgets.labels.${id}`)}
                    </label>
                  ))}
                </div>
              </details>
            )}
            <details className="relative group">
              <summary className="btn-secondary btn-sm cursor-pointer list-none text-xs text-slate-500">
                {t('app.dashboard.filters.configure')}
              </summary>
              <div className="absolute left-0 top-full mt-1 z-20 bg-white border border-slate-200 rounded-lg shadow-lg py-2 min-w-[180px] max-h-[280px] overflow-y-auto">
                {(['period', 'dateRange', 'dateField', 'vacancy', 'company', 'manager', 'stages', 'compare', 'presets', 'widgets'] as DashboardFilterId[]).map((fid) => (
                  <label
                    key={fid}
                    className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-50 cursor-pointer text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={visibleFilters.has(fid)}
                      onChange={() => toggleFilter(fid)}
                    />
                    {t(`app.dashboard.filters.labels.${fid}`)}
                  </label>
                ))}
              </div>
            </details>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2">
            <span>
              {t('app.dashboard.filters.sample', { values: { count: formatNumber(periodTotal) } })}
              {dateFrom && dateTo && (
                <span className="ml-2"> • {dateFrom} — {dateTo}</span>
              )}
            </span>
            {loading && <span>{t('common.loading')}</span>}
          </div>

        {isWidgetVisible('pivot') && (
        <div className="border-t border-slate-100 pt-4 mt-2">
        <>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <div className="text-sm font-semibold">{t('app.dashboard.pivot.title')}</div>
              <div className="text-xs text-slate-500">
                {primaryLabel}
                {pivotSecondary !== 'none' && ` → ${secondaryLabel}`}
              </div>
            </div>
            <div className="flex flex-wrap gap-3 text-sm items-end">
              <label className="flex flex-col gap-1">
                {t('app.dashboard.pivot.group_by')}
                <select
                  className="input text-sm"
                  value={pivotPrimary}
                  onChange={(e) => setPivotPrimary(e.target.value as PivotDimension)}
                >
                  {dimensionOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1">
                {t('app.dashboard.pivot.subgroup')}
                <select
                  className="input text-sm"
                  value={pivotSecondary}
                  onChange={(e) => setPivotSecondary((e.target.value || 'none') as PivotDimension | 'none')}
                >
                  <option value="none">{t('app.dashboard.labels.no_subgroup')}</option>
                  {dimensionOptions.map((option) => (
                    <option key={`sec-${option.value}`} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              {pivotData.rows.length > 0 && (
                <button
                  type="button"
                  className="btn-secondary text-sm"
                  onClick={() => {
                    const headers = [
                      { key: 'key', title: primaryLabel },
                      ...pivotData.secondaryKeys.map((k) => ({ key: k, title: k })),
                      { key: 'total', title: t('app.dashboard.pivot.total') },
                    ]
                    const rows = pivotData.rows.map((row) => ({
                      key: row.key,
                      ...Object.fromEntries(pivotData.secondaryKeys.map((k) => [k, row.breakdown[k] ?? 0])),
                      total: row.total,
                    }))
                    const csv = toCSV(rows, headers)
                    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `dashboard_pivot_${new Date().toISOString().slice(0, 10)}.csv`
                    a.click()
                    URL.revokeObjectURL(url)
                  }}
                >
                  {t('app.dashboard.pivot.export')}
                </button>
              )}
            </div>
          </div>
          {pivotData.rows.length ? (
            <div className="overflow-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-slate-500">
                    <th className="py-2 pr-4">{primaryLabel}</th>
                    {pivotData.secondaryKeys.map((key) => (
                      <th key={`sec-head-${key}`} className="py-2 pr-4 text-right">
                        {key}
                      </th>
                    ))}
                    <th className="py-2 text-right">{t('app.dashboard.pivot.total')}</th>
                  </tr>
                </thead>
                <tbody>
                  {pivotData.rows.map((row) => {
                    const params = row.filterParams && Object.keys(row.filterParams).length > 0
                      ? new URLSearchParams(row.filterParams).toString()
                      : ''
                    const href = params ? `/app/candidates?${params}` : null
                    return (
                    <tr key={`pivot-${row.key}`} className="border-t border-slate-100">
                      <td className="py-2 pr-4 whitespace-nowrap">
                        {href ? (
                          <Link to={href} className="text-brand-600 hover:underline">
                            {row.key}
                          </Link>
                        ) : (
                          row.key
                        )}
                      </td>
                      {pivotSecondary !== 'none' &&
                        pivotData.secondaryKeys.map((key) => (
                          <td key={`sec-${row.key}-${key}`} className="py-2 pr-4 text-right">
                            {formatNumber(row.breakdown[key] ?? 0)}
                          </td>
                        ))}
                      {pivotSecondary === 'none' && (
                        <td className="py-2 pr-4 text-right">{formatNumber(row.total)}</td>
                      )}
                      {pivotSecondary !== 'none' && (
                        <td className="py-2 text-right font-semibold">
                          {formatNumber(row.total)}
                        </td>
                      )}
                    </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-sm text-slate-500">{t('app.dashboard.pivot.empty')}</div>
          )}
        </>
        </div>
        )}
        </div>

        {isWidgetVisible('pivotChart') && pivotData.rows.length > 0 && (
        <div className="card min-w-0 p-4 space-y-3">
          <div>
            <div className="text-sm font-semibold">{t('app.dashboard.pivot.chart_title')}</div>
            <div className="text-xs text-slate-500">
              {primaryLabel}
              {pivotSecondary !== 'none' && ` × ${secondaryLabel}`}
            </div>
          </div>
          <div className="w-full min-w-0 overflow-hidden" style={{ height: 256, minHeight: 200 }}>
            <ResponsiveContainer width="100%" height="100%" minHeight={200} minWidth={0}>
              <BarChart
                data={pivotData.rows.slice(0, 15).map((r) => ({
                  name: r.key.length > 20 ? r.key.slice(0, 18) + '…' : r.key,
                  total: r.total,
                  ...(pivotSecondary !== 'none' && pivotData.secondaryKeys.length > 0
                    ? Object.fromEntries(
                        pivotData.secondaryKeys.slice(0, 5).map((k) => [k, r.breakdown[k] ?? 0]),
                      )
                    : {}),
                }))}
                margin={{ top: 8, right: 8, left: 0, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} tickFormatter={(v) => (v?.length > 12 ? v.slice(0, 10) + '…' : v)} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => formatNumber(v)} />
                {pivotSecondary === 'none' ? (
                  <Bar dataKey="total" fill="rgb(99 102 241)" radius={[4, 4, 0, 0]} />
                ) : (
                  pivotData.secondaryKeys.slice(0, 5).map((key, i) => {
                    const colors = ['rgb(99 102 241)', 'rgb(34 197 94)', 'rgb(234 179 8)', 'rgb(239 68 68)', 'rgb(168 85 247)']
                    return <Bar key={key} dataKey={key} fill={colors[i % colors.length]} stackId="stack" radius={i === pivotData.secondaryKeys.length - 1 ? [4, 4, 0, 0] : 0} />
                  })
                )}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        )}

        {((isWidgetVisible('handoff') && handoffStats) || (isWidgetVisible('contact') && contactStats) || (isWidgetVisible('documents') && documentStats)) && (
          <div className="grid gap-4 md:grid-cols-3">
            {isWidgetVisible('handoff') && handoffStats && (
              <div className="card p-4">
                <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.widgets.handoff.title', { defaultValue: 'Передачи' })}</div>
                <div className="text-xs text-slate-500 mt-0.5">{t('app.dashboard.widgets.handoff.subtitle', { defaultValue: 'По запросам за период' })}</div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <div className="rounded-lg bg-slate-50 p-2"><span className="text-slate-500">{t('app.dashboard.widgets.handoff.requested', { defaultValue: 'Запросов' })}</span><div className="font-semibold">{formatNumber(handoffStats.total_requested)}</div></div>
                  <div className="rounded-lg bg-emerald-50 p-2"><span className="text-slate-500">{t('app.dashboard.widgets.handoff.accepted', { defaultValue: 'Принято' })}</span><div className="font-semibold text-emerald-700">{formatNumber(handoffStats.total_accepted)}</div></div>
                  <div className="rounded-lg bg-rose-50 p-2"><span className="text-slate-500">{t('app.dashboard.widgets.handoff.rejected', { defaultValue: 'Отклонено' })}</span><div className="font-semibold text-rose-700">{formatNumber(handoffStats.total_rejected)}</div></div>
                  <div className="rounded-lg bg-amber-50 p-2"><span className="text-slate-500">{t('app.dashboard.widgets.handoff.returned', { defaultValue: 'Возвращено' })}</span><div className="font-semibold text-amber-700">{formatNumber(handoffStats.total_returned)}</div></div>
                </div>
              </div>
            )}
            {isWidgetVisible('contact') && contactStats && (
              <div className="card p-4">
                <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.widgets.contact_attempts.title', { defaultValue: 'Попытки контакта' })}</div>
                <div className="text-xs text-slate-500 mt-0.5">{t('app.dashboard.widgets.contact_attempts.subtitle', { defaultValue: 'По кандидатам за период' })}</div>
                <div className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-slate-500">{t('app.dashboard.widgets.contact_attempts.total', { defaultValue: 'Всего попыток' })}</span><span className="font-semibold">{formatNumber(contactStats.total_attempts)}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">{t('app.dashboard.widgets.contact_attempts.avg', { defaultValue: 'Ср. на кандидата' })}</span><span className="font-semibold">{contactStats.avg_per_candidate.toFixed(1)}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">{t('app.dashboard.widgets.contact_attempts.limit_reached', { defaultValue: 'Достигнут лимит 3+' })}</span><span className="font-semibold">{formatNumber(contactStats.limit_reached_count)}</span></div>
                </div>
              </div>
            )}
            {isWidgetVisible('documents') && documentStats && (
              <div className="card p-4">
                <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.widgets.documents.title', { defaultValue: 'Документы' })}</div>
                <div className="text-xs text-slate-500 mt-0.5">{t('app.dashboard.widgets.documents.subtitle', { defaultValue: 'Реальные данные из БД' })}</div>
                <div className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-slate-500">{t('app.dashboard.widgets.documents.total', { defaultValue: 'Всего документов' })}</span><span className="font-semibold">{formatNumber(documentStats.total_docs)}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">{t('app.dashboard.widgets.documents.complete', { defaultValue: 'Кандидатов с готовыми' })}</span><span className="font-semibold">{formatNumber(documentStats.candidates_with_complete_docs)}</span></div>
                  {Object.keys(documentStats.by_status || {}).length > 0 && (
                    <div className="mt-2 pt-2 border-t border-slate-100">
                      <span className="text-xs text-slate-500">{t('app.dashboard.widgets.documents.by_status', { defaultValue: 'По статусу' })}</span>
                      <ul className="mt-1 space-y-0.5 text-xs">
                        {Object.entries(documentStats.by_status || {}).slice(0, 5).map(([status, count]) => (
                          <li key={status} className="flex justify-between"><span>{status}</span><span>{formatNumber(count)}</span></li>
                        ))}
                      </ul>
                    </div>
                  )}
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
                <div key={`legend-${segment.label}`} className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${STAGE_STACK_COLORS[segment.outcome]}`} />
                  <span className="truncate">
                    {segment.label} · {segment.percent}%
                  </span>
                </div>
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
          <div className="card p-4">
            <div className="text-slate-500 text-sm mb-1">{t('app.dashboard.stats.candidates_total')}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.candidates)}</div>
          </div>
          <div className="card p-4">
            <div className="text-slate-500 text-sm mb-1">{dashboardCompanyLabels.plural}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.companies)}</div>
          </div>
          <div className="card p-4">
            <div className="text-slate-500 text-sm mb-1">{t('app.dashboard.stats.vacancies')}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.vacancies)}</div>
          </div>
          <div className="card p-4 border border-brand-100">
            <div className="text-slate-500 text-sm mb-1">{t('app.dashboard.stats.period')}</div>
            <div className="text-2xl font-semibold">{formatNumber(periodTotal)}</div>
            <div className="text-xs text-slate-500 mt-1">
              {dateField === 'created'
                ? t('app.dashboard.stats.period_suffix_created')
                : t('app.dashboard.stats.period_suffix_updated')}
            </div>
          </div>
        </div>
        )}

        {businessProfileCards.length > 0 && (
          <div className="card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold">
                {t('app.dashboard.business.title', { defaultValue: 'Business profile analytics' })}
              </div>
              <div className="text-xs text-slate-500">
                {t('app.dashboard.business.type_label', { defaultValue: 'Type' })}: {businessTypeLabel}
              </div>
            </div>
            <div className="grid w-full gap-3 grid-cols-[repeat(auto-fill,minmax(180px,1fr))]">
              {businessProfileCards.map((card) => (
                <div key={card.key} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <div className="text-xs text-slate-500">{card.label}</div>
                  <div className="mt-1 text-xl font-semibold text-slate-900">{formatNumber(card.value)}</div>
                </div>
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
                    <td>{stage.label}</td>
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
                      <span className="truncate">{item.label}</span>
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
                      <span className="truncate">{item.label}</span>
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
                {t('app.dashboard.companies.title', {
                  defaultValue: '{label} overview',
                  values: { label: dashboardCompanyLabels.plural },
                })}
              </div>
              <div className="text-xs text-slate-500">
                {t('app.dashboard.companies.subtitle', {
                  defaultValue: 'Top {label} pipelines',
                  values: { label: dashboardCompanyLabels.plural.toLowerCase() },
                })}
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
                        <td className="truncate">{item.label}</td>
                        <td className="text-right font-medium">{formatNumber(item.count)}</td>
                        <td className="text-right">{formatNumber(highlight.pipeline)}</td>
                        <td className="text-right text-emerald-600">{formatNumber(highlight.hired)}</td>
                        <td className="text-right text-red-600">
                          {formatNumber(highlight.rejected + highlight.declined)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            ) : (
              <div className="text-sm text-slate-500">
                {t('app.dashboard.companies.empty', {
                  defaultValue: 'No {label} data.',
                  values: { label: dashboardCompanyLabels.singular.toLowerCase() },
                })}
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
                        <td className="truncate">{item.label}</td>
                        <td className="text-right font-medium">{formatNumber(item.count)}</td>
                        <td className="text-right">{formatNumber(highlight.pipeline)}</td>
                        <td className="text-right text-emerald-600">{formatNumber(highlight.hired)}</td>
                        <td className="text-right text-red-600">
                          {formatNumber(highlight.rejected + highlight.declined)}
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
                        <td className="truncate">{row.label}</td>
                        <td className="text-right">{formatNumber(row.highlight.pipeline)}</td>
                        <td className="text-right text-emerald-600">{formatNumber(row.highlight.hired)}</td>
                        <td className="text-right text-rose-600">
                          {formatNumber(row.highlight.rejected + row.highlight.declined)}
                        </td>
                        <td className="text-right font-semibold">{formatNumber(row.total)}</td>
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
                          <span>{t(`app.dashboard.docs_risk.${bucket}`)}</span>
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
                    <div key={row.label} className="relative overflow-hidden rounded-xl border border-brand-50">
                      <div
                        className="absolute inset-y-0 left-0 bg-brand-500/20"
                        style={{ width: `${Math.max(row.intensity * 100, 8)}%` }}
                      />
                      <div className="relative flex items-center justify-between px-3 py-2 text-sm">
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
                      </div>
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
                      <td>{row.label}</td>
                      <td className="text-right font-semibold">{formatNumber(row.pipeline)}</td>
                      <td className="text-right text-slate-600">{formatNumber(row.total)}</td>
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
    </section>
  )
}
