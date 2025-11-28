// src/pages/Dashboard.tsx
import { useCallback, useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import { useI18n } from '../i18n'

type ListResp<T> = { items: T[]; total?: number } | T[]

type NamedCount = { key: string; label: string; count: number }
type StageBreakdownItem = NamedCount & { by_stage?: Record<string, number> }

type CandidateSnapshot = {
  id: string
  stage: string | null
  stage_label: string | null
  company: string | null
  vacancy: string | null
  source: string | null
  citizenship: string | null
  country: string | null
  manager?: string | null
  manager_name?: string | null
  manager_short?: string | null
  status_reason_codes?: string[]
  status_reason_labels?: string[]
  reason_stage?: string | null
  reason_stage_label?: string | null
  created_at?: string | null
  updated_at?: string | null
}

type CandidateSlicesResponse = {
  period: { from: string | null; to: string | null }
  by: 'created' | 'updated'
  total: number
  stages: NamedCount[]
  companies: StageBreakdownItem[]
  vacancies: StageBreakdownItem[]
  sources: NamedCount[]
  citizenships: NamedCount[]
  countries: NamedCount[]
  reasons: {
    rejected: NamedCount[]
    declined: NamedCount[]
  }
  snapshot: CandidateSnapshot[]
}

type PivotDimension = 'stage' | 'company' | 'vacancy' | 'source' | 'citizenship' | 'country' | 'reason'
type QuickRange = '7d' | '30d' | '90d' | 'ytd' | 'all'
type LoadOverrides = {
  from?: string
  to?: string
  field?: 'created' | 'updated'
  vacancyId?: string | null
}

const DAY_MS = 24 * 60 * 60 * 1000

const QUICK_RANGE_OPTIONS: QuickRange[] = ['7d', '30d', '90d', 'ytd', 'all']

const DIMENSION_OPTIONS: PivotDimension[] = ['stage', 'company', 'vacancy', 'source', 'citizenship', 'country', 'reason']

const formatDateInput = (date: Date) => date.toISOString().slice(0, 10)

const calcRange = (range: QuickRange): { from: string; to: string } => {
  const today = new Date()
  const to = formatDateInput(today)
  if (range === 'all') return { from: '', to: '' }
  if (range === 'ytd') {
    const start = new Date(today.getFullYear(), 0, 1)
    return { from: formatDateInput(start), to }
  }
  const days = range === '7d' ? 7 : range === '30d' ? 30 : 90
  const from = new Date(today.getTime() - days * DAY_MS)
  return { from: formatDateInput(from), to }
}

type StageLabelConfig = {
  hired: string[]
  rejected: string[]
  declined: string[]
}

const DEFAULT_STAGE_LABELS: StageLabelConfig = {
  hired: [],
  rejected: [],
  declined: [],
}

const normalizeKey = (value?: string | null) => {
  if (!value) return ''
  const normalized = value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
  return normalized
    .replace(/[^a-z0-9\u0400-\u04ff]+/g, '_')
    .replace(/^_+|_+$/g, '')
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

const normalizeTotal = (payload: any): number => {
  if (!payload) return 0
  if (Array.isArray(payload)) return payload.length
  if (typeof payload === 'object') {
    if (typeof payload.total === 'number') return payload.total
    if (Array.isArray(payload.items)) return payload.items.length
  }
  return 0
}

export default function Dashboard() {
  const { t, locale } = useI18n()
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

  const [pivotPrimary, setPivotPrimary] = useState<PivotDimension>('company')
  const [pivotSecondary, setPivotSecondary] = useState<PivotDimension | 'none'>('stage')
  const [vacancyFilter, setVacancyFilter] = useState<string>('')
  const [vacancyOptions, setVacancyOptions] = useState<{ id: string; label: string }[]>([])

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
        const translationKey = `app.dashboard.stage_labels.${finalKey}`
        const translated = t(translationKey)
        if (translated !== translationKey) {
          return translated
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
    const vacancyId = overrides?.vacancyId ?? vacancyFilter

    if (from && to && from > to) {
      setErrText(t('app.dashboard.errors.range_invalid'))
      return
    }

    setLoading(true)
    setErrText(null)
    try {
      const params: Record<string, any> = { limit: 40, by: field }
      if (from) params.from = from
      if (to) params.to = to
      if (vacancyId) params.vacancy_id = vacancyId

      const [cand, comps, vacs, sliceResp] = await Promise.all([
        api.get<ListResp<any>>('/candidates', { params: { limit: 1, offset: 0 } }),
        api.get<ListResp<any>>('/companies/', { params: { limit: 50, offset: 0 } }),
        api.get<ListResp<any>>('/vacancies/', { params: { limit: 50, offset: 0 } }),
        api.get<CandidateSlicesResponse>('/analytics/candidate-slices', { params }),
      ])

      setGlobalCounts({
        candidates: normalizeTotal(cand.data),
        companies: normalizeTotal(comps.data),
        vacancies: normalizeTotal(vacs.data),
      })
      setSlices(sliceResp.data)
      setPeriodTotal(sliceResp.data?.total ?? 0)
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
      console.error('Dashboard load error:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
    load({ vacancyId: value || null })
  }

  const selectedVacancyLabel = useMemo(() => {
    if (!vacancyFilter) return ''
    const match = vacancyOptions.find((option) => option.id === vacancyFilter)
    return match?.label ?? notAvailableLabel
  }, [vacancyFilter, vacancyOptions, notAvailableLabel])

  const pivotData = useMemo(() => {
    if (!slices?.snapshot?.length) return { rows: [] as { key: string; total: number; breakdown: Record<string, number> }[], secondaryKeys: [] as string[] }

    const totals = new Map<string, { total: number; breakdown: Map<string, number> }>()
    const secondaryTotals = new Map<string, number>()
    const pivotSecondaryDimension = pivotSecondary === 'none' ? null : pivotSecondary
    const secondaryEnabled = Boolean(pivotSecondaryDimension)

    for (const row of slices.snapshot) {
      const primaryValues = getDimensionValues(row, pivotPrimary)
      const normalizedPrimary = primaryValues.length ? primaryValues : [notAvailableLabel]

      const secondaryValues = secondaryEnabled && pivotSecondaryDimension
        ? getDimensionValues(row, pivotSecondaryDimension as PivotDimension)
        : []
      const normalizedSecondary = secondaryEnabled
        ? (secondaryValues.length ? secondaryValues : [notAvailableLabel])
        : []

      for (const primary of normalizedPrimary) {
        const key = primary || notAvailableLabel
        const entry = totals.get(key) ?? { total: 0, breakdown: new Map<string, number>() }
        if (secondaryEnabled) {
          for (const secondary of normalizedSecondary) {
            const secKey = secondary || notAvailableLabel
            entry.breakdown.set(secKey, (entry.breakdown.get(secKey) ?? 0) + 1)
            secondaryTotals.set(secKey, (secondaryTotals.get(secKey) ?? 0) + 1)
          }
          entry.total += normalizedSecondary.length || 1
        } else {
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
      }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 30)

    return { rows, secondaryKeys }
  }, [getDimensionValues, pivotPrimary, pivotSecondary, slices?.snapshot])

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
      .map((item) => ({
        label: item.label || item.key || notAvailableLabel,
        count: item.count,
        intensity: Math.min(item.count / max, 1),
      }))
      .slice(0, 12)
  }, [slices?.countries, notAvailableLabel])

  const rangeInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo)
  const primaryLabel = dimensionOptions.find((opt) => opt.value === pivotPrimary)?.label ?? ''
  const secondaryLabel =
    pivotSecondary === 'none'
      ? t('app.dashboard.labels.no_subgroup')
      : dimensionOptions.find((opt) => opt.value === pivotSecondary)?.label ?? ''
  const heroTotal = slices?.total ?? 0
  const heroVacancies = slices?.vacancies?.length ?? 0
  const heroStages = slices?.stages?.length ?? 0
  const heroTopManager = managerLoadRows[0]
  const heroTopCountry = countryHeatmapRows[0]
  const managerWidgetRows = managerLoadRows.slice(0, 4)
  const countryWidgetRows = countryHeatmapRows.slice(0, 4)
  const topCompanyCards = useMemo(() => {
    if (!slices?.companies?.length) return []
    return slices.companies.slice(0, 3).map((item) => {
      const highlight = stageHighlights(item.by_stage, stageLabels)
      return {
        label: item.label,
        total: item.count,
        pipeline: highlight.pipeline,
        hired: highlight.hired,
      }
    })
  }, [slices?.companies, stageLabels])

  const topVacancyCards = useMemo(() => {
    if (!slices?.vacancies?.length) return []
    return slices.vacancies.slice(0, 3).map((item) => {
      const highlight = stageHighlights(item.by_stage, stageLabels)
      return {
        label: item.label,
        total: item.count,
        pipeline: highlight.pipeline,
        hired: highlight.hired,
      }
    })
  }, [slices?.vacancies, stageLabels])

  const stageStackSegments = useMemo(() => {
    if (!slices?.stages?.length) return []
    const total = slices.stages.reduce((acc, stage) => acc + (stage.count ?? 0), 0)
    if (!total) return []
    return slices.stages.map((stage) => {
      const canonical = canonicalStageKey(stage.key, stage.label)
      const outcome = determineStageOutcome(canonical, stageLabels)
      const label = translateStageLabel(stage.key, stage.label) || stage.label
      const value = stage.count ?? 0
      const percent = total ? Math.round((value / total) * 1000) / 10 : 0
      return { label, value, percent, outcome }
    })
  }, [slices?.stages, stageLabels])

  return (
    <section className="h-full min-h-0 w-full flex flex-col">
      <div className="flex-1 min-h-0 overflow-auto px-6 py-4 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-xl font-semibold">{t('app.dashboard.title')}</h1>
          <div className="flex items-center gap-2">
            <button className="btn-ghost" onClick={() => load()} disabled={loading || rangeInvalid}>
              {loading ? t('app.dashboard.refresh.loading') : t('app.dashboard.refresh.action')}
            </button>
          </div>
        </div>

        <div className="rounded-3xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-6 text-white shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="max-w-2xl text-sm text-white/80">{t('app.dashboard.hero.subtitle')}</p>
          </div>
          <div className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
            <div className="rounded-2xl border border-white/30 bg-white/10 p-4">
              <p className="text-xs uppercase tracking-wide text-white/80">{t('app.dashboard.hero.stats.total')}</p>
              <p className="text-2xl font-semibold">{heroTotal.toLocaleString()}</p>
            </div>
            <div className="rounded-2xl border border-white/30 bg-white/10 p-4">
              <p className="text-xs uppercase tracking-wide text-white/80">{t('app.dashboard.hero.stats.vacancies')}</p>
              <p className="text-2xl font-semibold">{heroVacancies}</p>
            </div>
            <div className="rounded-2xl border border-white/30 bg-white/10 p-4">
              <p className="text-xs uppercase tracking-wide text-white/80">{t('app.dashboard.hero.stats.stages')}</p>
              <p className="text-2xl font-semibold">{heroStages}</p>
            </div>
          </div>
          {(heroTopManager || heroTopCountry) && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {heroTopManager && (
                <div className="rounded-2xl border border-white/30 bg-white/10 p-4 text-sm">
                  <div className="text-xs uppercase tracking-wide text-white/80">
                    {t('app.dashboard.manager_load.title')}
                  </div>
                  <div className="mt-1 text-lg font-semibold text-white">{heroTopManager.label}</div>
                  <div className="text-xs text-white/80">
                    {t('app.dashboard.manager_load.pipeline')}: {formatNumber(heroTopManager.pipeline)} ·{' '}
                    {t('app.dashboard.manager_load.total')}: {formatNumber(heroTopManager.total)}
                  </div>
                </div>
              )}
              {heroTopCountry && (
                <div className="rounded-2xl border border-white/30 bg-white/10 p-4 text-sm">
                  <div className="text-xs uppercase tracking-wide text-white/80">
                    {t('app.dashboard.country_heatmap.title')}
                  </div>
                  <div className="mt-1 text-lg font-semibold text-white">{heroTopCountry.label}</div>
                  <div className="text-xs text-white/80">
                    {t('app.dashboard.country_heatmap.count_label', {
                      values: { count: formatNumber(heroTopCountry.count) },
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {(managerWidgetRows.length || countryWidgetRows.length) && (
          <div className="grid gap-4 lg:grid-cols-3">
            {managerWidgetRows.length > 0 && (
              <div className="card p-4">
                <div className="text-sm font-semibold text-gray-800">{t('app.dashboard.manager_load.title')}</div>
                <div className="text-xs text-gray-500">{t('app.dashboard.manager_load.subtitle')}</div>
                <ul className="mt-3 space-y-2 text-sm text-gray-700">
                  {managerWidgetRows.map((row) => (
                    <li key={row.managerLabel} className="flex items-center justify-between">
                      <span className="font-medium">{row.managerLabel}</span>
                      <span className="text-xs text-gray-500">
                        {t('app.dashboard.manager_load.pipeline')}: {formatNumber(row.pipeline)} ·{' '}
                        {t('app.dashboard.manager_load.total')}: {formatNumber(row.total)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {countryWidgetRows.length > 0 && (
              <div className="card p-4">
                <div className="text-sm font-semibold text-gray-800">{t('app.dashboard.country_heatmap.title')}</div>
                <div className="text-xs text-gray-500">{t('app.dashboard.country_heatmap.subtitle')}</div>
                <ul className="mt-3 space-y-2 text-sm text-gray-700">
                  {countryWidgetRows.map((row) => (
                    <li key={row.label} className="flex items-center justify-between">
                      <span>{row.label}</span>
                      <span className="text-xs text-gray-500">
                        {t('app.dashboard.country_heatmap.count_label', { values: { count: formatNumber(row.count) } })}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {(topCompanyCards.length || topVacancyCards.length || docStageStats.total) && (
          <div className="grid gap-4 xl:grid-cols-3">
            <div className="card p-4">
              <div className="text-sm font-semibold text-gray-800">{t('app.dashboard.top_cards.companies.title')}</div>
              <div className="text-xs text-gray-500">{t('app.dashboard.top_cards.companies.subtitle')}</div>
              {topCompanyCards.length ? (
                <ul className="mt-3 space-y-2 text-sm text-gray-700">
                  {topCompanyCards.map((item) => (
                    <li key={`top-company-${item.label}`} className="rounded-xl border border-gray-100 bg-white/80 p-3">
                      <p className="font-semibold text-gray-900">{item.label}</p>
                      <p className="text-xs text-gray-500">
                        {t('app.dashboard.top_cards.total', { values: { count: formatNumber(item.total) } })}
                      </p>
                      <p className="text-xs text-gray-500">
                        {t('app.dashboard.manager_load.pipeline')}: {formatNumber(item.pipeline)} ·{' '}
                        {t('app.dashboard.top_cards.hired')}: {formatNumber(item.hired)}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="mt-3 text-sm text-gray-500">{t('app.dashboard.top_cards.empty')}</div>
              )}
            </div>
            <div className="card p-4">
              <div className="text-sm font-semibold text-gray-800">{t('app.dashboard.top_cards.vacancies.title')}</div>
              <div className="text-xs text-gray-500">{t('app.dashboard.top_cards.vacancies.subtitle')}</div>
              {topVacancyCards.length ? (
                <ul className="mt-3 space-y-2 text-sm text-gray-700">
                  {topVacancyCards.map((item) => (
                    <li key={`top-vacancy-${item.label}`} className="rounded-xl border border-gray-100 bg-white/80 p-3">
                      <p className="font-semibold text-gray-900">{item.label}</p>
                      <p className="text-xs text-gray-500">
                        {t('app.dashboard.top_cards.total', { values: { count: formatNumber(item.total) } })}
                      </p>
                      <p className="text-xs text-gray-500">
                        {t('app.dashboard.manager_load.pipeline')}: {formatNumber(item.pipeline)} ·{' '}
                        {t('app.dashboard.top_cards.hired')}: {formatNumber(item.hired)}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="mt-3 text-sm text-gray-500">{t('app.dashboard.top_cards.empty')}</div>
              )}
            </div>
            <div className="card p-4">
              <div className="text-sm font-semibold text-gray-800">{t('app.dashboard.top_cards.docs.title')}</div>
              <div className="text-xs text-gray-500">{t('app.dashboard.top_cards.docs.subtitle')}</div>
              {docStageStats.total ? (
                <ul className="mt-3 space-y-2 text-sm">
                  {(['waiting', 'attention', 'ready'] as const).map((bucket) => {
                    const value = docStageStats[bucket] ?? 0
                    const percent = docStageStats.total ? Math.round((value / docStageStats.total) * 100) : 0
                    const barClass =
                      bucket === 'ready'
                        ? 'bg-emerald-400'
                        : bucket === 'attention'
                          ? 'bg-amber-400'
                          : 'bg-brand-400'
                    return (
                      <li key={`doc-card-${bucket}`}>
                        <div className="flex items-center justify-between text-xs font-semibold text-gray-600">
                          <span>{t(`app.dashboard.docs_risk.${bucket}`)}</span>
                          <span>
                            {formatNumber(value)} · {percent}%
                          </span>
                        </div>
                        <div className="mt-1 h-2 rounded-full bg-gray-100">
                          <div className={`h-full rounded-full ${barClass}`} style={{ width: `${percent}%` }} />
                        </div>
                      </li>
                    )
                  })}
                </ul>
              ) : (
                <div className="mt-3 text-sm text-gray-500">{t('app.dashboard.top_cards.empty')}</div>
              )}
            </div>
          </div>
        )}

        {stageStackSegments.length > 0 && (
          <div className="card p-4 space-y-3">
            <div>
              <div className="text-sm font-semibold text-gray-800">{t('app.dashboard.stages.stack_title')}</div>
              <div className="text-xs text-gray-500">{t('app.dashboard.stages.stack_subtitle')}</div>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-gray-100 flex">
              {stageStackSegments.map((segment) => (
                <div
                  key={`stack-${segment.label}`}
                  className={['h-full', STAGE_STACK_COLORS[segment.outcome]].join(' ')}
                  style={{ width: `${segment.percent}%` }}
                  title={`${segment.label}: ${formatNumber(segment.value)} (${segment.percent}%)`}
                />
              ))}
            </div>
            <div className="grid gap-2 text-xs text-gray-600 sm:grid-cols-2 lg:grid-cols-3">
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

        <div className="card p-4 space-y-3">
          <div className="flex flex-wrap items-end gap-4">
            <label className="flex flex-col text-sm gap-1">
              {t('app.dashboard.filters.from')}
              <input
                type="date"
                className="input"
                autoComplete="off"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value)
                  setActiveRange('custom')
                }}
              />
            </label>
            <label className="flex flex-col text-sm gap-1">
              {t('app.dashboard.filters.to')}
              <input
                type="date"
                className="input"
                autoComplete="off"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value)
                  setActiveRange('custom')
                }}
              />
            </label>
            <label className="flex flex-col text-sm gap-1">
              {t('app.dashboard.filters.date_field')}
              <select
                className="input"
                value={dateField}
                onChange={(e) => {
                  const next = e.target.value === 'updated' ? 'updated' : 'created'
                  setDateField(next)
                  load({ field: next })
                }}
              >
                <option value="created">{t('app.dashboard.filters.field_created')}</option>
                <option value="updated">{t('app.dashboard.filters.field_updated')}</option>
              </select>
            </label>
            <label className="flex flex-col text-sm gap-1 min-w-[220px]">
              {t('app.dashboard.filters.vacancy')}
              <select
                className="input"
                value={vacancyFilter}
                onChange={(e) => handleVacancyChange(e.target.value)}
              >
                <option value="">{t('app.dashboard.filters.all_vacancies')}</option>
                {vacancyOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="text-sm text-gray-500">
              {t('app.dashboard.filters.sample', { values: { count: formatNumber(periodTotal) } })}
              {vacancyFilter && (
                <span className="ml-2">
                  {t('app.dashboard.filters.selected_vacancy', {
                    values: { label: selectedVacancyLabel || notAvailableLabel },
                  })}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {quickRangeOptions.map((option) => (
              <button
                key={option.value}
                className={`px-3 py-1 rounded border text-sm ${
                  activeRange === option.value
                    ? 'bg-brand-600 text-white border-brand-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => applyQuickRange(option.value)}
                type="button"
              >
                {option.label}
              </button>
            ))}
            {activeRange === 'custom' && (
              <span className="text-xs uppercase tracking-wide text-gray-500 self-center">
                {t('app.dashboard.filters.custom_range')}
              </span>
            )}
          </div>
          {rangeInvalid && (
            <div className="text-sm text-red-600">{t('app.dashboard.errors.range_invalid')}</div>
          )}
        </div>

        <div className="grid w-full gap-4 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
          <div className="card p-4">
            <div className="text-gray-500 text-sm mb-1">{t('app.dashboard.stats.candidates_total')}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.candidates)}</div>
          </div>
          <div className="card p-4">
            <div className="text-gray-500 text-sm mb-1">{t('app.dashboard.stats.companies')}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.companies)}</div>
          </div>
          <div className="card p-4">
            <div className="text-gray-500 text-sm mb-1">{t('app.dashboard.stats.vacancies')}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.vacancies)}</div>
          </div>
          <div className="card p-4 border border-brand-100">
            <div className="text-gray-500 text-sm mb-1">{t('app.dashboard.stats.period')}</div>
            <div className="text-2xl font-semibold">{formatNumber(periodTotal)}</div>
            <div className="text-xs text-gray-500 mt-1">
              {dateField === 'created'
                ? t('app.dashboard.stats.period_suffix_created')
                : t('app.dashboard.stats.period_suffix_updated')}
            </div>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="card p-4 lg:col-span-2">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-sm font-semibold">{t('app.dashboard.stages.title')}</div>
                <div className="text-xs text-gray-500">{t('app.dashboard.stages.subtitle')}</div>
              </div>
            </div>
            {slices?.stages?.length ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-gray-500">
                    <th className="py-2">{t('app.dashboard.stages.table.status')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.stages.table.count')}</th>
                  </tr>
                </thead>
                <tbody>
                {slices.stages.map((stage) => (
                  <tr key={stage.key} className="border-t border-gray-100">
                    <td className="py-2">{translateStageLabel(stage.key, stage.label)}</td>
                    <td className="py-2 text-right font-medium">{formatNumber(stage.count)}</td>
                  </tr>
                ))}
                </tbody>
              </table>
            ) : (
              <div className="text-sm text-gray-500">{t('app.dashboard.stages.empty')}</div>
            )}
          </div>

          <div className="card p-4 space-y-4">
            <div>
              <div className="text-sm font-semibold mb-2">{t('app.dashboard.reasons.rejected_title')}</div>
              {slices?.reasons?.rejected?.length ? (
                <ul className="space-y-1 text-sm">
                  {slices.reasons.rejected.slice(0, 8).map((item) => (
                    <li key={`rejected-${item.key}`} className="flex justify-between gap-2">
                      <span className="truncate">{translateReasonLabel(item.key, item.label)}</span>
                      <span className="font-medium">{formatNumber(item.count)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-sm text-gray-500">{t('app.dashboard.reasons.rejected_empty')}</div>
              )}
            </div>
            <div>
              <div className="text-sm font-semibold mb-2">{t('app.dashboard.reasons.declined_title')}</div>
              {slices?.reasons?.declined?.length ? (
                <ul className="space-y-1 text-sm">
                  {slices.reasons.declined.slice(0, 8).map((item) => (
                    <li key={`declined-${item.key}`} className="flex justify-between gap-2">
                      <span className="truncate">{translateReasonLabel(item.key, item.label)}</span>
                      <span className="font-medium">{formatNumber(item.count)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-sm text-gray-500">{t('app.dashboard.reasons.declined_empty')}</div>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold">{t('app.dashboard.companies.title')}</div>
              <div className="text-xs text-gray-500">{t('app.dashboard.companies.subtitle')}</div>
            </div>
            {slices?.companies?.length ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-gray-500">
                    <th className="py-2">{t('app.dashboard.companies.table.company')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.companies.table.total')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.companies.table.in_pipeline')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.companies.table.hired')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.companies.table.rejected')}</th>
                  </tr>
                </thead>
                <tbody>
                  {slices.companies.map((item) => {
                    const highlight = stageHighlights(item.by_stage, stageLabels)
                    return (
                      <tr key={`company-${item.key}`} className="border-t border-gray-100">
                        <td className="py-2 pr-2 truncate">{item.label}</td>
                        <td className="py-2 text-right font-medium">{formatNumber(item.count)}</td>
                        <td className="py-2 text-right">{formatNumber(highlight.pipeline)}</td>
                        <td className="py-2 text-right text-emerald-600">{formatNumber(highlight.hired)}</td>
                        <td className="py-2 text-right text-red-600">
                          {formatNumber(highlight.rejected + highlight.declined)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            ) : (
              <div className="text-sm text-gray-500">{t('app.dashboard.companies.empty')}</div>
            )}
          </div>
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold">{t('app.dashboard.vacancies.title')}</div>
              <div className="text-xs text-gray-500">{t('app.dashboard.vacancies.subtitle')}</div>
            </div>
            {slices?.vacancies?.length ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-gray-500">
                    <th className="py-2">{t('app.dashboard.vacancies.table.vacancy')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.vacancies.table.total')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.vacancies.table.in_pipeline')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.vacancies.table.hired')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.vacancies.table.rejected')}</th>
                  </tr>
                </thead>
                <tbody>
                  {slices.vacancies.map((item) => {
                    const highlight = stageHighlights(item.by_stage, stageLabels)
                    return (
                      <tr key={`vacancy-${item.key}`} className="border-t border-gray-100">
                        <td className="py-2 pr-2 truncate">{item.label}</td>
                        <td className="py-2 text-right font-medium">{formatNumber(item.count)}</td>
                        <td className="py-2 text-right">{formatNumber(highlight.pipeline)}</td>
                        <td className="py-2 text-right text-emerald-600">{formatNumber(highlight.hired)}</td>
                        <td className="py-2 text-right text-red-600">
                          {formatNumber(highlight.rejected + highlight.declined)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            ) : (
              <div className="text-sm text-gray-500">{t('app.dashboard.vacancies.empty')}</div>
            )}
          </div>
        </div>

        {(sourceStageRows.length > 0 || docStageStats.total > 0 || stageVelocityRows.length > 0) && (
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold">{t('app.dashboard.sources.detail_title')}</div>
                <div className="text-xs text-gray-500">{t('app.dashboard.sources.detail_subtitle')}</div>
              </div>
              {sourceStageRows.length ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-gray-500">
                      <th className="py-2">{t('app.dashboard.sources.table.source')}</th>
                      <th className="py-2 text-right">{t('app.dashboard.sources.table.pipeline')}</th>
                      <th className="py-2 text-right">{t('app.dashboard.sources.table.hired')}</th>
                      <th className="py-2 text-right">{t('app.dashboard.sources.table.rejected')}</th>
                      <th className="py-2 text-right">{t('app.dashboard.sources.table.total')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sourceStageRows.map((row) => (
                      <tr key={`source-${row.label}`} className="border-t border-gray-100">
                        <td className="py-2 pr-2 truncate">{row.label}</td>
                        <td className="py-2 text-right">{formatNumber(row.highlight.pipeline)}</td>
                        <td className="py-2 text-right text-emerald-600">{formatNumber(row.highlight.hired)}</td>
                        <td className="py-2 text-right text-rose-600">
                          {formatNumber(row.highlight.rejected + row.highlight.declined)}
                        </td>
                        <td className="py-2 text-right font-semibold">{formatNumber(row.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="text-sm text-gray-500">{t('app.dashboard.sources.empty')}</div>
              )}
            </div>
            <div className="card p-4 space-y-3">
              <div>
                <div className="text-sm font-semibold">{t('app.dashboard.docs_risk.title')}</div>
                <div className="text-xs text-gray-500">{t('app.dashboard.docs_risk.subtitle')}</div>
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
                        <div className="flex items-center justify-between text-xs font-semibold text-gray-600">
                          <span>{t(`app.dashboard.docs_risk.${bucket}`)}</span>
                          <span>{percent}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-gray-100">
                          <div
                            className={`h-full rounded-full ${barColor}`}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                        <div className="text-xs text-gray-500">
                          {t('app.dashboard.docs_risk.count', { values: { count: formatNumber(value) } })}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-sm text-gray-500">{t('app.dashboard.docs_risk.empty')}</div>
              )}
            </div>
            <div className="card p-4 space-y-3">
              <div>
                <div className="text-sm font-semibold">{t('app.dashboard.velocity.title')}</div>
                <div className="text-xs text-gray-500">{t('app.dashboard.velocity.subtitle')}</div>
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
                          <div className="text-xs text-gray-500">
                            {t('app.dashboard.velocity.avg', { values: { value: Math.round(row.avgDays) } })}
                            {' · '}
                            {t('app.dashboard.velocity.p90', { values: { value: Math.round(row.p90) } })}
                          </div>
                        </div>
                        <div className="text-xs text-gray-500">
                          {t('app.dashboard.velocity.count', { values: { value: formatNumber(row.total) } })}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-gray-500">{t('app.dashboard.velocity.empty')}</div>
              )}
            </div>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold">{t('app.dashboard.manager_load.title')}</div>
              <div className="text-xs text-gray-500">{t('app.dashboard.manager_load.subtitle')}</div>
            </div>
            {managerLoadRows.length ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-gray-500">
                    <th className="py-2">{t('app.dashboard.manager_load.manager')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.manager_load.pipeline')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.manager_load.total')}</th>
                  </tr>
                </thead>
                <tbody>
                  {managerLoadRows.map((row) => (
                    <tr key={row.label} className="border-t border-gray-100">
                      <td className="py-2 pr-2">{row.label}</td>
                      <td className="py-2 text-right font-semibold">{formatNumber(row.pipeline)}</td>
                      <td className="py-2 text-right text-gray-600">{formatNumber(row.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-sm text-gray-500">{t('app.dashboard.manager_load.empty')}</div>
            )}
          </div>
          <div className="card p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold">{t('app.dashboard.country_heatmap.title')}</div>
              <div className="text-xs text-gray-500">{t('app.dashboard.country_heatmap.subtitle')}</div>
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
              <div className="text-sm text-gray-500">{t('app.dashboard.country_heatmap.empty')}</div>
            )}
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="card p-4">
            <div className="text-sm font-semibold mb-2">{t('app.dashboard.sources.title')}</div>
            {slices?.sources?.length ? (
              <ul className="space-y-1 text-sm">
                {slices.sources.slice(0, 12).map((item) => (
                  <li key={`source-${item.key}`} className="flex justify-between gap-2">
                    <span className="truncate">{item.label}</span>
                    <span className="font-medium">{formatNumber(item.count)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-sm text-gray-500">{t('app.dashboard.messages.no_data')}</div>
            )}
          </div>
          <div className="card p-4">
            <div className="text-sm font-semibold mb-2">{t('app.dashboard.citizenship.title')}</div>
            {slices?.citizenships?.length ? (
              <ul className="space-y-1 text-sm">
                {slices.citizenships.slice(0, 12).map((item) => (
                  <li key={`citizenship-${item.key}`} className="flex justify-between gap-2">
                    <span className="truncate">{item.label}</span>
                    <span className="font-medium">{formatNumber(item.count)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-sm text-gray-500">{t('app.dashboard.messages.no_data')}</div>
            )}
          </div>
          <div className="card p-4">
            <div className="text-sm font-semibold mb-2">{t('app.dashboard.country.title')}</div>
            {slices?.countries?.length ? (
              <ul className="space-y-1 text-sm">
                {slices.countries.slice(0, 12).map((item) => (
                  <li key={`country-${item.key}`} className="flex justify-between gap-2">
                    <span className="truncate">{item.label}</span>
                    <span className="font-medium">{formatNumber(item.count)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-sm text-gray-500">{t('app.dashboard.messages.no_data')}</div>
            )}
          </div>
        </div>

        <div className="card p-4 space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <div className="text-sm font-semibold">{t('app.dashboard.pivot.title')}</div>
              <div className="text-xs text-gray-500">
                {primaryLabel}
                {pivotSecondary !== 'none' && ` → ${secondaryLabel}`}
              </div>
            </div>
            <div className="flex flex-wrap gap-3 text-sm">
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
            </div>
          </div>
          {pivotData.rows.length ? (
            <div className="overflow-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-gray-500">
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
                  {pivotData.rows.map((row) => (
                    <tr key={`pivot-${row.key}`} className="border-t border-gray-100">
                      <td className="py-2 pr-4 whitespace-nowrap">{row.key}</td>
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
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-sm text-gray-500">{t('app.dashboard.pivot.empty')}</div>
          )}
        </div>
      </div>
    </section>
  )
}
