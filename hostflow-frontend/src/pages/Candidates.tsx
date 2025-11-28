// src/pages/Candidates.tsx
import clsx from 'clsx'
import type { ReactNode } from 'react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../api/client'
import { patchUserMe } from '../api/users'
import type { Candidate, UserSavedView, Vacancy } from '../api/types'
import StageTag from '../components/StageTag'
import { Modal } from '../components/Modal'
import { useMetaStages } from '../store/useMeta'
import { usePermissions } from '../hooks/usePermissions'
import { useAuth } from '../store/useAuth'
import { useI18n } from '../i18n'
import {
  canonicalReasonKey,
  normalizeLabelKey,
  translateReasonLabel,
  translateStageLabel,
} from '../utils/stageLabels'
import Pipeline from './Pipeline'

// simple CSV creator
function toCSV(rows: any[], headers: { key: string; title: string }[]) {
  const esc = (v: any) => {
    if (v === null || v === undefined) return ''
    const s = String(v)
    if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"'
    return s
  }
  const head = headers.map(h => esc(h.title)).join(',')
  const body = rows.map(r => headers.map(h => esc(r[h.key])).join(',')).join('\n')
  return head + '\n' + body
}

const DOC_READINESS_META: Record<string, { labelKey: string; className: string }> = {
  pending: { labelKey: 'app.candidates.docs.readiness.pending', className: 'bg-gray-100 text-gray-600' },
  requested: { labelKey: 'app.candidates.docs.readiness.requested', className: 'bg-blue-50 text-blue-700' },
  ordered: { labelKey: 'app.candidates.docs.readiness.ordered', className: 'bg-indigo-50 text-indigo-700' },
  in_progress: { labelKey: 'app.candidates.docs.readiness.in_progress', className: 'bg-sky-50 text-sky-700' },
  awaiting_review: { labelKey: 'app.candidates.docs.readiness.awaiting_review', className: 'bg-amber-50 text-amber-700' },
  ready: { labelKey: 'app.candidates.docs.readiness.ready', className: 'bg-green-50 text-green-700' },
  problem: { labelKey: 'app.candidates.docs.readiness.problem', className: 'bg-rose-50 text-rose-700' },
}

const DOC_READINESS_ORDER: Record<string, number> = {
  problem: 6,
  awaiting_review: 5,
  in_progress: 4,
  ordered: 3,
  requested: 2,
  pending: 1,
  ready: 0,
}

const DOC_ORDER_FILTERS: Array<{ value: string; labelKey: string }> = [
  { value: 'ordered', labelKey: 'app.candidates.docs.order_filter.ordered' },
  { value: 'not_ordered', labelKey: 'app.candidates.docs.order_filter.not_ordered' },
]

const QUICK_DOC_STATUS_SETS: Record<string, string[]> = {
  ready: ['ready'],
  attention: ['problem', 'awaiting_review', 'in_progress'],
  pending: ['pending', 'requested', 'ordered'],
}

const sanitizeDocsProgress = (value: any): Record<string, any> => {
  if (value == null) return {}
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return typeof parsed === 'object' && !Array.isArray(parsed) && parsed ? parsed : {}
    } catch {
      return {}
    }
  }
  if (typeof value === 'object' && !Array.isArray(value)) {
    return { ...value }
  }
  return {}
}

const firstNonEmpty = (...values: any[]): string => {
  for (const val of values) {
    if (val == null) continue
    const str = String(val).trim()
    if (str) return str
  }
  return ''
}

const normalizeDateString = (value: any): string | null => {
  if (!value) return null
  if (value instanceof Date) return value.toISOString().slice(0, 10)
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return null
    const parsed = Date.parse(trimmed)
    if (Number.isNaN(parsed)) {
      return trimmed.length >= 10 ? trimmed.slice(0, 10) : trimmed
    }
    return new Date(parsed).toISOString().slice(0, 10)
  }
  return null
}

const toTimestamp = (value: string | null): number => {
  if (!value) return 0
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? 0 : parsed
}

const formatDateSafe = (value: string | null): string => {
  if (!value) return '—'
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) return value
  return new Date(parsed).toLocaleDateString()
}

type DocsMeta = {
  readinessState: string
  readinessLabelKey: string
  readinessClass: string
  readinessKey: string
  rank: number
  orderDate: string | null
  orderTs: number
  validFrom: string | null
  validTs: number
  hasFiles: boolean
  isOrdered: boolean
}

const deriveDocsMeta = (candidate: UICandidate): DocsMeta => {
  const progress = sanitizeDocsProgress(candidate.docs_progress)

  const readinessRaw = firstNonEmpty(
    candidate.docs_readiness_state,
    progress.readiness_state,
    progress.readinessState,
    progress.state,
  ).toLowerCase()

  let readiness = readinessRaw

  const orderedAt = normalizeDateString(
    candidate.docs_last_ordered_at ??
      progress.last_ordered_at ??
      progress.ordered_at ??
      progress.orderedAt ??
      progress.timeline?.ordered_at ??
      progress.timeline?.orderedAt ??
      progress.most_recent_ordered_at ??
      null,
  )

  const validFrom = normalizeDateString(
    candidate.docs_next_valid_from ??
      progress.next_valid_from ??
      progress.valid_from ??
      progress.validFrom ??
      progress.timeline?.valid_from ??
      progress.timeline?.validFrom ??
      null,
  )

  const total = Number(progress.total ?? progress.count ?? 0) || 0
  const readyCount = Number(progress.ready ?? progress.verified ?? progress.approved ?? 0) || 0
  const problemCount =
    Number(progress.problem ?? progress.invalid ?? progress.expired ?? progress.overdue ?? 0) || 0
  const inProgressCount =
    Number(progress.in_progress ?? progress.submitted ?? progress.pending_validation ?? 0) || 0
  const orderedCount =
    Number(progress.ordered ?? progress.requested ?? progress.pending ?? progress.ordered_count ?? 0) || 0
  const withFilesCount =
    Number(progress.with_files ?? progress.uploaded ?? progress.files ?? progress.files_count ?? 0) || 0

  const hasFiles =
    typeof candidate.docs_has_files === 'boolean'
      ? candidate.docs_has_files
      : Boolean(withFilesCount > 0)

  const isOrdered =
    Boolean(orderedAt) ||
    Boolean(orderedCount > 0) ||
    readiness === 'ordered' ||
    String(progress.latest_status || '').toLowerCase() === 'ordered'

  if (!readiness) {
    if (problemCount > 0) readiness = 'problem'
    else if (readyCount > 0 && readyCount >= (total || readyCount)) readiness = 'ready'
    else if (inProgressCount > 0) readiness = 'in_progress'
    else if (isOrdered) readiness = 'ordered'
    else if (hasFiles || withFilesCount > 0) readiness = 'awaiting_review'
    else if (total > 0) readiness = 'pending'
    else readiness = 'pending'
  }

  const meta = DOC_READINESS_META[readiness] ?? DOC_READINESS_META.pending
  const rank =
    typeof candidate.docs_readiness_rank === 'number'
      ? candidate.docs_readiness_rank
      : DOC_READINESS_ORDER[readiness] ?? 0

  return {
    readinessState: readiness,
    readinessLabelKey: meta.labelKey,
    readinessClass: meta.className,
    readinessKey: readiness,
    rank,
    orderDate: orderedAt,
    orderTs: toTimestamp(orderedAt),
    validFrom: validFrom,
    validTs: toTimestamp(validFrom),
    hasFiles,
    isOrdered,
  }
}

const extractExtraObject = (raw: any): Record<string, any> => {
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    return raw
  }
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed
      }
    } catch {
      /* ignore malformed JSON */
    }
  }
  return {}
}

type CandidateExtraNormalized = {
  citizenship: string | null
  preferredContact: string | null
  firstContactAt: string | null
  inPoland: boolean | null
  polandStayBasis: string | null
  trailerTypes: string[]
}

type DateRangeFilter = { from: string | null; to: string | null }

type ColumnTextFilters = {
  name: string
  email: string
  phone: string
  citizenship: string
  short: string
}

const makeEmptyTextFilters = (): ColumnTextFilters => ({
  name: '',
  email: '',
  phone: '',
  citizenship: '',
  short: '',
})

const EMPTY_OPTION_VALUE = '__empty__'

const normalizeCandidateExtra = (raw: any): CandidateExtraNormalized => {
  const extra = extractExtraObject(raw)
  const asString = (value: any): string | null => {
    if (typeof value !== 'string') return null
    const trimmed = value.trim()
    return trimmed.length > 0 ? trimmed : null
  }
  const toBool = (value: any): boolean | null => {
    if (value === true) return true
    if (value === false) return false
    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase()
      if (normalized === 'true' || normalized === 'yes') return true
      if (normalized === 'false' || normalized === 'no') return false
    }
    if (typeof value === 'number') {
      if (value === 1) return true
      if (value === 0) return false
    }
    return null
  }
  const arrayOfStrings = (value: any): string[] => {
    if (!value) return []
    if (Array.isArray(value)) {
      return value.map((item) => String(item).trim()).filter((item) => item.length > 0)
    }
    if (typeof value === 'string') {
      if (!value.trim()) return []
      try {
        const parsed = JSON.parse(value)
        if (Array.isArray(parsed)) {
          return parsed.map((item) => String(item).trim()).filter((item) => item.length > 0)
        }
      } catch {
        return value
          .split(',')
          .map((piece) => piece.trim())
          .filter((piece) => piece.length > 0)
      }
    }
    return []
  }

  return {
    citizenship: asString(extra.citizenship ?? extra.passport_country) ?? null,
    preferredContact: asString(extra.preferred_contact) ?? null,
    firstContactAt: asString(extra.first_contact_at) ?? null,
    inPoland: toBool(extra.in_poland),
    polandStayBasis: asString(extra.poland_stay_basis) ?? null,
    trailerTypes: arrayOfStrings(extra.trailer_types),
  }
}

const isRangeActive = (range: DateRangeFilter): boolean => Boolean(range.from || range.to)

const parseBoundary = (value: string | null, endOfDay = false): number | null => {
  if (!value) return null
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) return null
  if (!endOfDay) return parsed
  const end = new Date(parsed)
  end.setHours(23, 59, 59, 999)
  return end.getTime()
}

const matchesDateRange = (value: string | null, range: DateRangeFilter): boolean => {
  if (!isRangeActive(range)) return true
  if (!value) return false
  const target = Date.parse(value)
  if (Number.isNaN(target)) return false
  const from = parseBoundary(range.from, false)
  const to = parseBoundary(range.to, true)
  if (from !== null && target < from) return false
  if (to !== null && target > to) return false
  return true
}

const compareStrings = (a: string | null | undefined, b: string | null | undefined): number =>
  (a || '').localeCompare(b || '', undefined, { sensitivity: 'base' })

const compareNumbers = (a: number, b: number): number => a - b

const normalizeStageKey = (value?: string | null): string => (value ?? '').trim().toLowerCase()
const isLikelyNewStage = (stage: string) => stage === 'new' || stage.startsWith('new_') || stage.includes('new')

const normalizeSearchValue = (value: string): string => value.trim().toLowerCase()
const textMatches = (source: string | null | undefined, query: string): boolean => {
  if (!query) return true
  if (!source) return false
  return source.toLowerCase().includes(query)
}

const boolRank = (value: boolean | null | undefined): number => {
  if (value === true) return 2
  if (value === false) return 1
  return 0
}

const getCandidateVacancyId = (candidate: UICandidate): string | null => {
  const raw =
    (candidate as any)?.vacancy_id ??
    (candidate as any)?.vacancy?.id ??
    (candidate as any)?.vacancy_uuid ??
    null
  if (!raw) return null
  const value = String(raw)
  return value && value !== 'null' ? value : null
}

const getCandidateManagerId = (candidate: UICandidate): string | null => {
  const raw =
    (candidate as any)?.manager_id ??
    (candidate as any)?.manager?.id ??
    (candidate as any)?.manager ??
    null
  if (!raw) return null
  const value = String(raw)
  return value && value !== 'null' ? value : null
}

type UICandidate = Candidate & {
  manager_name?: string | null
  manager_short?: string | null
}

type AugmentedCandidate = UICandidate & {
  __docsMeta: DocsMeta
  __extra: CandidateExtraNormalized
  __reasonCodes: string[]
  __reasonFallbackLabels: string[]
}

type ManagerItem = { id: string; name: string }

// API may return either a plain array or a paginated object
type ListResp = { items?: UICandidate[]; total?: number } | UICandidate[]

type CandidateFilterSnapshot = {
  stage: string[]
  vacancy: string[]
  manager: string[]
  statusReasons: string[]
  docsStatus: string[]
  docsOrdered: string[]
  createdRange: DateRangeFilter
  firstContactRange: DateRangeFilter
  docsValidRange: DateRangeFilter
  preferredChannels: string[]
  polandPresence: string[]
  polandBasis: string[]
  trailerTypes: string[]
  docsHasFiles: string[]
  query: string
  textFilters: ColumnTextFilters
}

type SortKey =
  | 'created_at'
  | 'name'
  | 'email'
  | 'phone'
  | 'citizenship'
  | 'vacancy'
  | 'short_id'
  | 'manager'
  | 'stage'
  | 'reasons'
  | 'docs_status'
  | 'docs_ordered_at'
  | 'docs_valid_from'
  | 'docs_has_files'
  | 'first_contact'
  | 'preferred_channel'
  | 'in_poland'
  | 'poland_basis'
  | 'trailer_types'

