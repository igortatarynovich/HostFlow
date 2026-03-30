// src/pages/Dashboard.tsx
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { BarChart, Bar, Line, LineChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import api, {
  createBulkReminders,
  createReminder,
  getOnboardingStatus,
  listInvoices,
  type OnboardingStatus,
  withTenant,
} from '../api/client'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { useCurrentTenantId } from '../contexts/CurrentTenant'
import { useTenantInfo } from '../contexts/TenantInfo'
import { OnboardingWizard } from '../components/OnboardingWizard'
import { DashboardAnalyticsHubLinks } from '../components/dashboard/DashboardAnalyticsHubLinks'
import { DashboardLeadAutoFixCard } from '../components/dashboard/DashboardLeadAutoFixCard'
import { DashboardSectionCollapsible } from '../components/dashboard/DashboardSectionCollapsible'

const AnalyticsLeadConversionFunnelPageLazy = lazy(() => import('./AnalyticsLeadConversionFunnelPage'))
import {
  getTrialRetentionReport,
  getAnalyticsProfileSummary,
  getHandoffStats,
  getContactAttemptStats,
  getDocumentStats,
  getOpsCounters,
  getGoals,
  getStageMetrics,
  ackRiskIntelligenceManagerDigest,
  getRiskIntelligence,
  getRiskIntelligenceManagerDigestQueue,
  getRiskIntelligenceShadowSnapshot,
  getRiskIntelligenceTrends,
  getRiskIntelligenceValidation,
  getPerfBaseline,
  getPerfBudgets,
  recordPerfMeasurement,
  recordTrialRetentionEvent,
  type OpsCounters,
  type GoalsResponse,
  type PerfBudgetsResponse,
  type PerfBaselineResponse,
  type RiskIntelDigestQueueResponse,
  type RiskIntelShadowSnapshotItem,
  type RiskIntelShadowSnapshotResponse,
  type RiskIntelTrendsResponse,
  type RiskIntelValidationResponse,
  type RiskIntelligenceResponse,
  type StageMetricsResponse,
  type TrialRetentionReport,
} from '../api/analytics'
import { listTenantManagers } from '../api/users'
import {
  BILLING_SUBSCRIPTION_UPDATED_EVENT,
  getBillingSubscriptionCached,
} from '../api/billingSubscriptionCache'
import { listCandidateStages } from '../api/candidate_stages'
import { usePermissions } from '../hooks/usePermissions'
import { listVacancies } from '../api/vacancies'
import { invoiceDaysPastDue, invoiceOutstandingAmount } from '../modules/services/utils'
import type { Invoice } from '../api/types'
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
import {
  CRM_APP_DRILLDOWN_HREFS,
  CRM_APP_PATHS,
  dashboardInvoiceOpsDrilldownPath,
} from '../app/crmAppPaths'
import { ACTIVATION_PATHS, getRetentionNextPath, getRetentionStepKey } from '../app/activationRoutes'
import { servicesOrdersTabPath } from '../modules/services/utils'

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

type DigestBulkResultReport = {
  kind: 'remind' | 'claim'
  ok: number
  fail: number
  errors: string[]
}

type InvoiceWithPaid = Invoice & { paid_amount?: number | null }

function formatDigestBulkError(reason: unknown): string {
  const r = reason as { response?: { data?: { detail?: unknown } }; message?: string }
  const d = r?.response?.data
  const detail = d?.detail
  if (typeof detail === 'string') return detail.slice(0, 220)
  if (Array.isArray(detail)) {
    const msg = detail
      .map((x: { msg?: string; message?: string }) => x?.msg || x?.message || String(x))
      .join('; ')
    return msg.slice(0, 220)
  }
  return String(r?.message || reason || 'Error').slice(0, 220)
}

// normalizeTotal is now imported from modules/dashboard/utils

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

  const [opsCounters, setOpsCounters] = useState<OpsCounters | null>(null)
  const [opsCountersLoading, setOpsCountersLoading] = useState(false)
  const [invoiceMoneyLoading, setInvoiceMoneyLoading] = useState(false)
  const [invoiceMoney, setInvoiceMoney] = useState<{
    totalOutstanding: number
    overdueUnpaidCount: number
    maxDaysPastDue: number | null
    currency: string
  } | null>(null)
  const [vacanciesOpenLoading, setVacanciesOpenLoading] = useState(false)
  const [vacanciesOpenSummary, setVacanciesOpenSummary] = useState<{
    openCount: number
    candidatesInOpen: number
    capped: boolean
  } | null>(null)
  const [goals, setGoals] = useState<GoalsResponse | null>(null)
  const [goalsLoading, setGoalsLoading] = useState(false)
  const [stageMetrics, setStageMetrics] = useState<StageMetricsResponse | null>(null)
  const [stageMetricsLoading, setStageMetricsLoading] = useState(false)
  const [riskIntel, setRiskIntel] = useState<RiskIntelligenceResponse | null>(null)
  const [riskTrends, setRiskTrends] = useState<RiskIntelTrendsResponse | null>(null)
  const [riskValidation, setRiskValidation] = useState<RiskIntelValidationResponse | null>(null)
  const [riskShadowSnapshot, setRiskShadowSnapshot] = useState<RiskIntelShadowSnapshotResponse | null>(null)
  const [riskDigestQueue, setRiskDigestQueue] = useState<RiskIntelDigestQueueResponse | null>(null)
  const [riskDigestMinBand, setRiskDigestMinBand] = useState<'low' | 'medium' | 'high' | 'critical'>('high')
  const [riskDigestQueueReadFilter, setRiskDigestQueueReadFilter] = useState<'all' | 'unread' | 'read'>('all')
  const [riskShadowBucketStart, setRiskShadowBucketStart] = useState<string | null>(null)
  const [riskIntelLoading, setRiskIntelLoading] = useState(false)
  const [riskIntelShadowLoading, setRiskIntelShadowLoading] = useState(false)
  const [digestAckLoading, setDigestAckLoading] = useState(false)
  const [digestHandoffBusyId, setDigestHandoffBusyId] = useState<string | null>(null)
  /** Per candidate row: optional reminder assignee (user id). Empty = owner if set, else current user. */
  const [digestReminderAssigneePick, setDigestReminderAssigneePick] = useState<Record<string, string>>({})
  const [digestBulkSelected, setDigestBulkSelected] = useState<Set<string>>(() => new Set())
  const [digestBulkReminderAssignee, setDigestBulkReminderAssignee] = useState('')
  const [digestBulkBusy, setDigestBulkBusy] = useState(false)
  const [digestBulkResultReport, setDigestBulkResultReport] = useState<DigestBulkResultReport | null>(null)
  const digestBulkHeadRef = useRef<HTMLInputElement>(null)
  const [perfBaseline, setPerfBaseline] = useState<PerfBaselineResponse | null>(null)
  const [perfBaselineLoading, setPerfBaselineLoading] = useState(false)
  const [perfBudgets, setPerfBudgets] = useState<PerfBudgetsResponse | null>(null)

  const loadOpsCounters = useCallback(async () => {
    setOpsCountersLoading(true)
    if (canVacanciesOpenWidget) setVacanciesOpenLoading(true)
    try {
      const data = await getOpsCounters()
      setOpsCounters(data)
      if (canVacanciesOpenWidget) {
        if (typeof data.open_vacancies === 'number') {
          setVacanciesOpenSummary({
            openCount: data.open_vacancies,
            candidatesInOpen: typeof data.open_vacancies_candidates === 'number' ? data.open_vacancies_candidates : 0,
            capped: false,
          })
        } else {
          try {
            const rows = await listVacancies({ status: 'open', limit: 200 })
            const list = Array.isArray(rows) ? rows : []
            const capped = list.length >= 200
            let candidatesInOpen = 0
            for (const v of list) {
              candidatesInOpen += Number(v.candidate_count || 0)
            }
            setVacanciesOpenSummary({ openCount: list.length, candidatesInOpen, capped })
          } catch {
            setVacanciesOpenSummary(null)
          }
        }
      }
    } catch {
      setOpsCounters(null)
      if (canVacanciesOpenWidget) setVacanciesOpenSummary(null)
    } finally {
      setOpsCountersLoading(false)
      if (canVacanciesOpenWidget) setVacanciesOpenLoading(false)
    }
  }, [canVacanciesOpenWidget])

  useEffect(() => {
    void loadOpsCounters()
  }, [loadOpsCounters])

  const loadInvoiceMoneyWidget = useCallback(async () => {
    if (!canServicesOpsWidgets) return
    setInvoiceMoneyLoading(true)
    try {
      const data = await listInvoices({ limit: 200 })
      const rows = Array.isArray(data) ? (data as InvoiceWithPaid[]) : []
      let totalOutstanding = 0
      let overdueUnpaidCount = 0
      let maxDaysPastDue: number | null = null
      let currency = 'PLN'
      for (const inv of rows) {
        const st = String(inv.status || '').toLowerCase()
        if (st === 'cancelled' || st === 'paid') continue
        const out = invoiceOutstandingAmount(inv.total_amount, inv.paid_amount)
        if (out <= 0) continue
        currency = inv.currency || currency
        totalOutstanding += out
        const days = invoiceDaysPastDue(inv.due_date, out)
        if (days != null) {
          maxDaysPastDue = maxDaysPastDue == null ? days : Math.max(maxDaysPastDue, days)
        }
        if (inv.status === 'overdue' && Number(inv.total_amount || 0) > Number(inv.paid_amount || 0)) {
          overdueUnpaidCount += 1
        }
      }
      setInvoiceMoney({ totalOutstanding, overdueUnpaidCount, maxDaysPastDue, currency })
    } catch {
      setInvoiceMoney(null)
    } finally {
      setInvoiceMoneyLoading(false)
    }
  }, [canServicesOpsWidgets])

  useEffect(() => {
    void loadInvoiceMoneyWidget()
  }, [loadInvoiceMoneyWidget])

  const loadGoals = useCallback(async () => {
    setGoalsLoading(true)
    try {
      const data = await getGoals()
      setGoals(data)
    } catch {
      setGoals(null)
    } finally {
      setGoalsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadGoals()
  }, [loadGoals])

  const loadStageMetrics = useCallback(async () => {
    setStageMetricsLoading(true)
    try {
      const data = await getStageMetrics({ limit_transitions: 12 })
      setStageMetrics(data)
    } catch {
      setStageMetrics(null)
    } finally {
      setStageMetricsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadStageMetrics()
  }, [loadStageMetrics])

  const loadRiskOpsCore = useCallback(async () => {
    if (!canViewRiskOpsUi) {
      setRiskIntel(null)
      setRiskTrends(null)
      setRiskValidation(null)
      setRiskDigestQueue(null)
      setRiskShadowSnapshot(null)
      setRiskShadowBucketStart(null)
      return
    }
    const perfT0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
    setRiskIntelLoading(true)
    let settledMeta: {
      baseline: string
      trends: string
      validation: string
      digest_queue: string
    } | null = null
    try {
      const [br, trr, vr, dq] = await Promise.allSettled([
        getRiskIntelligence({ limit: 5000 }),
        getRiskIntelligenceTrends({ days: 30 }),
        getRiskIntelligenceValidation({ cohort_days: 14, lag_days: 7 }),
        getRiskIntelligenceManagerDigestQueue({ min_band: riskDigestMinBand, limit_buckets: 21 }),
      ])
      settledMeta = {
        baseline: br.status,
        trends: trr.status,
        validation: vr.status,
        digest_queue: dq.status,
      }
      setRiskIntel(br.status === 'fulfilled' ? br.value : null)
      setRiskTrends(trr.status === 'fulfilled' ? trr.value : null)
      setRiskValidation(vr.status === 'fulfilled' ? vr.value : null)
      setRiskDigestQueue(dq.status === 'fulfilled' ? dq.value : null)
    } finally {
      setRiskIntelLoading(false)
      if (settledMeta) {
        const durationMs = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - perfT0
        void recordPerfMeasurement({
          metricKey: 'dashboard.risk_intel.core.load',
          durationMs,
          route: typeof window !== 'undefined' ? `${window.location.pathname}${window.location.search}` : undefined,
          meta: {
            min_band: riskDigestMinBand,
            ...settledMeta,
          },
        }).catch(() => {})
      }
    }
  }, [canViewRiskOpsUi, riskDigestMinBand])

  const loadRiskShadow = useCallback(async () => {
    if (!canViewRiskOpsUi) {
      setRiskShadowSnapshot(null)
      return
    }
    const perfT0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
    setRiskIntelShadowLoading(true)
    let ok = false
    try {
      const snap = await getRiskIntelligenceShadowSnapshot({
        limit: 50,
        min_band: riskDigestMinBand,
        bucket_start: riskShadowBucketStart ?? undefined,
      })
      setRiskShadowSnapshot(snap)
      ok = true
    } catch {
      setRiskShadowSnapshot(null)
    } finally {
      const durationMs = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - perfT0
      void recordPerfMeasurement({
        metricKey: 'dashboard.risk_intel.shadow_snapshot.load',
        durationMs,
        route: typeof window !== 'undefined' ? `${window.location.pathname}${window.location.search}` : undefined,
        meta: {
          ok,
          min_band: riskDigestMinBand,
          bucket_pinned: Boolean(riskShadowBucketStart),
        },
      }).catch(() => {})
      setRiskIntelShadowLoading(false)
    }
  }, [canViewRiskOpsUi, riskShadowBucketStart, riskDigestMinBand])

  useEffect(() => {
    setRiskShadowBucketStart(null)
    setRiskDigestQueueReadFilter('all')
  }, [riskDigestMinBand])

  const filteredDigestBuckets = useMemo(() => {
    const all = riskDigestQueue?.buckets ?? []
    if (riskDigestQueueReadFilter === 'unread') return all.filter((b) => b.unread)
    if (riskDigestQueueReadFilter === 'read') return all.filter((b) => !b.unread)
    return all
  }, [riskDigestQueue, riskDigestQueueReadFilter])

  useEffect(() => {
    if (!riskDigestQueue || riskShadowBucketStart === null) return
    const visible = filteredDigestBuckets.some((b) => b.bucket_start === riskShadowBucketStart)
    if (!visible) setRiskShadowBucketStart(null)
  }, [filteredDigestBuckets, riskDigestQueue, riskShadowBucketStart])

  const latestDigestBucketStart = riskDigestQueue?.buckets[0]?.bucket_start ?? null

  useEffect(() => {
    void loadRiskOpsCore()
  }, [loadRiskOpsCore])

  useEffect(() => {
    void loadRiskShadow()
  }, [loadRiskShadow])

  const onManagerDigestAck = useCallback(async () => {
    const bs = riskShadowSnapshot?.bucket_start
    if (!bs || digestAckLoading) return
    setDigestAckLoading(true)
    try {
      await ackRiskIntelligenceManagerDigest({ bucket_start: bs })
      await loadRiskOpsCore()
    } catch (e) {
      console.error('manager digest ack failed', e)
    } finally {
      setDigestAckLoading(false)
    }
  }, [riskShadowSnapshot?.bucket_start, digestAckLoading, loadRiskOpsCore])

  const onManagerDigestAckLatest = useCallback(async () => {
    const latest = riskDigestQueue?.buckets[0]?.bucket_start
    if (!latest || digestAckLoading) return
    setDigestAckLoading(true)
    try {
      await ackRiskIntelligenceManagerDigest({ bucket_start: latest })
      await loadRiskOpsCore()
    } catch (e) {
      console.error('manager digest ack latest failed', e)
    } finally {
      setDigestAckLoading(false)
    }
  }, [riskDigestQueue?.buckets?.[0]?.bucket_start, digestAckLoading, loadRiskOpsCore])

  const refreshRiskOpsIntel = useCallback(() => {
    void Promise.all([loadRiskOpsCore(), loadRiskShadow()])
  }, [loadRiskOpsCore, loadRiskShadow])

  const onShadowDigestReminder = useCallback(
    async (row: RiskIntelShadowSnapshotItem, assigneeChoice?: string | null) => {
      if (!myUserId || digestHandoffBusyId) return
      const label =
        row.display_name?.trim() ||
        (row.short_id ? `#${row.short_id}` : row.entity_id.slice(0, 8))
      setDigestHandoffBusyId(row.entity_id)
      try {
        const due = new Date(Date.now() + 24 * 60 * 60 * 1000)
        const explicit = assigneeChoice?.trim()
        const recruiter = row.recruiter_id?.trim()
        const assignee_id = explicit || recruiter || undefined
        await createReminder({
          title: t('app.dashboard.risk_intel.shadow_handoff_reminder_title', { values: { name: label } }),
          description:
            row.drivers?.length ?
              row.drivers.slice(0, 5).join('; ')
            : t('app.dashboard.risk_intel.shadow_handoff_reminder_fallback'),
          type: 'custom',
          entity_type: 'candidate',
          entity_id: row.entity_id,
          due_at: due.toISOString(),
          source: 'risk_intel.shadow_digest',
          ...(assignee_id ? { assignee_id } : {}),
          payload: {
            risk_intel_digest: {
              band: row.band,
              score: row.score,
              bucket_start: riskShadowSnapshot?.bucket_start ?? null,
              assignee_choice: explicit || null,
            },
          },
        })
        setDigestReminderAssigneePick((p) => {
          const next = { ...p }
          delete next[row.entity_id]
          return next
        })
      } catch (e) {
        console.error('shadow digest reminder failed', e)
      } finally {
        setDigestHandoffBusyId(null)
      }
    },
    [myUserId, digestHandoffBusyId, t, riskShadowSnapshot?.bucket_start],
  )

  const onShadowDigestClaim = useCallback(
    async (row: RiskIntelShadowSnapshotItem) => {
      if (!myUserId || digestHandoffBusyId) return
      setDigestHandoffBusyId(row.entity_id)
      try {
        await api.patch(`/candidates/${row.entity_id}`, { recruiter_id: myUserId })
        await loadRiskShadow()
      } catch (e) {
        console.error('shadow digest claim failed', e)
      } finally {
        setDigestHandoffBusyId(null)
      }
    },
    [myUserId, digestHandoffBusyId, loadRiskShadow],
  )

  const digestBulkRowIds = useMemo(
    () => (riskShadowSnapshot?.items ?? []).map((r) => r.entity_id),
    [riskShadowSnapshot?.items],
  )

  useEffect(() => {
    setDigestBulkSelected(new Set())
    setDigestBulkResultReport(null)
  }, [riskShadowSnapshot?.bucket_start])

  useEffect(() => {
    const el = digestBulkHeadRef.current
    if (!el) return
    const n = digestBulkRowIds.length
    const c = digestBulkSelected.size
    el.indeterminate = n > 0 && c > 0 && c < n
  }, [digestBulkRowIds.length, digestBulkSelected.size])

  const toggleDigestBulkRow = useCallback((id: string) => {
    setDigestBulkSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const toggleDigestBulkAll = useCallback(() => {
    setDigestBulkSelected((prev) => {
      if (digestBulkRowIds.length === 0) return new Set()
      const allOn = digestBulkRowIds.every((id) => prev.has(id))
      if (allOn) return new Set()
      return new Set(digestBulkRowIds)
    })
  }, [digestBulkRowIds])

  const onShadowDigestBulkRemind = useCallback(async () => {
    if (!myUserId || digestBulkBusy || !riskShadowSnapshot) return
    const ids = Array.from(digestBulkSelected)
    if (ids.length === 0) return
    const rowById = new Map(riskShadowSnapshot.items.map((r) => [r.entity_id, r]))
    setDigestBulkBusy(true)
    setDigestBulkResultReport(null)
    try {
      const due = new Date(Date.now() + 24 * 60 * 60 * 1000)
      const bulkPick = digestBulkReminderAssignee.trim()
      const sharedPayload = {
        risk_intel_digest: {
          bulk: true,
          bucket_start: riskShadowSnapshot.bucket_start ?? null,
          min_band: riskShadowSnapshot.min_band,
          assignee_choice: bulkPick || null,
        },
      }
      if (bulkPick) {
        const data = await createBulkReminders({
          title: t('app.dashboard.risk_intel.shadow_bulk_reminder_title', { values: { n: ids.length } }),
          description: t('app.dashboard.risk_intel.shadow_bulk_reminder_desc'),
          type: 'custom',
          entity_type: 'candidate',
          entity_ids: ids,
          due_at: due.toISOString(),
          source: 'risk_intel.shadow_digest',
          assignee_id: bulkPick,
          payload: sharedPayload,
        })
        const results = data?.results ?? []
        const ok = results.filter((r) => r.ok).length
        const fail =
          results.length > 0 ? results.length - ok : ids.length > 0 ? ids.length : 0
        const errors =
          results.length === 0 && ids.length > 0 ?
            [t('app.dashboard.risk_intel.shadow_bulk_empty_response')]
          : results
              .filter((r) => !r.ok)
              .map((r) => String(r.error || r.entity_id || 'Unknown').slice(0, 220))
              .slice(0, 5)
        setDigestBulkResultReport({ kind: 'remind', ok, fail, errors })
        if (fail === 0) {
          setDigestBulkSelected(new Set())
          setDigestBulkReminderAssignee('')
        }
      } else {
        const settled = await Promise.allSettled(
          ids.map((id) => {
            const row = rowById.get(id)
            if (!row) return Promise.reject(new Error(`Missing row ${id}`))
            const label =
              row.display_name?.trim() ||
              (row.short_id ? `#${row.short_id}` : row.entity_id.slice(0, 8))
            const recruiter = row.recruiter_id?.trim()
            return createReminder({
              title: t('app.dashboard.risk_intel.shadow_handoff_reminder_title', { values: { name: label } }),
              description:
                row.drivers?.length ?
                  row.drivers.slice(0, 5).join('; ')
                : t('app.dashboard.risk_intel.shadow_handoff_reminder_fallback'),
              type: 'custom',
              entity_type: 'candidate',
              entity_id: id,
              due_at: due.toISOString(),
              source: 'risk_intel.shadow_digest',
              ...(recruiter ? { assignee_id: recruiter } : {}),
              payload: {
                risk_intel_digest: {
                  band: row.band,
                  score: row.score,
                  bucket_start: riskShadowSnapshot.bucket_start ?? null,
                  bulk: true,
                },
              },
            })
          }),
        )
        let ok = 0
        let fail = 0
        const errors: string[] = []
        for (const s of settled) {
          if (s.status === 'fulfilled') {
            ok += 1
          } else {
            fail += 1
            if (errors.length < 5) errors.push(formatDigestBulkError(s.reason))
          }
        }
        setDigestBulkResultReport({ kind: 'remind', ok, fail, errors })
        if (fail === 0) {
          setDigestBulkSelected(new Set())
          setDigestBulkReminderAssignee('')
        }
      }
    } catch (e) {
      console.error('shadow digest bulk remind failed', e)
      setDigestBulkResultReport({
        kind: 'remind',
        ok: 0,
        fail: ids.length,
        errors: [formatDigestBulkError(e)],
      })
    } finally {
      setDigestBulkBusy(false)
    }
  }, [
    myUserId,
    digestBulkBusy,
    digestBulkSelected,
    digestBulkReminderAssignee,
    t,
    riskShadowSnapshot,
  ])

  const onShadowDigestBulkClaim = useCallback(async () => {
    if (!myUserId || digestBulkBusy) return
    const ids = Array.from(digestBulkSelected)
    if (ids.length === 0) return
    setDigestBulkBusy(true)
    setDigestBulkResultReport(null)
    try {
      const settled = await Promise.allSettled(
        ids.map((id) => api.patch(`/candidates/${id}`, { recruiter_id: myUserId })),
      )
      let ok = 0
      let fail = 0
      const errors: string[] = []
      for (const s of settled) {
        if (s.status === 'fulfilled') ok += 1
        else {
          fail += 1
          if (errors.length < 5) errors.push(formatDigestBulkError(s.reason))
        }
      }
      setDigestBulkResultReport({ kind: 'claim', ok, fail, errors })
      if (ok > 0) await loadRiskShadow()
      if (fail === 0) setDigestBulkSelected(new Set())
    } catch (e) {
      console.error('shadow digest bulk claim failed', e)
      setDigestBulkResultReport({
        kind: 'claim',
        ok: 0,
        fail: ids.length,
        errors: [formatDigestBulkError(e)],
      })
    } finally {
      setDigestBulkBusy(false)
    }
  }, [myUserId, digestBulkBusy, digestBulkSelected, loadRiskShadow])

  const loadPerfBaseline = useCallback(async () => {
    setPerfBaselineLoading(true)
    try {
      const data = await getPerfBaseline({ days: 14, limit: 30 })
      setPerfBaseline(data)
    } catch {
      setPerfBaseline(null)
    } finally {
      setPerfBaselineLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadPerfBaseline()
  }, [loadPerfBaseline])

  useEffect(() => {
    ;(async () => {
      try {
        const data = await getPerfBudgets()
        setPerfBudgets(data)
      } catch {
        setPerfBudgets(null)
      }
    })()
  }, [])

  const [globalCounts, setGlobalCounts] = useState({ candidates: 0, companies: 0, vacancies: 0 })
  const [periodTotal, setPeriodTotal] = useState(0)
  const [slices, setSlices] = useState<CandidateSlicesResponse | null>(null)
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
  const [savedPreset, setSavedPreset] = useState<Record<string, unknown> | null>(null)
  const pivotChartContainerRef = useRef<HTMLDivElement | null>(null)
  const [isPivotChartContainerReady, setIsPivotChartContainerReady] = useState(false)

  useEffect(() => {
    if (!isTrialTenant || !canManageBilling) {
      setTrialEndsAt(null)
      return
    }
    let cancelled = false
    const loadTrialEnd = async () => {
      try {
        const subscription = await getBillingSubscriptionCached()
        if (!cancelled) {
          setTrialEndsAt(subscription?.trial_ends_at || null)
        }
      } catch {
        if (!cancelled) {
          setTrialEndsAt(null)
        }
      }
    }
    void loadTrialEnd()
    const onBillingUpdated = () => {
      void loadTrialEnd()
    }
    window.addEventListener(BILLING_SUBSCRIPTION_UPDATED_EVENT, onBillingUpdated)
    return () => {
      cancelled = true
      window.removeEventListener(BILLING_SUBSCRIPTION_UPDATED_EVENT, onBillingUpdated)
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
      d1: t('app.dashboard.trial_center.retention.day1'),
      d2: t('app.dashboard.trial_center.retention.day2'),
      d3: t('app.dashboard.trial_center.retention.day3'),
      d7: t('app.dashboard.trial_center.retention.day7'),
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

  const visibleWidgetsKey = useMemo(() => `${dashUserBase}:visibleWidgets`, [dashUserBase])
  const visibleFiltersKey = useMemo(() => `${dashUserBase}:visibleFilters`, [dashUserBase])
  const dashboardPresetKey = useMemo(() => `${dashUserBase}:preset`, [dashUserBase])

  useEffect(() => {
    const migrate = (suffix: string) => {
      const nk = `${dashUserBase}:${suffix}`
      const ok = `hf:dashboard:${tenantId}:${suffix}`
      try {
        if (!localStorage.getItem(nk) && localStorage.getItem(ok)) {
          localStorage.setItem(nk, localStorage.getItem(ok)!)
        }
      } catch {
        /* ignore */
      }
    }
    migrate('visibleWidgets')
    migrate('visibleFilters')
    migrate('preset')
    migrate('sections')
  }, [dashUserBase, tenantId])
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
  }, [dashUserBase, loadVisibleWidgets, loadVisibleFilters])
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

  const documentBlockerAnalytics = useMemo(() => {
    if (!documentStats) {
      return {
        total: 0,
        missingOrRequested: 0,
        awaitingReview: 0,
        problematic: 0,
        estimatedBlockedRevenue: 0,
      }
    }
    const byStatus = Object.entries(documentStats.by_status || {}).reduce<Record<string, number>>((acc, [k, v]) => {
      acc[String(k || '').toLowerCase()] = Number(v || 0)
      return acc
    }, {})
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
    const estimatedBlockedRevenue = serviceOrdersInProgress > 0 && avgOrderRevenue > 0
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

  const stageVelocityRows = useMemo(() => {
    if (!slices?.snapshot?.length) return []
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
    const rows = Array.from(store.entries()).map(([stageCode, payload]) => {
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

  const businessProfileCards = useMemo(() => {
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

  const managerLoadRows = useMemo(() => {
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
      <div className="min-h-0 flex-1 space-y-0 gap-0 overflow-auto px-0 py-0">
        {tenantId && retentionStatus?.onboarding_required === true && <OnboardingWizard tenantId={tenantId} />}
        <DashboardLeadAutoFixCard opsCounters={opsCounters} onRefreshOps={loadOpsCounters} />
        {(() => {
          const slow = stageVelocityRows[0]
          const showStrip =
            can('leads.view') || documentBlockerAnalytics.total > 0 || Boolean(slow && slow.avgDays >= 2 && slow.total >= 2)
          if (!showStrip) return null
          return (
            <div className="mb-3 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-700">
                <span className="font-semibold text-slate-900">
                  {t('app.dashboard.insights_strip.title', { defaultValue: 'Signals' })}
                </span>
                {can('leads.view') ? (
                  <a className="text-brand-700 hover:underline" href="#lead-conversion">
                    {t('app.dashboard.insights_strip.lead_funnel', { defaultValue: 'Lead conversion funnel →' })}
                  </a>
                ) : null}
                {documentBlockerAnalytics.total > 0 ? (
                  <Link className="text-amber-800 hover:underline" to={documentQuickFilterHref('missing')}>
                    {t('app.dashboard.insights_strip.docs_blockers', {
                      defaultValue: '{count} document issues →',
                      values: { count: documentBlockerAnalytics.total },
                    })}
                  </Link>
                ) : null}
                {slow && slow.avgDays >= 2 && slow.total >= 2 ? (
                  <span className="text-slate-600">
                    {t('app.dashboard.insights_strip.slow_stage', {
                      defaultValue: 'Avg time in «{stage}»: ~{days} d ({n} candidates)',
                      values: {
                        stage: slow.label,
                        days: Math.round(slow.avgDays * 10) / 10,
                        n: slow.total,
                      },
                    })}
                  </span>
                ) : null}
              </div>
            </div>
          )
        })()}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">
                {t('app.dashboard.ops.title')}
              </div>
              <div className="mt-0.5 text-xs text-slate-500">
                {t('app.dashboard.ops.subtitle')}
              </div>
            </div>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                void loadOpsCounters()
                void loadInvoiceMoneyWidget()
              }}
              disabled={opsCountersLoading || invoiceMoneyLoading || vacanciesOpenLoading}
            >
              {opsCountersLoading || invoiceMoneyLoading || vacanciesOpenLoading
                ? t('common.loading')
                : t('common.actions.refresh')}
            </button>
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Link
              to={CRM_APP_DRILLDOWN_HREFS.candidatesQueueNoNextAction}
              title={drilldownTitle}
              className="rounded-xl border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100"
            >
              <div className="text-xs text-slate-500">{t('app.dashboard.ops.no_next_action')}</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{opsCounters?.no_next_action_candidates ?? '—'}</div>
              <div className="mt-1 text-xs text-slate-600">{t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span></div>
            </Link>

            {canVacanciesOpenWidget ? (
              <Link
                to={CRM_APP_DRILLDOWN_HREFS.vacanciesOpen}
                title={drilldownTitle}
                className="rounded-xl border border-slate-200 bg-brand-50/50 p-3 hover:bg-brand-50/80"
              >
                <div className="text-xs text-slate-500">
                  {t('app.dashboard.ops.open_vacancies')}
                </div>
                <div className="mt-1 text-2xl font-semibold text-brand-950">
                  {vacanciesOpenLoading
                    ? '…'
                    : vacanciesOpenSummary
                      ? vacanciesOpenSummary.capped
                        ? `${vacanciesOpenSummary.openCount}+`
                        : vacanciesOpenSummary.openCount
                      : '—'}
                </div>
                {vacanciesOpenSummary && !vacanciesOpenLoading ? (
                  <div className="mt-1 text-xs text-slate-600">
                    {t('app.dashboard.ops.open_vacancies_pipeline', { values: { count: vacanciesOpenSummary.candidatesInOpen } })}
                  </div>
                ) : null}
                {vacanciesOpenSummary?.capped ? (
                  <div className="mt-0.5 text-[11px] text-slate-500">
                    {t('app.dashboard.ops.open_vacancies_capped')}
                  </div>
                ) : null}
                <div className="mt-1 text-xs text-slate-600">
                  {t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span>
                </div>
              </Link>
            ) : null}

            <Link
              to={CRM_APP_DRILLDOWN_HREFS.tasksOverdueReminders}
              title={drilldownTitle}
              className="rounded-xl border border-slate-200 bg-rose-50/60 p-3 hover:bg-rose-50"
            >
              <div className="text-xs text-slate-500">{t('app.dashboard.ops.overdue_reminders')}</div>
              <div className="mt-1 text-2xl font-semibold text-rose-700">{opsCounters?.overdue_reminders ?? '—'}</div>
              <div className="mt-1 text-xs text-slate-600">{t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span></div>
            </Link>

            {canServicesOpsWidgets ? (
              <Link
                to={CRM_APP_DRILLDOWN_HREFS.ordersOpen}
                title={drilldownTitle}
                className="rounded-xl border border-slate-200 bg-sky-50/60 p-3 hover:bg-sky-50"
              >
                <div className="text-xs text-slate-500">
                  {t('app.dashboard.ops.open_service_orders')}
                </div>
                <div className="mt-1 text-2xl font-semibold text-slate-900">
                  {opsCountersLoading ? '…' : opsCounters?.open_service_orders ?? '—'}
                </div>
                <div className="mt-1 text-xs text-slate-600">
                  {t('app.dashboard.ops.open_service_orders_hint')}
                </div>
                <div className="mt-1 text-xs text-slate-600">
                  {t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span>
                </div>
              </Link>
            ) : null}

            {canServicesOpsWidgets ? (
              <Link
                to={dashboardInvoiceOpsDrilldownPath(invoiceMoney?.overdueUnpaidCount ?? 0)}
                title={drilldownTitle}
                className={`rounded-xl border border-slate-200 p-3 hover:bg-slate-100 ${
                  invoiceMoney && invoiceMoney.overdueUnpaidCount > 0 ? 'bg-amber-50/70' : 'bg-slate-50'
                }`}
              >
                <div className="text-xs text-slate-500">
                  {t('app.dashboard.ops.invoice_outstanding')}
                </div>
                <div className="mt-1 text-2xl font-semibold text-slate-900">
                  {invoiceMoneyLoading
                    ? '…'
                    : invoiceMoney
                      ? (() => {
                          try {
                            return new Intl.NumberFormat(locale, {
                              style: 'currency',
                              currency: invoiceMoney.currency,
                            }).format(invoiceMoney.totalOutstanding)
                          } catch {
                            return String(invoiceMoney.totalOutstanding)
                          }
                        })()
                      : '—'}
                </div>
                {invoiceMoney && invoiceMoney.overdueUnpaidCount > 0 ? (
                  <div className="mt-1 text-xs font-medium text-rose-700">
                    {t('app.dashboard.ops.invoice_overdue_unpaid', { values: { count: invoiceMoney.overdueUnpaidCount } })}
                  </div>
                ) : null}
                <div className="mt-1 text-xs text-slate-600">
                  {t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span>
                </div>
              </Link>
            ) : null}

            <Link
              to={CRM_APP_DRILLDOWN_HREFS.leadsNeedsRouting}
              title={drilldownTitle}
              className="rounded-xl border border-slate-200 bg-amber-50/60 p-3 hover:bg-amber-50"
            >
              <div className="text-xs text-slate-500">{t('app.dashboard.ops.leads_needs_routing')}</div>
              <div className="mt-1 text-2xl font-semibold text-amber-700">{opsCounters?.leads_needs_routing ?? '—'}</div>
              <div className="mt-1 text-xs text-slate-600">{t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span></div>
            </Link>

            <Link
              to={CRM_APP_DRILLDOWN_HREFS.leadsFailed}
              title={drilldownTitle}
              className="rounded-xl border border-slate-200 bg-rose-50/60 p-3 hover:bg-rose-50"
            >
              <div className="text-xs text-slate-500">{t('app.dashboard.ops.leads_failed')}</div>
              <div className="mt-1 text-2xl font-semibold text-rose-700">{opsCounters?.leads_failed ?? '—'}</div>
              <div className="mt-1 text-xs text-slate-600">{t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span></div>
            </Link>

            <Link
              to={CRM_APP_DRILLDOWN_HREFS.leadsProcessedNoNextAction}
              title={drilldownTitle}
              className="rounded-xl border border-slate-200 bg-amber-50/60 p-3 hover:bg-amber-50"
            >
              <div className="text-xs text-slate-500">
                {t('app.dashboard.ops.leads_no_next_action')}
              </div>
              <div className="mt-1 text-2xl font-semibold text-amber-700">{opsCounters?.leads_no_next_action ?? '—'}</div>
              <div className="mt-1 text-xs text-slate-600">{t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span></div>
            </Link>

            <Link
              to={CRM_APP_DRILLDOWN_HREFS.tasksLeadsSlaNudges}
              title={drilldownTitle}
              className="rounded-xl border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100"
            >
              <div className="text-xs text-slate-500">
                {t('app.dashboard.ops.leads_sla_nudges')}
              </div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{opsCounters?.leads_sla_no_next_action_reminders ?? '—'}</div>
              <div className="mt-1 text-xs text-slate-600">{t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span></div>
            </Link>

            <Link
              to={CRM_APP_DRILLDOWN_HREFS.leadsProcessedStuck}
              title={drilldownTitle}
              className="rounded-xl border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100"
            >
              <div className="text-xs text-slate-500">
                {t('app.dashboard.ops.leads_stuck_nudges')}
              </div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{opsCounters?.leads_sla_stuck_stage_reminders ?? '—'}</div>
              <div className="mt-1 text-xs text-slate-600">{t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span></div>
            </Link>

            <Link
              to={CRM_APP_DRILLDOWN_HREFS.candidatesDraftIntakeDebug}
              title={drilldownTitle}
              className="rounded-xl border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100"
            >
              <div className="text-xs text-slate-500">{t('app.dashboard.ops.draft_intake')}</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{opsCounters?.draft_intake_stale ?? '—'}</div>
              <div className="mt-1 text-xs text-slate-600">{t('app.dashboard.ops.note')}</div>
            </Link>

            <Link to={CRM_APP_PATHS.automationRules} className="rounded-xl border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100">
              <div className="text-xs text-slate-500">{t('app.dashboard.ops.automation_rules')}</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{opsCounters?.automation_rules_enabled ?? '—'}</div>
              <div className="mt-1 text-xs text-slate-600">{t('app.dashboard.ops.drilldown')} <span className="text-[10px]">↗</span></div>
            </Link>

            <Link to={CRM_APP_PATHS.automationLog} className="rounded-xl border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100">
              <div className="text-xs text-slate-500">{t('app.dashboard.ops.automation_24h')}</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">{opsCounters?.automation_events_24h ?? '—'}</div>
              <div className="mt-1 text-xs text-slate-600">{t('app.dashboard.ops.drilldown')}</div>
            </Link>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">
                {t('app.dashboard.goals.title')}
              </div>
              <div className="mt-0.5 text-xs text-slate-500">
                {t('app.dashboard.goals.subtitle')}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {goals?.share_url ? (
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => void navigator.clipboard?.writeText(`${window.location.origin}${goals.share_url}`).catch(() => {})}
                >
                  {t('app.dashboard.goals.copy_share')}
                </button>
              ) : null}
              <button type="button" className="btn-secondary btn-sm" onClick={() => void loadGoals()} disabled={goalsLoading}>
                {goalsLoading ? t('common.loading') : t('common.actions.refresh')}
              </button>
            </div>
          </div>

          {!goals ? (
            <div className="mt-3 text-sm text-slate-500">{t('app.dashboard.goals.empty')}</div>
          ) : (
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              {(goals.goals || []).map((g) => {
                const value = (goals.metrics || {})[g.key]
                const target = g.target
                const op = String(g.op || '>=')
                const ok =
                  typeof value === 'number'
                    ? op === '>='
                      ? value >= target
                      : op === '<='
                        ? value <= target
                        : value === target
                    : true
                return (
                  <div key={g.key} className={ok ? 'rounded-xl border border-emerald-200 bg-emerald-50/50 p-3' : 'rounded-xl border border-rose-200 bg-rose-50/50 p-3'}>
                    <div className="text-xs font-semibold text-slate-700">{g.label || g.key}</div>
                    <div className="mt-1 flex items-baseline justify-between gap-2">
                      <div className="text-2xl font-semibold text-slate-900">{value ?? '—'}</div>
                      <div className="text-xs text-slate-600">
                        {op} {target}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {canViewRiskOpsUi ? (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">
                {t('app.dashboard.risk_intel.title')}
              </div>
              <div className="mt-0.5 text-xs text-slate-500">
                {t('app.dashboard.risk_intel.subtitle')}
              </div>
            </div>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => refreshRiskOpsIntel()}
              disabled={riskIntelLoading || riskIntelShadowLoading}
            >
              {riskIntelLoading || riskIntelShadowLoading
                ? t('common.loading')
                : t('common.actions.refresh')}
            </button>
          </div>

          {!riskIntel ? (
            <div className="mt-3 text-sm text-slate-500">
              {t('app.dashboard.risk_intel.empty')}
            </div>
          ) : (
            <div className="mt-3 grid gap-3 lg:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-semibold text-slate-700">
                  {t('app.dashboard.risk_intel.summary')}
                </div>
                <div className="mt-2 space-y-1 text-sm text-slate-700">
                  <div className="flex justify-between gap-2">
                    <span>{t('app.dashboard.risk_intel.evaluated')}</span>
                    <span className="font-semibold">{riskIntel.candidates_evaluated}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span>{t('app.dashboard.risk_intel.avg_score')}</span>
                    <span className="font-semibold">{riskIntel.avg_risk_score}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span>{t('app.dashboard.risk_intel.high_plus')}</span>
                    <span className="font-semibold text-amber-800">{riskIntel.high_risk_volume}</span>
                  </div>
                  <div className="pt-1 text-xs text-slate-500">
                    {riskIntel.risk_version} ·{' '}
                    {riskIntel.generated_at ? new Date(riskIntel.generated_at).toLocaleString() : '—'}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-semibold text-slate-700">
                  {t('app.dashboard.risk_intel.bands')}
                </div>
                <div className="mt-2 space-y-1 text-sm">
                  {(['low', 'medium', 'high', 'critical'] as const).map((b) => (
                    <div key={b} className="flex justify-between gap-2">
                      <span className="capitalize text-slate-600">{b}</span>
                      <span className="font-semibold text-slate-900">{riskIntel.band_distribution?.[b] ?? 0}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-semibold text-slate-700">
                  {t('app.dashboard.risk_intel.first_response')}
                </div>
                <div className="mt-2 space-y-1 text-sm">
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-600">0–24h</span>
                    <span className="font-semibold text-slate-900">{riskIntel.first_response_hours_histogram?.['0_24h'] ?? 0}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-600">24–48h</span>
                    <span className="font-semibold text-slate-900">{riskIntel.first_response_hours_histogram?.['24_48h'] ?? 0}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-600">48–72h</span>
                    <span className="font-semibold text-slate-900">{riskIntel.first_response_hours_histogram?.['48_72h'] ?? 0}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-600">72h+</span>
                    <span className="font-semibold text-slate-900">{riskIntel.first_response_hours_histogram?.['72h_plus'] ?? 0}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-600">{t('app.dashboard.risk_intel.no_touch')}</span>
                    <span className="font-semibold text-slate-900">{riskIntel.first_response_hours_histogram?.['no_touch'] ?? 0}</span>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 lg:col-span-3">
                <div className="text-xs font-semibold text-slate-700">
                  {t('app.dashboard.risk_intel.by_stage')}
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.entries(riskIntel.risk_distribution_by_stage || {})
                    .slice(0, 12)
                    .map(([code, row]) => (
                      <div
                        key={code}
                        className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700"
                        title={translateStageLabel(code, code) || code}
                      >
                        <span className="font-medium">{translateStageLabel(code, code) || code}</span>
                        <span className="ml-1 text-slate-500">
                          {row.avg_risk_score?.toFixed?.(1) ?? row.avg_risk_score} · {row.high_plus_count ?? 0}+
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}

          {!riskIntelLoading && riskTrends && riskTrends.points && riskTrends.points.length > 0 ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs font-semibold text-slate-700">
                {t('app.dashboard.risk_intel.trend_title')}
              </div>
              <div className="mt-2 h-52 w-full min-w-0 shrink-0">
                <ResponsiveContainer width="100%" height={208} minHeight={160} minWidth={0}>
                  <LineChart
                    data={riskTrends.points.map((p) => ({
                      label: p.bucket_start
                        ? new Date(p.bucket_start).toLocaleString(locale, {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                          })
                        : '',
                      avg: p.avg_risk_score,
                      high: p.high_risk_volume,
                    }))}
                    margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                    <YAxis yAxisId="l" tick={{ fontSize: 10 }} domain={[0, 100]} width={32} />
                    <YAxis yAxisId="r" orientation="right" tick={{ fontSize: 10 }} width={36} />
                    <Tooltip />
                    <Line
                      yAxisId="l"
                      type="monotone"
                      dataKey="avg"
                      stroke="#2E6F74"
                      strokeWidth={2}
                      dot={false}
                      name={t('app.dashboard.risk_intel.avg_score')}
                    />
                    <Line
                      yAxisId="r"
                      type="monotone"
                      dataKey="high"
                      stroke="#c2410c"
                      strokeWidth={2}
                      dot={false}
                      name={t('app.dashboard.risk_intel.high_plus')}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : !riskIntelLoading && riskTrends ? (
            <div className="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-3 text-xs text-slate-500">
              {t('app.dashboard.risk_intel.trend_empty')}
            </div>
          ) : null}

          {!riskIntelLoading && riskDigestQueue ? (
            <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
                  <div className="text-xs font-semibold text-slate-800">
                    {t('app.dashboard.risk_intel.digest_queue_title')}
                  </div>
                  <label className="flex items-center gap-1 text-[11px] text-slate-700">
                    <span className="shrink-0 capitalize">{t('app.dashboard.risk_intel.digest_queue_min_band')}</span>
                    <select
                      className="rounded border border-slate-300 bg-white px-1.5 py-0.5 text-[11px] capitalize"
                      value={riskDigestMinBand}
                      onChange={(e) => {
                        const v = e.target.value
                        if (v === 'low' || v === 'medium' || v === 'high' || v === 'critical') {
                          setRiskDigestMinBand(v)
                        }
                      }}
                    >
                      {(['low', 'medium', 'high', 'critical'] as const).map((b) => (
                        <option key={b} value={b}>
                          {b}+
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex items-center gap-1 text-[11px] text-slate-700">
                    <span className="shrink-0">{t('app.dashboard.risk_intel.digest_queue_filter')}</span>
                    <select
                      className="rounded border border-slate-300 bg-white px-1.5 py-0.5 text-[11px]"
                      value={riskDigestQueueReadFilter}
                      onChange={(e) => {
                        const v = e.target.value
                        if (v === 'all' || v === 'unread' || v === 'read') setRiskDigestQueueReadFilter(v)
                      }}
                    >
                      <option value="all">{t('app.dashboard.risk_intel.digest_queue_filter_all')}</option>
                      <option value="unread">{t('app.dashboard.risk_intel.digest_queue_filter_unread')}</option>
                      <option value="read">{t('app.dashboard.risk_intel.digest_queue_filter_read')}</option>
                    </select>
                  </label>
                  {riskDigestQueue.unread_count > 0 ? (
                    <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold text-rose-800">
                      {t('app.dashboard.risk_intel.digest_queue_unread', { values: { n: riskDigestQueue.unread_count } })}
                    </span>
                  ) : null}
                </div>
                <div className="flex shrink-0 flex-wrap gap-1.5">
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={!riskDigestQueue.buckets[0]?.bucket_start || digestAckLoading}
                    onClick={() => void onManagerDigestAckLatest()}
                  >
                    {digestAckLoading
                      ? t('common.loading')
                      : t('app.dashboard.risk_intel.digest_queue_ack_latest')}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={!riskShadowSnapshot?.bucket_start || digestAckLoading}
                    onClick={() => void onManagerDigestAck()}
                  >
                    {digestAckLoading
                      ? t('common.loading')
                      : t('app.dashboard.risk_intel.digest_queue_ack')}
                  </button>
                </div>
              </div>
              <div className="mt-2 text-[11px] text-slate-600">
                {t('app.dashboard.risk_intel.digest_queue_hint')}
              </div>
              {riskDigestQueue.buckets.length === 0 ? (
                <div className="mt-2 text-xs text-slate-500">
                  {t('app.dashboard.risk_intel.digest_queue_empty')}
                </div>
              ) : filteredDigestBuckets.length === 0 ? (
                <div className="mt-2 text-xs text-slate-500">
                  {t('app.dashboard.risk_intel.digest_queue_filter_empty')}
                </div>
              ) : (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {filteredDigestBuckets.map((b) => {
                    const isLatestRow = Boolean(latestDigestBucketStart && b.bucket_start === latestDigestBucketStart)
                    const selected =
                      riskShadowBucketStart === null ? isLatestRow : riskShadowBucketStart === b.bucket_start
                    const shortWhen = new Date(b.bucket_start).toLocaleString(locale, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                    const label = isLatestRow
                      ? `${t('app.dashboard.risk_intel.digest_queue_latest')} · ${shortWhen}`
                      : shortWhen
                    return (
                      <button
                        key={b.bucket_start}
                        type="button"
                        onClick={() => setRiskShadowBucketStart(isLatestRow ? null : b.bucket_start)}
                        className={`rounded-lg border px-2 py-1 text-left text-[11px] transition-colors ${
                          selected
                            ? 'border-indigo-400 bg-white font-semibold text-indigo-900 shadow-sm'
                            : 'border-slate-200 bg-white/80 text-slate-700 hover:border-slate-300'
                        }`}
                      >
                        <span>{label}</span>
                        <span className="ml-1 text-slate-500">
                          ({b.total_matching}){b.unread ? ' · ●' : ''}
                        </span>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          ) : null}

          {riskShadowSnapshot || riskIntelShadowLoading ? (
            <div
              className={`mt-4 rounded-xl border border-slate-200 bg-white p-3 transition-opacity ${riskIntelShadowLoading ? 'opacity-60' : ''}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="text-xs font-semibold text-slate-700">
                  {t('app.dashboard.risk_intel.shadow_snapshot_title')}
                </div>
                {riskShadowSnapshot?.bucket_start && riskShadowSnapshot.total_matching > 0 ? (
                  <Link
                    to={makeCandidatesHref({
                      shadow_bucket: riskShadowSnapshot.bucket_start,
                      shadow_min_band: ['low', 'medium', 'high', 'critical'].includes(String(riskShadowSnapshot.min_band || ''))
                        ? String(riskShadowSnapshot.min_band)
                        : 'high',
                    })}
                    className="shrink-0 text-[11px] font-medium text-brand-700 hover:underline"
                  >
                    {t('app.dashboard.risk_intel.open_cohort_in_list')}
                  </Link>
                ) : null}
              </div>
              {!riskShadowSnapshot ? (
                <div className="mt-2 text-sm text-slate-500">
                  {t('common.loading')}
                </div>
              ) : (
                <>
                  <div className="mt-1 text-[11px] text-slate-500">
                    {riskShadowSnapshot.bucket_start
                      ? t('app.dashboard.risk_intel.shadow_snapshot_bucket', {
                          values: {
                            bucket: new Date(riskShadowSnapshot.bucket_start).toLocaleString(locale),
                            min_band: riskShadowSnapshot.min_band,
                            total: riskShadowSnapshot.total_matching,
                            shown: riskShadowSnapshot.items.length,
                          },
                        })
                      : t('app.dashboard.risk_intel.shadow_snapshot_empty_hint')}
                    {riskShadowSnapshot.note ? ` ${riskShadowSnapshot.note}` : ''}
                  </div>
                  {riskShadowSnapshot.items.length > 0 ? (
                    <>
                      <div className="mt-1 text-[10px] text-slate-500">
                        {t('app.dashboard.risk_intel.shadow_handoff_hint')}
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-slate-50/90 px-2 py-1.5 text-[11px] text-slate-700">
                        <span className="font-medium text-slate-600">
                          {t('app.dashboard.risk_intel.shadow_bulk_selected', { values: { n: digestBulkSelected.size } })}
                        </span>
                        <label className="flex items-center gap-1">
                          <span className="shrink-0 text-slate-500">
                            {t('app.dashboard.risk_intel.shadow_bulk_assignee')}
                          </span>
                          <select
                            className="max-w-[10rem] truncate rounded border border-slate-200 bg-white px-1 py-0.5 text-[10px]"
                            disabled={digestBulkBusy || digestHandoffBusyId !== null}
                            value={digestBulkReminderAssignee}
                            onChange={(e) => setDigestBulkReminderAssignee(e.target.value.trim())}
                          >
                            <option value="">
                              {t('app.dashboard.risk_intel.shadow_handoff_assignee_auto')}
                            </option>
                            {managerOptions.map((opt) => (
                              <option key={opt.id} value={opt.id}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        </label>
                        <button
                          type="button"
                          className="rounded border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium hover:bg-slate-50 disabled:opacity-50"
                          disabled={digestBulkSelected.size === 0 || digestBulkBusy || digestHandoffBusyId !== null}
                          onClick={() => void onShadowDigestBulkRemind()}
                        >
                          {digestBulkBusy
                            ? t('common.loading')
                            : t('app.dashboard.risk_intel.shadow_bulk_remind')}
                        </button>
                        <button
                          type="button"
                          className="rounded border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[10px] font-medium text-indigo-900 hover:bg-indigo-100 disabled:opacity-50"
                          disabled={digestBulkSelected.size === 0 || digestBulkBusy || digestHandoffBusyId !== null}
                          onClick={() => void onShadowDigestBulkClaim()}
                        >
                          {digestBulkBusy
                            ? t('common.loading')
                            : t('app.dashboard.risk_intel.shadow_bulk_claim')}
                        </button>
                      </div>
                      {digestBulkResultReport ? (
                        <div
                          className={`mt-2 rounded-lg border px-2 py-1.5 text-[11px] ${
                            digestBulkResultReport.fail === 0 ?
                              'border-emerald-200 bg-emerald-50/90 text-emerald-950'
                            : 'border-amber-200 bg-amber-50/90 text-amber-950'
                          }`}
                        >
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                              <div className="font-semibold">
                                {digestBulkResultReport.kind === 'remind' ?
                                  t('app.dashboard.risk_intel.shadow_bulk_result_remind', {
                                    values: {
                                      ok: digestBulkResultReport.ok,
                                      fail: digestBulkResultReport.fail,
                                    },
                                  })
                                : t('app.dashboard.risk_intel.shadow_bulk_result_claim', {
                                    values: {
                                      ok: digestBulkResultReport.ok,
                                      fail: digestBulkResultReport.fail,
                                    },
                                  })}
                              </div>
                              {digestBulkResultReport.errors.length > 0 ? (
                                <ul className="mt-1 list-inside list-disc break-words text-[10px] text-slate-800">
                                  {digestBulkResultReport.errors.map((err, i) => (
                                    <li key={i}>{err}</li>
                                  ))}
                                </ul>
                              ) : null}
                              {digestBulkResultReport.fail > 0 ? (
                                <div className="mt-1 text-[10px] text-slate-700">
                                  {t('app.dashboard.risk_intel.shadow_bulk_result_keep_selection')}
                                </div>
                              ) : null}
                            </div>
                            <button
                              type="button"
                              className="shrink-0 rounded border border-slate-300/80 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-700 hover:bg-slate-50"
                              onClick={() => setDigestBulkResultReport(null)}
                            >
                              {t('app.dashboard.risk_intel.shadow_bulk_dismiss')}
                            </button>
                          </div>
                        </div>
                      ) : null}
                      <div className="mt-2 max-h-56 overflow-auto rounded-lg border border-slate-100">
                        <table className="w-full text-left text-[11px]">
                          <thead className="sticky top-0 bg-slate-50 text-slate-600">
                            <tr>
                              <th className="w-8 px-1 py-1.5">
                                <input
                                  ref={digestBulkHeadRef}
                                  type="checkbox"
                                  className="h-3.5 w-3.5 rounded border-slate-300"
                                  checked={
                                    digestBulkRowIds.length > 0 &&
                                    digestBulkRowIds.every((id) => digestBulkSelected.has(id))
                                  }
                                  disabled={
                                    digestBulkRowIds.length === 0 ||
                                    digestBulkBusy ||
                                    digestHandoffBusyId !== null
                                  }
                                  onChange={() => toggleDigestBulkAll()}
                                  title={t('app.dashboard.risk_intel.shadow_bulk_select_all')}
                                />
                              </th>
                              <th className="px-2 py-1.5 font-medium">{t('app.dashboard.risk_intel.col_candidate')}</th>
                              <th className="px-2 py-1.5 font-medium">{t('app.dashboard.risk_intel.col_band')}</th>
                              <th className="px-2 py-1.5 font-medium">{t('app.dashboard.risk_intel.col_score')}</th>
                              <th className="px-2 py-1.5 font-medium">{t('app.dashboard.risk_intel.col_stage')}</th>
                              <th className="px-2 py-1.5 font-medium">{t('app.dashboard.risk_intel.col_handoff')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {riskShadowSnapshot.items.map((row) => {
                              const label =
                                row.display_name?.trim() ||
                                (row.short_id ? `#${row.short_id}` : row.entity_id.slice(0, 8))
                              const ownerId = row.recruiter_id?.trim() || ''
                              const showClaim = !ownerId || ownerId !== myUserId
                              const rowBusy = digestHandoffBusyId === row.entity_id
                              const rowDisabled = digestBulkBusy || digestHandoffBusyId !== null
                              return (
                                <tr key={row.entity_id} className="border-t border-slate-100">
                                  <td className="px-1 py-1 align-top">
                                    <input
                                      type="checkbox"
                                      className="mt-0.5 h-3.5 w-3.5 rounded border-slate-300"
                                      checked={digestBulkSelected.has(row.entity_id)}
                                      disabled={rowDisabled}
                                      onChange={() => toggleDigestBulkRow(row.entity_id)}
                                    />
                                  </td>
                                  <td className="px-2 py-1">
                                    <Link
                                      className="font-medium text-brand-700 hover:underline"
                                      to={`${CRM_APP_PATHS.candidates}/${row.entity_id}`}
                                    >
                                      {label}
                                    </Link>
                                  </td>
                                  <td className="px-2 py-1 capitalize">{row.band}</td>
                                  <td className="px-2 py-1 font-mono">{Math.round(row.score)}</td>
                                  <td className="px-2 py-1 text-slate-600">{row.stage_at_score || '—'}</td>
                                  <td className="px-2 py-1">
                                    <div className="flex min-w-[9.5rem] flex-col gap-1">
                                      <select
                                        className="max-w-[12rem] truncate rounded border border-slate-200 bg-white px-1 py-0.5 text-[10px] text-slate-800 disabled:opacity-50"
                                        disabled={rowDisabled}
                                        title={t('app.dashboard.risk_intel.shadow_handoff_assignee_title')}
                                        value={digestReminderAssigneePick[row.entity_id] ?? ''}
                                        onChange={(e) => {
                                          const v = e.target.value.trim()
                                          setDigestReminderAssigneePick((p) => {
                                            const next = { ...p }
                                            if (!v) delete next[row.entity_id]
                                            else next[row.entity_id] = v
                                            return next
                                          })
                                        }}
                                      >
                                        <option value="">
                                          {t('app.dashboard.risk_intel.shadow_handoff_assignee_auto')}
                                        </option>
                                        {managerOptions.map((opt) => (
                                          <option key={opt.id} value={opt.id}>
                                            {opt.label}
                                          </option>
                                        ))}
                                      </select>
                                      <div className="flex flex-wrap gap-1">
                                      <button
                                        type="button"
                                        className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                                        disabled={rowDisabled}
                                        onClick={() =>
                                          void onShadowDigestReminder(row, digestReminderAssigneePick[row.entity_id])
                                        }
                                      >
                                        {rowBusy
                                          ? t('common.loading')
                                          : t('app.dashboard.risk_intel.shadow_handoff_remind')}
                                      </button>
                                      {showClaim ? (
                                        <button
                                          type="button"
                                          className="rounded border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-900 hover:bg-indigo-100 disabled:opacity-50"
                                          disabled={rowDisabled}
                                          onClick={() => void onShadowDigestClaim(row)}
                                        >
                                          {rowBusy
                                            ? t('common.loading')
                                            : t('app.dashboard.risk_intel.shadow_handoff_claim')}
                                        </button>
                                      ) : null}
                                      </div>
                                    </div>
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </>
                  ) : null}
                </>
              )}
            </div>
          ) : null}

          {riskValidation ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs font-semibold text-slate-700">
                {t('app.dashboard.risk_intel.validation_title')}
              </div>
              <div className="mt-2 space-y-1 text-sm text-slate-700">
                <div>
                  {t('app.dashboard.risk_intel.validation_samples')}:{' '}
                  <span className="font-semibold">{riskValidation.samples}</span>
                  {riskValidation.forward_stage_progression_rate != null ? (
                    <>
                      {' '}
                      · {t('app.dashboard.risk_intel.validation_rate')}:{' '}
                      <span className="font-semibold">{riskValidation.forward_stage_progression_rate}%</span>
                    </>
                  ) : null}
                </div>
                {riskValidation.note ? <div className="text-xs text-slate-500">{riskValidation.note}</div> : null}
                {riskValidation.interpretation ? (
                  <div className="text-xs text-slate-500">{riskValidation.interpretation}</div>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
        ) : null}

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">
                {t('app.dashboard.stage_metrics.title')}
              </div>
              <div className="mt-0.5 text-xs text-slate-500">
                {t('app.dashboard.stage_metrics.subtitle')}
              </div>
            </div>
            <button type="button" className="btn-secondary btn-sm" onClick={() => void loadStageMetrics()} disabled={stageMetricsLoading}>
              {stageMetricsLoading ? t('common.loading') : t('common.actions.refresh')}
            </button>
          </div>

          {!stageMetrics ? (
            <div className="mt-3 text-sm text-slate-500">{t('app.dashboard.stage_metrics.empty')}</div>
          ) : (
            <div className="mt-3 grid gap-3 lg:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-semibold text-slate-700">{t('app.dashboard.stage_metrics.readiness')}</div>
                <div className="mt-2 space-y-1 text-sm">
                  {Object.entries(stageMetrics.readiness || {})
                    .sort((a, b) => (b[1] || 0) - (a[1] || 0))
                    .slice(0, 8)
                    .map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-slate-600">
                          {(() => {
                            const readinessLabel = t(`admin.documents.readiness_labels.${k}`, { defaultValue: '' }).trim()
                            if (readinessLabel) return readinessLabel
                            const stageLabel = translateStageLabel(k, k)
                            return stageLabel || k
                          })()}
                        </span>
                        <span className="font-semibold text-slate-900">{String(v)}</span>
                      </div>
                    ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-semibold text-slate-700">{t('app.dashboard.stage_metrics.stage_time')}</div>
                <div className="mt-2 space-y-1 text-sm">
                  {(stageMetrics.stage_time || []).slice(0, 8).map((s) => (
                    <div key={s.stage} className="flex items-center justify-between gap-2">
                      <span className="truncate text-slate-600" title={translateStageLabel(s.stage, s.stage) || s.stage}>
                        {translateStageLabel(s.stage, s.stage) || s.stage}
                      </span>
                      <span className="shrink-0 font-semibold text-slate-900">{s.avg_days}d</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-semibold text-slate-700">{t('app.dashboard.stage_metrics.transitions')}</div>
                <div className="mt-2 space-y-1 text-sm">
                  {(stageMetrics.transitions || []).slice(0, 10).map((tr, idx) => {
                    const fromLabel = translateStageLabel(tr.from_stage, tr.from_stage) || startStageLabel
                    const toLabel = translateStageLabel(tr.to_stage, tr.to_stage) || notAvailableLabel
                    return (
                    <div key={`${tr.from_stage || 'none'}-${tr.to_stage}-${idx}`} className="flex items-center justify-between gap-2">
                      <span
                        className="truncate text-slate-600"
                        title={`${fromLabel} → ${toLabel}`}
                      >
                        {`${fromLabel} → ${toLabel}`}
                      </span>
                      <span className="shrink-0 font-semibold text-slate-900">{tr.count}</span>
                    </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900">
                {t('app.dashboard.perf.title')}
              </div>
              <div className="mt-0.5 text-xs text-slate-500">
                {t('app.dashboard.perf.subtitle')}
              </div>
            </div>
            <button type="button" className="btn-secondary btn-sm" onClick={() => void loadPerfBaseline()} disabled={perfBaselineLoading}>
              {perfBaselineLoading ? t('common.loading') : t('common.actions.refresh')}
            </button>
          </div>

          {!perfBaseline || (perfBaseline.rows || []).length === 0 ? (
            <div className="mt-3 text-sm text-slate-500">{t('app.dashboard.perf.empty')}</div>
          ) : (
            <div className="mt-3 overflow-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500">
                    <th className="py-2 pr-3 font-medium">{t('app.dashboard.perf.metric')}</th>
                    <th className="py-2 pr-3 font-medium">{t('app.dashboard.perf.samples')}</th>
                    <th className="py-2 pr-3 font-medium">{t('app.dashboard.perf.p50')}</th>
                    <th className="py-2 pr-3 font-medium">{t('app.dashboard.perf.p95')}</th>
                    <th className="py-2 pr-3 font-medium">{t('app.dashboard.perf.budget')}</th>
                    <th className="py-2 pr-3 font-medium">{t('app.dashboard.perf.range')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(perfBaseline.rows || []).map((r) => {
                    const budget = perfBudgets?.budgets_p95_ms?.[r.metric_key]
                    const breached = budget != null && Number.isFinite(budget) && r.p95_ms > Number(budget)
                    return (
                    <tr key={r.metric_key} className="border-t border-slate-100">
                      <td className="py-2 pr-3 font-mono text-xs text-slate-700">{r.metric_key}</td>
                      <td className="py-2 pr-3 text-slate-700">{r.samples}</td>
                      <td className="py-2 pr-3 font-semibold text-slate-900">{r.p50_ms}</td>
                      <td className={breached ? "py-2 pr-3 font-semibold text-rose-700" : "py-2 pr-3 font-semibold text-slate-900"}>{r.p95_ms}</td>
                      <td className="py-2 pr-3 text-slate-700">{budget != null ? String(budget) : '—'}</td>
                      <td className="py-2 pr-3 text-slate-700">
                        {r.min_ms}–{r.max_ms}
                      </td>
                    </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
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
        {isTrialTenant && (
          <div className={trialCenterClasses.wrapper}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className={trialCenterClasses.badge}>
                  {t('app.dashboard.trial_center.badge')}
                </p>
                <h2 className={trialCenterClasses.title}>
                  {trialDaysLeft != null
                    ? t('app.dashboard.trial_center.title_with_days', { values: { days: trialDaysLeft } })
                    : t('app.dashboard.trial_center.title')}
                </h2>
                <p className={trialCenterClasses.subtitle}>
                  {t('app.dashboard.trial_center.subtitle')}
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
            {canManageBilling && (
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
            {isFilterVisible('candidate') && (
              <label className="flex flex-col text-xs gap-0.5">
                <span className="text-slate-500">{t('app.dashboard.filters.candidate')}</span>
                <input
                  type="text"
                  className="input input-sm w-44 font-mono"
                  value={candidateFilter}
                  onChange={(e) => setCandidateFilter(e.target.value)}
                  onBlur={(e) => handleCandidateFilterApply(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleCandidateFilterApply((e.target as HTMLInputElement).value)
                      ;(e.target as HTMLInputElement).blur()
                    }
                  }}
                  placeholder={t('app.dashboard.filters.candidate_placeholder')}
                  autoComplete="off"
                />
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
                {(['period', 'dateRange', 'dateField', 'vacancy', 'company', 'manager', 'candidate', 'stages', 'compare', 'presets', 'widgets'] as DashboardFilterId[]).map((fid) => (
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
            defaultOpen
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

        {isWidgetVisible('pivot') && (
        <div className="border-t border-slate-100 pt-4 mt-2 sm:border-0 sm:pt-0">
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
                    const href = params ? `${CRM_APP_PATHS.candidates}?${params}` : null
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

        {isWidgetVisible('pivotChart') && pivotData.rows.length > 0 && (
        <div className="card min-w-0 p-4 space-y-3">
          <div>
            <div className="text-sm font-semibold">{t('app.dashboard.pivot.chart_title')}</div>
            <div className="text-xs text-slate-500">
              {primaryLabel}
              {pivotSecondary !== 'none' && ` × ${secondaryLabel}`}
            </div>
          </div>
          <div ref={pivotChartContainerRef} className="h-64 w-full min-w-0 shrink-0 overflow-hidden">
            {isPivotChartContainerReady ? (
              <ResponsiveContainer width="100%" height={256} minHeight={200} minWidth={0}>
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
            ) : (
              <div className="flex h-64 items-center justify-center text-xs text-slate-500">
                {t('common.loading')}
              </div>
            )}
          </div>
        </div>
        )}

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
      </div>
    </section>
  )
}