const SORTABLE_KEYS: SortKey[] = [
  'created_at',
  'name',
  'email',
  'phone',
  'citizenship',
  'vacancy',
  'short_id',
  'manager',
  'stage',
  'reasons',
  'docs_status',
  'docs_ordered_at',
  'docs_valid_from',
  'docs_has_files',
  'first_contact',
  'preferred_channel',
  'in_poland',
  'poland_basis',
  'trailer_types',
]

const isSortKey = (value: any): value is SortKey =>
  typeof value === 'string' && SORTABLE_KEYS.includes(value as SortKey)

const DEFAULT_VISIBLE_COLS: Record<string, boolean> = {
  name: true,
  email: true,
  phone: true,
  citizenship: true,
  vacancy: true,
  short: true,
  manager: true,
  stage: true,
  created: true,
  firstContact: true,
  preferredChannel: true,
  inPoland: true,
  polandBasis: true,
  trailerTypes: true,
  reasons: true,
  docsStatus: true,
  docsOrdered: false,
  docsValid: false,
  docsFiles: true,
}

const FILTER_STORAGE_KEY = 'cand.filters'
const VISIBLE_COLS_STORAGE_KEY = 'cand.visibleCols'

// универсальный фетчер, который пытается разные варианты пагинации
async function getWithFallbacks<T = any>(
  path: string,
  params: Record<string, any>
) {
  const limit = params.limit ?? 50
  const offset = params.offset ?? 0
  const vacancy = params.vacancy_id ?? params.vacancy ?? undefined
  const common = {
    q: params.q,
    stage: params.stage,
    order_by: params.order_by,
    desc: params.desc,
    status_reason: params.status_reason,
    // пробуем оба ключа для фильтра по вакансии
    vacancy_id: vacancy,
    vacancy: vacancy,
  }

  const attempts = [
    { ...common, limit, offset },                              // вариант 1: limit/offset
    { ...common, limit, skip: offset },                        // вариант 2: limit/skip
    { ...common, page: Math.floor(offset / limit) + 1, per_page: limit }, // вариант 3: page/per_page
    { ...common, limit },                                      // вариант 4: только limit
    { ...common },                                             // вариант 5: без пагинации
  ]

  let lastErr: any = null
  for (const p of attempts) {
    try {
      const res = await api.get<T>(path, { params: p })
      return res
    } catch (e: any) {
      const status = e?.response?.status
      // если это не 422 — нет смысла продолжать попытки
      if (status && status !== 422) throw e
      lastErr = e
    }
  }
  throw lastErr
}

export default function Candidates(){
  const { t } = useI18n()
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<'table' | 'kanban'>(() =>
    searchParams.get('view') === 'kanban' ? 'kanban' : 'table'
  )
  const isKanban = viewMode === 'kanban'

  const [q, setQ] = useState('')
  const [stageFilter, setStageFilter] = useState<string[]>([])
  const [vacancyFilter, setVacancyFilter] = useState<string[]>([])
  const [managerFilter, setManagerFilter] = useState<string[]>([])
  const [docsStatusFilter, setDocsStatusFilter] = useState<string[]>([])
  const [docsOrderedFilter, setDocsOrderedFilter] = useState<string[]>([])
  const [vacancies, setVacancies] = useState<Vacancy[]>([])

  const [items, setItems] = useState<UICandidate[]>([])
  const [limit] = useState(100)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [errorText, setErrorText] = useState<string | null>(null)

  const [checked, setChecked] = useState<Record<string, boolean>>({})
  const [bulkOpen, setBulkOpen] = useState(false)
  const [bulkStage, setBulkStage] = useState<string>('')
  const [bulkReasons, setBulkReasons] = useState<string[]>([])
  const [statusReasonFilter, setStatusReasonFilter] = useState<string[]>([])
  const [preferredChannelFilter, setPreferredChannelFilter] = useState<string[]>([])
  const [inPolandFilter, setInPolandFilter] = useState<string[]>([])
  const [polandBasisFilter, setPolandBasisFilter] = useState<string[]>([])
  const [trailerTypesFilter, setTrailerTypesFilter] = useState<string[]>([])
  const [createdRange, setCreatedRange] = useState<DateRangeFilter>({ from: null, to: null })
  const [firstContactRange, setFirstContactRange] = useState<DateRangeFilter>({ from: null, to: null })
  const [docsValidRange, setDocsValidRange] = useState<DateRangeFilter>({ from: null, to: null })
  const [docsHasFilesFilter, setDocsHasFilesFilter] = useState<string[]>([])
  const [textFilters, setTextFilters] = useState<ColumnTextFilters>(() => makeEmptyTextFilters())
  const setTextFilter = useCallback(
    (key: keyof ColumnTextFilters, value: string) => {
      setTextFilters((prev) => {
        if (prev[key] === value) return prev
        return { ...prev, [key]: value }
      })
    },
    []
  )

  // managers for filter and bulk-assign
  const [managers, setManagers] = useState<ManagerItem[]>([])
  const [bulkManagerOpen, setBulkManagerOpen] = useState(false)
  const [bulkManagerId, setBulkManagerId] = useState('')
  const [bulkArchiveOpen, setBulkArchiveOpen] = useState(false)

  const [bulkVacancyOpen, setBulkVacancyOpen] = useState(false)
  const [bulkVacancyId, setBulkVacancyId] = useState('')

  const { me, preferences, updatePreferences } = useAuth()
  const tenantScopeKey = me?.tenant_id ? String(me.tenant_id) : 'default'
  const filterStorageKey = useMemo(() => `${FILTER_STORAGE_KEY}:${tenantScopeKey}`, [tenantScopeKey])
  const visibleColsStorageKey = useMemo(() => `${VISIBLE_COLS_STORAGE_KEY}:${tenantScopeKey}`, [tenantScopeKey])

  const vacancySavedViews = useMemo(() => preferences?.saved_views?.vacancies ?? [], [preferences?.saved_views?.vacancies])
  const [savedViews, setSavedViews] = useState<UserSavedView[]>(preferences?.saved_views?.candidates ?? [])
  const [saveViewOpen, setSaveViewOpen] = useState(false)
  const [saveViewName, setSaveViewName] = useState('')
  const [actionsMenuOpen, setActionsMenuOpen] = useState(false)
  const appliedDefaultIdRef = useRef<string | null>(null)
  const actionsMenuRef = useRef<HTMLDivElement | null>(null)

  const preferredManagerId = useMemo(() => {
    const selfId = (me as any)?.sub || (me as any)?.id || ''
    if (selfId && managers.some(m => m.id === selfId)) return selfId
    return managers[0]?.id || ''
  }, [managers, me])

  useEffect(() => {
    setSavedViews(preferences?.saved_views?.candidates ?? [])
  }, [preferences?.saved_views?.candidates])

  useEffect(() => {
    if (!actionsMenuOpen) return
    const handleClick = (event: MouseEvent) => {
      if (actionsMenuRef.current && !actionsMenuRef.current.contains(event.target as Node)) {
        setActionsMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [actionsMenuOpen])

  const syncCandidateViews = useCallback(async (next: UserSavedView[]) => {
    setSavedViews(next)
    try {
      const result = await patchUserMe({
        preferences: {
          saved_views: {
            candidates: next,
            vacancies: vacancySavedViews,
          },
        },
      })
      updatePreferences(result.preferences)
    } catch (err) {
      console.warn('[Candidates] failed to persist saved views', err)
      setSavedViews(preferences?.saved_views?.candidates ?? [])
    }
  }, [updatePreferences, vacancySavedViews, preferences?.saved_views?.candidates])

  const normalizeReasonList = useCallback((value: any): string[] => {
    if (value == null) return []
    const parts = new Set<string>()
    const push = (input: unknown) => {
      if (input == null) return
      if (Array.isArray(input)) {
        input.forEach((entry) => push(entry))
        return
      }
      if (typeof input === 'object') {
        const obj = input as Record<string, unknown>
        const candidate =
          obj.code ??
          obj.value ??
          obj.id ??
          obj.reason ??
          obj.label ??
          obj.name ??
          (typeof obj.text === 'string' ? obj.text : undefined)
        if (candidate) {
          push(candidate)
        }
        if (Array.isArray(obj.codes)) {
          obj.codes.forEach((entry) => push(entry))
        }
        return
      }
      const str = String(input)
      str
        .split(',')
        .map((chunk) => chunk.trim())
        .filter(Boolean)
        .forEach((chunk) => parts.add(chunk))
    }
    push(value)
    return Array.from(parts)
  }, [])

  const normalizeArrayFilter = useCallback((value: any): string[] => {
    if (!value) return []
    if (Array.isArray(value)) {
      return value.map((item) => String(item)).filter((item) => item.trim().length > 0)
    }
    if (typeof value === 'string') {
      return value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
    }
    return [String(value)]
  }, [])
  const normalizeRangeFilter = useCallback((value: any): DateRangeFilter => {
    const sanitize = (input: any): string | null => {
      if (typeof input !== 'string') return null
      const trimmed = input.trim()
      return trimmed ? trimmed.slice(0, 10) : null
    }
    if (!value || typeof value !== 'object') {
      return { from: null, to: null }
    }
    return {
      from: sanitize((value as any).from),
      to: sanitize((value as any).to),
    }
  }, [])
  const normalizeTextFilterState = useCallback((value: any): ColumnTextFilters => {
    if (!value || typeof value !== 'object') return makeEmptyTextFilters()
    return {
      name: typeof value.name === 'string' ? value.name : '',
      email: typeof value.email === 'string' ? value.email : '',
      phone: typeof value.phone === 'string' ? value.phone : '',
      citizenship: typeof value.citizenship === 'string' ? value.citizenship : '',
      short: typeof value.short === 'string' ? value.short : '',
    }
  }, [])

  const applyViewFilters = useCallback(
    (filters: Record<string, any> | undefined) => {
      setQ(filters?.q ?? '')
      setStageFilter(normalizeArrayFilter(filters?.stage ?? filters?.stages))
      setVacancyFilter(normalizeArrayFilter(filters?.vacancy ?? filters?.vacancyId ?? filters?.vacancies))
      setManagerFilter(normalizeArrayFilter(filters?.managers ?? filters?.manager))
      setStatusReasonFilter(normalizeReasonList(filters?.statusReason ?? filters?.status_reason))
      setDocsStatusFilter(normalizeArrayFilter(filters?.docsStatus))
      setDocsOrderedFilter(normalizeArrayFilter(filters?.docsOrdered))
      setPreferredChannelFilter(normalizeArrayFilter(filters?.preferredChannel ?? filters?.preferred_contact))
      setInPolandFilter(normalizeArrayFilter(filters?.inPoland ?? filters?.in_poland))
      setPolandBasisFilter(normalizeArrayFilter(filters?.polandBasis ?? filters?.poland_basis))
      setTrailerTypesFilter(normalizeArrayFilter(filters?.trailerTypes ?? filters?.trailer_types))
      setCreatedRange(normalizeRangeFilter(filters?.createdRange ?? filters?.created_at))
      setFirstContactRange(normalizeRangeFilter(filters?.firstContactRange ?? filters?.first_contact_at))
      setDocsValidRange(normalizeRangeFilter(filters?.docsValidRange ?? filters?.docs_valid_from))
      setDocsHasFilesFilter(normalizeArrayFilter(filters?.docsHasFiles ?? filters?.docs_has_files))
      setTextFilters(normalizeTextFilterState(filters?.textFilters))
    },
    [normalizeArrayFilter, normalizeRangeFilter, normalizeReasonList, normalizeTextFilterState]
  )

  const [filtersHydrated, setFiltersHydrated] = useState(false)
  const persistedFiltersRef = useRef(false)

  useEffect(() => {
    if (!filtersHydrated) return
    if (persistedFiltersRef.current) return
    const defaultView = savedViews.find((view) => view.is_default)
    if (defaultView && appliedDefaultIdRef.current !== defaultView.id) {
      applyViewFilters(defaultView.filters ?? {})
      appliedDefaultIdRef.current = defaultView.id
    }
  }, [filtersHydrated, savedViews, applyViewFilters])

  const applyView = (view: UserSavedView) => {
    applyViewFilters(view.filters ?? {})
  }

  const deleteView = async (id: string) => {
    const next = savedViews.filter((view) => view.id !== id)
    await syncCandidateViews(next)
  }

  const meta = useMetaStages()
  const stageOptions = useMemo(() => meta?.order || meta?.codes || [], [meta])
  const reasonOptions = useMemo(() => {
    if (!meta?.reason_choices) return []
    const out: {
      code: string
      canonicalCode: string | null
      label: string
      rawLabel: string
      stage: string
      stageLabel: string
    }[] = []
    const seen = new Set<string>()
    const labels = meta.labels ?? {}
    for (const [stageCode, items] of Object.entries(meta.reason_choices)) {
      const rawStageLabel = labels?.[stageCode] || stageCode
      const stageLabel = translateStageLabel(t, stageCode, rawStageLabel)
      for (const item of items ?? []) {
        const code = String(item?.code ?? '').trim()
        if (!code || seen.has(code)) continue
        const rawLabel = String(item?.label ?? code)
        const canonicalCode = canonicalReasonKey(code, rawLabel)
        out.push({
          code,
          canonicalCode,
          label: translateReasonLabel(t, canonicalCode ?? code, rawLabel),
          rawLabel,
          stage: stageCode,
          stageLabel,
        })
        seen.add(code)
      }
    }
    out.sort((a, b) => {
      const stageCmp = a.stageLabel.localeCompare(b.stageLabel)
      return stageCmp !== 0 ? stageCmp : a.label.localeCompare(b.label)
    })
    return out
  }, [meta, t])
  const reasonLabelMap = useMemo(() => {
    const map = new Map<string, string>()
    reasonOptions.forEach((option) => {
      map.set(option.code, option.label)
    })
    return map
  }, [reasonOptions])
  const reasonLabelLookup = useMemo(() => {
    const map = new Map<string, string>()
    reasonOptions.forEach((option) => {
      const labels = [option.rawLabel, option.label]
      labels.forEach((label) => {
        const normalized = normalizeLabelKey(label)
        const canonicalFromLabel = canonicalReasonKey(label, label)
        if (normalized && !map.has(normalized)) {
          map.set(normalized, option.code)
        }
        if (canonicalFromLabel && !map.has(canonicalFromLabel)) {
          map.set(canonicalFromLabel, option.code)
        }
      })
      if (option.canonicalCode && !map.has(option.canonicalCode)) {
        map.set(option.canonicalCode, option.code)
      }
    })
    return map
  }, [reasonOptions])
  const reasonStageMap = useMemo(() => {
    const map = new Map<string, string>()
    reasonOptions.forEach((option) => {
      map.set(option.code, option.stageLabel)
    })
    return map
  }, [reasonOptions])
  const deriveReasonData = useCallback(
    (candidate: any, extraSource: Record<string, any>): { codes: string[]; fallbackLabels: string[] } => {
      const codes = new Set(
        normalizeReasonList(
          candidate?.statusReason ??
            candidate?.status_reason ??
            candidate?.reason ??
            candidate?.status_reason_details ??
            candidate?.status_reason_codes ??
            ''
        )
      )
      const fallback: string[] = []
      const labelSources = [
        candidate?.status_reason_labels,
        candidate?.reason_labels,
        extraSource?.status_reason_labels,
        extraSource?.reason_labels,
        extraSource?.status_reason_details,
      ]
      normalizeReasonList(labelSources).forEach((label) => {
        const normalized = label.trim().toLowerCase()
        if (!normalized) return
        const mapped = reasonLabelLookup.get(normalized)
        if (mapped) {
          codes.add(mapped)
          return
        }
        if (!fallback.some((existing) => existing.trim().toLowerCase() === normalized)) {
          fallback.push(label)
        }
      })
      return {
        codes: Array.from(codes),
        fallbackLabels: fallback,
      }
    },
    [normalizeReasonList, reasonLabelLookup]
  )
  const stageLabelMap = useMemo(() => meta?.labels ?? {}, [meta?.labels])
  const stageFilterOptions = useMemo(
    () =>
      stageOptions.map((code) => ({
        value: code,
        label: translateStageLabel(t, code, stageLabelMap[code] || code),
      })),
    [stageOptions, stageLabelMap, t]
  )
  const vacancyLabelMap = useMemo(() => {
    const map = new Map<string, string>()
    const fallback = t('app.candidates.labels.untitled')
    vacancies.forEach((vac: any) => {
      const id = vac?.id ?? vac?.uuid
      if (!id) return
      map.set(String(id), vac?.title || fallback)
    })
    return map
  }, [vacancies, t])
  const managerLabelMap = useMemo(() => {
    const map = new Map<string, string>()
    managers.forEach((manager) => {
      if (!manager.id) return
      map.set(String(manager.id), manager.name || '—')
    })
    return map
  }, [managers])
  const preferredChannelLabelMap = useMemo<Record<string, string>>(
    () => ({
      [EMPTY_OPTION_VALUE]: t('common.candidate_card.contacts.options.none'),
      phone: t('common.candidate_card.contacts.options.phone'),
      viber: t('common.candidate_card.contacts.options.viber'),
      whatsapp: t('common.candidate_card.contacts.options.whatsapp'),
      telegram: t('common.candidate_card.contacts.options.telegram'),
    }),
    [t]
  )
  const inPolandLabelMap = useMemo<Record<string, string>>(
    () => ({
      yes: t('common.words.yes'),
      no: t('common.words.no'),
      unknown: t('common.labels.not_available'),
    }),
    [t]
  )
  const getPolandBasisLabel = useCallback(
    (code: string | null) => {
      if (!code) return t('common.candidate_card.status.poland_basis.none')
      const key = `common.candidate_card.status.poland_basis.${code}`
      const translated = t(key)
      return translated === key ? code : translated
    },
    [t]
  )
  const getTrailerTypeLabel = useCallback(
    (code: string) => {
      if (!code) return t('common.labels.not_available')
      const key = `common.candidate_card.intake.trailers.${code}`
      const translated = t(key)
      if (translated === key) {
        return code.length ? code.charAt(0).toUpperCase() + code.slice(1) : t('common.labels.not_available')
      }
      return translated
    },
    [t]
  )
  const columnLabelMap = useMemo(
    () => ({
      name: t('app.candidates.table.columns.name'),
      email: 'Email',
      phone: t('app.candidates.table.columns.phone'),
      citizenship: t('app.candidates.table.columns.citizenship'),
      vacancy: t('app.candidates.table.columns.vacancy'),
      short: 'Short ID',
      manager: t('app.candidates.table.columns.manager'),
      stage: t('app.candidates.table.columns.stage'),
      created: t('app.candidates.table.columns.created'),
      firstContact: t('app.candidates.table.columns.first_contact'),
      preferredChannel: t('app.candidates.table.columns.preferred_channel'),
      inPoland: t('app.candidates.table.columns.in_poland'),
      polandBasis: t('app.candidates.table.columns.poland_basis'),
      trailerTypes: t('app.candidates.table.columns.trailer_types'),
      reasons: t('app.candidates.table.columns.reasons'),
      docsStatus: t('app.candidates.table.columns.docs_status'),
      docsOrdered: t('app.candidates.table.columns.docs_ordered'),
      docsValid: t('app.candidates.table.columns.docs_valid'),
      docsFiles: t('app.candidates.table.columns.docs_files'),
    }),
    [t]
  )
  const columnToggleKeys = [
    'name',
    'email',
    'phone',
    'citizenship',
    'vacancy',
    'short',
    'manager',
    'stage',
    'created',
    'firstContact',
    'preferredChannel',
    'inPoland',
    'polandBasis',
    'trailerTypes',
    'reasons',
    'docsStatus',
    'docsOrdered',
    'docsValid',
    'docsFiles',
  ] as const
  useEffect(() => {
    if (!reasonOptions.length) {
      setStatusReasonFilter((prev) => (prev.length ? [] : prev))
      return
    }
    const valid = new Set(reasonOptions.map((option) => option.code))
    setStatusReasonFilter((prev) => {
      const filtered = prev.filter((code) => valid.has(code))
      return filtered.length === prev.length ? prev : filtered
    })
  }, [reasonOptions])
  useEffect(() => {
    const options = meta?.reason_choices?.[bulkStage] ?? []
    setBulkReasons((prev) => prev.filter((code) => options.some((opt) => opt.code === code)))
    if (!options.length) {
      setBulkReasons([])
    }
  }, [meta, bulkStage])

  const [visibleCols, setVisibleCols] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem(visibleColsStorageKey)
      const parsed = raw ? JSON.parse(raw) : {}
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return { ...DEFAULT_VISIBLE_COLS, ...parsed }
      }
    } catch {
      /* ignore malformed storage */
    }
    return { ...DEFAULT_VISIBLE_COLS }
  })
  useEffect(() => {
    try {
      const raw = localStorage.getItem(visibleColsStorageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          setVisibleCols({ ...DEFAULT_VISIBLE_COLS, ...parsed })
          return
        }
      }
    } catch {
      /* ignore malformed storage */
    }
    setVisibleCols({ ...DEFAULT_VISIBLE_COLS })
  }, [visibleColsStorageKey])
  const [sortKey, setSortKey] = useState<SortKey>('created_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const handleSortChange = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'created_at' ? 'desc' : 'asc')
    }
  }
  const renderSortButton = (label: string, key: SortKey) => (
    <button
      type="button"
      className="flex items-center gap-1 font-semibold text-left text-gray-700"
      onClick={() => handleSortChange(key)}
    >
      <span>{label}</span>
      {sortKey === key && (
        <span className="text-xs text-gray-500">{sortDir === 'asc' ? '▲' : '▼'}</span>
      )}
    </button>
  )
  const renderRangeMenu = (
    title: string,
    range: DateRangeFilter,
    onChange: (next: DateRangeFilter) => void,
    onReset: () => void
  ) => (
    <ColumnFilterMenu title={title} count={isRangeActive(range) ? 1 : 0}>
      {(close) => (
        <div className="space-y-2">
          <label className="flex flex-col gap-1 text-xs text-gray-600">
            {t('app.candidates.filters.date_from')}
            <input
              type="date"
              className="input"
              value={range.from ?? ''}
              onChange={(e) => onChange({ ...range, from: e.currentTarget.value || null })}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-gray-600">
            {t('app.candidates.filters.date_to')}
            <input
              type="date"
              className="input"
              value={range.to ?? ''}
              onChange={(e) => onChange({ ...range, to: e.currentTarget.value || null })}
            />
          </label>
          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              className="btn-ghost btn-xs"
              onClick={() => {
                onReset()
                close()
              }}
            >
              {t('app.candidates.filters.reset')}
            </button>
            <button type="button" className="btn-primary btn-xs" onClick={close}>
              {t('common.actions.close')}
            </button>
          </div>
        </div>
      )}
    </ColumnFilterMenu>
  )
  const renderTextFilterMenu = (
    key: keyof ColumnTextFilters,
    title: string,
    placeholder: string
  ) => (
    <ColumnFilterMenu title={title} count={textFilters[key].trim() ? 1 : 0}>
      {(close) => (
        <div className="space-y-2">
          <input
            className="input"
            value={textFilters[key]}
            onChange={(e) => setTextFilter(key, e.currentTarget.value)}
            placeholder={placeholder}
          />
          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              className="btn-ghost btn-xs"
              onClick={() => {
                setTextFilter(key, '')
                close()
              }}
              disabled={!textFilters[key]}
            >
              {t('app.candidates.filters.reset')}
            </button>
            <button type="button" className="btn-primary btn-xs" onClick={close}>
              {t('common.actions.close')}
            </button>
          </div>
        </div>
      )}
    </ColumnFilterMenu>
  )

  const searchRef = useRef<HTMLInputElement>(null)
  const { can } = usePermissions()
  const canManage = can('candidates.manage')

  useEffect(() => {
    setViewMode(searchParams.get('view') === 'kanban' ? 'kanban' : 'table')
  }, [searchParams])

  useEffect(() => {
    let applied = false
    try {
      const raw = localStorage.getItem(filterStorageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed && typeof parsed === 'object') {
          if (typeof parsed.q === 'string') {
            setQ(parsed.q)
            applied = applied || Boolean(parsed.q)
          }
          const restoredStage = normalizeArrayFilter(parsed.stage ?? parsed.stages)
          setStageFilter(restoredStage)
          applied = applied || restoredStage.length > 0

          const restoredVacancies = normalizeArrayFilter(parsed.vacancy ?? parsed.vacancyId ?? parsed.vacancies)
          setVacancyFilter(restoredVacancies)
          applied = applied || restoredVacancies.length > 0

          const restoredManagers = normalizeArrayFilter(parsed.managers ?? parsed.manager)
          setManagerFilter(restoredManagers)
          applied = applied || restoredManagers.length > 0

          const parsedReason = parsed.statusReason ?? parsed.status_reason
          const reasonList = normalizeReasonList(parsedReason)
          setStatusReasonFilter(reasonList)
          applied = applied || reasonList.length > 0

          const restoredDocsStatus = normalizeArrayFilter(parsed.docsStatus)
          setDocsStatusFilter(restoredDocsStatus)
          applied = applied || restoredDocsStatus.length > 0

          const restoredDocsOrdered = normalizeArrayFilter(parsed.docsOrdered ?? parsed.documents_ordered)
          setDocsOrderedFilter(restoredDocsOrdered)
          applied = applied || restoredDocsOrdered.length > 0

          const restoredPreferred = normalizeArrayFilter(parsed.preferredChannel ?? parsed.preferred_contact)
          setPreferredChannelFilter(restoredPreferred)
          applied = applied || restoredPreferred.length > 0

          const restoredInPoland = normalizeArrayFilter(parsed.inPoland ?? parsed.in_poland)
          setInPolandFilter(restoredInPoland)
          applied = applied || restoredInPoland.length > 0

          const restoredPolandBasis = normalizeArrayFilter(parsed.polandBasis ?? parsed.poland_basis)
          setPolandBasisFilter(restoredPolandBasis)
          applied = applied || restoredPolandBasis.length > 0

          const restoredTrailerTypes = normalizeArrayFilter(parsed.trailerTypes ?? parsed.trailer_types)
          setTrailerTypesFilter(restoredTrailerTypes)
          applied = applied || restoredTrailerTypes.length > 0

          const restoredCreated = normalizeRangeFilter(parsed.createdRange ?? parsed.created_at)
          setCreatedRange(restoredCreated)
          applied = applied || isRangeActive(restoredCreated)

          const restoredFirstContact = normalizeRangeFilter(parsed.firstContactRange ?? parsed.first_contact_at)
          setFirstContactRange(restoredFirstContact)
          applied = applied || isRangeActive(restoredFirstContact)

          const restoredDocsValid = normalizeRangeFilter(parsed.docsValidRange ?? parsed.docs_valid_from)
          setDocsValidRange(restoredDocsValid)
          applied = applied || isRangeActive(restoredDocsValid)

          const restoredDocsFiles = normalizeArrayFilter(parsed.docsHasFiles ?? parsed.docs_has_files)
          setDocsHasFilesFilter(restoredDocsFiles)
          applied = applied || restoredDocsFiles.length > 0

          const restoredTextFilters = normalizeTextFilterState(parsed.textFilters)
          setTextFilters(restoredTextFilters)
          applied = applied || Object.values(restoredTextFilters).some((value) => value.trim().length > 0)

          if (isSortKey(parsed.sortKey)) {
            setSortKey(parsed.sortKey)
            applied = applied || parsed.sortKey !== 'created_at'
          }
          if (typeof parsed.sortDir === 'string' && (parsed.sortDir === 'asc' || parsed.sortDir === 'desc')) {
            setSortDir(parsed.sortDir)
            applied = applied || parsed.sortDir !== 'desc'
          }
        }
      }
    } catch (err) {
      console.warn('[Candidates] failed to restore filters', err)
    } finally {
      persistedFiltersRef.current = applied
      setFiltersHydrated(true)
    }
  }, [filterStorageKey, normalizeArrayFilter, normalizeRangeFilter, normalizeReasonList, normalizeTextFilterState])
  useEffect(() => {
    if (!canManage) {
      setChecked({})
      setBulkOpen(false)
      setBulkManagerOpen(false)
      setBulkVacancyOpen(false)
      setBulkArchiveOpen(false)
    }
  }, [canManage])

  useEffect(() => {
    if (!filtersHydrated) return
    try {
      localStorage.setItem(
        filterStorageKey,
        JSON.stringify({
          q,
          stage: stageFilter,
          vacancies: vacancyFilter,
          managers: managerFilter,
          statusReason: statusReasonFilter,
          docsStatus: docsStatusFilter,
          docsOrdered: docsOrderedFilter,
          preferredChannel: preferredChannelFilter,
          inPoland: inPolandFilter,
          polandBasis: polandBasisFilter,
          trailerTypes: trailerTypesFilter,
          createdRange,
          firstContactRange,
          docsValidRange,
          docsHasFiles: docsHasFilesFilter,
          textFilters,
          sortKey,
          sortDir,
        })
      )
    } catch (err) {
      console.warn('[Candidates] failed to persist filters', err)
    }
  }, [
    filterStorageKey,
    filtersHydrated,
    q,
    stageFilter,
    vacancyFilter,
    managerFilter,
    statusReasonFilter,
    docsStatusFilter,
    docsOrderedFilter,
    preferredChannelFilter,
    inPolandFilter,
    polandBasisFilter,
    trailerTypesFilter,
    createdRange,
    firstContactRange,
    docsValidRange,
    docsHasFilesFilter,
    textFilters,
    sortKey,
    sortDir,
  ])

  const enrichedItems = useMemo<AugmentedCandidate[]>(
    () =>
      items.map((item) => {
        const rawExtra = extractExtraObject((item as any)?.extra ?? item.extra ?? null)
        const extra = normalizeCandidateExtra(rawExtra)
        const reasonData = deriveReasonData(item, rawExtra)
        return {
          ...item,
          __docsMeta: deriveDocsMeta(item),
          __extra: extra,
          __reasonCodes: reasonData.codes,
          __reasonFallbackLabels: reasonData.fallbackLabels,
        }
      }),
    [items, deriveReasonData]
  )

  const filterSnapshot = useMemo<CandidateFilterSnapshot>(
    () => ({
      stage: stageFilter,
      vacancy: vacancyFilter,
      manager: managerFilter,
      statusReasons: statusReasonFilter,
      docsStatus: docsStatusFilter,
      docsOrdered: docsOrderedFilter,
      createdRange,
      firstContactRange,
      docsValidRange,
      preferredChannels: preferredChannelFilter,
      polandPresence: inPolandFilter,
      polandBasis: polandBasisFilter,
      trailerTypes: trailerTypesFilter,
      docsHasFiles: docsHasFilesFilter,
      query: q,
      textFilters,
    }),
    [
      stageFilter,
      vacancyFilter,
      managerFilter,
      statusReasonFilter,
      docsStatusFilter,
      docsOrderedFilter,
      createdRange,
      firstContactRange,
      docsValidRange,
      preferredChannelFilter,
      inPolandFilter,
      polandBasisFilter,
      trailerTypesFilter,
      docsHasFilesFilter,
      q,
      textFilters,
    ]
  )

  const filterCandidates = useCallback((source: AugmentedCandidate[], snapshot: CandidateFilterSnapshot) => {
    const shouldFilterDocsOrdered = snapshot.docsOrdered.length === 1
    const orderedTarget = shouldFilterDocsOrdered ? snapshot.docsOrdered[0] : null
    const normalizedQuery = normalizeSearchValue(snapshot.query ?? '')
    const textQueries = {
      name: normalizeSearchValue(snapshot.textFilters.name ?? ''),
      email: normalizeSearchValue(snapshot.textFilters.email ?? ''),
      phone: normalizeSearchValue(snapshot.textFilters.phone ?? ''),
      citizenship: normalizeSearchValue(snapshot.textFilters.citizenship ?? ''),
      short: normalizeSearchValue(snapshot.textFilters.short ?? ''),
    }

    return source.filter((item) => {
      if (normalizedQuery) {
        const haystacks = [
          `${item.first_name ?? ''} ${item.last_name ?? ''}`.trim(),
          item.email ?? '',
          item.phone ?? '',
          item.short_id ?? '',
          item.stage ?? '',
          item.__extra.citizenship ?? '',
          (item as any)?.vacancy?.title ?? (item as any)?.vacancy_title ?? '',
        ]
        const queryMatch = haystacks.some((value) => textMatches(value, normalizedQuery))
        if (!queryMatch) return false
      }

      if (textQueries.name && !textMatches(`${item.first_name ?? ''} ${item.last_name ?? ''}`.trim(), textQueries.name)) {
        return false
      }
      if (textQueries.email && !textMatches(item.email ?? '', textQueries.email)) {
        return false
      }
      if (textQueries.phone && !textMatches(item.phone ?? '', textQueries.phone)) {
        return false
      }
      if (textQueries.citizenship && !textMatches(item.__extra.citizenship ?? '', textQueries.citizenship)) {
        return false
      }
      if (textQueries.short && !textMatches(item.short_id ?? '', textQueries.short)) {
        return false
      }

      if (snapshot.stage.length && (!item.stage || !snapshot.stage.includes(item.stage))) {
        return false
      }

      if (snapshot.vacancy.length) {
        const candidateVacancy =
          (item as any)?.vacancy_id || (item as any)?.vacancy?.id || (item as any)?.vacancy_uuid || null
        if (!candidateVacancy || !snapshot.vacancy.includes(String(candidateVacancy))) {
          return false
        }
      }

      if (snapshot.manager.length) {
        const candidateManager = (item as any)?.manager_id || (item as any)?.manager?.id || (item as any)?.manager || null
        if (!candidateManager || !snapshot.manager.includes(String(candidateManager))) {
          return false
        }
      }

      if (snapshot.statusReasons.length) {
        if (!item.__reasonCodes.some((code) => snapshot.statusReasons.includes(code))) {
          return false
        }
      }

      if (snapshot.docsStatus.length && !snapshot.docsStatus.includes(item.__docsMeta.readinessKey)) {
        return false
      }

      if (shouldFilterDocsOrdered) {
        if (orderedTarget === 'ordered' && !item.__docsMeta.isOrdered) return false
        if (orderedTarget === 'not_ordered' && item.__docsMeta.isOrdered) return false
      }

      if (snapshot.docsHasFiles.length) {
        const bucket = item.__docsMeta.hasFiles ? 'with' : 'without'
        if (!snapshot.docsHasFiles.includes(bucket)) {
          return false
        }
      }

      if (!matchesDateRange(item.created_at ?? null, snapshot.createdRange)) {
        return false
      }

      if (!matchesDateRange(item.__extra.firstContactAt, snapshot.firstContactRange)) {
        return false
      }

      if (!matchesDateRange(item.__docsMeta.validFrom, snapshot.docsValidRange)) {
        return false
      }

      if (snapshot.preferredChannels.length) {
        const channel = item.__extra.preferredContact ?? EMPTY_OPTION_VALUE
        if (!snapshot.preferredChannels.includes(channel)) {
          return false
        }
      }

      if (snapshot.polandPresence.length) {
        const presence = item.__extra.inPoland === true ? 'yes' : item.__extra.inPoland === false ? 'no' : 'unknown'
        if (!snapshot.polandPresence.includes(presence)) {
          return false
        }
      }

      if (snapshot.polandBasis.length) {
        const basis = item.__extra.polandStayBasis ?? EMPTY_OPTION_VALUE
        if (!snapshot.polandBasis.includes(basis)) {
          return false
        }
      }

      if (snapshot.trailerTypes.length) {
        if (!item.__extra.trailerTypes.some((code) => snapshot.trailerTypes.includes(code))) {
          return false
        }
      }

      return true
    })
  }, [])

  const buildFilterSource = useCallback(
    (overrides: Partial<CandidateFilterSnapshot>) =>
      filterCandidates(enrichedItems, { ...filterSnapshot, ...overrides }),
    [enrichedItems, filterSnapshot, filterCandidates]
  )

  const filteredItems = useMemo(
    () => filterCandidates(enrichedItems, filterSnapshot),
    [enrichedItems, filterSnapshot, filterCandidates]
  )

  const candidateInsights = useMemo(() => {
    let newCount = 0
    let docsReady = 0
    let docsAttention = 0
    let docsOrdered = 0
    filteredItems.forEach((item) => {
      const stageKey = normalizeStageKey(item.stage)
      if (isLikelyNewStage(stageKey)) newCount += 1
      if (item.__docsMeta.isOrdered) docsOrdered += 1
      const readiness = item.__docsMeta.readinessKey
      if (readiness === 'ready') docsReady += 1
      if (readiness === 'in_progress' || readiness === 'awaiting_review' || readiness === 'problem') {
        docsAttention += 1
      }
    })
    return {
      total: filteredItems.length,
      newCount,
      docsReady,
      docsAttention,
      docsOrdered,
    }
  }, [filteredItems])

  const displayedItems = useMemo<AugmentedCandidate[]>(() => {
    const sorted = [...filteredItems]
    sorted.sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'name':
          cmp = compareStrings(
            `${a.first_name ?? ''} ${a.last_name ?? ''}`.trim(),
            `${b.first_name ?? ''} ${b.last_name ?? ''}`.trim()
          )
          break
        case 'email':
          cmp = compareStrings(a.email, b.email)
          break
        case 'phone':
          cmp = compareStrings(a.phone, b.phone)
          break
        case 'citizenship':
          cmp = compareStrings(a.__extra.citizenship, b.__extra.citizenship)
          break
        case 'vacancy':
          cmp = compareStrings(
            (a as any)?.vacancy?.title || (a as any)?.vacancy_title || '',
            (b as any)?.vacancy?.title || (b as any)?.vacancy_title || ''
          )
          break
        case 'short_id':
          cmp = compareStrings(a.short_id, b.short_id)
          break
        case 'manager':
          cmp = compareStrings(
            a.manager_name || a.manager_short || (a as any)?.manager,
            b.manager_name || b.manager_short || (b as any)?.manager
          )
          break
        case 'stage':
          cmp = compareStrings(a.stage, b.stage)
          break
        case 'reasons':
          cmp = compareStrings(a.__reasonCodes.join(','), b.__reasonCodes.join(','))
          break
        case 'docs_status':
          if (a.__docsMeta.rank !== b.__docsMeta.rank) {
            cmp = compareNumbers(a.__docsMeta.rank, b.__docsMeta.rank)
          } else {
            cmp = compareNumbers(a.__docsMeta.orderTs, b.__docsMeta.orderTs)
          }
          break
        case 'docs_ordered_at':
          cmp = compareNumbers(a.__docsMeta.orderTs, b.__docsMeta.orderTs)
          break
        case 'docs_valid_from':
          cmp = compareNumbers(a.__docsMeta.validTs, b.__docsMeta.validTs)
          break
        case 'docs_has_files':
          cmp = compareNumbers(boolRank(a.__docsMeta.hasFiles), boolRank(b.__docsMeta.hasFiles))
          break
        case 'first_contact':
          cmp = compareNumbers(toTimestamp(a.__extra.firstContactAt), toTimestamp(b.__extra.firstContactAt))
          break
        case 'preferred_channel':
          cmp = compareStrings(a.__extra.preferredContact ?? EMPTY_OPTION_VALUE, b.__extra.preferredContact ?? EMPTY_OPTION_VALUE)
          break
        case 'in_poland': {
          const rankA = boolRank(a.__extra.inPoland)
          const rankB = boolRank(b.__extra.inPoland)
          cmp = compareNumbers(rankA, rankB)
          break
        }
        case 'poland_basis':
          cmp = compareStrings(a.__extra.polandStayBasis ?? EMPTY_OPTION_VALUE, b.__extra.polandStayBasis ?? EMPTY_OPTION_VALUE)
          break
        case 'trailer_types':
          cmp = compareStrings(
            a.__extra.trailerTypes.slice().sort().join(','),
            b.__extra.trailerTypes.slice().sort().join(',')
          )
          break
        case 'created_at':
        default:
          cmp = compareNumbers(toTimestamp(a.created_at ?? null), toTimestamp(b.created_at ?? null))
          break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
    return sorted
  }, [filteredItems, sortKey, sortDir])

  const vacancyFilterOptions = useMemo(() => {
    const source = buildFilterSource({ vacancy: [] })
    const map = new Map<string, string>()
    const ensure = (value: string | null, label: string) => {
      if (!value || map.has(value)) return
      map.set(value, label || t('app.candidates.labels.untitled'))
    }
    source.forEach((item) => {
      const id = getCandidateVacancyId(item)
      if (!id) return
      const title =
        (item as any)?.vacancy?.title ||
        (item as any)?.vacancy_title ||
        vacancyLabelMap.get(id) ||
        t('app.candidates.labels.untitled')
      ensure(id, title)
    })
    vacancyFilter.forEach((value) => ensure(value, vacancyLabelMap.get(value) || value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [buildFilterSource, vacancyFilter, vacancyLabelMap, t])

  const managerFilterOptions = useMemo(() => {
    const source = buildFilterSource({ manager: [] })
    const map = new Map<string, string>()
    const ensure = (value: string | null, label: string) => {
      if (!value || map.has(value)) return
      map.set(value, label || '—')
    }
    source.forEach((item) => {
      const id = getCandidateManagerId(item)
      if (!id) return
      const label = managerLabelMap.get(id) || item.manager_name || item.manager_short || id
      ensure(id, label)
    })
    managerFilter.forEach((value) => ensure(value, managerLabelMap.get(value) || value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [buildFilterSource, managerFilter, managerLabelMap])

  const reasonFilterOptions = useMemo(() => {
    const source = buildFilterSource({ statusReasons: [] })
    const present = new Set<string>(statusReasonFilter)
    source.forEach((item) => {
      item.__reasonCodes.forEach((code) => present.add(code))
    })
    const options = reasonOptions
      .filter((option) => present.has(option.code))
      .map((option) => ({
        value: option.code,
        label: `${option.label} (${option.stageLabel})`,
      }))
    return options
  }, [buildFilterSource, reasonOptions, statusReasonFilter])

  const docsStatusPresence = useMemo(() => {
    const source = buildFilterSource({ docsStatus: [] })
    const set = new Set<string>(docsStatusFilter)
    source.forEach((item) => set.add(item.__docsMeta.readinessKey))
    return set
  }, [buildFilterSource, docsStatusFilter])

  const allDocsStatusOptions = useMemo(
    () =>
      Object.entries(DOC_READINESS_META).map(([value, meta]) => ({
        value,
        label: t(meta.labelKey),
      })),
    [t]
  )

  const docsStatusOptions = useMemo(
    () => allDocsStatusOptions.filter((option) => docsStatusPresence.has(option.value)),
    [allDocsStatusOptions, docsStatusPresence]
  )

  const quickDocFilters = useMemo(() => {
    const entries: Array<{ key: keyof typeof QUICK_DOC_STATUS_SETS; label: string; statuses: string[] }> = [
      { key: 'ready', label: t('app.candidates.filters.quick_docs_ready'), statuses: QUICK_DOC_STATUS_SETS.ready },
      { key: 'attention', label: t('app.candidates.filters.quick_docs_attention'), statuses: QUICK_DOC_STATUS_SETS.attention },
      { key: 'pending', label: t('app.candidates.filters.quick_docs_pending'), statuses: QUICK_DOC_STATUS_SETS.pending },
    ]
    return entries.map((entry) => {
      const active =
        docsStatusFilter.length === entry.statuses.length &&
        entry.statuses.every((status) => docsStatusFilter.includes(status))
      return { ...entry, active }
    })
  }, [docsStatusFilter, t])

  const docsOrderPresence = useMemo(() => {
    const source = buildFilterSource({ docsOrdered: [] })
    const set = new Set<string>(docsOrderedFilter)
    source.forEach((item) => set.add(item.__docsMeta.isOrdered ? 'ordered' : 'not_ordered'))
    return set
  }, [buildFilterSource, docsOrderedFilter])

  const docsOrderFilterOptions = useMemo(
    () =>
      DOC_ORDER_FILTERS.map((option) => ({ value: option.value, label: t(option.labelKey) })).filter(
        (option) => docsOrderPresence.has(option.value)
      ),
    [docsOrderPresence, t]
  )

  const docsFilesOptions = useMemo(() => {
    const source = buildFilterSource({ docsHasFiles: [] })
    const map = new Map<string, string>()
    const ensure = (value: 'with' | 'without') => {
      if (map.has(value)) return
      map.set(
        value,
        value === 'with'
          ? t('app.candidates.filters.docs_files_with')
          : t('app.candidates.filters.docs_files_without')
      )
    }
    source.forEach((item) => ensure(item.__docsMeta.hasFiles ? 'with' : 'without'))
    docsHasFilesFilter.forEach((value) => {
      if (value === 'with' || value === 'without') ensure(value)
    })
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [buildFilterSource, docsHasFilesFilter, t])

  const preferredChannelOptions = useMemo(() => {
    const source = buildFilterSource({ preferredChannels: [] })
    const map = new Map<string, string>()
    const ensure = (value: string, label: string) => {
      if (map.has(value)) return
      map.set(value, label)
    }
    source.forEach((item) => {
      const key = item.__extra.preferredContact ?? EMPTY_OPTION_VALUE
      ensure(key, preferredChannelLabelMap[key] ?? key)
    })
    preferredChannelFilter.forEach((value) => {
      ensure(value, preferredChannelLabelMap[value] ?? value)
    })
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [buildFilterSource, preferredChannelFilter, preferredChannelLabelMap])

  const inPolandOptions = useMemo(() => {
    const source = buildFilterSource({ polandPresence: [] })
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (map.has(value)) return
      map.set(value, inPolandLabelMap[value] ?? inPolandLabelMap.unknown)
    }
    source.forEach((item) => {
      const key = item.__extra.inPoland === true ? 'yes' : item.__extra.inPoland === false ? 'no' : 'unknown'
      ensure(key)
    })
    inPolandFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [buildFilterSource, inPolandFilter, inPolandLabelMap])

  const polandBasisOptions = useMemo(() => {
    const source = buildFilterSource({ polandBasis: [] })
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (map.has(value)) return
      map.set(value, value === EMPTY_OPTION_VALUE ? t('common.labels.not_available') : getPolandBasisLabel(value))
    }
    source.forEach((item) => {
      ensure(item.__extra.polandStayBasis ?? EMPTY_OPTION_VALUE)
    })
    polandBasisFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [buildFilterSource, polandBasisFilter, getPolandBasisLabel, t])

  const trailerTypeOptions = useMemo(() => {
    const source = buildFilterSource({ trailerTypes: [] })
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (!value || map.has(value)) return
      map.set(value, getTrailerTypeLabel(value))
    }
    source.forEach((item) => {
      item.__extra.trailerTypes.forEach((code) => ensure(code))
    })
    trailerTypesFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [buildFilterSource, getTrailerTypeLabel, trailerTypesFilter])

  const visibleColumnsCount = 1 + Object.values(visibleCols).filter(Boolean).length
  const allVisibleSelected =
    displayedItems.length > 0 && displayedItems.every((candidate) => checked[candidate.id])

  // load managers catalog (array or {items})
  useEffect(() => {
    (async () => {
      try{
        const { data } = await api.get('/catalogs/managers')
        const list: any[] = Array.isArray(data) ? data : (data?.items || [])
        const mapped: ManagerItem[] = list.map((it:any) => ({ id: it?.id || it?.user_id || it?.uid, name: it?.name || it?.email || '—' }))
          .filter(m => m.id)

        // add current user if API omitted them (happens for restricted catalogs)
        const selfId = (me as any)?.sub || (me as any)?.id || null
        const selfName = (me as any)?.full_name || (me as any)?.email || null
        if (selfId && !mapped.some(m => m.id === selfId)) {
          mapped.push({ id: selfId, name: selfName || selfId })
        }

        setManagers(mapped)
      } catch{/* ignore */}
    })()
  }, [me])

  useEffect(() => {
    if (bulkManagerId) return
    if (preferredManagerId) {
      setBulkManagerId(preferredManagerId)
    }
  }, [bulkManagerId, preferredManagerId])

  // load vacancies for filter and bulk assign
  useEffect(() => {
    (async () => {
      try{
        const { data } = await api.get('/vacancies/')
        const list: any[] = Array.isArray(data) ? data : (data?.items || [])
        setVacancies(list as Vacancy[])
      } catch {/* ignore */}
    })()
  }, [])

  async function load(){
    if (!filtersHydrated) return
    setLoading(true)
    setErrorText(null)
    try{
      let nextOffset = 0
      let accumulated: UICandidate[] = []
      let totalCount: number | null = null
      let keepFetching = true

      while (keepFetching) {
        const { data } = await getWithFallbacks<ListResp>('/candidates', {
          limit,
          offset: nextOffset,
          order_by: 'created_at',
          desc: true,
        })

        const dataAny = data as any
        const batch: UICandidate[] = Array.isArray(dataAny)
          ? dataAny
          : Array.isArray(dataAny?.items)
            ? dataAny.items
            : []

        accumulated = accumulated.concat(batch)
        if (typeof dataAny?.total === 'number') {
          totalCount = dataAny.total
        }

        nextOffset += batch.length
        const reachedEnd =
          batch.length < limit ||
          (totalCount !== null && accumulated.length >= totalCount) ||
          batch.length === 0
        keepFetching = !reachedEnd
      }

      setItems(accumulated)
      setTotal(totalCount ?? accumulated.length)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      const text = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail, null, 2) : e?.message || t('app.candidates.messages.load_failed')
      setErrorText(text)
      setItems([])
      setTotal(0)
      console.error('Candidates load error:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!filtersHydrated) return
    load()
  }, [filtersHydrated]) // первый запуск

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'k')){
        e.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  function toggle(id: string){
    if (!canManage) return
    setChecked(s => ({ ...s, [id]: !s[id] }))
  }
  function allSelected(){ return items.filter(i => checked[i.id]).map(i => i.id) }

  async function doBulk(){
    const ids = allSelected()
    if (ids.length === 0 || !bulkStage) return
    const reasonOptions = meta?.reason_choices?.[bulkStage] ?? []
    if (reasonOptions.length > 0 && bulkReasons.length === 0) {
      alert(t('app.candidates.messages.reason_required'))
      return
    }
    try {
      const payload: Record<string, any> = { candidate_ids: ids, stage: bulkStage }
      if (reasonOptions.length > 0) {
        payload.status_reason = bulkReasons
      }
      await api.post('/candidates/bulk-stage', payload)
      setBulkOpen(false); setChecked({}); setBulkReasons([])
      await load()
    } catch (e) {
      const detail = (e as any)?.response?.data?.detail
      alert(typeof detail === 'string' ? detail : t('app.candidates.messages.bulk_stage_failed'))
    }
  }

  async function doBulkAssign(){
    const ids = allSelected()
    if (ids.length === 0 || !bulkManagerId) return
    try{
      const { data } = await api.post('/candidates/bulk-manager', {
        candidate_ids: ids,
        manager_id: bulkManagerId,
      })
      const results: Array<{ candidate_id?: string; ok?: boolean; error?: string }> = Array.isArray(data) ? data : []
      const failures = results.filter((item) => item && item.ok === false)
      if (failures.length) {
        const labelById = new Map(items.map((c) => [c.id, `${c.first_name} ${c.last_name}`.trim() || c.short_id || c.id]))
        const details = failures
          .map((f) => {
            const name = f.candidate_id ? (labelById.get(f.candidate_id) || f.candidate_id) : ''
            return `${name}: ${f.error || 'failed'}`
          })
          .join('\n')
        alert(
          `${t('app.candidates.messages.bulk_manager_partial', {
            values: { count: failures.length },
          })}\n${details}`,
        )
        return
      }
      setBulkManagerOpen(false); setChecked({}); setBulkManagerId(preferredManagerId)
      await load()
    } catch (e:any){
      const detail = e?.response?.data?.detail
      alert(typeof detail === 'string' ? detail : t('app.candidates.messages.bulk_manager_failed'))
    }
  }

  async function doBulkAssignVacancy(){
    const ids = allSelected()
    if (ids.length === 0 || !bulkVacancyId) return
    try{
      await Promise.allSettled(ids.map(id => api.patch(`/candidates/${id}`, { vacancy_id: bulkVacancyId })))
      setBulkVacancyOpen(false); setChecked({}); setBulkVacancyId('')
      await load()
    } catch (e:any){
      const detail = e?.response?.data?.detail
      alert(typeof detail === 'string' ? detail : t('app.candidates.messages.bulk_vacancy_failed'))
    }
  }

  async function doBulkArchive(){
    const ids = allSelected()
    if (ids.length === 0) return
    try{
      await Promise.allSettled(ids.map(id => api.patch(`/candidates/${id}`, { is_archived: true })))
      setBulkArchiveOpen(false); setChecked({})
      await load()
    } catch (e:any){
      const detail = e?.response?.data?.detail
      alert(typeof detail === 'string' ? detail : t('app.candidates.messages.bulk_archive_failed'))
    }
  }

  const asTelHref = (display: string | null | undefined) => {
    if (!display) return undefined
    const digits = display.replace(/[\s()-]/g, '')
    return digits ? `tel:${digits}` : undefined
  }

  const handleResetFilters = () => {
    setQ('')
    setStageFilter([])
    setVacancyFilter([])
    setManagerFilter([])
    setStatusReasonFilter([])
    setDocsStatusFilter([])
    setDocsOrderedFilter([])
    setPreferredChannelFilter([])
    setInPolandFilter([])
    setPolandBasisFilter([])
    setTrailerTypesFilter([])
    setCreatedRange({ from: null, to: null })
    setFirstContactRange({ from: null, to: null })
    setDocsValidRange({ from: null, to: null })
    setDocsHasFilesFilter([])
    setTextFilters(makeEmptyTextFilters())
    setSortKey('created_at')
    setSortDir('desc')
    persistedFiltersRef.current = false
    try {
      localStorage.removeItem(filterStorageKey)
    } catch {/* ignore */}
  }

  // Reusable secondary button style for top/filter actions
  const secondaryBtn = "inline-flex items-center gap-2 px-3 py-2 rounded-md border border-gray-300 text-gray-800 bg-white hover:bg-gray-100 active:bg-gray-200 transition-colors cursor-pointer";

  const hasFilterBadges =
    Boolean(q) ||
    stageFilter.length > 0 ||
    vacancyFilter.length > 0 ||
    managerFilter.length > 0 ||
    statusReasonFilter.length > 0 ||
    docsStatusFilter.length > 0 ||
    docsOrderedFilter.length > 0 ||
    preferredChannelFilter.length > 0 ||
    inPolandFilter.length > 0 ||
    polandBasisFilter.length > 0 ||
    trailerTypesFilter.length > 0 ||
    docsHasFilesFilter.length > 0 ||
    isRangeActive(createdRange) ||
    isRangeActive(firstContactRange) ||
    isRangeActive(docsValidRange) ||
    Object.values(textFilters).some((value) => value.trim().length > 0)

  const changeView = (mode: 'table' | 'kanban') => {
    setViewMode(mode)
    const next = new URLSearchParams(searchParams)
    if (mode === 'kanban') {
      next.set('view', 'kanban')
    } else {
      next.delete('view')
    }
    setSearchParams(next, { replace: true })
  }

  const viewToggle = (
    <div className="inline-flex rounded-full border border-brand-200 bg-white p-1 shadow">
      <button
        type="button"
        className={clsx(
          'rounded-full px-3 py-1.5 text-sm font-medium transition',
          !isKanban ? 'bg-brand-600 text-white shadow' : 'text-brand-700 hover:bg-brand-50'
        )}
        onClick={() => changeView('table')}
      >
        {t('app.candidates.views.table')}
      </button>
      <button
        type="button"
        className={clsx(
          'rounded-full px-3 py-1.5 text-sm font-medium transition',
          isKanban ? 'bg-brand-600 text-white shadow' : 'text-brand-700 hover:bg-brand-50'
        )}
        onClick={() => changeView('kanban')}
      >
        {t('app.candidates.views.kanban')}
      </button>
    </div>
  )
  const canSaveCurrentView = hasFilterBadges && filteredItems.length > 0
  const insightCards = [
    {
      label: t('app.candidates.insights.total'),
      value: candidateInsights.total,
      hint: t('app.candidates.insights.total_hint', { values: { count: candidateInsights.total } }),
    },
    {
      label: t('app.candidates.insights.new'),
      value: candidateInsights.newCount,
      hint: t('app.candidates.insights.new_hint', { values: { count: candidateInsights.newCount } }),
    },
    {
      label: t('app.candidates.insights.docs_ready'),
      value: candidateInsights.docsReady,
      hint: t('app.candidates.insights.docs_ready_hint', { values: { count: candidateInsights.docsReady } }),
    },
    {
      label: t('app.candidates.insights.docs_attention'),
      value: candidateInsights.docsAttention,
      hint: t('app.candidates.insights.docs_attention_hint', {
        values: { count: candidateInsights.docsAttention },
      }),
    },
  ]
  const summaryHero = (
    <section className="rounded-3xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-6 text-white shadow-card">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <p className="text-2xl font-semibold">{t('app.candidates.header.title')}</p>
          <p className="text-sm text-white/80">{t('app.candidates.insights.subtitle')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {viewToggle}
          {canSaveCurrentView && (
            <button
              type="button"
              className="btn-ghost border border-white/30 bg-white/10 text-white hover:bg-white/20"
              onClick={() => {
                setSaveViewName('')
                setSaveViewOpen(true)
              }}
            >
              {t('app.candidates.insights.save_view')}
            </button>
          )}
        </div>
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {insightCards.map((card) => (
          <div
            key={card.label}
            className="rounded-2xl border border-white/30 bg-white/10 p-4 shadow-inner backdrop-blur"
          >
            <div className="text-sm text-white/80">{card.label}</div>
            <div className="text-3xl font-semibold">{card.value}</div>
            <div className="text-xs text-white/70">{card.hint}</div>
          </div>
        ))}
      </div>
    </section>
  )

  if (isKanban) {
    return (
      <div className="space-y-4">
        {summaryHero}
        <Pipeline />
      </div>
    )
  }

  const toggleQuickDocFilter = (statuses: string[], active: boolean) => {
    if (active) {
      setDocsStatusFilter([])
    } else {
      setDocsStatusFilter(statuses)
    }
  }

  return (
    <div className="space-y-4">
      {summaryHero}
      <section className="app-surface space-y-4 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex-1 min-w-[260px]">
            <label className="sr-only" htmlFor="cand-search">{t('app.candidates.search.label')}</label>
            <input
              id="cand-search"
              ref={searchRef}
              className="input w-full"
              value={q}
              onChange={(e)=>setQ(e.target.value)}
              placeholder={t('app.candidates.search.placeholder')}
            />
            <p className="mt-1 text-xs text-gray-500">{t('app.candidates.search.hint')}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 self-end lg:self-start">
            {viewToggle}
            <button
              className={secondaryBtn}
              onClick={()=>load()}
              disabled={loading}
              title={t('app.candidates.actions.refresh_title')}
            >
              {loading ? t('app.candidates.actions.refreshing') : t('app.candidates.actions.refresh')}
            </button>
            <button
              className={secondaryBtn}
              title={t('app.candidates.actions.export_title')}
              onClick={() => {
                const rows = displayedItems.map(item => {
                  const c = item as AugmentedCandidate
                  const docsMeta = c.__docsMeta
                  return {
                    name: `${c.first_name ?? ''} ${c.last_name ?? ''}`.trim(),
                    email: c.email ?? '',
                    phone: c.phone ?? '',
                    citizenship: (()=>{ try{ const ex = typeof (c as any).extra === 'string' ? JSON.parse((c as any).extra) : (c as any).extra || {}; return ex.citizenship || ex.passport_country || '' }catch{return ''} })(),
                    vacancy: (c as any).vacancy?.title || (c as any).vacancy_title || '',
                    short_id: (c as any).short_id || '',
                    manager: c.manager_name || c.manager_short || (c as any).manager || '',
                    stage: c.stage,
                    docs_status: t(docsMeta.readinessLabelKey),
                    docs_ordered_at: docsMeta.orderDate ?? '',
                    docs_valid_from: docsMeta.validFrom ?? '',
                    docs_has_files: docsMeta.hasFiles ? t('common.words.yes') : t('common.words.no'),
                  }
                })
                const csv = toCSV(rows, [
                  { key:'name', title: t('app.candidates.table.columns.name') },
                  { key:'email', title:'Email' },
                  { key:'phone', title: t('app.candidates.table.columns.phone') },
                  { key:'citizenship', title: t('app.candidates.table.columns.citizenship') },
                  { key:'vacancy', title: t('app.candidates.table.columns.vacancy') },
                  { key:'short_id', title:'Short ID' },
                  { key:'manager', title: t('app.candidates.table.columns.manager') },
                  { key:'stage', title: t('app.candidates.table.columns.stage') },
                  { key:'docs_status', title: t('app.candidates.table.columns.docs_status') },
                  { key:'docs_ordered_at', title: t('app.candidates.table.columns.docs_ordered') },
                  { key:'docs_valid_from', title: t('app.candidates.table.columns.docs_valid') },
                  { key:'docs_has_files', title: t('app.candidates.table.columns.docs_files') },
                ])
                const blob = new Blob([csv], { type:'text/csv;charset=utf-8;' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = 'candidates.csv'
                a.click()
                URL.revokeObjectURL(url)
              }}
            >{t('app.candidates.actions.export')}</button>
            <button
              className={secondaryBtn}
              onClick={handleResetFilters}
              disabled={!hasFilterBadges}
            >
              {t('app.candidates.actions.reset_filters')}
            </button>
            <div className="relative" ref={actionsMenuRef}>
              <button
                type="button"
                className={secondaryBtn}
                title={t('app.candidates.actions.more')}
                onClick={() => setActionsMenuOpen((prev) => !prev)}
              >
                ⋯
              </button>
              {actionsMenuOpen && (
                <div className="absolute right-0 z-20 mt-2 w-64 rounded-md border border-gray-200 bg-white p-3 shadow-lg">
                  <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                    {t('app.candidates.table.columns.title')}
                  </div>
                  <div className="mt-2 max-h-48 space-y-1 overflow-auto">
                    {columnToggleKeys.map((key) => (
                      <label key={key} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={!!visibleCols[key]}
                          onChange={(e)=>{
                            const next = { ...visibleCols, [key]: e.currentTarget.checked }
                            setVisibleCols(next)
                            try{ localStorage.setItem(visibleColsStorageKey, JSON.stringify(next)) }catch{}
                          }}
                        />
                        <span>{columnLabelMap[key]}</span>
                      </label>
                    ))}
                  </div>
                  <button
                    type="button"
                    className="btn-primary mt-3 w-full"
                    onClick={() => {
                      setActionsMenuOpen(false)
                      setSaveViewName('')
                      setSaveViewOpen(true)
                    }}
                    disabled={!hasFilterBadges}
                  >
                    {t('app.candidates.views.save_action')}
                  </button>
                </div>
              )}
            </div>
            {canManage && (
              <Link className="btn-primary" to="/app/candidates/new" title={t('app.candidates.actions.new_candidate_title')}>
                {t('app.candidates.actions.new_candidate')}
              </Link>
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {quickDocFilters.map((filter) => (
            <button
              key={filter.key}
              type="button"
              onClick={() => toggleQuickDocFilter(filter.statuses, filter.active)}
              className={[
                'rounded-full px-4 py-2 text-sm font-medium',
                filter.active ? 'bg-brand-600 text-white shadow' : 'bg-white text-brand-700 border border-brand-100 hover:bg-brand-50',
              ].join(' ')}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </section>

      {savedViews.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <details className="relative">
            <summary className={secondaryBtn + " select-none"} title={t('app.candidates.views.manage_title')}>
              {t('app.candidates.views.toggle')}
            </summary>
            <div className="absolute right-0 z-10 mt-2 card p-2 w-64 space-y-2 max-h-72 overflow-auto">
              {savedViews.map(v => (
                <div key={v.id} className="flex items-center justify-between gap-2">
                  <button
                    className="btn-ghost text-left flex-1 truncate"
                    title={t('app.candidates.views.apply_title', { values: { name: v.name } })}
                    onClick={()=>applyView(v)}
                  >{v.name}</button>
                  <button
                    className="btn-ghost text-red-600"
                    title={t('app.candidates.views.delete_title')}
                    onClick={(e)=>{ e.preventDefault(); void deleteView(v.id) }}
                  >×</button>
                </div>
              ))}
              {savedViews.length === 0 && (
                <div className="text-xs text-gray-500">{t('app.candidates.views.empty')}</div>
              )}
            </div>
          </details>
        </div>
      )}

      {/* Active filter badges */}
      {hasFilterBadges && (
        <div className="flex flex-wrap items-center gap-2 mt-2">
          {q && (
            <span className="badge">
              {t('app.candidates.filters.search', { values: { value: q } })}
              <button className="ml-2 text-xs" onClick={()=>setQ('')}>×</button>
            </span>
          )}
          {textFilters.name.trim() && (
            <span className="badge">
              {t('app.candidates.filters.name_badge', { values: { value: textFilters.name } })}
              <button className="ml-2 text-xs" onClick={()=>setTextFilter('name','')}>×</button>
            </span>
          )}
          {textFilters.email.trim() && (
            <span className="badge">
              {t('app.candidates.filters.email_badge', { values: { value: textFilters.email } })}
              <button className="ml-2 text-xs" onClick={()=>setTextFilter('email','')}>×</button>
            </span>
          )}
          {textFilters.phone.trim() && (
            <span className="badge">
              {t('app.candidates.filters.phone_badge', { values: { value: textFilters.phone } })}
              <button className="ml-2 text-xs" onClick={()=>setTextFilter('phone','')}>×</button>
            </span>
          )}
          {textFilters.citizenship.trim() && (
            <span className="badge">
              {t('app.candidates.filters.citizenship_badge', { values: { value: textFilters.citizenship } })}
              <button className="ml-2 text-xs" onClick={()=>setTextFilter('citizenship','')}>×</button>
            </span>
          )}
          {textFilters.short.trim() && (
            <span className="badge">
              {t('app.candidates.filters.short_badge', { values: { value: textFilters.short } })}
              <button className="ml-2 text-xs" onClick={()=>setTextFilter('short','')}>×</button>
            </span>
          )}
          {stageFilter.map((code) => (
            <span className="badge" key={`stage-${code}`}>
              {t('app.candidates.filters.stage', { values: { value: stageLabelMap[code] || code } })}
              <button className="ml-2 text-xs" onClick={()=>setStageFilter(prev => prev.filter((item) => item !== code))}>×</button>
            </span>
          ))}
          {vacancyFilter.map((id) => (
            <span className="badge" key={`vacancy-${id}`}>
              {t('app.candidates.filters.vacancy', { values: { value: vacancyLabelMap.get(id) || '—' } })}
              <button className="ml-2 text-xs" onClick={()=>setVacancyFilter(prev => prev.filter((item) => item !== id))}>×</button>
            </span>
          ))}
          {managerFilter.map((id) => (
            <span className="badge" key={`manager-${id}`}>
              {t('app.candidates.filters.manager', { values: { value: managerLabelMap.get(id) || '—' } })}
              <button className="ml-2 text-xs" onClick={()=>setManagerFilter(prev => prev.filter((item) => item !== id))}>×</button>
            </span>
          ))}
          {statusReasonFilter.map((code) => (
            <span className="badge" key={`reason-${code}`}>
              {t('app.candidates.filters.reason', { values: { value: reasonLabelMap.get(code) || code } })}
              <span className="ml-1 text-xs text-gray-500">
                {t('app.candidates.filters.reason_stage', { values: { stage: reasonStageMap.get(code) || '—' } })}
              </span>
              <button
                className="ml-2 text-xs"
                onClick={() => setStatusReasonFilter((prev) => prev.filter((item) => item !== code))}
              >
                ×
              </button>
            </span>
          ))}
          {docsStatusFilter.map((value) => {
            const entry = docsStatusOptions.find((option) => option.value === value)
            return (
              <span className="badge" key={`docs-status-${value}`}>
                {t('app.candidates.filters.docs_status', { values: { value: entry?.label || value } })}
                <button className="ml-2 text-xs" onClick={()=>setDocsStatusFilter(prev => prev.filter((item) => item !== value))}>×</button>
              </span>
            )
          })}
          {docsOrderedFilter.map((value) => {
            const entry = docsOrderFilterOptions.find((option) => option.value === value)
            return (
              <span className="badge" key={`docs-ordered-${value}`}>
                {t('app.candidates.filters.docs_order', { values: { value: entry?.label || value } })}
                <button className="ml-2 text-xs" onClick={()=>setDocsOrderedFilter(prev => prev.filter((item) => item !== value))}>×</button>
              </span>
            )
          })}
          {preferredChannelFilter.map((value) => (
            <span className="badge" key={`preferred-${value}`}>
              {t('app.candidates.filters.preferred_channel', {
                values: { value: preferredChannelLabelMap[value] ?? value },
              })}
              <button className="ml-2 text-xs" onClick={()=>setPreferredChannelFilter(prev => prev.filter((item) => item !== value))}>×</button>
            </span>
          ))}
          {inPolandFilter.map((value) => (
            <span className="badge" key={`poland-now-${value}`}>
              {t('app.candidates.filters.in_poland', { values: { value: inPolandLabelMap[value] || value } })}
              <button className="ml-2 text-xs" onClick={()=>setInPolandFilter(prev => prev.filter((item) => item !== value))}>×</button>
            </span>
          ))}
          {polandBasisFilter.map((value) => (
            <span className="badge" key={`poland-basis-${value}`}>
              {t('app.candidates.filters.poland_basis', {
                values: { value: value === EMPTY_OPTION_VALUE ? t('common.labels.not_available') : getPolandBasisLabel(value) },
              })}
              <button className="ml-2 text-xs" onClick={()=>setPolandBasisFilter(prev => prev.filter((item) => item !== value))}>×</button>
            </span>
          ))}
          {trailerTypesFilter.map((value) => (
            <span className="badge" key={`trailer-${value}`}>
              {t('app.candidates.filters.trailer_types', { values: { value: getTrailerTypeLabel(value) } })}
              <button className="ml-2 text-xs" onClick={()=>setTrailerTypesFilter(prev => prev.filter((item) => item !== value))}>×</button>
            </span>
          ))}
          {isRangeActive(createdRange) && (
            <span className="badge">
              {t('app.candidates.filters.created_range', {
                values: { from: createdRange.from || '—', to: createdRange.to || '—' },
              })}
              <button className="ml-2 text-xs" onClick={()=>setCreatedRange({ from: null, to: null })}>×</button>
            </span>
          )}
          {isRangeActive(firstContactRange) && (
            <span className="badge">
              {t('app.candidates.filters.first_contact_range', {
                values: { from: firstContactRange.from || '—', to: firstContactRange.to || '—' },
              })}
              <button className="ml-2 text-xs" onClick={()=>setFirstContactRange({ from: null, to: null })}>×</button>
            </span>
          )}
          {isRangeActive(docsValidRange) && (
            <span className="badge">
              {t('app.candidates.filters.docs_valid_range', {
                values: { from: docsValidRange.from || '—', to: docsValidRange.to || '—' },
              })}
              <button className="ml-2 text-xs" onClick={()=>setDocsValidRange({ from: null, to: null })}>×</button>
            </span>
          )}
          {docsHasFilesFilter.map((value) => (
            <span className="badge" key={`docs-files-${value}`}>
              {t('app.candidates.filters.docs_files_badge', {
                values: {
                  value:
                    value === 'with'
                      ? t('app.candidates.filters.docs_files_with')
                      : t('app.candidates.filters.docs_files_without'),
                },
              })}
              <button className="ml-2 text-xs" onClick={()=>setDocsHasFilesFilter((prev)=>prev.filter((item)=>item!==value))}>×</button>
            </span>
          ))}
        </div>
      )}

      {/* Bulk actions appear only when there is a selection */}
      {canManage && Object.values(checked).some(Boolean) && (
        <div className="card p-3 flex flex-wrap items-center gap-2">
          <div className="text-sm">
            {t('app.candidates.bulk.selected', { values: { count: Object.values(checked).filter(Boolean).length } })}
          </div>
          <button
            className="btn-primary"
            title={t('app.candidates.bulk.stage.title')}
            onClick={()=>{ setBulkStage(stageOptions[0] || 'new'); setBulkReasons([]); setBulkOpen(true) }}
          >
            {t('app.candidates.bulk.stage.action')}
          </button>
          <button
            className="btn"
            title={t('app.candidates.bulk.manager.title')}
            onClick={()=>{ setBulkManagerId(preferredManagerId); setBulkManagerOpen(true) }}
          >
            {t('app.candidates.bulk.manager.action')}
          </button>
          <button
            className="btn"
            title={t('app.candidates.bulk.vacancy.title')}
            onClick={()=>{ setBulkVacancyId(vacancies[0]?.id || ''); setBulkVacancyOpen(true) }}
          >
            {t('app.candidates.bulk.vacancy.action')}
          </button>
          <button className="btn" title={t('app.candidates.bulk.archive.title')} onClick={()=> setBulkArchiveOpen(true)}>
            {t('app.candidates.bulk.archive.action')}
          </button>
          <div className="flex-1" />
          <button
            className="btn-ghost"
            title={t('app.candidates.bulk.clear_title')}
            onClick={()=> setChecked({})}
          >
            {t('app.candidates.bulk.clear_action')}
          </button>
        </div>
      )}

      {errorText && (
        <div className="text-sm text-red-600 whitespace-pre-wrap break-words">
          {errorText}
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left">
              <th className="px-4 py-3 w-1">
                <input
                  type="checkbox"
                  checked={allVisibleSelected}
                  disabled={!canManage}
                  onChange={(e) => {
                    if (!canManage) return
                    const val = e.currentTarget.checked
                    setChecked((prev) => {
                      const next = { ...prev }
                      displayedItems.forEach((candidate) => {
                        next[candidate.id] = val
                      })
                      return next
                    })
                  }}
                />
              </th>
              {visibleCols.name && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.name, 'name')}
                    {renderTextFilterMenu(
                      'name',
                      t('app.candidates.filters.name_menu'),
                      t('app.candidates.filters.name_placeholder')
                    )}
                  </div>
                </th>
              )}
              {visibleCols.email && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.email, 'email')}
                    {renderTextFilterMenu(
                      'email',
                      t('app.candidates.filters.email_menu'),
                      t('app.candidates.filters.email_placeholder')
                    )}
                  </div>
                </th>
              )}
              {visibleCols.phone && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.phone, 'phone')}
                    {renderTextFilterMenu(
                      'phone',
                      t('app.candidates.filters.phone_menu'),
                      t('app.candidates.filters.phone_placeholder')
                    )}
                  </div>
                </th>
              )}
              {visibleCols.citizenship && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.citizenship, 'citizenship')}
                    {renderTextFilterMenu(
                      'citizenship',
                      t('app.candidates.filters.citizenship_menu'),
                      t('app.candidates.filters.citizenship_placeholder')
                    )}
                  </div>
                </th>
              )}
              {visibleCols.vacancy && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.vacancy, 'vacancy')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.vacancy_menu')}
                      options={vacancyFilterOptions}
                      selected={vacancyFilter}
                      onChange={setVacancyFilter}
                    />
                  </div>
                </th>
              )}
              {visibleCols.short && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.short, 'short_id')}
                    {renderTextFilterMenu(
                      'short',
                      t('app.candidates.filters.short_menu'),
                      t('app.candidates.filters.short_placeholder')
                    )}
                  </div>
                </th>
              )}
              {visibleCols.manager && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.manager, 'manager')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.manager_menu')}
                      options={managerFilterOptions}
                      selected={managerFilter}
                      onChange={setManagerFilter}
                    />
                  </div>
                </th>
              )}
              {visibleCols.stage && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.stage, 'stage')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.stage_menu')}
                      options={stageFilterOptions}
                      selected={stageFilter}
                      onChange={setStageFilter}
                    />
                  </div>
                </th>
              )}
              {visibleCols.created && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.created, 'created_at')}
                    {renderRangeMenu(
                      t('app.candidates.filters.created_menu'),
                      createdRange,
                      (next) => setCreatedRange(next),
                      () => setCreatedRange({ from: null, to: null })
                    )}
                  </div>
                </th>
              )}
              {visibleCols.firstContact && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.firstContact, 'first_contact')}
                    {renderRangeMenu(
                      t('app.candidates.filters.first_contact_menu'),
                      firstContactRange,
                      (next) => setFirstContactRange(next),
                      () => setFirstContactRange({ from: null, to: null })
                    )}
                  </div>
                </th>
              )}
              {visibleCols.preferredChannel && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.preferredChannel, 'preferred_channel')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.preferred_channel_menu')}
                      options={preferredChannelOptions}
                      selected={preferredChannelFilter}
                      onChange={setPreferredChannelFilter}
                    />
                  </div>
                </th>
              )}
              {visibleCols.inPoland && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.inPoland, 'in_poland')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.in_poland_menu')}
                      options={inPolandOptions}
                      selected={inPolandFilter}
                      onChange={setInPolandFilter}
                    />
                  </div>
                </th>
              )}
              {visibleCols.polandBasis && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.polandBasis, 'poland_basis')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.poland_basis_menu')}
                      options={polandBasisOptions}
                      selected={polandBasisFilter}
                      onChange={setPolandBasisFilter}
                    />
                  </div>
                </th>
              )}
              {visibleCols.trailerTypes && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.trailerTypes, 'trailer_types')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.trailer_types_menu')}
                      options={trailerTypeOptions}
                      selected={trailerTypesFilter}
                      onChange={setTrailerTypesFilter}
                    />
                  </div>
                </th>
              )}
              {visibleCols.reasons && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.reasons, 'reasons')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.reason_menu')}
                      options={reasonFilterOptions}
                      selected={statusReasonFilter}
                      onChange={setStatusReasonFilter}
                    />
                  </div>
                </th>
              )}
              {visibleCols.docsStatus && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.docsStatus, 'docs_status')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.docs_status_menu')}
                      options={docsStatusOptions}
                      selected={docsStatusFilter}
                      onChange={setDocsStatusFilter}
                    />
                  </div>
                </th>
              )}
              {visibleCols.docsOrdered && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.docsOrdered, 'docs_ordered_at')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.docs_order_menu')}
                      options={docsOrderFilterOptions}
                      selected={docsOrderedFilter}
                      onChange={setDocsOrderedFilter}
                    />
                  </div>
                </th>
              )}
              {visibleCols.docsValid && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.docsValid, 'docs_valid_from')}
                    {renderRangeMenu(
                      t('app.candidates.filters.docs_valid_menu'),
                      docsValidRange,
                      (next) => setDocsValidRange(next),
                      () => setDocsValidRange({ from: null, to: null })
                    )}
                  </div>
                </th>
              )}
              {visibleCols.docsFiles && (
                <th className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    {renderSortButton(columnLabelMap.docsFiles, 'docs_has_files')}
                    <ColumnFilterMenu
                      title={t('app.candidates.filters.docs_files_menu')}
                      options={docsFilesOptions}
                      selected={docsHasFilesFilter}
                      onChange={setDocsHasFilesFilter}
                    />
                  </div>
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td className="px-4 py-3" colSpan={visibleColumnsCount}>{t('common.loading')}</td>
              </tr>
            )}
            {!loading && displayedItems.map((item) => {
              const c = item as AugmentedCandidate
              const phoneDisplay = c.phone || '—'
              const href = phoneDisplay && phoneDisplay !== '—' ? asTelHref(phoneDisplay) : undefined
              const docsMeta = c.__docsMeta
              const reasonTags = c.__reasonCodes
              const fallbackReasons = c.__reasonFallbackLabels
              return (
                <tr key={c.id} className="border-t border-gray-100 transition hover:bg-brand-50/50">
                  <td className="px-4 py-3">
                    <input type="checkbox" checked={!!checked[c.id]} disabled={!canManage} onChange={()=>toggle(c.id)} />
                  </td>
                  {visibleCols.name && (
                    <td className="px-4 py-3 font-medium">
                      <div className="flex items-center gap-3">
                        <div>
                          <Link className="text-brand-700 hover:underline" to={`/app/candidates/${c.id}`}>
                            {c.first_name} {c.last_name}
                          </Link>
                          <div className="text-xs text-gray-500">
                            {c.short_id ? `ID ${c.short_id}` : t('common.labels.not_available')}
                          </div>
                        </div>
                      </div>
                    </td>
                  )}
                  {visibleCols.email && (
                    <td className="px-4 py-3">{c.email || '—'}</td>
                  )}
                  {visibleCols.phone && (
                    <td className="px-4 py-3">
                      {href ? <a className="text-brand-600 hover:underline" href={href}>{phoneDisplay}</a> : phoneDisplay}
                    </td>
                  )}
                  {visibleCols.citizenship && (
                    <td className="px-4 py-3">{c.__extra.citizenship || '—'}</td>
                  )}
                  {visibleCols.vacancy && (
                    <td className="px-4 py-3">{(c as any).vacancy?.title || (c as any).vacancy_title || '—'}</td>
                  )}
                  {visibleCols.short && (
                    <td className="px-4 py-3">{c.short_id || '—'}</td>
                  )}
                  {visibleCols.manager && (
                    <td className="px-4 py-3">
                      {c.manager_name || c.manager_short || (c as any).manager || '—'}
                    </td>
                  )}
                  {visibleCols.stage && (
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <StageTag code={c.stage}/>
                        {canManage && (
                          <details className="relative">
                            <summary className="inline-flex cursor-pointer select-none rounded-full border border-brand-100 bg-white px-2 py-0.5 text-xs text-brand-700 shadow-sm hover:bg-brand-50">
                              {t('common.actions.more')}
                            </summary>
                            <div className="absolute z-10 right-0 mt-1 card p-2 w-56 space-y-2">
                              <button className="btn w-full" onClick={()=>{ setChecked({ [c.id]: true }); setBulkStage(stageOptions[0] || 'new'); setBulkReasons([]); setBulkOpen(true) }}>
                                {t('app.candidates.row_actions.change_stage')}
                              </button>
                              <button className="btn w-full" onClick={()=>{ setChecked({ [c.id]: true }); setBulkManagerOpen(true); setBulkManagerId(preferredManagerId) }}>
                                {t('app.candidates.row_actions.assign_manager')}
                              </button>
                              <button className="btn w-full" onClick={()=>{ setChecked({ [c.id]: true }); setBulkVacancyOpen(true); setBulkVacancyId(vacancies[0]?.id || '') }}>
                                {t('app.candidates.row_actions.assign_vacancy')}
                              </button>
                            </div>
                          </details>
                        )}
                      </div>
                    </td>
                  )}
                  {visibleCols.created && (
                    <td className="px-4 py-3">{c.created_at ? formatDateSafe(c.created_at) : '—'}</td>
                  )}
                  {visibleCols.firstContact && (
                    <td className="px-4 py-3">
                      {c.__extra.firstContactAt ? formatDateSafe(c.__extra.firstContactAt) : '—'}
                    </td>
                  )}
                  {visibleCols.preferredChannel && (
                    <td className="px-4 py-3">
                      {preferredChannelLabelMap[c.__extra.preferredContact ?? EMPTY_OPTION_VALUE] || '—'}
                    </td>
                  )}
                  {visibleCols.inPoland && (
                    <td className="px-4 py-3">
                      {(() => {
                        const key = c.__extra.inPoland === true ? 'yes' : c.__extra.inPoland === false ? 'no' : 'unknown'
                        const label = inPolandLabelMap[key] || inPolandLabelMap.unknown
                        const className =
                          key === 'yes'
                            ? 'bg-emerald-50 text-emerald-700'
                            : key === 'no'
                              ? 'bg-gray-100 text-gray-600'
                              : 'bg-gray-50 text-gray-500'
                        return (
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${className}`}>
                            {label}
                          </span>
                        )
                      })()}
                    </td>
                  )}
                  {visibleCols.polandBasis && (
                    <td className="px-4 py-3">
                      {c.__extra.polandStayBasis
                        ? getPolandBasisLabel(c.__extra.polandStayBasis)
                        : t('common.labels.not_available')}
                    </td>
                  )}
                  {visibleCols.trailerTypes && (
                    <td className="px-4 py-3">
                      {c.__extra.trailerTypes.length === 0 ? (
                        <span className="text-gray-400">—</span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {c.__extra.trailerTypes.map((code) => (
                            <span key={`${c.id}-trailer-${code}`} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                              {getTrailerTypeLabel(code)}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                  )}
                  {visibleCols.reasons && (
                    <td className="px-4 py-3">
                      {reasonTags.length === 0 && fallbackReasons.length === 0 ? (
                        <span className="text-gray-400">—</span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {reasonTags.map((code) => (
                            <span
                              key={`${c.id}-reason-${code}`}
                              className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                            >
                              {reasonLabelMap.get(code) || code}
                            </span>
                          ))}
                          {fallbackReasons.map((label, idx) => (
                            <span
                              key={`${c.id}-reason-fallback-${idx}`}
                              className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 italic"
                            >
                              {label}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                  )}
                  {visibleCols.docsStatus && (
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${docsMeta.readinessClass}`}>
                        {t(docsMeta.readinessLabelKey)}
                      </span>
                    </td>
                  )}
                  {visibleCols.docsOrdered && (
                    <td className="px-4 py-3">{docsMeta.orderDate ? formatDateSafe(docsMeta.orderDate) : '—'}</td>
                  )}
                  {visibleCols.docsValid && (
                    <td className="px-4 py-3">{docsMeta.validFrom ? formatDateSafe(docsMeta.validFrom) : '—'}</td>
                  )}
                  {visibleCols.docsFiles && (
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${
                          docsMeta.hasFiles ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        {docsMeta.hasFiles ? t('common.words.yes') : t('common.words.no')}
                      </span>
                    </td>
                  )}
                </tr>
              )
            })}
            {!loading && displayedItems.length === 0 && !errorText && (
              <tr><td className="px-4 py-8 text-center text-gray-500" colSpan={visibleColumnsCount}>{t('app.candidates.table.empty')}</td></tr>
            )}
          </tbody>
          </table>
        </div>
      </div>

      <div className="text-sm text-gray-500">{t('app.candidates.table.total', { values: { count: total } })}</div>

      <Modal open={saveViewOpen} onClose={()=>setSaveViewOpen(false)} title={t('app.candidates.views.save_modal.title')}>
        <div className="space-y-3">
          <div>
            <div className="label">{t('app.candidates.views.save_modal.name_label')}</div>
            <input
              className="input w-full"
              value={saveViewName}
              onChange={e=>setSaveViewName(e.target.value)}
              placeholder={t('app.candidates.views.save_modal.placeholder')}
            />
          </div>
          <div className="text-xs text-gray-500">
            {t('app.candidates.views.save_modal.hint')}
          </div>
          <div className="flex gap-2">
            <button
              className="btn-primary"
              onClick={()=>{
                const name = saveViewName.trim() || t('app.candidates.labels.untitled')
                const newView: UserSavedView = {
                  id: (typeof crypto !== 'undefined' && 'randomUUID' in crypto) ? crypto.randomUUID() : String(Date.now()),
                  name,
                  filters: {
                    q,
                    stage: stageFilter,
                    vacancies: vacancyFilter,
                    managers: managerFilter,
                    statusReason: statusReasonFilter,
                    docsStatus: docsStatusFilter,
                    docsOrdered: docsOrderedFilter,
                    preferredChannel: preferredChannelFilter,
                    inPoland: inPolandFilter,
                    polandBasis: polandBasisFilter,
                    trailerTypes: trailerTypesFilter,
                    createdRange,
                    firstContactRange,
                    docsValidRange,
                    docsHasFiles: docsHasFilesFilter,
                    textFilters,
                  },
                }
                void syncCandidateViews([...savedViews, newView])
                setSaveViewOpen(false)
              }}
            >{t('common.actions.save')}</button>
            <button className="btn-ghost" onClick={()=>setSaveViewOpen(false)}>{t('common.actions.cancel')}</button>
          </div>
        </div>
      </Modal>

      <Modal open={canManage && bulkManagerOpen} onClose={()=>setBulkManagerOpen(false)} title={t('app.candidates.modals.manager.title')}>
        <div className="space-y-3">
          <div>
            <div className="label">{t('app.candidates.modals.manager.label')}</div>
            <select className="input" value={bulkManagerId} onChange={e=>setBulkManagerId(e.target.value)}>
              <option value="">{t('app.candidates.select.placeholder')}</option>
              {managers.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={doBulkAssign}>{t('common.actions.apply')}</button>
            <button className="btn-ghost" onClick={()=>setBulkManagerOpen(false)}>{t('common.actions.cancel')}</button>
          </div>
        </div>
      </Modal>

      <Modal open={canManage && bulkVacancyOpen} onClose={()=>setBulkVacancyOpen(false)} title={t('app.candidates.modals.vacancy.title')}>
        <div className="space-y-3">
          <div>
            <div className="label">{t('app.candidates.modals.vacancy.label')}</div>
            <select className="input" value={bulkVacancyId} onChange={e=>setBulkVacancyId(e.target.value)}>
              <option value="">{t('app.candidates.select.placeholder')}</option>
              {vacancies.map(v => <option key={v.id} value={v.id}>{(v as any).title || t('app.candidates.labels.untitled')}</option>)}
            </select>
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={doBulkAssignVacancy}>{t('common.actions.apply')}</button>
            <button className="btn-ghost" onClick={()=>setBulkVacancyOpen(false)}>{t('common.actions.cancel')}</button>
          </div>
        </div>
      </Modal>

      <Modal open={canManage && bulkArchiveOpen} onClose={()=>setBulkArchiveOpen(false)} title={t('app.candidates.modals.archive.title')}>
        <div className="space-y-3">
          <div className="text-sm">{t('app.candidates.modals.archive.body')}</div>
          <div className="flex gap-2">
            <button className="btn" onClick={doBulkArchive}>{t('app.candidates.modals.archive.confirm')}</button>
            <button className="btn-ghost" onClick={()=>setBulkArchiveOpen(false)}>{t('common.actions.cancel')}</button>
          </div>
        </div>
      </Modal>

      <Modal open={canManage && bulkOpen} onClose={()=>{ setBulkOpen(false); setBulkReasons([]) }} title={t('app.candidates.modals.stage.title')}>
        <div className="space-y-3">
          <div>
            <div className="label">{t('app.candidates.modals.stage.new_stage')}</div>
            <select className="input" value={bulkStage} onChange={e=>setBulkStage(e.target.value)}>
              {stageOptions.map(c => (
                <option key={c} value={c}>{translateStageLabel(t, c, meta?.labels?.[c] || c)}</option>
              ))}
            </select>
          </div>
          {(meta?.reason_choices?.[bulkStage]?.length ?? 0) > 0 && (
            <div>
              <div className="label">{t('app.candidates.modals.stage.reasons_label')}</div>
              <div className="space-y-1">
                {(meta?.reason_choices?.[bulkStage] ?? []).map(option => (
                  <label key={option.code} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={bulkReasons.includes(option.code)}
                      onChange={(e) => {
                        const checked = e.target.checked
                        setBulkReasons(prev => {
                          if (checked) {
                            if (prev.includes(option.code)) return prev
                            return [...prev, option.code]
                          }
                          return prev.filter(code => code !== option.code)
                        })
                      }}
                    />
                    <span>{translateReasonLabel(t, option.code, option.label || option.code)}</span>
                  </label>
                ))}
              </div>
              {bulkReasons.length === 0 && (
                <div className="text-xs text-red-600">{t('app.candidates.messages.reason_required')}</div>
              )}
            </div>
          )}
          <div className="flex gap-2">
            <button className="btn-primary" onClick={doBulk}>{t('common.actions.apply')}</button>
            <button className="btn-ghost" onClick={()=>setBulkOpen(false)}>{t('common.actions.cancel')}</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

type ColumnFilterMenuProps =
  | {
      title: string
      options: Array<{ value: string; label: string }>
      selected: string[]
      onChange: (next: string[]) => void
      count?: number
      children?: undefined
    }
  | {
    title: string
    count?: number
    children: (close: () => void) => ReactNode
    options?: undefined
    selected?: undefined
    onChange?: undefined
  }

function ColumnFilterMenu(props: ColumnFilterMenuProps) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    const handler = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const toggle = () => setOpen((prev) => !prev)
  const badgeCount =
    'children' in props && props.children
      ? props.count ?? 0
      : props.selected?.length ?? 0

  return (
    <div className="relative inline-flex" ref={ref}>
      <button
        type="button"
        className="btn-icon"
        onClick={toggle}
        aria-label={props.title}
      >
        <FilterIcon />
        {badgeCount > 0 && (
          <span className="ml-1 rounded bg-brand-50 px-1 text-[10px] font-semibold text-brand-700">
            {badgeCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-72 rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-xl">
          <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">{props.title}</div>
          {'children' in props && props.children ? (
            <div className="mt-2 space-y-2">{props.children(() => setOpen(false))}</div>
          ) : props.options && props.options.length > 0 ? (
            <div className="mt-2 max-h-56 space-y-1 overflow-y-auto pr-1">
              {props.options.map((option) => (
                <label key={option.value} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={props.selected?.includes(option.value)}
                    onChange={(event) => {
                      if (!props.selected || !props.onChange) return
                      const checked = event.currentTarget.checked
                      props.onChange(
                        checked
                          ? [...props.selected, option.value]
                          : props.selected.filter((value) => value !== option.value)
                      )
                    }}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          ) : (
            <div className="mt-2 text-xs text-gray-500">{t('app.candidates.filters.empty')}</div>
          )}
          {!('children' in props && props.children) && (
            <button
              type="button"
              className="btn-ghost btn-xs mt-2"
              onClick={() => props.onChange?.([])}
              disabled={!props.selected || props.selected.length === 0}
            >
              {t('app.candidates.filters.reset')}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

const FilterIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
    className="h-4 w-4 text-gray-500"
  >
    <path d="M3 5a1 1 0 0 1 1-1h16a1 1 0 0 1 .78 1.63l-5.78 7.04V19a1 1 0 0 1-1.45.9l-4-2A1 1 0 0 1 9 17v-4.33L3.22 5.63A1 1 0 0 1 3 5Z" />
  </svg>
)
