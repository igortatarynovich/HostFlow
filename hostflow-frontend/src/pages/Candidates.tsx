// src/pages/Candidates.tsx
import clsx from 'clsx'
import type { ReactNode } from 'react'
import { useCallback, useEffect, useMemo, useRef, useState, forwardRef } from 'react'
import { createPortal } from 'react-dom'
import { Link, useSearchParams, useLocation, useNavigate } from 'react-router-dom'
import {
  IconBookmark,
  IconBookmarkFilled,
  IconClipboardList,
} from '@tabler/icons-react'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import {
  useSortable,
  SortableContext,
  horizontalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import api, { completeReminder, createReminder, listReminders, withTenant } from '../api/client'
import { useCurrentTenantId } from '../contexts/CurrentTenant'
import { patchUserMe } from '../api/users'
import type { Candidate, UserSavedView, Vacancy } from '../api/types'
import type { ReminderRecord } from '../api/types/notification'
import StageTag from '../components/StageTag'
import { Modal } from '../components/Modal'
import EmptyStatePanel from '../components/EmptyStatePanel'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
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
import { getRegionDisplayName } from '../utils/catalogLocale'
import Pipeline from './Pipeline'
import { prefetchCandidate } from '../api/candidateCache'
import { TableVirtuoso, type VirtuosoHandle } from 'react-virtuoso'
import HoverCard from '../components/HoverCard'
import {
  DOC_READINESS_META,
  DOC_READINESS_ORDER,
  DOC_ORDER_FILTERS,
  QUICK_DOC_STATUS_SETS,
  FILTER_STORAGE_KEY,
  VISIBLE_COLS_STORAGE_KEY,
  COLUMN_WIDTHS_STORAGE_KEY,
  COLUMN_ORDER_STORAGE_KEY,
  CANDIDATE_LIST_STORAGE_KEY,
  CANDIDATE_CACHE_TTL_MS,
  SCROLL_STATE_KEY,
  SCROLL_STATE_TTL_MS,
  APP_SCROLL_SELECTOR,
  RESTORE_SCROLL_MAX_ATTEMPTS,
  EMPTY_OPTION_VALUE,
  SORTABLE_KEYS,
  DEFAULT_VISIBLE_COLS,
  DEFAULT_COLUMN_ORDER,
} from '../modules/candidates/constants'
import { toCSV } from '../modules/candidates/candidateUtils'
import type {
  DateRangeFilter,
  ColumnTextFilters,
  CandidateOpsMode,
  UICandidate,
  DocsMeta,
  CandidateExtraNormalized,
  AugmentedCandidate,
  ManagerItem,
  ListResp,
  CandidateFilterSnapshot,
  CandidateListCacheEntry,
  SortKey,
} from '../modules/candidates/types'
import { makeEmptyTextFilters } from '../modules/candidates/types'
import { formatErrorForDisplay, getErrorInfo } from '../utils/errorHandling'
import {
  deriveDocsMeta,
  normalizeCandidateExtra,
  getCandidateVacancyId,
  getCandidateManagerId,
} from '../modules/candidates/utils'
import {
  sanitizeDocsProgress,
  firstNonEmpty,
  normalizeDateString,
  toTimestamp,
  formatDateSafe,
  extractExtraObject,
  isRangeActive,
  parseBoundary,
  matchesDateRange,
  compareStrings,
  compareNumbers,
  normalizeStageKey,
  isLikelyNewStage,
  normalizeSearchValue,
  textMatches,
  boolRank,
} from '../modules/candidates/candidateUtils'
import { isSortKey } from '../modules/candidates/constants'
import {
  BulkStageModal,
  BulkManagerModal,
  BulkVacancyModal,
  BulkHandoffModal,
  BulkTagsModal,
  BulkDeleteModal,
  ColumnFilterMenu,
  FilterBadges,
} from '../modules/candidates/components'
import { getAvailableClients, createBulkHandoff } from '../api/handoffs'

// Cache for candidate lists
const candidateListCache = new Map<string, CandidateListCacheEntry>()

// All utility functions, types, and constants are now imported from modules/candidates

// универсальный фетчер (tenantId = X-Tenant-Id для запроса, чтобы список совпадал с аналитикой для клиента)
async function getWithFallbacks<T = any>(
  path: string,
  params: Record<string, any>,
  tenantId?: string | null
) {
  const client = tenantId ? withTenant(tenantId) : api
  const limit = params.limit ?? 50
  const offset = params.offset ?? 0
  const vacancy = params.vacancy_id ?? params.vacancy ?? undefined
  const scopeTid = params.scope_tenant_id ?? undefined
  const common = {
    q: params.q,
    stage: params.stage,
    order_by: params.order_by,
    desc: params.desc,
    status_reason: params.status_reason,
    tags: params.tags,
    vacancy_id: vacancy,
    vacancy: vacancy,
    ...(scopeTid ? { scope_tenant_id: scopeTid } : {}),
  }

  const attempts = [
    { ...common, limit, offset },
    { ...common, limit, skip: offset },
    { ...common, page: Math.floor(offset / limit) + 1, per_page: limit },
    { ...common, limit },
    { ...common },
  ]

  let lastErr: any = null
  for (const p of attempts) {
    try {
      const res = await client.get<T>(path, { params: p })
      return res
    } catch (e: any) {
      const status = e?.response?.status
      if (status && status !== 422) throw e
      lastErr = e
    }
  }
  throw lastErr
}

export default function Candidates(){
  const { t, locale } = useI18n()
  const location = useLocation()
  const navigate = useNavigate()
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

  // R1.1: candidate quick preview side panel (in existing right sidebar)
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null)
  const [previewTab, setPreviewTab] = useState<'composer' | 'focus' | 'history'>('composer')
  const [previewRemindersLoading, setPreviewRemindersLoading] = useState(false)
  const [previewRemindersError, setPreviewRemindersError] = useState<string | null>(null)
  const [previewReminders, setPreviewReminders] = useState<ReminderRecord[]>([])
  const [previewReminderTitle, setPreviewReminderTitle] = useState('')
  const [previewReminderDueAt, setPreviewReminderDueAt] = useState(() =>
    new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16),
  )
  const [previewReminderOffset, setPreviewReminderOffset] = useState<number>(15)

  const [debugClientView, setDebugClientView] = useState<Record<string, unknown> | null>(null)
  const [debugClientViewLoading, setDebugClientViewLoading] = useState(false)
  const [debugClientViewError, setDebugClientViewError] = useState<string | null>(null)
  const showDebugPanel = searchParams.get('debug') === '1'

  const [checked, setChecked] = useState<Record<string, boolean>>({})
  const [bulkOpen, setBulkOpen] = useState(false)
  const [bulkStage, setBulkStage] = useState<string>('')
  const [bulkReasons, setBulkReasons] = useState<string[]>([])
  const [statusReasonFilter, setStatusReasonFilter] = useState<string[]>([])
  const [tagsFilter, setTagsFilter] = useState<string[]>([])
  const [isFavoriteFilter, setIsFavoriteFilter] = useState<boolean | null>(null)
  const [preferredChannelFilter, setPreferredChannelFilter] = useState<string[]>([])
  const [inPolandFilter, setInPolandFilter] = useState<string[]>([])
  const [opsModeFilter, setOpsModeFilter] = useState<CandidateOpsMode[]>([])
  const [polandBasisFilter, setPolandBasisFilter] = useState<string[]>([])
  const [trailerTypesFilter, setTrailerTypesFilter] = useState<string[]>([])
  const [createdRange, setCreatedRange] = useState<DateRangeFilter>({ from: null, to: null })
  const [firstContactRange, setFirstContactRange] = useState<DateRangeFilter>({ from: null, to: null })
  const [docsValidRange, setDocsValidRange] = useState<DateRangeFilter>({ from: null, to: null })
  const [docsHasFilesFilter, setDocsHasFilesFilter] = useState<string[]>([])
  const [handoffStatusFilter, setHandoffStatusFilter] = useState<string>('')
  const [contactAttemptsFilter, setContactAttemptsFilter] = useState<string>('')
  const [processorFilter, setProcessorFilter] = useState<string>('')
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

  const [bulkVacancyOpen, setBulkVacancyOpen] = useState(false)
  const [bulkVacancyId, setBulkVacancyId] = useState('')

  const [bulkTagsOpen, setBulkTagsOpen] = useState(false)
  const [bulkTagsOperation, setBulkTagsOperation] = useState<'add' | 'remove'>('add')
  const [bulkTagsList, setBulkTagsList] = useState<string>('')

  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)

  const [bulkHandoffOpen, setBulkHandoffOpen] = useState(false)
  const [handoffClients, setHandoffClients] = useState<Array<{ link_id: string; client_company_id: string; company_name: string }>>([])
  const [handoffClientsLoading, setHandoffClientsLoading] = useState(false)
  const [bulkHandoffClientId, setBulkHandoffClientId] = useState('')

  const { me, preferences, updatePreferences } = useAuth()
  const currentTenantId = useCurrentTenantId()
  const tenantScopeKey = (currentTenantId ?? me?.tenant_id) ? String(currentTenantId ?? me?.tenant_id) : 'default'
  const filterStorageKey = useMemo(() => `${FILTER_STORAGE_KEY}:${tenantScopeKey}`, [tenantScopeKey])
  const visibleColsStorageKey = useMemo(() => `${VISIBLE_COLS_STORAGE_KEY}:${tenantScopeKey}`, [tenantScopeKey])
  const columnWidthsStorageKey = useMemo(() => `${COLUMN_WIDTHS_STORAGE_KEY}:${tenantScopeKey}`, [tenantScopeKey])
  const columnOrderStorageKey = useMemo(() => `${COLUMN_ORDER_STORAGE_KEY}:${tenantScopeKey}`, [tenantScopeKey])
  const listStorageKey = useMemo(() => `${CANDIDATE_LIST_STORAGE_KEY}:${tenantScopeKey}`, [tenantScopeKey])
  // Include filter state in cache key so count and items update when filters change (was: same key for all filters → stale total)
  const filterSignature = useMemo(() => {
    const p: Record<string, string> = {
      q: (q || '').trim(),
      stages: stageFilter.slice().sort().join(','),
      status_reason: statusReasonFilter.slice().sort().join(','),
      tags: tagsFilter.slice().sort().join(','),
      vacancy_id: vacancyFilter.slice().sort().join(','),
      manager_id: managerFilter.slice().sort().join(','),
      documents_ordered: docsOrderedFilter.join(','),
      ops_mode: opsModeFilter.slice().sort().join(','),
      handoff_status: handoffStatusFilter || '',
      contact_attempts: contactAttemptsFilter || '',
      processor_id: processorFilter || '',
      created_from: createdRange.from || '',
      created_to: createdRange.to || '',
      is_favorite: isFavoriteFilter === null ? '' : String(isFavoriteFilter),
    }
    const s = JSON.stringify(p)
    let h = 0
    for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0
    return (h >>> 0).toString(36)
  }, [
    q,
    stageFilter,
    statusReasonFilter,
    tagsFilter,
    vacancyFilter,
    managerFilter,
    docsOrderedFilter,
    opsModeFilter,
    handoffStatusFilter,
    contactAttemptsFilter,
    processorFilter,
    createdRange.from,
    createdRange.to,
    isFavoriteFilter,
  ])
  const cacheKey = useMemo(
    () => `candidates:list:${tenantScopeKey}:${filterSignature}`,
    [tenantScopeKey, filterSignature]
  )
  const scrollKey = useMemo(() => `${SCROLL_STATE_KEY}:${tenantScopeKey}:${viewMode}`, [tenantScopeKey, viewMode])

  const vacancySavedViews = useMemo(() => preferences?.saved_views?.vacancies ?? [], [preferences?.saved_views?.vacancies])
  const [savedViews, setSavedViews] = useState<UserSavedView[]>(preferences?.saved_views?.candidates ?? [])
  const [saveViewOpen, setSaveViewOpen] = useState(false)
  const [saveViewName, setSaveViewName] = useState('')
  const [actionsMenuOpen, setActionsMenuOpen] = useState(false)
  const appliedDefaultIdRef = useRef<string | null>(null)
  const actionsMenuRef = useRef<HTMLDivElement | null>(null)
  
  // Контекстное меню для строк
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; candidateId: string } | null>(null)
  const contextMenuRef = useRef<HTMLDivElement | null>(null)
  
  // Рефы для управления обновлением кандидатов
  const updateInProgressRef = useRef<Set<string>>(new Set())
  const lastUpdateTimeRef = useRef<Map<string, number>>(new Map())
  // Храним ID недавно обновленных кандидатов, чтобы они оставались видимыми даже если не проходят фильтры
  const recentlyUpdatedIdsRef = useRef<Map<string, number>>(new Map())
  
  // Для отслеживания предыдущего пути
  const prevLocationRef = useRef<string | null>(null)

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

  useEffect(() => {
    if (bulkHandoffOpen) {
      setHandoffClientsLoading(true)
      getAvailableClients()
        .then(setHandoffClients)
        .catch(() => setHandoffClients([]))
        .finally(() => setHandoffClientsLoading(false))
      setBulkHandoffClientId('')
    }
  }, [bulkHandoffOpen])

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
  const normalizeOpsModeList = useCallback(
    (value: any): CandidateOpsMode[] =>
      normalizeArrayFilter(value).filter(
        (item): item is CandidateOpsMode =>
          item === 'in_work' || item === 'later' || item === 'no_reply_needed' || item === 'escalated'
      ),
    [normalizeArrayFilter]
  )

  const applyViewFilters = useCallback(
    (filters: Record<string, any> | undefined) => {
      setQ(filters?.q ?? '')
      setStageFilter(normalizeArrayFilter(filters?.stage ?? filters?.stages))
      setVacancyFilter(normalizeArrayFilter(filters?.vacancy ?? filters?.vacancyId ?? filters?.vacancies))
      setManagerFilter(normalizeArrayFilter(filters?.managers ?? filters?.manager))
      setStatusReasonFilter(normalizeReasonList(filters?.statusReason ?? filters?.status_reason))
      setTagsFilter(normalizeArrayFilter(filters?.tags))
      setDocsStatusFilter(normalizeArrayFilter(filters?.docsStatus))
      setDocsOrderedFilter(normalizeArrayFilter(filters?.docsOrdered))
      setPreferredChannelFilter(normalizeArrayFilter(filters?.preferredChannel ?? filters?.preferred_contact))
      setInPolandFilter(normalizeArrayFilter(filters?.inPoland ?? filters?.in_poland))
      setOpsModeFilter(normalizeOpsModeList(filters?.opsMode ?? filters?.ops_mode))
      setPolandBasisFilter(normalizeArrayFilter(filters?.polandBasis ?? filters?.poland_basis))
      setTrailerTypesFilter(normalizeArrayFilter(filters?.trailerTypes ?? filters?.trailer_types))
      setCreatedRange(normalizeRangeFilter(filters?.createdRange ?? filters?.created_at))
      setFirstContactRange(normalizeRangeFilter(filters?.firstContactRange ?? filters?.first_contact_at))
      setDocsValidRange(normalizeRangeFilter(filters?.docsValidRange ?? filters?.docs_valid_from))
      setDocsHasFilesFilter(normalizeArrayFilter(filters?.docsHasFiles ?? filters?.docs_has_files))
      setTextFilters(normalizeTextFilterState(filters?.textFilters))
    },
    [normalizeArrayFilter, normalizeRangeFilter, normalizeReasonList, normalizeTextFilterState, normalizeOpsModeList]
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
  const { role, isClientTenant } = usePermissions()
  const isClientRole = isClientTenant && role !== 'administrator'

  const stageOptions = useMemo(() => {
    const base = meta?.order || meta?.codes || []
    if (!meta?.meta) return base
    if (!isClientRole) return base
    return base.filter((code) => meta.meta?.[code]?.visible_for_client)
  }, [meta, isClientRole])
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
  const resolveManagerLabel = useCallback(
    (candidate: UICandidate): string | null => {
      const managerId = getCandidateManagerId(candidate)
      const mappedLabel = managerId ? managerLabelMap.get(managerId) ?? null : null
      const isUuidLike = (value: string | null | undefined): boolean =>
        typeof value === 'string' &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
      const managerObj = (candidate as any)?.manager
      const objLabel =
        managerObj && typeof managerObj === 'object'
          ? managerObj.label || managerObj.full_name || managerObj.name || managerObj.email || managerObj.short_id || null
          : null
      const rawLabel =
        candidate.manager_name ||
        candidate.manager_short ||
        objLabel ||
        (typeof managerObj === 'string' ? managerObj : null)

      if (rawLabel && managerId && (rawLabel === managerId || isUuidLike(rawLabel))) {
        const recruiterId = (candidate as any)?.recruiter_id ? String((candidate as any).recruiter_id) : null
        if (recruiterId && recruiterId === managerId) {
          const recruiterLabel =
            (candidate as any)?.recruiter_name ||
            (candidate as any)?.recruiter_short ||
            null
          if (recruiterLabel && !isUuidLike(String(recruiterLabel))) {
            return String(recruiterLabel)
          }
        }
        return mappedLabel || null
      }
      if (rawLabel) return rawLabel
      return mappedLabel || null
    },
    [managerLabelMap]
  )
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
  const opsModeLabelMap = useMemo<Record<CandidateOpsMode, string>>(
    () => ({
      in_work: t('app.candidate_card.ops_mode.in_work'),
      later: t('app.candidate_card.ops_mode.later'),
      no_reply_needed: t('app.candidate_card.ops_mode.no_reply_needed'),
      escalated: t('app.candidate_card.ops_mode.escalated'),
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
      is_favorite: t('app.candidates.table.columns.is_favorite'),
      tags: t('app.candidates.table.columns.tags'),
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
    'tags',
    'is_favorite',
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

  // Дефолтные ширины колонок (в пикселях) - константа, не нужно мемоизировать
  const DEFAULT_COLUMN_WIDTHS: Record<string, number> = {
    name: 200,
    email: 180,
    phone: 150,
    citizenship: 140,
    vacancy: 180,
    short: 120,
    manager: 160,
    stage: 160,
    created: 140,
    firstContact: 140,
    preferredChannel: 150,
    inPoland: 120,
    polandBasis: 220,
    trailerTypes: 160,
    reasons: 200,
    is_favorite: 80,
    docsStatus: 140,
    docsOrdered: 140,
    docsValid: 140,
    docsFiles: 120,
  }

  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(() => {
    try {
      const raw = localStorage.getItem(columnWidthsStorageKey)
      const parsed = raw ? JSON.parse(raw) : {}
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return { ...DEFAULT_COLUMN_WIDTHS, ...parsed }
      }
    } catch {
      /* ignore malformed storage */
    }
    return { ...DEFAULT_COLUMN_WIDTHS }
  })

  useEffect(() => {
    try {
      localStorage.setItem(columnWidthsStorageKey, JSON.stringify(columnWidths))
    } catch {
      /* ignore storage errors */
    }
  }, [columnWidths, columnWidthsStorageKey])

  // Порядок колонок для drag & drop
  const [columnOrder, setColumnOrder] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(columnOrderStorageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed
        }
      }
    } catch {
      /* ignore malformed storage */
    }
    return [...DEFAULT_COLUMN_ORDER]
  })

  useEffect(() => {
    try {
      localStorage.setItem(columnOrderStorageKey, JSON.stringify(columnOrder))
    } catch {
      /* ignore storage errors */
    }
  }, [columnOrder, columnOrderStorageKey])

  // Получаем видимые колонки в правильном порядке
  const orderedVisibleColumns = useMemo(() => {
    const visible = columnOrder.filter((key) => visibleCols[key])
    // Добавляем колонки, которые есть в visibleCols, но отсутствуют в columnOrder
    const missing = Object.keys(visibleCols)
      .filter((key) => visibleCols[key] && !columnOrder.includes(key))
    return [...visible, ...missing]
  }, [columnOrder, visibleCols])

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // Нужно переместить мышь на 8px перед началом drag
      },
    })
  )

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const oldIndex = columnOrder.indexOf(String(active.id))
    const newIndex = columnOrder.indexOf(String(over.id))

    if (oldIndex === -1 || newIndex === -1) return

    const newOrder = [...columnOrder]
    const [removed] = newOrder.splice(oldIndex, 1)
    newOrder.splice(newIndex, 0, removed)

    setColumnOrder(newOrder)
  }, [columnOrder])

  // Состояние для ресайза колонок
  const [resizingColumn, setResizingColumn] = useState<string | null>(null)
  const [resizeStartX, setResizeStartX] = useState<number>(0)
  const [resizeStartWidth, setResizeStartWidth] = useState<number>(0)

  // Обработчик начала ресайза
  const handleResizeStart = useCallback((columnKey: string, startX: number) => {
    setResizingColumn(columnKey)
    setResizeStartX(startX)
    setResizeStartWidth(columnWidths[columnKey] || DEFAULT_COLUMN_WIDTHS[columnKey] || 150)
  }, [columnWidths])

  // Обработчик ресайза
  useEffect(() => {
    if (!resizingColumn) return

    const handleMouseMove = (e: MouseEvent) => {
      const diff = e.clientX - resizeStartX
      const newWidth = Math.max(80, resizeStartWidth + diff) // Минимальная ширина 80px
      setColumnWidths((prev) => ({
        ...prev,
        [resizingColumn]: newWidth,
      }))
    }

    const handleMouseUp = () => {
      setResizingColumn(null)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [resizingColumn, resizeStartX, resizeStartWidth])

  // Функция для получения ширины колонки
  const getColumnWidth = useCallback((columnKey: string): number => {
    return columnWidths[columnKey] || DEFAULT_COLUMN_WIDTHS[columnKey] || 150
  }, [columnWidths])

  // Компонент для ресайза колонки
  const ColumnResizeHandle = ({ columnKey }: { columnKey: string }) => {
    if (columnKey === 'checkbox') return null // Первая колонка не ресайзится
    return (
      <div
        className="absolute right-0 top-0 h-full w-1 cursor-col-resize bg-transparent hover:bg-brand-400 transition-colors z-20"
        onMouseDown={(e) => {
          e.preventDefault()
          e.stopPropagation()
          handleResizeStart(columnKey, e.clientX)
        }}
        title={t('app.candidates.table.resize_column') || 'Изменить ширину колонки'}
      />
    )
  }


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
      className="flex items-center gap-1 font-semibold text-left text-slate-700 hover:text-brand-600 transition-colors group relative"
      onClick={() => handleSortChange(key)}
      title={
        sortKey === key
          ? t('app.candidates.table.sort_by', { values: { column: label, dir: sortDir === 'asc' ? t('common.sort.asc') : t('common.sort.desc') } }) || `Сортировка по ${label} (${sortDir === 'asc' ? '↑' : '↓'})`
          : t('app.candidates.table.click_to_sort', { values: { column: label } }) || `Кликните для сортировки по ${label}`
      }
    >
      <span>{label}</span>
      {sortKey === key && (
        <span className="text-xs text-brand-600 font-bold" title={sortDir === 'asc' ? t('common.sort.asc') || 'По возрастанию' : t('common.sort.desc') || 'По убыванию'}>
          {sortDir === 'asc' ? '▲' : '▼'}
        </span>
      )}
      {sortKey !== key && (
        <span className="text-xs text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">↕</span>
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
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            {t('app.candidates.filters.date_from')}
            <input
              type="date"
              className="input"
              value={range.from ?? ''}
              onChange={(e) => onChange({ ...range, from: e.currentTarget.value || null })}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
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
              className="btn-secondary btn-xs"
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
              className="btn-secondary btn-xs"
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
  const scrollContainerRef = useRef<HTMLElement | null>(null)
  const outerScrollRef = useRef<HTMLElement | null>(null)
  const virtuosoRef = useRef<VirtuosoHandle | null>(null)
  const { can } = usePermissions()
  const canManage = can('candidates.manage')
  const [recentlyOpenedId, setRecentlyOpenedId] = useState<string | null>(null)
  const restoredScrollRef = useRef(false)
  const restoreAttemptsRef = useRef(0)
  const pendingFullReloadRef = useRef(false)
  const loadDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retriedEmptyItemsRef = useRef(false)
  const loadIdRef = useRef(0)
  const loadInProgressRef = useRef(false)
  const lastSuccessfulListRef = useRef<{ items: UICandidate[]; total: number } | null>(null)
  const [tableHeight, setTableHeight] = useState<number | undefined>(undefined)
  const tableContainerRef = useRef<HTMLDivElement | null>(null)
  const QUICK_FILTERS_STORAGE_KEY = 'hf:candidates:quickFiltersExpanded'
  const [quickFiltersExpanded, setQuickFiltersExpanded] = useState(() => {
    try {
      return window.localStorage.getItem(QUICK_FILTERS_STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })
  useEffect(() => {
    try {
      window.localStorage.setItem(QUICK_FILTERS_STORAGE_KEY, quickFiltersExpanded ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [quickFiltersExpanded])
  const getScrollContainer = useCallback((): HTMLElement | null => {
    return scrollContainerRef.current
  }, [])

  useEffect(() => {
    setViewMode(searchParams.get('view') === 'kanban' ? 'kanban' : 'table')
  }, [searchParams])

  // Обновляем список при возврате на страницу (например, после редактирования кандидата)
  useEffect(() => {
    if (items.length > 0) return
    try {
      const raw = localStorage.getItem(listStorageKey)
      if (!raw) return
      const parsed = JSON.parse(raw)
      if (!parsed || typeof parsed !== 'object') return
      if (typeof parsed.total === 'number' && parsed.total === 0) return
      // Do not restore broken state: total>0 but items empty
      if (typeof parsed.total === 'number' && parsed.total > 0 && (!Array.isArray(parsed.items) || parsed.items.length === 0)) return
      const ts = typeof parsed.timestamp === 'number' ? parsed.timestamp : 0
      if (Date.now() - ts > CANDIDATE_CACHE_TTL_MS) return
      if (!Array.isArray(parsed.items)) return
      const cachedEntry = {
        items: parsed.items as UICandidate[],
        total: typeof parsed.total === 'number' ? parsed.total : parsed.items.length,
        timestamp: ts,
      }
      candidateListCache.set(cacheKey, cachedEntry)
      setItems(cachedEntry.items)
      setTotal(cachedEntry.total)
      setErrorText(null)
      setLoading(false)
    } catch (err) {
      console.warn('[Candidates] failed to restore list cache', err)
    }
  }, [cacheKey, listStorageKey, items.length])

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

          const restoredOpsMode = normalizeOpsModeList(parsed.opsMode ?? parsed.ops_mode)
          setOpsModeFilter(restoredOpsMode)
          applied = applied || restoredOpsMode.length > 0

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

          const restoredHandoffStatus = typeof parsed.handoffStatus === 'string' ? parsed.handoffStatus.trim() : ''
          if (['none', 'pending', 'accepted', 'returned'].includes(restoredHandoffStatus)) {
            setHandoffStatusFilter(restoredHandoffStatus)
            applied = applied || true
          }
          const restoredContactAttempts = typeof parsed.contactAttempts === 'string' ? parsed.contactAttempts.trim() : ''
          if (['none', 'some', 'limit_reached'].includes(restoredContactAttempts)) {
            setContactAttemptsFilter(restoredContactAttempts)
            applied = applied || true
          }
          const restoredProcessorId = typeof parsed.processorId === 'string' ? parsed.processorId.trim() : ''
          if (restoredProcessorId) {
            setProcessorFilter(restoredProcessorId)
            applied = applied || true
          }

          const restoredTextFilters = normalizeTextFilterState(parsed.textFilters)
          setTextFilters(restoredTextFilters)
          applied = applied || Object.values(restoredTextFilters).some((value) => value.trim().length > 0)

          const restoredIsFavorite = typeof parsed.isFavorite === 'boolean' ? parsed.isFavorite : (parsed.is_favorite === true ? true : null)
          setIsFavoriteFilter(restoredIsFavorite)
          applied = applied || restoredIsFavorite === true

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
  }, [filterStorageKey, normalizeArrayFilter, normalizeRangeFilter, normalizeReasonList, normalizeTextFilterState, normalizeOpsModeList])

  // Deep-link from Dashboard pivot: apply URL params (stage, vacancy_id, status_reason, citizenship)
  useEffect(() => {
    if (!filtersHydrated) return
    const stageParam = searchParams.get('stage')
    const vacancyParam = searchParams.get('vacancy_id') || searchParams.get('vacancy')
    const reasonParam = searchParams.get('status_reason')
    const citizenshipParam = searchParams.get('citizenship')
    const hasDeepLink = stageParam || vacancyParam || reasonParam || citizenshipParam
    if (!hasDeepLink) return
    if (stageParam) setStageFilter(normalizeArrayFilter([stageParam]))
    if (vacancyParam) setVacancyFilter(normalizeArrayFilter([vacancyParam]))
    if (reasonParam) setStatusReasonFilter(normalizeReasonList([reasonParam]))
    if (citizenshipParam) setTextFilter('citizenship', String(citizenshipParam).trim())
  }, [filtersHydrated, searchParams, normalizeArrayFilter, normalizeReasonList, setTextFilter])

  useEffect(() => {
    if (!canManage) {
      setChecked({})
      setBulkOpen(false)
      setBulkManagerOpen(false)
      setBulkVacancyOpen(false)
      setBulkTagsOpen(false)
      setBulkDeleteOpen(false)
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
          tags: tagsFilter,
          docsStatus: docsStatusFilter,
          docsOrdered: docsOrderedFilter,
          preferredChannel: preferredChannelFilter,
          inPoland: inPolandFilter,
          opsMode: opsModeFilter,
          polandBasis: polandBasisFilter,
          trailerTypes: trailerTypesFilter,
          createdRange,
          firstContactRange,
          docsValidRange,
          docsHasFiles: docsHasFilesFilter,
          handoffStatus: handoffStatusFilter,
          contactAttempts: contactAttemptsFilter,
          processorId: processorFilter,
          textFilters,
          isFavorite: isFavoriteFilter,
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
    tagsFilter,
    docsStatusFilter,
    docsOrderedFilter,
    preferredChannelFilter,
    inPolandFilter,
    opsModeFilter,
    polandBasisFilter,
    trailerTypesFilter,
    createdRange,
    firstContactRange,
    docsValidRange,
    docsHasFilesFilter,
    handoffStatusFilter,
    contactAttemptsFilter,
    processorFilter,
    textFilters,
    isFavoriteFilter,
    sortKey,
    sortDir,
  ])

  const enrichedItems = useMemo<AugmentedCandidate[]>(
    () => {
      const result = items.map((item) => {
        const rawExtra = extractExtraObject(
          (item as any)?.extra_summary ?? (item as any)?.extra ?? item.extra ?? null
        )
        const extra = normalizeCandidateExtra(rawExtra)
        const reasonData = deriveReasonData(item, rawExtra)
        return {
          ...item,
          __docsMeta: deriveDocsMeta(item),
          __extra: extra,
          __reasonCodes: reasonData.codes,
          __reasonFallbackLabels: reasonData.fallbackLabels,
        }
      })
      console.info('[Candidates] enrichedItems computed: items.length=', items.length, 'enrichedItems.length=', result.length)
      return result
    },
    [items, deriveReasonData]
  )

  const filterSnapshot = useMemo<CandidateFilterSnapshot>(
    () => ({
      stage: stageFilter,
      vacancy: vacancyFilter,
      manager: managerFilter,
      statusReasons: statusReasonFilter,
      tags: tagsFilter,
      docsStatus: docsStatusFilter,
      docsOrdered: docsOrderedFilter,
      createdRange,
      firstContactRange,
      docsValidRange,
      preferredChannels: preferredChannelFilter,
      polandPresence: inPolandFilter,
      opsModes: opsModeFilter,
      polandBasis: polandBasisFilter,
      trailerTypes: trailerTypesFilter,
      docsHasFiles: docsHasFilesFilter,
      query: q,
      textFilters,
      isFavorite: isFavoriteFilter,
    }),
    [
      stageFilter,
      vacancyFilter,
      managerFilter,
      statusReasonFilter,
      tagsFilter,
      docsStatusFilter,
      docsOrderedFilter,
      createdRange,
      firstContactRange,
      docsValidRange,
      preferredChannelFilter,
      inPolandFilter,
      opsModeFilter,
      polandBasisFilter,
      trailerTypesFilter,
      docsHasFilesFilter,
      q,
      textFilters,
      isFavoriteFilter,
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

    const debugFiltering = source.length > 0 && source.length === 670 && Object.keys(snapshot).some(key => {
      const val = (snapshot as any)[key]
      if (Array.isArray(val)) return val.length > 0
      if (typeof val === 'object' && val !== null) {
        if ('from' in val || 'to' in val) return Boolean((val as any).from || (val as any).to)
        return Object.keys(val).length > 0
      }
      return Boolean(val)
    })

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
        if (debugFiltering) console.warn('[Candidates] Filtered by createdRange:', { item_id: item.id, created_at: item.created_at, range: snapshot.createdRange })
        return false
      }

      if (!matchesDateRange(item.__extra.firstContactAt, snapshot.firstContactRange)) {
        if (debugFiltering) console.warn('[Candidates] Filtered by firstContactRange:', { item_id: item.id, firstContactAt: item.__extra.firstContactAt, range: snapshot.firstContactRange })
        return false
      }

      if (!matchesDateRange(item.__docsMeta.validFrom, snapshot.docsValidRange)) {
        if (debugFiltering) console.warn('[Candidates] Filtered by docsValidRange:', { item_id: item.id, validFrom: item.__docsMeta.validFrom, range: snapshot.docsValidRange })
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
      if (snapshot.opsModes.length) {
        const mode = item.__extra.opsMode
        if (!mode || !snapshot.opsModes.includes(mode)) {
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

      if (snapshot.isFavorite !== null && snapshot.isFavorite !== undefined) {
        const isFavorite = item.is_favorite ?? false
        if (snapshot.isFavorite !== isFavorite) {
          if (debugFiltering) console.warn('[Candidates] Filtered by isFavorite:', { item_id: item.id, item_is_favorite: item.is_favorite, filter_isFavorite: snapshot.isFavorite })
          return false
        }
      }

      if (snapshot.tags.length > 0) {
        const candidateTags = Array.isArray(item.tags) ? item.tags : []
        // Кандидат должен иметь хотя бы один из выбранных тегов
        if (!snapshot.tags.some(tag => candidateTags.includes(tag))) {
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

  const stagePresence = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные
    const set = new Set<string>(stageFilter)
    enrichedItems.forEach((item) => {
      if (item.stage) set.add(String(item.stage))
    })
    return set
  }, [enrichedItems, stageFilter])

  const stageFilterOptions = useMemo(
    () =>
      stageOptions
        .filter((code) => stagePresence.has(code))
        .map((code) => ({
          value: code,
          label: translateStageLabel(t, code, stageLabelMap[code] || code),
        })),
    [stageOptions, stagePresence, stageLabelMap, t]
  )

  const filteredItems = useMemo(() => {
    const filtered = filterCandidates(enrichedItems, filterSnapshot)
    // Добавляем недавно обновленных кандидатов, чтобы они оставались видимыми даже если не проходят фильтры
    const now = Date.now()
    const recentlyUpdated = new Set<string>()
    recentlyUpdatedIdsRef.current.forEach((timestamp, candidateId) => {
      // Кандидат считается недавно обновленным в течение 60 секунд после обновления
      if (now - timestamp < 60000) {
        recentlyUpdated.add(candidateId)
      } else {
        // Удаляем устаревшие записи
        recentlyUpdatedIdsRef.current.delete(candidateId)
      }
    })
    
    // Если есть недавно обновленные кандидаты, добавляем их в список, если их там еще нет
    if (recentlyUpdated.size > 0) {
      const filteredIds = new Set(filtered.map(item => String(item.id)))
      const toAdd = enrichedItems.filter(item => {
        const id = String(item.id)
        return recentlyUpdated.has(id) && !filteredIds.has(id)
      })
      if (toAdd.length > 0) {
        // Добавляем недавно обновленных кандидатов в начало списка
        const result = [...toAdd, ...filtered]
        console.info('[Candidates] filteredItems computed: enrichedItems.length=', enrichedItems.length, 'filtered.length=', filtered.length, 'result.length=', result.length)
        return result
      }
    }
    
    if (enrichedItems.length > 0 && filtered.length === 0) {
      console.warn('[Candidates] ALL items filtered out! Active filters:', JSON.stringify(filterSnapshot, null, 2))
      // Также попробуем понять, какой именно фильтр блокирует
      const sampleItem = enrichedItems[0]
      const sampleIsFavorite = sampleItem.is_favorite ?? false
      console.warn('[Candidates] Sample item for debugging:', {
        id: sampleItem.id,
        stage: sampleItem.stage,
        vacancy_id: (sampleItem as any)?.vacancy_id || (sampleItem as any)?.vacancy?.id,
        manager_id: (sampleItem as any)?.manager_id || (sampleItem as any)?.manager?.id,
        tags: sampleItem.tags,
        is_favorite: sampleItem.is_favorite,
        is_favorite_raw: sampleItem.is_favorite,
        filter_isFavorite: filterSnapshot.isFavorite,
        matches_isFavorite: filterSnapshot.isFavorite === null || filterSnapshot.isFavorite === undefined || filterSnapshot.isFavorite === sampleIsFavorite,
        created_at: sampleItem.created_at,
        __docsMeta: sampleItem.__docsMeta,
        __extra: sampleItem.__extra,
      })
      // Проверим, сколько элементов имеют is_favorite === true
      const favoriteCount = enrichedItems.filter(item => (item.is_favorite ?? false) === true).length
      console.warn('[Candidates] Items with is_favorite=true:', favoriteCount, 'out of', enrichedItems.length)
    }
    console.info('[Candidates] filteredItems computed: enrichedItems.length=', enrichedItems.length, 'filtered.length=', filtered.length)
    return filtered
  }, [enrichedItems, filterSnapshot, filterCandidates])

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
        case 'manager': {
          cmp = compareStrings(resolveManagerLabel(a) || '', resolveManagerLabel(b) || '')
          break
        }
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
    console.info('[Candidates] displayedItems computed: filteredItems.length=', filteredItems.length, 'sorted.length=', sorted.length)
    return sorted
  }, [filteredItems, sortKey, sortDir])

  const selectedCandidate = useMemo(
    () => (selectedCandidateId ? displayedItems.find((c) => c.id === selectedCandidateId) ?? null : null),
    [displayedItems, selectedCandidateId],
  )

  const loadPreviewReminders = useCallback(
    async (candidateId: string) => {
      setPreviewRemindersLoading(true)
      setPreviewRemindersError(null)
      try {
        const res = await listReminders({ entityType: 'candidate', entityId: candidateId, status: ['pending', 'new', 'overdue'] })
        const list = Array.isArray(res?.items) ? (res.items as ReminderRecord[]) : []
        setPreviewReminders(list)
      } catch (err: any) {
        setPreviewRemindersError(err?.response?.data?.detail ?? err?.message ?? 'Failed to load reminders')
        setPreviewReminders([])
      } finally {
        setPreviewRemindersLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    if (!selectedCandidateId) {
      setPreviewReminders([])
      setPreviewRemindersError(null)
      setPreviewRemindersLoading(false)
      return
    }
    void loadPreviewReminders(selectedCandidateId)
  }, [loadPreviewReminders, selectedCandidateId])

  const handleCreatePreviewReminder = useCallback(async () => {
    if (!selectedCandidateId || !previewReminderTitle || !previewReminderDueAt) return
    try {
      const due = new Date(previewReminderDueAt)
      const remindAt = new Date(due.getTime() - previewReminderOffset * 60 * 1000)
      await createReminder({
        title: previewReminderTitle,
        description: '',
        type: 'custom',
        entity_type: 'candidate',
        entity_id: selectedCandidateId,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: 'normal',
      })
      setPreviewReminderTitle('')
      setPreviewReminderDueAt(new Date(due.getTime() + 60 * 60 * 1000).toISOString().slice(0, 16))
      await loadPreviewReminders(selectedCandidateId)
      setPreviewTab('focus')
    } catch (err: any) {
      setPreviewRemindersError(err?.response?.data?.detail ?? err?.message ?? 'Failed to create reminder')
    }
  }, [loadPreviewReminders, previewReminderDueAt, previewReminderOffset, previewReminderTitle, selectedCandidateId])

  const handleCompletePreviewReminder = useCallback(
    async (id: string) => {
      try {
        await completeReminder(id)
        if (selectedCandidateId) await loadPreviewReminders(selectedCandidateId)
      } catch (err: any) {
        setPreviewRemindersError(err?.response?.data?.detail ?? err?.message ?? 'Failed to complete reminder')
      }
    },
    [loadPreviewReminders, selectedCandidateId],
  )

  const allVisibleSelected =
    displayedItems.length > 0 && displayedItems.every((candidate) => checked[candidate.id])

  const vacancyFilterOptions = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные, чтобы опции не пропадали при применении фильтров
    const map = new Map<string, string>()
    const ensure = (value: string | null, label: string) => {
      if (!value || map.has(value)) return
      map.set(value, label || t('app.candidates.labels.untitled'))
    }
    enrichedItems.forEach((item) => {
      const id = getCandidateVacancyId(item)
      if (!id) return
      const title =
        (item as any)?.vacancy?.title ||
        (item as any)?.vacancy_title ||
        vacancyLabelMap.get(id) ||
        t('app.candidates.labels.untitled')
      ensure(id, title)
    })
    // Добавляем выбранные значения, даже если их нет в текущих items (для сохранения выбора)
    vacancyFilter.forEach((value) => ensure(value, vacancyLabelMap.get(value) || value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, vacancyFilter, vacancyLabelMap, t])

  const managerFilterOptions = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные, чтобы опции не пропадали при применении фильтров
    const map = new Map<string, string>()
    const ensure = (value: string | null, label: string) => {
      if (!value || map.has(value)) return
      map.set(value, label || '—')
    }
    enrichedItems.forEach((item) => {
      const id = getCandidateManagerId(item)
      if (!id) return
      const label = resolveManagerLabel(item) || id
      ensure(id, label)
    })
    // Добавляем выбранные значения, даже если их нет в текущих items (для сохранения выбора)
    managerFilter.forEach((value) => ensure(value, managerLabelMap.get(value) || value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, managerFilter, managerLabelMap, resolveManagerLabel])

  const reasonFilterOptions = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные
    const present = new Set<string>(statusReasonFilter)
    enrichedItems.forEach((item) => {
      item.__reasonCodes.forEach((code) => present.add(code))
    })
    const options = reasonOptions
      .filter((option) => present.has(option.code))
      .map((option) => ({
        value: option.code,
        label: `${option.label} (${option.stageLabel})`,
      }))
    return options
  }, [enrichedItems, reasonOptions, statusReasonFilter])

  const docsStatusPresence = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные
    const set = new Set<string>(docsStatusFilter)
    enrichedItems.forEach((item) => set.add(item.__docsMeta.readinessKey))
    return set
  }, [enrichedItems, docsStatusFilter])

  const allDocsStatusOptions = useMemo(
    () =>
      Object.entries(DOC_READINESS_META).map(([value, meta]) => ({
        value,
        label: t(meta.labelKey),
      })),
    [t]
  )

  const docsStatusFilterOptions = useMemo(
    () => allDocsStatusOptions.filter((option) => docsStatusPresence.has(option.value)),
    [allDocsStatusOptions, docsStatusPresence]
  )

  const docsOrderPresence = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные
    const set = new Set<string>(docsOrderedFilter)
    enrichedItems.forEach((item) => set.add(item.__docsMeta.isOrdered ? 'ordered' : 'not_ordered'))
    return set
  }, [enrichedItems, docsOrderedFilter])

  const docsOrderFilterOptions = useMemo(
    () =>
      DOC_ORDER_FILTERS.map((option) => ({ value: option.value, label: t(option.labelKey) })).filter(
        (option) => docsOrderPresence.has(option.value)
      ),
    [docsOrderPresence, t]
  )

  const docsHasFilesOptions = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные
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
    enrichedItems.forEach((item) => ensure(item.__docsMeta.hasFiles ? 'with' : 'without'))
    docsHasFilesFilter.forEach((value) => {
      if (value === 'with' || value === 'without') ensure(value)
    })
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, docsHasFilesFilter, t])

  const preferredChannelOptions = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные
    const map = new Map<string, string>()
    const ensure = (value: string, label: string) => {
      if (map.has(value)) return
      map.set(value, label)
    }
    enrichedItems.forEach((item) => {
      const key = item.__extra.preferredContact ?? EMPTY_OPTION_VALUE
      ensure(key, preferredChannelLabelMap[key] ?? key)
    })
    preferredChannelFilter.forEach((value) => {
      ensure(value, preferredChannelLabelMap[value] ?? value)
    })
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, preferredChannelFilter, preferredChannelLabelMap])

  const inPolandOptions = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (map.has(value)) return
      map.set(value, inPolandLabelMap[value] ?? inPolandLabelMap.unknown)
    }
    enrichedItems.forEach((item) => {
      const key = item.__extra.inPoland === true ? 'yes' : item.__extra.inPoland === false ? 'no' : 'unknown'
      ensure(key)
    })
    inPolandFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, inPolandFilter, inPolandLabelMap])
  const opsModeOptions = useMemo(() => {
    const map = new Map<CandidateOpsMode, string>()
    const ensure = (value: CandidateOpsMode) => {
      if (map.has(value)) return
      map.set(value, opsModeLabelMap[value])
    }
    enrichedItems.forEach((item) => {
      if (item.__extra.opsMode) ensure(item.__extra.opsMode)
    })
    opsModeFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, opsModeFilter, opsModeLabelMap])

  const polandBasisOptions = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (map.has(value)) return
      map.set(value, value === EMPTY_OPTION_VALUE ? t('common.labels.not_available') : getPolandBasisLabel(value))
    }
    enrichedItems.forEach((item) => {
      ensure(item.__extra.polandStayBasis ?? EMPTY_OPTION_VALUE)
    })
    polandBasisFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, polandBasisFilter, getPolandBasisLabel, t])

  const trailerTypesOptions = useMemo(() => {
    // Используем все enrichedItems, а не отфильтрованные
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (!value || map.has(value)) return
      map.set(value, getTrailerTypeLabel(value))
    }
    enrichedItems.forEach((item) => {
      item.__extra.trailerTypes.forEach((code) => ensure(code))
    })
    trailerTypesFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, getTrailerTypeLabel, trailerTypesFilter])

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

  // Функция для рендеринга содержимого заголовка колонки
  const renderColumnHeaderContent = useCallback((columnKey: string) => {
    switch (columnKey) {
      case 'checkbox':
        return (
          <div className="flex items-center justify-center">
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
              className="cursor-pointer w-4 h-4"
              title={allVisibleSelected ? (t('app.candidates.table.deselect_all') || 'Снять выделение со всех') : (t('app.candidates.table.select_all') || 'Выделить все видимые')}
              aria-label={allVisibleSelected ? (t('app.candidates.table.deselect_all') || 'Снять выделение со всех') : (t('app.candidates.table.select_all') || 'Выделить все видимые')}
            />
          </div>
        )
      case 'name':
        return (
          <>
            {renderSortButton(columnLabelMap.name, 'name')}
            {renderTextFilterMenu('name', t('app.candidates.filters.name_menu'), t('app.candidates.filters.name_placeholder'))}
          </>
        )
      case 'email':
        return (
          <>
            {renderSortButton(columnLabelMap.email, 'email')}
            {renderTextFilterMenu('email', t('app.candidates.filters.email_menu'), t('app.candidates.filters.email_placeholder'))}
          </>
        )
      case 'phone':
        return (
          <>
            {renderSortButton(columnLabelMap.phone, 'phone')}
            {renderTextFilterMenu('phone', t('app.candidates.filters.phone_menu'), t('app.candidates.filters.phone_placeholder'))}
          </>
        )
      case 'citizenship':
        return (
          <>
            {renderSortButton(columnLabelMap.citizenship, 'citizenship')}
            {renderTextFilterMenu('citizenship', t('app.candidates.filters.citizenship_menu'), t('app.candidates.filters.citizenship_placeholder'))}
          </>
        )
      case 'vacancy':
        return (
          <>
            {renderSortButton(columnLabelMap.vacancy, 'vacancy')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.vacancy_menu')}
              options={vacancyFilterOptions}
              selected={vacancyFilter}
              onChange={setVacancyFilter}
            />
          </>
        )
      case 'short':
        return (
          <>
            {renderSortButton(columnLabelMap.short, 'short_id')}
            {renderTextFilterMenu('short', t('app.candidates.filters.short_menu'), t('app.candidates.filters.short_placeholder'))}
          </>
        )
      case 'manager':
        return (
          <>
            {renderSortButton(columnLabelMap.manager, 'manager')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.manager_menu')}
              options={managerFilterOptions}
              selected={managerFilter}
              onChange={setManagerFilter}
            />
          </>
        )
      case 'stage':
        return (
          <>
            {renderSortButton(columnLabelMap.stage, 'stage')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.stage_menu')}
              options={stageFilterOptions}
              selected={stageFilter}
              onChange={setStageFilter}
            />
          </>
        )
      case 'created':
        return (
          <>
            {renderSortButton(columnLabelMap.created, 'created_at')}
            {renderRangeMenu(
              t('app.candidates.filters.created_menu'),
              createdRange,
              (next) => setCreatedRange(next),
              () => setCreatedRange({ from: null, to: null })
            )}
          </>
        )
      case 'firstContact':
        return (
          <>
            {renderSortButton(columnLabelMap.firstContact, 'first_contact')}
            {renderRangeMenu(
              t('app.candidates.filters.first_contact_menu'),
              firstContactRange,
              (next) => setFirstContactRange(next),
              () => setFirstContactRange({ from: null, to: null })
            )}
          </>
        )
      case 'preferredChannel':
        return (
          <>
            {renderSortButton(columnLabelMap.preferredChannel, 'preferred_channel')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.preferred_channel_menu')}
              options={preferredChannelOptions}
              selected={preferredChannelFilter}
              onChange={setPreferredChannelFilter}
            />
          </>
        )
      case 'inPoland':
        return (
          <>
            {renderSortButton(columnLabelMap.inPoland, 'in_poland')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.in_poland_menu')}
              options={inPolandOptions}
              selected={inPolandFilter}
              onChange={setInPolandFilter}
            />
          </>
        )
      case 'polandBasis':
        return (
          <>
            {renderSortButton(columnLabelMap.polandBasis, 'poland_basis')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.poland_basis_menu')}
              options={polandBasisOptions}
              selected={polandBasisFilter}
              onChange={setPolandBasisFilter}
            />
          </>
        )
      case 'trailerTypes':
        return (
          <>
            {renderSortButton(columnLabelMap.trailerTypes, 'trailer_types')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.trailer_types_menu')}
              options={trailerTypesOptions}
              selected={trailerTypesFilter}
              onChange={setTrailerTypesFilter}
            />
          </>
        )
      case 'reasons':
        return (
          <>
            {renderSortButton(columnLabelMap.reasons, 'reasons')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.reason_menu')}
              options={reasonFilterOptions}
              selected={statusReasonFilter}
              onChange={setStatusReasonFilter}
            />
          </>
        )
      case 'is_favorite':
        return (
          <>
            {renderSortButton(columnLabelMap.is_favorite, 'is_favorite')}
          </>
        )
      case 'tags': {
        // Собираем все уникальные теги из всех кандидатов
        const allTags = new Set<string>()
        enrichedItems.forEach(item => {
          const tags = Array.isArray(item.tags) ? item.tags : []
          tags.forEach(tag => {
            if (tag && typeof tag === 'string') {
              allTags.add(tag.trim())
            }
          })
        })
        const tagOptions = Array.from(allTags).sort().map(tag => ({
          value: tag,
          label: tag,
        }))
        return (
          <>
            {renderSortButton(columnLabelMap.tags, 'tags')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.tags_menu')}
              options={tagOptions}
              selected={tagsFilter}
              onChange={setTagsFilter}
            />
          </>
        )
      }
      case 'docsStatus':
        return (
          <>
            {renderSortButton(columnLabelMap.docsStatus, 'docs_status')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.docs_status_menu')}
              options={docsStatusFilterOptions}
              selected={docsStatusFilter}
              onChange={setDocsStatusFilter}
            />
          </>
        )
      case 'docsOrdered':
        return (
          <>
            {renderSortButton(columnLabelMap.docsOrdered, 'docs_ordered_at')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.docs_order_menu')}
              options={docsOrderFilterOptions}
              selected={docsOrderedFilter}
              onChange={setDocsOrderedFilter}
            />
          </>
        )
      case 'docsValid':
        return (
          <>
            {renderSortButton(columnLabelMap.docsValid, 'docs_valid_from')}
            {renderRangeMenu(
              t('app.candidates.filters.docs_valid_menu'),
              docsValidRange,
              (next) => setDocsValidRange(next),
              () => setDocsValidRange({ from: null, to: null })
            )}
          </>
        )
      case 'docsFiles':
        return (
          <>
            {renderSortButton(columnLabelMap.docsFiles, 'docs_has_files')}
            <ColumnFilterMenu
              title={t('app.candidates.filters.docs_files_menu')}
              options={docsHasFilesOptions}
              selected={docsHasFilesFilter}
              onChange={setDocsHasFilesFilter}
            />
          </>
        )
      default:
        return null
    }
  }, [
    allVisibleSelected,
    canManage,
    displayedItems,
    setChecked,
    t,
    renderSortButton,
    columnLabelMap,
    renderTextFilterMenu,
    renderRangeMenu,
    vacancyFilterOptions,
    vacancyFilter,
    setVacancyFilter,
    managerFilterOptions,
    managerFilter,
    setManagerFilter,
    stageFilterOptions,
    stageFilter,
    setStageFilter,
    createdRange,
    setCreatedRange,
    firstContactRange,
    setFirstContactRange,
    preferredChannelOptions,
    preferredChannelFilter,
    setPreferredChannelFilter,
    inPolandOptions,
    inPolandFilter,
    setInPolandFilter,
    polandBasisOptions,
    polandBasisFilter,
    setPolandBasisFilter,
    trailerTypesOptions,
    trailerTypesFilter,
    setTrailerTypesFilter,
    reasonFilterOptions,
    statusReasonFilter,
    setStatusReasonFilter,
    docsStatusFilterOptions,
    docsStatusFilter,
    setDocsStatusFilter,
    docsOrderFilterOptions,
    docsOrderedFilter,
    setDocsOrderedFilter,
    docsValidRange,
    setDocsValidRange,
    docsHasFilesOptions,
    docsHasFilesFilter,
    setDocsHasFilesFilter,
  ])

  // Компонент для перетаскиваемого заголовка колонки
  const DraggableColumnHeader = ({ columnKey, isSticky, stickyLeft }: {
    columnKey: string
    isSticky?: boolean
    stickyLeft?: string
  }) => {
    const {
      attributes,
      listeners,
      setNodeRef,
      transform,
      transition,
      isDragging,
    } = useSortable({ id: columnKey, disabled: columnKey === 'checkbox' })

    const style = {
      transform: CSS.Transform.toString(transform),
      transition,
      opacity: isDragging ? 0.5 : 1,
    }

    const className = clsx(
      'px-4 py-3 border-r border-slate-200',
      isSticky ? 'sticky bg-slate-50 z-[25]' : 'relative',
      columnKey === 'checkbox' && 'cursor-default',
      columnKey !== 'checkbox' && !isDragging && 'cursor-move hover:bg-slate-100'
    )

    const dynamicStyle: React.CSSProperties = {
      ...style,
      width: columnKey === 'checkbox' ? '56px' : `${getColumnWidth(columnKey)}px`,
      minWidth: columnKey === 'checkbox' ? '56px' : `${getColumnWidth(columnKey)}px`,
      maxWidth: columnKey === 'checkbox' ? '56px' : `${getColumnWidth(columnKey)}px`,
    }

    if (isSticky) {
      dynamicStyle.position = 'sticky'
      dynamicStyle.top = 0
      dynamicStyle.zIndex = 25 // Выше, чем thead (15), чтобы заголовки были поверх
      dynamicStyle.backgroundColor = '#f9fafb' // bg-slate-50 - обязательно для sticky, чтобы скрыть прокручиваемый контент
      if (stickyLeft) {
        // Преобразуем строку "0" в "0px" или оставляем как есть, если уже есть единицы измерения
        dynamicStyle.left = stickyLeft === '0' ? '0px' : stickyLeft
      } else if (columnKey === 'checkbox') {
        // Для checkbox явно устанавливаем left: 0px
        dynamicStyle.left = '0px'
      }
    }

    const content = renderColumnHeaderContent(columnKey)

    if (columnKey === 'checkbox') {
      // Для checkbox sticky классы уже применены в className выше
      return (
        <th className={className} style={dynamicStyle}>
          {content}
        </th>
      )
    }

    return (
      <th
        ref={setNodeRef}
        className={className}
        style={dynamicStyle}
        {...attributes}
        {...listeners}
      >
        <div className="flex items-center justify-between gap-2">
          {content}
        </div>
        <ColumnResizeHandle columnKey={columnKey} />
      </th>
    )
  }

  const visibleColumnsCount = 1 + Object.values(visibleCols).filter(Boolean).length

  // load managers catalog (array or {items})
  useEffect(() => {
    (async () => {
      try{
        const { data } = await api.get('/catalogs/managers')
        const list: any[] = Array.isArray(data) ? data : (data?.items || [])
        const mapped: ManagerItem[] = list.map((it:any) => ({
          id: it?.id || it?.user_id || it?.uid || it?.uuid,
          name: it?.label || it?.full_name || it?.name || it?.email || '—',
        }))
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

  const load = useCallback(async (options?: { force?: boolean; allowCache?: boolean }) => {
    if (!filtersHydrated) return
    // Временно всегда перезагружаем список с сервера (без раннего выхода по кешу),
    // чтобы скоуп кандидатов и маскирование соответствовали актуальной backend-логике.
    const allowCache = options?.allowCache ?? true
    const forceReload = options?.force ?? true
    const cached = allowCache ? candidateListCache.get(cacheKey) : undefined
    // Do not treat cache as fresh when total>0 but items empty (broken API response)
    const cacheValid = cached && (cached.total === 0 || cached.items.length > 0)
    const cacheIsFresh = cacheValid
      ? Date.now() - cached.timestamp < CANDIDATE_CACHE_TTL_MS && cached.total !== 0
      : false
    const willRefetch = !cacheIsFresh || forceReload
    pendingFullReloadRef.current = willRefetch

    if (cacheValid && cached.total !== 0) {
      setItems(cached.items)
      setTotal(cached.total)
      setErrorText(null)
      setLoading(false)
      if (cacheIsFresh && !forceReload) return
    }

    if (loadInProgressRef.current) {
      console.debug('[Candidates] load() called but already in progress, skipping')
      return
    }
    loadInProgressRef.current = true
    loadIdRef.current += 1
    const myLoadId = loadIdRef.current
    console.debug('[Candidates] load() started: loadId=', myLoadId, 'force=', forceReload, 'allowCache=', allowCache)
    setLoading(true)
    setErrorText(null)
    try{
      let nextOffset = 0
      let accumulated: UICandidate[] = []
      let totalCount: number | null = null
      let keepFetching = true

      while (keepFetching) {
        const params: Record<string, any> = {
          limit,
          offset: nextOffset,
          order_by: 'created_at',
          desc: true,
          compact: true,
          q: q || undefined,
          stage: stageFilter.length === 1 ? stageFilter[0] : undefined,
          stages: stageFilter.length > 0 ? stageFilter.join(',') : undefined,
          status_reason: statusReasonFilter.length > 0 ? statusReasonFilter : undefined,
          tags: tagsFilter.length > 0 ? tagsFilter : undefined,
          vacancy_id: vacancyFilter.length > 0 ? vacancyFilter[0] : undefined,
          vacancy: vacancyFilter.length > 0 ? vacancyFilter.join(',') : undefined,
          manager_id: managerFilter.length === 1 ? managerFilter[0] : undefined,
          documents_ordered: docsOrderedFilter.length === 1 ? docsOrderedFilter[0] : undefined,
          handoff_status: handoffStatusFilter || undefined,
          contact_attempts: contactAttemptsFilter || undefined,
          processor_id: processorFilter || undefined,
        }
        if (createdRange.from) params.created_from = createdRange.from
        if (createdRange.to) params.created_to = createdRange.to
        if (isFavoriteFilter != null) params.is_favorite = isFavoriteFilter
        const scopeTid = currentTenantId ?? me?.tenant_id
        if (scopeTid) params.scope_tenant_id = typeof scopeTid === 'string' ? scopeTid : String(scopeTid)
        const { data } = await getWithFallbacks<ListResp>('/candidates', params, scopeTid ?? undefined)

        const dataAny = data as any
        let batch: UICandidate[] =
          Array.isArray(dataAny?.items)
            ? dataAny.items
            : Array.isArray(dataAny?.data)
              ? dataAny.data
              : Array.isArray((dataAny?.data as any)?.items)
                ? (dataAny.data as { items: UICandidate[] }).items
                : Array.isArray(dataAny?.results)
                  ? dataAny.results
                  : Array.isArray(dataAny)
                    ? dataAny
                    : []
        if (batch.length === 0 && typeof dataAny?.total === 'number' && dataAny.total > 0 && typeof dataAny?.items === 'string') {
          try {
            const parsed = JSON.parse(dataAny.items as string) as UICandidate[]
            if (Array.isArray(parsed)) batch = parsed
          } catch {
            /* ignore */
          }
        }
        if (typeof dataAny?.total === 'number' && batch.length === 0 && dataAny.total > 0) {
          console.warn('[Candidates] response total=', dataAny.total, 'but items batch empty; keys=', dataAny ? Object.keys(dataAny) : [], 'sample=', dataAny?.items != null ? typeof dataAny.items : 'missing')
        }
        // Ignore responses with 1 item when we requested limit=100 (e.g. from Dashboard limit=1 poll)
        const effectiveBatch =
          limit > 1 && typeof dataAny?.total === 'number' && dataAny.total > 1 && batch.length === 1
            ? []
            : batch
        if (effectiveBatch.length === 0 && batch.length === 1) {
          console.warn('[Candidates] ignoring response with 1 item (requested limit=', limit, ', total=', dataAny?.total, ')')
        }

        if (effectiveBatch.length > 0) {
          console.info('[Candidates] batch received', effectiveBatch.length, 'offset', nextOffset, 'total', dataAny?.total)
        }
        accumulated = accumulated.concat(effectiveBatch)
        if (typeof dataAny?.total === 'number') {
          totalCount = dataAny.total
        }

        nextOffset += effectiveBatch.length === 0 && batch.length === 1 ? limit : effectiveBatch.length
        if (myLoadId === loadIdRef.current && accumulated.length > 0) {
          setItems(accumulated)
          setTotal(totalCount ?? accumulated.length)
        }
        const ignoredOneItem = effectiveBatch.length === 0 && batch.length === 1
        const reachedEnd = ignoredOneItem
          ? false
          : effectiveBatch.length < limit ||
            (totalCount !== null && accumulated.length >= totalCount) ||
            effectiveBatch.length === 0
        keepFetching = !reachedEnd
      }

      const finalTotal = totalCount ?? accumulated.length
      // Do not persist broken state (total>0 but no items) so we never restore it
      const persistOk = finalTotal === 0 || accumulated.length > 0
      if (persistOk) {
        const cachedEntry = { items: accumulated, total: finalTotal, timestamp: Date.now() }
        candidateListCache.set(cacheKey, cachedEntry)
        try {
          localStorage.setItem(listStorageKey, JSON.stringify(cachedEntry))
        } catch {
          /* ignore storage errors */
        }
      }
      console.info('[Candidates] load finished: myLoadId=', myLoadId, 'currentLoadId=', loadIdRef.current, 'accumulated.length=', accumulated.length, 'finalTotal=', finalTotal)
      if (myLoadId === loadIdRef.current) {
        console.info('[Candidates] applying state (myLoadId matches): items=', accumulated.length, 'total=', finalTotal)
        setTotal(finalTotal)
        if (accumulated.length > 0) {
          setItems(accumulated)
        } else if (finalTotal === 0) {
          setItems([])
        }
      } else {
        console.warn('[Candidates] NOT applying state: myLoadId', myLoadId, '!= current', loadIdRef.current)
      }
      if (accumulated.length > 0) {
        lastSuccessfulListRef.current = { items: accumulated, total: finalTotal }
        const toApply = accumulated.slice()
        const tot = finalTotal
        console.info('[Candidates] scheduling queueMicrotask: items=', toApply.length, 'total=', tot)
        queueMicrotask(() => {
          console.info('[Candidates] queueMicrotask executing: applying items=', toApply.length, 'total=', tot)
          setItems(toApply)
          setTotal(tot)
        })
      }
    } catch (e: any) {
      const errorInfo = getErrorInfo(e)
      const formattedMessage = formatErrorForDisplay(e, {
        fallback: t('app.candidates.messages.load_failed') || 'Не удалось загрузить список кандидатов',
        includeStatusCode: true,
      })
      if (myLoadId === loadIdRef.current) {
        setErrorText(formattedMessage)
        setItems([])
        setTotal(0)
      }
      console.error('[Candidates] Load error:', errorInfo)
    } finally {
      loadInProgressRef.current = false
      if (myLoadId === loadIdRef.current) setLoading(false)
      if (willRefetch) {
        restoredScrollRef.current = false
      }
      pendingFullReloadRef.current = false
    }
  }, [
    filtersHydrated,
    cacheKey,
    listStorageKey,
    limit,
    t,
    q,
    currentTenantId,
    me?.tenant_id,
    stageFilter,
    statusReasonFilter,
    tagsFilter,
    vacancyFilter,
    managerFilter,
    docsOrderedFilter,
    handoffStatusFilter,
    contactAttemptsFilter,
    processorFilter,
    createdRange,
    firstContactRange,
    docsValidRange,
    isFavoriteFilter,
  ])

  // После окончания загрузки: если в state пусто, но последняя успешная загрузка принесла данные — применить из ref
  const prevLoadingRef = useRef(loading)
  useEffect(() => {
    const wasLoading = prevLoadingRef.current
    prevLoadingRef.current = loading
    if (wasLoading && !loading) {
      console.info('[Candidates] loading finished effect: items.length=', items.length, 'total=', total)
      const pending = lastSuccessfulListRef.current
      console.info('[Candidates] lastSuccessfulListRef:', pending ? `items=${pending.items.length} total=${pending.total}` : 'null')
      if (pending && pending.items.length > 0 && items.length === 0) {
        console.info('[Candidates] applying from ref: items=', pending.items.length, 'total=', pending.total)
        setItems(pending.items)
        setTotal(pending.total)
      }
    }
  }, [loading, items.length, total])

  // Отслеживаем изменения items для диагностики
  useEffect(() => {
    console.info('[Candidates] items state changed: length=', items.length, 'total=', total)
  }, [items.length, total])

  // Автоматически сбрасываем фильтр isFavorite, если он блокирует все элементы
  useEffect(() => {
    if (isFavoriteFilter === true && enrichedItems.length > 0) {
      const favoriteCount = enrichedItems.filter(item => (item.is_favorite ?? false) === true).length
      if (favoriteCount === 0) {
        console.warn('[Candidates] Auto-resetting isFavorite filter: filter is true but no favorites found')
        setIsFavoriteFilter(null)
      }
    }
  }, [isFavoriteFilter, enrichedItems.length])

  // Если total > 0 но items пустой — один раз принудительно перезапросить после короткой задержки
  // (даём первой загрузке время завершиться и обновить state, чтобы не гонять две загрузки)
  useEffect(() => {
    if (loading || items.length > 0 || total <= 0 || retriedEmptyItemsRef.current) return
    retriedEmptyItemsRef.current = true
    const t = setTimeout(() => {
      void load({ force: true, allowCache: false })
    }, 500)
    return () => clearTimeout(t)
  }, [total, items.length, loading, load])

  // Обновляем список при возврате на страницу (например, после редактирования кандидата)
  useEffect(() => {
    const currentPath = location.pathname
    const prevPath = prevLocationRef.current
    
    // Если вернулись на страницу списка с другой страницы (например, с карточки кандидата)
    if (prevPath && prevPath !== currentPath && currentPath === '/app/candidates') {
      // Проверяем, был ли недавно обновлен кандидат (в течение последних 10 секунд)
      let shouldFullReload = true
      try {
        const updateData = localStorage.getItem('hf:candidate-updated')
        if (updateData) {
          const data = JSON.parse(updateData)
          if (data && data.candidateId && data.timestamp && Date.now() - data.timestamp < 10000) {
            // Если кандидат был обновлен недавно, обновим только его, а не весь список
            // Это предотвратит исчезновение кандидата, если он изменил статус
            shouldFullReload = false
          }
        }
      } catch {
        /* ignore */
      }
      
      if (shouldFullReload) {
        // Инвалидируем кэш и обновляем список
        candidateListCache.delete(cacheKey)
        // Также очищаем localStorage кэш
        try {
          localStorage.removeItem(listStorageKey)
        } catch {
          /* ignore */
        }
        void load({ force: true, allowCache: false })
      }
      // Если shouldFullReload === false, обновление кандидата произойдет через handleCandidateUpdate
    }
    
    prevLocationRef.current = currentPath
  }, [location.pathname, cacheKey, listStorageKey, load])

  // Слушаем события обновления кандидата (из карточки кандидата или других вкладок)
  useEffect(() => {
    const handleCandidateUpdate = (event?: CustomEvent<{ candidateId: string }>) => {
      const candidateId = event?.detail?.candidateId
      
      if (!candidateId) return
      
      // Защита от множественных одновременных обновлений одного кандидата
      const now = Date.now()
      const lastUpdate = lastUpdateTimeRef.current.get(candidateId) || 0
      if (updateInProgressRef.current.has(candidateId) || (now - lastUpdate < 500)) {
        return // Игнорируем, если обновление уже идет или было недавно
      }
      
      updateInProgressRef.current.add(candidateId)
      lastUpdateTimeRef.current.set(candidateId, now)
      
      // Инвалидируем кэш для этого кандидата
      candidateListCache.delete(cacheKey)
      try {
        localStorage.removeItem(listStorageKey)
      } catch {
        /* ignore */
      }
      
      // Отмечаем кандидата как недавно обновленного (в течение 60 секунд он будет виден, даже если не проходит фильтры)
      recentlyUpdatedIdsRef.current.set(candidateId, now)
      
      // Принудительно перезагружаем список для получения актуальных данных
      // Это гарантирует, что все данные будут синхронизированы и нормализованы одинаково
      setTimeout(() => {
        load({ force: true, allowCache: false })
          .then(() => {
            updateInProgressRef.current.delete(candidateId)
          })
          .catch(() => {
            updateInProgressRef.current.delete(candidateId)
            // Игнорируем ошибки при перезагрузке
          })
      }, 300)
    }

    // Слушаем custom event
    const eventHandler = (e: Event) => {
      const customEvent = e as CustomEvent<{ candidateId: string }>
      handleCandidateUpdate(customEvent)
    }
    window.addEventListener('candidate-updated', eventHandler)
    
    // Слушаем изменения localStorage (для кросс-вкладок)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'hf:candidate-updated' && e.newValue) {
        try {
          const data = JSON.parse(e.newValue)
          if (data && data.candidateId) {
            handleCandidateUpdate(new CustomEvent('candidate-updated', { detail: { candidateId: data.candidateId } }))
          }
        } catch {
          /* ignore */
        }
      }
    }
    window.addEventListener('storage', handleStorageChange)
    
    // Проверяем localStorage при монтировании (на случай, если обновление произошло пока страница была неактивна)
    let checkTimeout: ReturnType<typeof setTimeout> | null = null
    const checkForUpdates = () => {
      // Debounce проверки, чтобы не вызывать слишком часто
      if (checkTimeout) {
        clearTimeout(checkTimeout)
      }
      checkTimeout = setTimeout(() => {
        try {
          const updateData = localStorage.getItem('hf:candidate-updated')
          if (updateData) {
            const data = JSON.parse(updateData)
            // Обновляем, если событие произошло недавно (в течение последних 10 секунд)
            if (data && data.candidateId && data.timestamp && Date.now() - data.timestamp < 10000) {
              if (!updateInProgressRef.current.has(data.candidateId)) {
                handleCandidateUpdate(new CustomEvent('candidate-updated', { detail: { candidateId: data.candidateId } }))
              }
            }
          }
        } catch {
          /* ignore */
        }
      }, 1000) // Debounce 1 секунда
    }
    
    // Проверяем при фокусе окна (с debounce)
    const handleFocus = () => {
      checkForUpdates()
    }
    window.addEventListener('focus', handleFocus)
    
    // Проверяем сразу при монтировании (с задержкой, чтобы не конфликтовать с начальной загрузкой)
    const initialCheckTimeout = setTimeout(checkForUpdates, 3000)
    
    return () => {
      window.removeEventListener('candidate-updated', eventHandler)
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener('focus', handleFocus)
    }
  }, [cacheKey, listStorageKey, load])

  const persistScrollState = useCallback(
    (candidateId?: string) => {
      try {
        const container = getScrollContainer()
        const containerTop = container?.scrollTop ?? null
        const outer = outerScrollRef.current
        const outerTop = (outer?.scrollTop ?? window.scrollY) || 0
        const idx = candidateId ? displayedItems.findIndex((it) => it.id === candidateId) : -1
        const payload = {
          top: outerTop,
          id: candidateId ?? null,
          ts: Date.now(),
          scrollContainerTop: containerTop,
          index: idx >= 0 ? idx : null,
          windowTop: outerTop,
        }
        localStorage.setItem(scrollKey, JSON.stringify(payload))
      } catch {/* ignore storage errors */}
    },
    [displayedItems, getScrollContainer, scrollKey]
  )

  const restoreScrollState = useCallback(() => {
    if (restoredScrollRef.current) return
    restoredScrollRef.current = true
    try {
      const raw = localStorage.getItem(scrollKey)
      if (!raw) return
      const parsed = JSON.parse(raw)
      if (!parsed || typeof parsed !== 'object') return
      const ts = typeof parsed.ts === 'number' ? parsed.ts : 0
      if (Date.now() - ts > SCROLL_STATE_TTL_MS) {
        // Удаляем устаревшее состояние
        try { localStorage.removeItem(scrollKey) } catch {/* ignore */}
        return
      }

      const top = typeof parsed.top === 'number' ? parsed.top : 0
      const containerTop = typeof parsed.scrollContainerTop === 'number' ? parsed.scrollContainerTop : null
      const windowTop = typeof parsed.windowTop === 'number' ? parsed.windowTop : null
      const savedIndex = typeof parsed.index === 'number' ? parsed.index : null
      const id = typeof parsed.id === 'string' ? parsed.id : null
      if (id) setRecentlyOpenedId(id)

      const attemptRestore = () => {
        const container = getScrollContainer()
        if (windowTop !== null && windowTop > 0) {
          const outer = outerScrollRef.current
          if (outer) {
            outer.scrollTo({ top: windowTop, behavior: 'auto' })
          } else {
            window.scrollTo({ top: windowTop, behavior: 'auto' })
          }
        }
        const rowSelector = id ? `[data-candidate-id="${id}"]` : null
        const rowEl = rowSelector ? document.querySelector(rowSelector) as HTMLElement | null : null
        const targetRow = rowEl?.closest('tr') as HTMLElement | null ?? rowEl
        if (targetRow) {
          targetRow.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'auto' })
          return true
        }

        // если строка не отрендерена, попробуем виртуализатором проскроллить по индексу
        if (virtuosoRef.current) {
          const idx =
            savedIndex !== null
              ? savedIndex
              : id
                ? displayedItems.findIndex((item) => item.id === id)
                : -1
          if (idx >= 0) {
            virtuosoRef.current.scrollToIndex({ index: idx, align: 'center' })
            return true
          }
        }

        if (container && containerTop !== null) {
          container.scrollTo({ top: containerTop, behavior: 'auto' })
          return true
        }

        return top === 0 ? false : true
      }

      const finalize = () => {
        // НЕ удаляем сохраненное состояние, чтобы оно сохранилось для следующего возврата
        // Удалим его только если это устаревшее состояние (уже проверено выше)
        restoreAttemptsRef.current = 0
      }

      const tryLater = () => {
        restoreAttemptsRef.current += 1
        restoredScrollRef.current = false
        if (restoreAttemptsRef.current >= RESTORE_SCROLL_MAX_ATTEMPTS) {
          finalize()
          restoredScrollRef.current = true
          return
        }
        // give virtuoso time to render more rows
        window.setTimeout(() => restoreScrollState(), 150)
      }

      requestAnimationFrame(() => {
        const ok = attemptRestore()
        if (ok) {
          finalize()
          restoredScrollRef.current = true
        } else {
          tryLater()
        }
      })
    } catch {/* ignore malformed storage */}
  }, [displayedItems, getScrollContainer, scrollKey])

  const handleCandidateOpen = useCallback(
    (id: string) => {
      setRecentlyOpenedId(id)
      persistScrollState(id)
    },
    [persistScrollState]
  )
  const handleCandidateHover = useCallback((id: string) => {
    void prefetchCandidate(id)
  }, [])

  useEffect(() => {
    if (!filtersHydrated) return
    load()
  }, [filtersHydrated, load]) // первый запуск и при смене tenant (me)

  // дебаунс загрузки при изменении фильтров/поиска, чтобы не спамить API
  useEffect(() => {
    if (!filtersHydrated) return
    if (loadDebounceRef.current) {
      clearTimeout(loadDebounceRef.current)
    }
    loadDebounceRef.current = window.setTimeout(() => {
      load()
    }, 250)
    return () => {
      if (loadDebounceRef.current) clearTimeout(loadDebounceRef.current)
    }
  }, [
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
    createdRange.from,
    createdRange.to,
    firstContactRange.from,
    firstContactRange.to,
    docsValidRange.from,
    docsValidRange.to,
    docsHasFilesFilter,
    handoffStatusFilter,
    contactAttemptsFilter,
    processorFilter,
    textFilters.name,
    textFilters.email,
    textFilters.phone,
    textFilters.citizenship,
    textFilters.short,
    sortKey,
    sortDir,
  ])

  useEffect(() => {
    const el = document.querySelector(APP_SCROLL_SELECTOR) as HTMLElement | null
    outerScrollRef.current = el
    if (el) {
      const h = el.clientHeight
      if (h > 0) setTableHeight(Math.max(900, h - 40))
    }
  }, [])

  // Сбрасываем флаг восстановления при изменении пути (возврат к списку)
  // И читаем returnFromCandidateId из location.state (при возврате из CandidateCard)
  useEffect(() => {
    const isOnCandidatesList = location.pathname === '/app/candidates' || location.pathname.startsWith('/app/candidates?')
    if (isOnCandidatesList) {
      restoredScrollRef.current = false
      restoreAttemptsRef.current = 0
      const returnId = (location.state as { returnFromCandidateId?: string } | null)?.returnFromCandidateId
      if (returnId) setRecentlyOpenedId(returnId)
    }
  }, [location.pathname, location.state])

  useEffect(() => {
    if (!filtersHydrated) return
    if (loading) return
    restoreScrollState()
  }, [filtersHydrated, loading, restoreScrollState, items.length, recentlyOpenedId])

  // Состояние для клавиатурной навигации
  const [focusedRowIndex, setFocusedRowIndex] = useState<number | null>(null)
  const focusedRowRef = useRef<HTMLTableRowElement | null>(null)

  // Расширенная клавиатурная навигация
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // Проверяем, не находится ли фокус в поле ввода (input, textarea, select)
      const target = e.target as HTMLElement
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT'
      const isContentEditable = target.isContentEditable || target.closest('[contenteditable]')

      // Ctrl/Cmd + K - фокус на поиск
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k' && !e.shiftKey) {
        e.preventDefault()
        searchRef.current?.focus()
        return
      }

      // Игнорируем горячие клавиши если фокус в поле ввода
      if (isInput || isContentEditable) {
        // Разрешаем Ctrl+A для выбора всех только в текстовых полях
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a' && (target.tagName === 'INPUT' && (target as HTMLInputElement).type !== 'checkbox')) {
          return
        }
        // Разрешаем Escape для закрытия модальных окон
        if (e.key === 'Escape') {
          return
        }
      }

      // Escape - сброс выбора и фокуса
      if (e.key === 'Escape' && !isInput && !isContentEditable) {
        e.preventDefault()
        setChecked({})
        setFocusedRowIndex(null)
        focusedRowRef.current = null
        return
      }

      // Ctrl/Cmd + A - выбрать все видимые кандидаты
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a' && !isInput && !isContentEditable) {
        e.preventDefault()
        if (!canManage) return
        const newChecked: Record<string, boolean> = {}
        displayedItems.forEach((candidate) => {
          newChecked[candidate.id] = true
        })
        setChecked(newChecked)
        return
      }

      // Клавиатурная навигация работает только если нет фокуса в полях ввода
      if (isInput || isContentEditable) return

      // Стрелки вверх/вниз - навигация по строкам
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault()
        const currentIndex = focusedRowIndex !== null ? focusedRowIndex : -1
        let nextIndex: number

        if (e.key === 'ArrowDown') {
          nextIndex = currentIndex < displayedItems.length - 1 ? currentIndex + 1 : displayedItems.length - 1
        } else {
          nextIndex = currentIndex > 0 ? currentIndex - 1 : 0
        }

        setFocusedRowIndex(nextIndex)
        // Прокручиваем к выбранной строке
        if (virtuosoRef.current && nextIndex >= 0 && nextIndex < displayedItems.length) {
          virtuosoRef.current.scrollToIndex({ index: nextIndex, align: 'center', behavior: 'smooth' })
        }
        return
      }

      // Space или Enter - выбрать/отменить выбор кандидата
      if ((e.key === ' ' || e.key === 'Enter') && focusedRowIndex !== null && focusedRowIndex >= 0 && focusedRowIndex < displayedItems.length) {
        e.preventDefault()
        const candidate = displayedItems[focusedRowIndex]
        if (candidate && canManage) {
          toggle(candidate.id)
        }
        return
      }

      // Enter на выбранном кандидате - открыть карточку
      if (e.key === 'Enter' && focusedRowIndex !== null && focusedRowIndex >= 0 && focusedRowIndex < displayedItems.length) {
        e.preventDefault()
        const candidate = displayedItems[focusedRowIndex]
        if (candidate) {
          handleCandidateOpen(candidate.id)
          navigate(`/app/candidates/${candidate.id}`)
        }
        return
      }


      // '/' - фокус на поиск (только если не в поле ввода)
      if (e.key === '/' && !isInput && !isContentEditable) {
        e.preventDefault()
        searchRef.current?.focus()
        return
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canManage, displayedItems.length, Object.keys(checked).length, focusedRowIndex])

  const toggle = useCallback((id: string) => {
    if (!canManage) return
    setChecked(s => ({ ...s, [id]: !s[id] }))
  }, [canManage])

  const allSelected = useCallback(() => {
    return items.filter(i => checked[i.id]).map(i => i.id)
  }, [items, checked])

  const [bulkOperationLoading, setBulkOperationLoading] = useState<string | null>(null) // 'stage' | 'manager' | 'vacancy' | 'handoff' | 'tags' | null

  async function doBulk(){
    const ids = allSelected()
    if (ids.length === 0 || !bulkStage) return
    const reasonOptions = meta?.reason_choices?.[bulkStage] ?? []
    if (reasonOptions.length > 0 && bulkReasons.length === 0) {
      alert(t('app.candidates.messages.reason_required'))
      return
    }
    setBulkOperationLoading('stage')
    try {
      const payload: Record<string, any> = { candidate_ids: ids, stage: bulkStage }
      if (reasonOptions.length > 0) {
        payload.status_reason = bulkReasons
      }
      const { data } = await api.post('/candidates/bulk-stage', payload)
      const results: Array<{ candidate_id?: string; ok?: boolean; error?: string }> = Array.isArray(data) ? data : []
      const failures = results.filter((item) => item && item.ok === false)
      const successes = results.filter((item) => item && item.ok === true)

      setBulkOpen(false)
      setBulkReasons([])

      if (failures.length > 0) {
        const failedIds = new Set(
          failures.map((item) => String(item?.candidate_id || '').trim()).filter(Boolean),
        )
        const nextChecked: Record<string, boolean> = {}
        for (const failedId of failedIds) {
          nextChecked[failedId] = true
        }
        setChecked(nextChecked)

        const rodoBlockedCount = failures.filter((item) =>
          String(item?.error || '').toLowerCase().includes('rodo must be sent'),
        ).length
        const parseErrorObject = (raw: unknown): Record<string, any> | null => {
          if (raw && typeof raw === 'object') return raw as Record<string, any>
          if (typeof raw !== 'string') return null
          const trimmed = raw.trim()
          if (!trimmed.startsWith('{')) return null
          try {
            const parsed = JSON.parse(trimmed)
            return parsed && typeof parsed === 'object' ? (parsed as Record<string, any>) : null
          } catch {
            return null
          }
        }
        const handoffDocsFailures = failures.filter((item) => {
          const parsed = parseErrorObject(item?.error)
          if (String(parsed?.code || '') === 'handoff_docs_incomplete') return true
          return String(item?.error || '').toLowerCase().includes('handoff_docs_incomplete')
        })
        if (rodoBlockedCount > 0) {
          alert(
            t('app.candidates.messages.bulk_stage_rodo_blocked', {
              values: { rodo: rodoBlockedCount, total: failures.length },
            }),
          )
        } else if (handoffDocsFailures.length > 0) {
          const firstParsed = parseErrorObject(handoffDocsFailures[0]?.error)
          const missingFromFirst = Array.isArray(firstParsed?.missing_types)
            ? firstParsed?.missing_types.map((code: any) => String(code || '').trim()).filter(Boolean)
            : []
          const missingLabels = missingFromFirst
            .map((code: string) => t(`admin.documents.types.${code}`, { defaultValue: code }))
            .join(', ')
          alert(
            t('app.candidates.messages.bulk_stage_handoff_docs_blocked', {
              values: {
                docs: handoffDocsFailures.length,
                total: failures.length,
                missing: missingLabels || '—',
              },
            }),
          )
        } else {
          alert(
            t('app.candidates.messages.bulk_stage_partial', {
              values: { failed: failures.length, total: ids.length },
            }),
          )
        }
      } else {
        setChecked({})
      }

      if (successes.length > 0) {
        const now = Date.now()
        successes.forEach((item) => {
          const cid = String(item?.candidate_id || '').trim()
          if (cid) recentlyUpdatedIdsRef.current.set(cid, now)
        })

        // Инвалидируем кэш перед обновлением
        candidateListCache.delete(cacheKey)
        try {
          localStorage.removeItem(listStorageKey)
        } catch {
          /* ignore */
        }
        await load({ force: true, allowCache: false })
      }
    } catch (e: any) {
      const errorMessage = formatErrorForDisplay(e, {
        fallback: t('app.candidates.messages.bulk_stage_failed') || 'Не удалось изменить этап кандидатов',
        includeStatusCode: false,
      })
      const errorInfo = getErrorInfo(e)
      console.error('[Candidates] Bulk stage update failed:', errorInfo)
      alert(errorMessage)
    } finally {
      setBulkOperationLoading(null)
    }
  }

  async function doBulkAssign(){
    const ids = allSelected()
    if (ids.length === 0 || !bulkManagerId) return
    setBulkOperationLoading('manager')
    try{
      const { data } = await api.post('/candidates/bulk-manager', {
        candidate_ids: ids,
        manager_id: bulkManagerId,
      })
      const results: Array<{ candidate_id?: string; ok?: boolean; error?: string }> = Array.isArray(data) ? data : []
      const failures = results.filter((item) => item && item.ok === false)
      const successes = results.filter((item) => item && item.ok === true)
      
      // Отмечаем успешно обновленных кандидатов как недавно обновленных
      const now = Date.now()
      successes.forEach((result) => {
        if (result.candidate_id) {
          recentlyUpdatedIdsRef.current.set(result.candidate_id, now)
        }
      })
      
      // Также отмечаем все ID из списка (на случай, если API не вернул детали)
      ids.forEach((id) => {
        recentlyUpdatedIdsRef.current.set(id, now)
      })
      
      if (failures.length) {
        const labelById = new Map(items.map((c) => [c.id, `${c.first_name} ${c.last_name}`.trim() || c.short_id || c.id]))
        const details = failures
          .map((f) => {
            const name = f.candidate_id ? (labelById.get(f.candidate_id) || f.candidate_id) : ''
            return `${name}: ${f.error || 'failed'}`
          })
          .join('\n')
        const errorMessage = `${t('app.candidates.messages.bulk_manager_partial', {
          values: { count: failures.length },
        })}\n${details}`
        console.warn('[Candidates] Bulk manager assignment partial failure:', failures)
        alert(errorMessage)
        // Все равно перезагружаем список, чтобы обновить успешно измененные кандидаты
        candidateListCache.delete(cacheKey)
        try {
          localStorage.removeItem(listStorageKey)
        } catch {
          /* ignore */
        }
        await load({ force: true, allowCache: false })
        return
      }
      setBulkManagerOpen(false); setChecked({}); setBulkManagerId(preferredManagerId)
      
      // Инвалидируем кэш перед обновлением
      candidateListCache.delete(cacheKey)
      try {
        localStorage.removeItem(listStorageKey)
      } catch {
        /* ignore */
      }
      await load({ force: true, allowCache: false })
    } catch (e:any){
      const errorMessage = formatErrorForDisplay(e, {
        fallback: t('app.candidates.messages.bulk_manager_failed') || 'Не удалось назначить менеджера',
        includeStatusCode: false,
      })
      const errorInfo = getErrorInfo(e)
      console.error('[Candidates] Bulk manager assignment failed:', errorInfo)
      alert(errorMessage)
    } finally {
      setBulkOperationLoading(null)
    }
  }

  async function doBulkAssignVacancy(){
    const ids = allSelected()
    if (ids.length === 0 || !bulkVacancyId) return
    setBulkOperationLoading('vacancy')
    try{
      const results = await Promise.allSettled(ids.map(id => api.patch(`/candidates/${id}`, { vacancy_id: bulkVacancyId })))
      const failures = results.filter(r => r.status === 'rejected')
      if (failures.length > 0) {
        const failureCount = failures.length
        const errorDetails = failures
          .map((f, idx) => {
            const candidateId = ids[idx]
            const candidate = items.find(c => c.id === candidateId)
            const name = candidate ? `${candidate.first_name} ${candidate.last_name}`.trim() || candidate.short_id || candidateId : candidateId
            const reason = f.status === 'rejected' ? (f.reason as any)?.response?.data?.detail || (f.reason as any)?.message || 'unknown error' : ''
            return `${name}: ${reason}`
          })
          .filter(Boolean)
          .join('\n')
        console.warn('[Candidates] Bulk vacancy assignment partial failure:', failures)
        alert(
          `${t('app.candidates.messages.bulk_vacancy_partial', {
            values: { count: failureCount, total: ids.length },
          }) || `Не удалось обновить вакансию для ${failureCount} из ${ids.length} кандидатов`}\n${errorDetails}`
        )
      }
      setBulkVacancyOpen(false); setChecked({}); setBulkVacancyId('')
      
      // Отмечаем успешно обновленных кандидатов как недавно обновленных
      const now = Date.now()
      const successfulIds = ids.filter((id, idx) => results[idx]?.status === 'fulfilled')
      successfulIds.forEach((id) => {
        recentlyUpdatedIdsRef.current.set(id, now)
      })
      
      // Инвалидируем кэш перед обновлением
      candidateListCache.delete(cacheKey)
      try {
        localStorage.removeItem(listStorageKey)
      } catch {
        /* ignore */
      }
      await load({ force: true, allowCache: false })
    } catch (e:any){
      const errorMessage = formatErrorForDisplay(e, {
        fallback: t('app.candidates.messages.bulk_vacancy_failed') || 'Не удалось назначить вакансию',
        includeStatusCode: false,
      })
      const errorInfo = getErrorInfo(e)
      console.error('[Candidates] Bulk vacancy assignment failed:', errorInfo)
      alert(errorMessage)
    } finally {
      setBulkOperationLoading(null)
    }
  }

  async function doBulkHandoff(){
    const ids = allSelected()
    if (ids.length === 0 || !bulkHandoffClientId) return
    setBulkOperationLoading('handoff')
    try {
      const result = await createBulkHandoff({
        candidate_ids: ids as import('../api/types').UUID[],
        client_company_id: bulkHandoffClientId as import('../api/types').UUID,
      })
      if (result.failed > 0) {
        const details = result.errors.slice(0, 5).map((e) => `${e.candidate_id}: ${e.error}`).join('\n')
        alert(
          (t('app.candidates.modals.handoff.partial', {
            values: { created: result.created, failed: result.failed, total: ids.length },
            defaultValue: `Przekazano ${result.created} z ${ids.length}. Nie udało się: ${result.failed}.`,
          }) as string) + (details ? `\n\n${details}` : '')
        )
      }
      if (result.created > 0) {
        setBulkHandoffOpen(false)
        setChecked({})
        setBulkHandoffClientId('')
        const now = Date.now()
        ids.forEach((id) => recentlyUpdatedIdsRef.current.set(id, now))
        candidateListCache.delete(cacheKey)
        try { localStorage.removeItem(listStorageKey) } catch { /* ignore */ }
        await load({ force: true, allowCache: false })
      }
    } catch (e: any) {
      const errorMessage = formatErrorForDisplay(e, {
        fallback: t('app.candidates.modals.handoff.failed', { defaultValue: 'Nie udało się przekazać do klienta' }),
        includeStatusCode: false,
      })
      alert(errorMessage)
    } finally {
      setBulkOperationLoading(null)
    }
  }

  async function doBulkTags(){
    const ids = allSelected()
    if (ids.length === 0 || !bulkTagsList.trim()) return
    const tagsToProcess = bulkTagsList.split(',').map(t => t.trim()).filter(Boolean)
    if (tagsToProcess.length === 0) return
    setBulkOperationLoading('tags')
    try{
      const results = await Promise.allSettled(ids.map(async (id) => {
        const candidate = items.find(c => c.id === id)
        const currentTags = Array.isArray(candidate?.tags) ? candidate.tags : []
        let newTags: string[]
        if (bulkTagsOperation === 'add') {
          newTags = [...new Set([...currentTags, ...tagsToProcess])].sort()
        } else {
          newTags = currentTags.filter(tag => !tagsToProcess.includes(tag))
        }
        return api.patch(`/candidates/${id}`, { tags: newTags })
      }))
      const failures = results.filter(r => r.status === 'rejected')
      if (failures.length > 0) {
        const failureCount = failures.length
        const errorDetails = failures
          .map((f, idx) => {
            const candidateId = ids[idx]
            const candidate = items.find(c => c.id === candidateId)
            const name = candidate ? `${candidate.first_name} ${candidate.last_name}`.trim() || candidate.short_id || candidateId : candidateId
            const reason = f.status === 'rejected' ? (f.reason as any)?.response?.data?.detail || (f.reason as any)?.message || 'unknown error' : ''
            return `${name}: ${reason}`
          })
          .filter(Boolean)
          .join('\n')
        console.warn('[Candidates] Bulk tags update partial failure:', failures)
        alert(
          `${t('app.candidates.messages.bulk_tags_partial', {
            values: { count: failureCount, total: ids.length },
          }) || `Не удалось обновить теги для ${failureCount} из ${ids.length} кандидатов`}\n${errorDetails}`
        )
      }
      setBulkTagsOpen(false); setChecked({}); setBulkTagsList('')
      
      // Отмечаем успешно обновленных кандидатов как недавно обновленных
      const now = Date.now()
      const successfulIds = ids.filter((id, idx) => results[idx]?.status === 'fulfilled')
      successfulIds.forEach((id) => {
        recentlyUpdatedIdsRef.current.set(id, now)
      })
      
      // Инвалидируем кэш перед обновлением
      candidateListCache.delete(cacheKey)
      try {
        localStorage.removeItem(listStorageKey)
      } catch {
        /* ignore */
      }
      await load({ force: true, allowCache: false })
    } catch (e:any){
      const errorMessage = formatErrorForDisplay(e, {
        fallback: t('app.candidates.messages.bulk_tags_failed') || 'Не удалось обновить теги',
        includeStatusCode: false,
      })
      const errorInfo = getErrorInfo(e)
      console.error('[Candidates] Bulk tags update failed:', errorInfo)
      alert(errorMessage)
    } finally {
      setBulkOperationLoading(null)
    }
  }

  async function doBulkDelete(){
    const ids = allSelected()
    if (ids.length === 0) return
    setBulkOperationLoading('delete')
    try{
      const { data: results } = await api.post('/candidates/bulk-delete', { candidate_ids: ids })
      const failures = results.filter((r: any) => !r.ok)
      if (failures.length > 0) {
        const failureCount = failures.length
        const errorDetails = failures
          .map((f: any) => {
            const candidateId = f.candidate_id
            const candidate = items.find(c => c.id === candidateId)
            const name = candidate ? `${candidate.first_name} ${candidate.last_name}`.trim() || candidate.short_id || candidateId : candidateId
            const reason = f.error || 'unknown error'
            return `${name}: ${reason}`
          })
          .filter(Boolean)
          .join('\n')
        console.warn('[Candidates] Bulk delete operation partial failure:', failures)
        alert(
          `${t('app.candidates.messages.bulk_delete_partial', {
            values: { count: failureCount, total: ids.length },
          }) || `Не удалось удалить ${failureCount} из ${ids.length} кандидатов`}\n${errorDetails}`
        )
      }
      setBulkDeleteOpen(false); setChecked({})
      // Инвалидируем кэш перед обновлением
      candidateListCache.delete(cacheKey)
      try {
        localStorage.removeItem(listStorageKey)
      } catch {
        /* ignore */
      }
      await load({ force: true, allowCache: false })
    } catch (e:any){
      const errorMessage = formatErrorForDisplay(e, {
        fallback: t('app.candidates.messages.bulk_delete_failed') || 'Не удалось удалить кандидатов',
        includeStatusCode: false,
      })
      const errorInfo = getErrorInfo(e)
      console.error('[Candidates] Bulk delete operation failed:', errorInfo)
      alert(errorMessage)
    } finally {
      setBulkOperationLoading(null)
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
    setTagsFilter([])
    setIsFavoriteFilter(null)
    setDocsStatusFilter([])
    setDocsOrderedFilter([])
    setPreferredChannelFilter([])
    setInPolandFilter([])
    setOpsModeFilter([])
    setPolandBasisFilter([])
    setTrailerTypesFilter([])
    setCreatedRange({ from: null, to: null })
    setFirstContactRange({ from: null, to: null })
    setDocsValidRange({ from: null, to: null })
    setDocsHasFilesFilter([])
    setHandoffStatusFilter('')
    setContactAttemptsFilter('')
    setProcessorFilter('')
    setTextFilters(makeEmptyTextFilters())
    setSortKey('created_at')
    setSortDir('desc')
    persistedFiltersRef.current = false
    try {
      localStorage.removeItem(filterStorageKey)
    } catch {/* ignore */}
  }

  // Reusable secondary button style for top/filter actions
  const secondaryBtn = "inline-flex items-center gap-2 px-3 py-2 rounded-md border border-slate-300 text-slate-800 bg-white hover:bg-slate-100 active:bg-slate-200 transition-colors cursor-pointer";

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
    opsModeFilter.length > 0 ||
    polandBasisFilter.length > 0 ||
    trailerTypesFilter.length > 0 ||
    docsHasFilesFilter.length > 0 ||
    !!handoffStatusFilter ||
    !!contactAttemptsFilter ||
    !!processorFilter ||
    isRangeActive(createdRange) ||
    isRangeActive(firstContactRange) ||
    isRangeActive(docsValidRange) ||
    Object.values(textFilters).some((value) => value.trim().length > 0)

  // Вычисляем высоту таблицы динамически (после определения hasFilterBadges)
  useEffect(() => {
    const updateHeight = () => {
      if (!tableContainerRef.current) return
      const container = tableContainerRef.current
      const rect = container.getBoundingClientRect()
      // Вычитаем высоту заголовка фильтров (если есть) и отступы
      const filterBadgesHeight = hasFilterBadges ? 64 : 0 // Примерная высота
      const bulkActionsHeight = canManage && Object.values(checked).some(Boolean) ? 64 : 0
      const padding = 32 // Отступы карточки (m-4 = 16px * 2)
      const headerHeight = 56 // Высота заголовка таблицы
      const calculatedHeight = rect.height - filterBadgesHeight - bulkActionsHeight - padding - headerHeight
      setTableHeight(Math.max(400, calculatedHeight))
    }
    updateHeight()
    const resizeObserver = new ResizeObserver(updateHeight)
    if (tableContainerRef.current) {
      resizeObserver.observe(tableContainerRef.current)
    }
    window.addEventListener('resize', updateHeight)
    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('resize', updateHeight)
    }
  }, [hasFilterBadges, canManage, checked])

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
    <div className="inline-flex rounded-md border border-brand-200 bg-white p-0.5 shadow-sm">
      <button
        type="button"
        className={clsx(
          'rounded px-2 py-1 text-xs font-medium transition',
          !isKanban ? 'bg-brand-600 text-white shadow-sm' : 'text-brand-700 hover:bg-brand-50'
        )}
        onClick={() => changeView('table')}
      >
        {t('app.candidates.views.table')}
      </button>
      <button
        type="button"
        className={clsx(
          'rounded px-2 py-1 text-xs font-medium transition',
          isKanban ? 'bg-brand-600 text-white shadow-sm' : 'text-brand-700 hover:bg-brand-50'
        )}
        onClick={() => changeView('kanban')}
      >
        {t('app.candidates.views.kanban')}
      </button>
    </div>
  )
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
  const HERO_STORAGE_KEY = 'hf:candidates:heroExpanded'
  const [heroExpanded, setHeroExpanded] = useState(() => {
    try {
      return window.localStorage.getItem(HERO_STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })
  useEffect(() => {
    try {
      window.localStorage.setItem(HERO_STORAGE_KEY, heroExpanded ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [heroExpanded])

  // Состояние для бокового меню
  const SIDEBAR_STORAGE_KEY = 'hf:candidates:sidebarOpen'
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    try {
      return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })
  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, sidebarOpen ? '1' : '0')
    } catch {
      /* ignore */
    }
    // Отправляем состояние в Topbar
    window.dispatchEvent(new CustomEvent('candidates-sidebar-state', { detail: { open: sidebarOpen } }))
  }, [sidebarOpen])

  // Слушаем события от Topbar
  const sidebarOpenRef = useRef(sidebarOpen)
  useEffect(() => {
    sidebarOpenRef.current = sidebarOpen
  }, [sidebarOpen])

  useEffect(() => {
    const handleToggle = (e: CustomEvent<{ open: boolean }>) => {
      setSidebarOpen(e.detail.open)
    }

    const handleRequestState = () => {
      // Используем ref для получения актуального значения
      window.dispatchEvent(new CustomEvent('candidates-sidebar-state', { detail: { open: sidebarOpenRef.current } }))
    }

    window.addEventListener('candidates-sidebar-toggle', handleToggle as EventListener)
    window.addEventListener('candidates-sidebar-request-state', handleRequestState)

    return () => {
      window.removeEventListener('candidates-sidebar-toggle', handleToggle as EventListener)
      window.removeEventListener('candidates-sidebar-request-state', handleRequestState)
    }
  }, [])

  // Закрытие контекстного меню при клике вне его и Escape
  useEffect(() => {
    if (!contextMenu) return
    const handleClick = (e: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(e.target as Node)) {
        setContextMenu(null)
      }
    }
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setContextMenu(null)
    }
    window.addEventListener('click', handleClick, true)
    window.addEventListener('contextmenu', handleClick, true)
    window.addEventListener('keydown', handleEscape)
    return () => {
      window.removeEventListener('click', handleClick, true)
      window.removeEventListener('contextmenu', handleClick, true)
      window.removeEventListener('keydown', handleEscape)
    }
  }, [contextMenu])

  const summaryHero = (
    <section className="rounded-xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-3 text-white shadow-sm">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold">{t('app.candidates.insights.title')}</h2>
          <button
            type="button"
            className="text-[10px] text-white/80 underline hover:text-white"
            onClick={() => setHeroExpanded((prev) => !prev)}
          >
            {heroExpanded ? t('common.actions.collapse') : t('common.actions.expand')}
          </button>
        </div>
        <p className="text-[10px] text-white/80 leading-tight">{t('app.candidates.insights.subtitle')}</p>
      </div>
      <div
        className={clsx(
          'mt-2 grid gap-1.5 transition-all duration-200',
          heroExpanded ? 'grid-cols-2' : 'grid-cols-2'
        )}
      >
        {insightCards.map((card) => (
          <div
            key={card.label}
            className={clsx(
              'rounded-lg border border-white/30 bg-white/10 px-2 py-1.5 shadow-inner backdrop-blur',
              !heroExpanded && 'py-1.5'
            )}
          >
            <div className="text-[9px] uppercase tracking-wide text-white/80 leading-tight">{card.label}</div>
            <div className="text-lg font-semibold leading-tight">{card.value}</div>
            {heroExpanded && <div className="text-[9px] text-white/70 leading-tight mt-0.5">{card.hint}</div>}
          </div>
        ))}
      </div>
    </section>
  )

  const visibleCandidatesCount = displayedItems.length
  const hasActiveTableFilters =
    hasFilterBadges || isFavoriteFilter === true || isFavoriteFilter === false
  const showsFilteredCount = total > 0 && visibleCandidatesCount !== total

  if (isKanban) {
    return <Pipeline />
  }

  const toggleQuickDocFilter = (statuses: string[], active: boolean) => {
    if (active) {
      setDocsStatusFilter([])
    } else {
      setDocsStatusFilter(statuses)
    }
  }

  return (
    <div className="relative flex flex-col -mx-6 -my-6" style={{ height: 'calc(100vh - 4rem)', minHeight: 0 }}>
      {/* Основной контент - таблица */}
      <div className={clsx("flex-1 transition-all duration-300 min-h-0 flex flex-col", sidebarOpen ? "mr-96" : "mr-0")}>
        <div ref={tableContainerRef} className="flex-1 min-h-0 overflow-hidden flex flex-col">
          {/* Debug: client view handoffs (only when ?debug=1, uses same auth as list) */}
          {showDebugPanel && (
            <div className="mx-4 mt-2 mb-2 p-3 rounded-lg border border-amber-200 bg-amber-50 text-sm">
              <div className="font-medium text-amber-900 mb-2">Debug: client view</div>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <button
                  type="button"
                  className="px-3 py-1.5 rounded border border-amber-400 bg-white hover:bg-amber-100 text-amber-900 disabled:opacity-50"
                  disabled={debugClientViewLoading}
                  onClick={async () => {
                    setDebugClientViewError(null)
                    setDebugClientViewLoading(true)
                    try {
                      const { data } = await api.get<Record<string, unknown>>('candidates/debug-client-view')
                      setDebugClientView(data)
                    } catch (e: any) {
                      setDebugClientViewError(e?.response?.data?.detail ?? e?.message ?? 'Request failed')
                      setDebugClientView(null)
                    } finally {
                      setDebugClientViewLoading(false)
                    }
                  }}
                >
                  {debugClientViewLoading ? '…' : 'Проверить handoffs'}
                </button>
                <button
                  type="button"
                  className="px-3 py-1.5 rounded border border-amber-600 bg-amber-500 hover:bg-amber-600 text-white disabled:opacity-50"
                  disabled={debugClientViewLoading}
                  onClick={async () => {
                    setDebugClientViewError(null)
                    setDebugClientViewLoading(true)
                    try {
                      const { data } = await api.post<{ updated?: number; message?: string }>('candidates/debug-client-view/force-two')
                      setDebugClientView(data as Record<string, unknown>)
                      load({ force: true })
                    } catch (e: any) {
                      setDebugClientViewError(e?.response?.data?.detail ?? e?.message ?? 'Request failed')
                      setDebugClientView(null)
                    } finally {
                      setDebugClientViewLoading(false)
                    }
                  }}
                >
                  Оставить 2 handoff и обновить список
                </button>
              </div>
              {debugClientViewError && <div className="text-red-600 mb-1">{debugClientViewError}</div>}
              {debugClientView && <pre className="text-xs bg-white p-2 rounded border overflow-auto max-h-32">{JSON.stringify(debugClientView, null, 2)}</pre>}
            </div>
          )}

          {/* Active filter badges */}
          {hasFilterBadges && (
            <FilterBadges
              q={q}
              textFilters={textFilters}
              stageFilter={stageFilter}
              vacancyFilter={vacancyFilter}
              managerFilter={managerFilter}
              statusReasonFilter={statusReasonFilter}
              docsStatusFilter={docsStatusFilter}
              docsOrderedFilter={docsOrderedFilter}
              preferredChannelFilter={preferredChannelFilter}
              inPolandFilter={inPolandFilter}
              opsModeFilter={opsModeFilter}
              polandBasisFilter={polandBasisFilter}
              trailerTypesFilter={trailerTypesFilter}
              createdRange={createdRange}
              firstContactRange={firstContactRange}
              docsValidRange={docsValidRange}
              docsHasFilesFilter={docsHasFilesFilter}
              handoffStatusFilter={handoffStatusFilter}
              contactAttemptsFilter={contactAttemptsFilter}
              processorFilter={processorFilter}
              stageLabelMap={stageLabelMap}
              vacancyLabelMap={vacancyLabelMap}
              managerLabelMap={managerLabelMap}
              reasonLabelMap={reasonLabelMap}
              reasonStageMap={reasonStageMap}
              preferredChannelLabelMap={preferredChannelLabelMap}
              inPolandLabelMap={inPolandLabelMap}
              opsModeLabelMap={opsModeLabelMap}
              getPolandBasisLabel={getPolandBasisLabel}
              getTrailerTypeLabel={getTrailerTypeLabel}
              docsStatusOptions={docsStatusFilterOptions}
              docsOrderFilterOptions={docsOrderFilterOptions}
              locale={locale}
              onQChange={setQ}
              onTextFilterChange={setTextFilter}
              onStageFilterChange={setStageFilter}
              onVacancyFilterChange={setVacancyFilter}
              onManagerFilterChange={setManagerFilter}
              onStatusReasonFilterChange={setStatusReasonFilter}
              onDocsStatusFilterChange={setDocsStatusFilter}
              onDocsOrderedFilterChange={setDocsOrderedFilter}
              onPreferredChannelFilterChange={setPreferredChannelFilter}
              onInPolandFilterChange={setInPolandFilter}
              onOpsModeFilterChange={setOpsModeFilter}
              onPolandBasisFilterChange={setPolandBasisFilter}
              onTrailerTypesFilterChange={setTrailerTypesFilter}
              onCreatedRangeChange={setCreatedRange}
              onFirstContactRangeChange={setFirstContactRange}
              onDocsValidRangeChange={setDocsValidRange}
              onDocsHasFilesFilterChange={setDocsHasFilesFilter}
              onHandoffStatusFilterChange={setHandoffStatusFilter}
              onContactAttemptsFilterChange={setContactAttemptsFilter}
              onProcessorFilterChange={setProcessorFilter}
            />
          )}

          {/* Bulk actions appear only when there is a selection */}
          {canManage && Object.values(checked).some(Boolean) && (
            <div className="card p-3 flex flex-wrap items-center gap-2 m-4">
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
              <button
                className="btn"
                title={t('app.candidates.bulk.handoff.title', { defaultValue: 'Przekaż wybranych do klienta' })}
                onClick={()=> setBulkHandoffOpen(true)}
              >
                {t('app.candidates.bulk.handoff.action', { defaultValue: 'Przekaż do klienta (wybrani)' })}
              </button>
              <button
                className="btn"
                title={t('app.candidates.bulk.tags.title')}
                onClick={()=>{ setBulkTagsOperation('add'); setBulkTagsList(''); setBulkTagsOpen(true) }}
              >
                {t('app.candidates.bulk.tags.action')}
              </button>
              <button
                className="btn bg-red-600 hover:bg-red-700 text-white"
                title={t('app.candidates.bulk.delete.title')}
                onClick={()=>{ setBulkDeleteOpen(true) }}
              >
                {t('app.candidates.bulk.delete.action')}
              </button>
              <div className="flex-1" />
              <button
                className="btn-secondary"
                title={t('app.candidates.bulk.clear_title')}
                onClick={()=> setChecked({})}
              >
                {t('app.candidates.bulk.clear_action')}
              </button>
            </div>
          )}

          {errorText && (
            <div className="m-4">
              <ErrorRecoveryBanner
                info={{
                  title: t('app.candidates.errors.title') || 'Ошибка загрузки',
                  detail: errorText,
                  hint: t('app.common.retry_hint', { defaultValue: 'Повторите действие или обновите страницу.' }),
                }}
                onRetry={() => void load({ force: true })}
                retryLabel={t('app.candidates.errors.retry') || 'Повторить попытку'}
              />
            </div>
          )}

          <div className="card overflow-hidden m-4 relative flex-1 min-h-0 flex flex-col">
        {loading && displayedItems.length > 0 && (
          <div className="absolute top-2 right-2 z-30 bg-white/95 backdrop-blur-sm border border-slate-200 rounded-lg px-3 py-1.5 shadow-lg">
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-brand-600"></div>
              <span className="font-medium">{t('app.candidates.table.updating') || 'Обновление...'}</span>
            </div>
          </div>
        )}
        <div className="flex-1 min-h-0 overflow-hidden">
          <TableVirtuoso
            ref={virtuosoRef}
            scrollerRef={(ref: HTMLElement | Window | null) => {
              if (ref && ref instanceof HTMLElement) scrollContainerRef.current = ref
            }}
            style={{ height: tableHeight ?? '100%', minHeight: 400 }}
            totalCount={displayedItems.length}
            data={displayedItems}
            increaseViewportBy={{ top: 400, bottom: 800 }}
            fixedHeaderContent={() => (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={orderedVisibleColumns} strategy={horizontalListSortingStrategy}>
                  <tr className="bg-slate-50 text-left">
                    <DraggableColumnHeader columnKey="checkbox" isSticky={true} stickyLeft="0" />
                    {orderedVisibleColumns.map((columnKey) => {
                      if (columnKey === 'name') {
                        return (
                          <DraggableColumnHeader key={columnKey} columnKey={columnKey} isSticky={true} stickyLeft="56px" />
                        )
                      }
                      return (
                        <DraggableColumnHeader key={columnKey} columnKey={columnKey} />
                      )
                    })}
                  </tr>
                </SortableContext>
              </DndContext>
            )}
          itemContent={(index, item) => {
            const c = item as AugmentedCandidate
            const phoneDisplay = c.phone || '—'
            const href = phoneDisplay && phoneDisplay !== '—' ? asTelHref(phoneDisplay) : undefined
            const docsMeta = c.__docsMeta
            const reasonTags = c.__reasonCodes
            const fallbackReasons = c.__reasonFallbackLabels
            const isFocused = focusedRowIndex === index
            return (
              <>
                <td className={clsx("px-4 py-3 sticky left-0 top-0 z-[5] border-r border-slate-200", isFocused ? "bg-brand-100" : "bg-white")} data-candidate-id={c.id} style={{ width: '56px', minWidth: '56px', maxWidth: '56px', position: 'sticky', left: 0, top: 0 }}>
                  <div className="flex items-center justify-center">
                    <input 
                      type="checkbox" 
                      checked={!!checked[c.id]} 
                      disabled={!canManage} 
                      onChange={()=>toggle(c.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="cursor-pointer w-4 h-4"
                      title={checked[c.id] ? (t('app.candidates.table.deselect') || 'Снять выделение') : (t('app.candidates.table.select') || 'Выделить')}
                      aria-label={t('app.candidates.table.select_candidate', {
                        values: {
                          name: (c as AugmentedCandidate).masked === true
                            ? (c.short_id ? t('app.candidates.table.masked_label_short_id', { defaultValue: 'Кандидат {short_id}', values: { short_id: c.short_id } }) : t('app.candidates.table.masked_label', { defaultValue: 'Кандидат #{id}', values: { id: (c.id ?? '').slice(0, 8) } }))
                            : `${c.first_name ?? ''} ${c.last_name ?? ''}`.trim(),
                        },
                      }) || 'Select candidate'}
                    />
                  </div>
                </td>
                {orderedVisibleColumns.map((columnKey) => {
                  if (!visibleCols[columnKey]) return null
                  
                  let cellContent: ReactNode = null
                  let stickyProps: React.CSSProperties = {}
                  
                  if (columnKey === 'name') {
                    stickyProps.position = 'sticky'
                    stickyProps.left = '56px'
                    stickyProps.top = 0
                    stickyProps.zIndex = 5
                    stickyProps.backgroundColor = '#ffffff' // bg-white
                    const candidateLabel =
                      (c as AugmentedCandidate).masked === true
                        ? (c.short_id
                            ? t('app.candidates.table.masked_label_short_id', { defaultValue: 'Кандидат {short_id}', values: { short_id: c.short_id } })
                            : t('app.candidates.table.masked_label', { defaultValue: 'Кандидат #{id}', values: { id: (c.id ?? '').slice(0, 8) } }))
                        : `${c.first_name ?? ''} ${c.last_name ?? ''}`.trim() || t('common.labels.not_available')
                    const managerName = resolveManagerLabel(c) || t('common.labels.not_available')
                    const companyName = (c as any).company_name || (c as any).__extra?.companyName || t('common.labels.not_available')
                    cellContent = (
                      <div className="flex flex-col gap-1">
                        <HoverCard
                          content={
                            <div className="space-y-2">
                              <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0">
                                  <div className="truncate text-sm font-semibold text-slate-900">{candidateLabel}</div>
                                  <div className="mt-0.5 text-xs text-slate-600">
                                    <span className="font-medium">{t('app.candidates.columns.stage', { defaultValue: 'Stage' })}:</span>{' '}
                                    <span className="text-slate-700">{String(c.stage || '—')}</span>
                                  </div>
                                </div>
                                <div className="shrink-0">
                                  <StageTag code={c.stage} />
                                </div>
                              </div>
                              <div className="grid grid-cols-1 gap-1 text-xs text-slate-700">
                                <div className="truncate">
                                  <span className="text-slate-500">{t('app.candidates.columns.manager', { defaultValue: 'Manager' })}:</span>{' '}
                                  <span className="font-medium text-slate-800">{managerName}</span>
                                </div>
                                <div className="truncate">
                                  <span className="text-slate-500">{t('app.candidates.columns.company', { defaultValue: 'Company' })}:</span>{' '}
                                  <span className="font-medium text-slate-800">{companyName}</span>
                                </div>
                              </div>
                              <div className="flex flex-wrap gap-2 pt-1">
                                <button
                                  type="button"
                                  className="btn-primary btn-xs"
                                  onClick={() => navigate(`/app/candidates/${c.id}`)}
                                >
                                  {t('common.actions.open', { defaultValue: 'Open' })}
                                </button>
                                <button
                                  type="button"
                                  className="btn-secondary btn-xs"
                                  onClick={() => navigate(`/app/candidates/${c.id}/documents`)}
                                >
                                  {t('app.nav.items.documents', { defaultValue: 'Documents' })}
                                </button>
                              </div>
                            </div>
                          }
                        >
                          <Link
                            to={`/app/candidates/${c.id}`}
                            className="font-medium text-brand-600 hover:text-brand-700 hover:underline"
                            onClick={(e) => {
                              e.preventDefault()
                              handleCandidateOpen(c.id)
                              navigate(`/app/candidates/${c.id}`)
                            }}
                            onMouseEnter={() => handleCandidateHover(c.id)}
                            onFocus={() => handleCandidateHover(c.id)}
                            title={t('app.candidates.table.open_card') || ((c as AugmentedCandidate).masked === true ? t('app.candidates.table.open_card_masked', { defaultValue: 'Открыть карточку кандидата' }) : `Открыть карточку кандидата ${c.first_name} ${c.last_name}`)}
                          >
                            {candidateLabel}
                          </Link>
                        </HoverCard>
                        <div className="text-xs text-slate-500" title={(c.short_id || ((c as AugmentedCandidate).masked && (c.id ?? '').slice(0, 8))) ? `Short ID: ${c.short_id || (c.id ?? '').slice(0, 8)}` : undefined}>
                          {c.short_id ? `ID ${c.short_id}` : (c as AugmentedCandidate).masked === true ? `ID ${(c.id ?? '').slice(0, 8)}` : t('common.labels.not_available')}
                        </div>
                        {c.__extra.opsMode && (
                          <div>
                            <span className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">
                              {opsModeLabelMap[c.__extra.opsMode]}
                            </span>
                          </div>
                        )}
                      </div>
                    )
                  } else if (columnKey === 'email') {
                    cellContent = (c as AugmentedCandidate).masked === true ? t('common.labels.not_available') : (c.email || t('common.labels.not_available'))
                  } else if (columnKey === 'phone') {
                    const phoneDisplay = (c as AugmentedCandidate).masked === true ? '—' : (c.phone || '—')
                    const href = phoneDisplay && phoneDisplay !== '—' ? asTelHref(phoneDisplay) : undefined
                    cellContent = href ? (
                      <a href={href} className="text-brand-600 hover:text-brand-700 hover:underline" title={t('app.candidates.table.call') || `Позвонить ${phoneDisplay}`}>
                        {phoneDisplay}
                      </a>
                    ) : (
                      phoneDisplay
                    )
                  } else if (columnKey === 'citizenship') {
                    const cit = c.__extra.citizenship || ''
                    cellContent = cit
                      ? (/^[A-Z]{2}$/.test(String(cit).toUpperCase()) ? getRegionDisplayName(cit, locale) : cit)
                      : t('common.labels.not_available')
                  } else if (columnKey === 'vacancy') {
                    const vacancyId = getCandidateVacancyId(c)
                    const vacancyName = vacancyId ? vacancyLabelMap.get(vacancyId) : null
                    cellContent = vacancyName || t('common.labels.not_available')
                  } else if (columnKey === 'short') {
                    // For masked candidates, backend sends short_id or id prefix; fallback to id slice for display
                    cellContent = (c as AugmentedCandidate).masked === true
                      ? (c.short_id || (c.id ?? '').slice(0, 8) || t('common.labels.not_available'))
                      : (c.short_id || t('common.labels.not_available'))
                  } else if (columnKey === 'manager') {
                    const managerName = resolveManagerLabel(c)
                    cellContent = managerName || t('common.labels.not_available')
                  } else if (columnKey === 'stage') {
                    cellContent = <StageTag code={c.stage} />
                  } else if (columnKey === 'created') {
                    cellContent = c.created_at ? formatDateSafe(c.created_at, locale) : t('common.labels.not_available')
                  } else if (columnKey === 'firstContact') {
                    cellContent = c.__extra.firstContactAt ? formatDateSafe(c.__extra.firstContactAt, locale) : t('common.labels.not_available')
                  } else if (columnKey === 'preferredChannel') {
                    const channel = c.__extra.preferredContact
                    const channelKey = channel ?? EMPTY_OPTION_VALUE
                    cellContent = preferredChannelLabelMap[channelKey] || t('common.labels.not_available')
                  } else if (columnKey === 'inPoland') {
                    const inPoland = c.__extra.inPoland
                    const key = inPoland === true ? 'yes' : inPoland === false ? 'no' : 'unknown'
                    cellContent = inPolandLabelMap[key] || inPolandLabelMap.unknown
                  } else if (columnKey === 'polandBasis') {
                    const basis = c.__extra.polandStayBasis
                    cellContent = basis ? getPolandBasisLabel(basis) : t('common.labels.not_available')
                  } else if (columnKey === 'trailerTypes') {
                    const trailers = c.__extra.trailerTypes
                    if (Array.isArray(trailers) && trailers.length > 0) {
                      cellContent = (
                        <div className="flex flex-wrap gap-1">
                          {trailers.map((t: string, idx: number) => (
                            <span key={idx} className="text-xs bg-slate-100 px-2 py-0.5 rounded">
                              {getTrailerTypeLabel(t)}
                            </span>
                          ))}
                        </div>
                      )
                    } else {
                      cellContent = t('common.labels.not_available')
                    }
                  } else if (columnKey === 'reasons') {
                    if (reasonTags && reasonTags.length > 0) {
                      cellContent = (
                        <div className="flex flex-wrap gap-1">
                          {reasonTags.slice(0, 2).map((code) => (
                            <span key={code} className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded">
                              {reasonLabelMap.get(code) || code}
                            </span>
                          ))}
                          {reasonTags.length > 2 && (
                            <span className="text-xs text-slate-500">+{reasonTags.length - 2}</span>
                          )}
                        </div>
                      )
                    } else if (fallbackReasons && fallbackReasons.length > 0) {
                      cellContent = (
                        <div className="flex flex-wrap gap-1">
                          {fallbackReasons.slice(0, 2).map((label, idx) => (
                            <span key={idx} className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded">
                              {label}
                            </span>
                          ))}
                          {fallbackReasons.length > 2 && (
                            <span className="text-xs text-slate-500">+{fallbackReasons.length - 2}</span>
                          )}
                        </div>
                      )
                    } else {
                      cellContent = t('common.labels.not_available')
                    }
                  } else if (columnKey === 'tags') {
                    const candidateTags = Array.isArray(c.tags) ? c.tags : []
                    if (candidateTags.length > 0) {
                      cellContent = (
                        <div className="flex flex-wrap gap-1">
                          {candidateTags.slice(0, 3).map((tag, idx) => (
                            <span key={idx} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-200">
                              {tag}
                            </span>
                          ))}
                          {candidateTags.length > 3 && (
                            <span className="text-xs text-slate-500">+{candidateTags.length - 3}</span>
                          )}
                        </div>
                      )
                    } else {
                      cellContent = t('common.labels.not_available')
                    }
                  } else if (columnKey === 'is_favorite') {
                    const isFavorite = c.is_favorite ?? false
                    cellContent = (
                      <button
                        type="button"
                        onClick={async (e) => {
                          e.stopPropagation()
                          if (!c.id || !canManage) return
                          try {
                            const newFavoriteValue = !isFavorite
                            await api.patch(`/candidates/${c.id}`, { is_favorite: newFavoriteValue })
                            // Обновляем локальное состояние
                            setItems((prev) => prev.map(item => item.id === c.id ? { ...item, is_favorite: newFavoriteValue } : item))
                            // Уведомляем другие компоненты
                            try {
                              window.dispatchEvent(new CustomEvent('candidate-updated', { detail: { candidateId: c.id } }))
                              localStorage.setItem('hf:candidate-updated', JSON.stringify({ candidateId: c.id, timestamp: Date.now() }))
                            } catch {
                              /* ignore */
                            }
                          } catch (err: any) {
                            console.error('[Candidates] Favorite toggle error:', err)
                            const errorMessage = formatErrorForDisplay(err, { fallback: t('app.candidates.messages.favorite_toggle_failed') })
                            alert(errorMessage)
                          }
                        }}
                        disabled={!canManage}
                        className={clsx(
                          'text-lg transition-all hover:scale-110',
                          isFavorite ? 'text-yellow-400' : 'text-slate-300 hover:text-yellow-300',
                          !canManage && 'opacity-50 cursor-not-allowed'
                        )}
                        title={isFavorite ? t('app.candidate_card.actions.remove_favorite') : t('app.candidate_card.actions.add_favorite')}
                      >
                        {isFavorite ? <IconBookmarkFilled size={18} /> : <IconBookmark size={18} />}
                      </button>
                    )
                  } else if (columnKey === 'docsStatus') {
                    if (docsMeta?.readinessState) {
                      const meta = DOC_READINESS_META[docsMeta.readinessState] || DOC_READINESS_META.pending
                      cellContent = (
                        <span className={clsx('text-xs px-2 py-0.5 rounded', meta.className)}>
                          {t(meta.labelKey)}
                        </span>
                      )
                    } else {
                      cellContent = t('common.labels.not_available')
                    }
                  } else if (columnKey === 'docsOrdered') {
                    cellContent = docsMeta?.orderDate ? formatDateSafe(docsMeta.orderDate, locale) : t('common.labels.not_available')
                  } else if (columnKey === 'docsValid') {
                    cellContent = docsMeta?.validFrom ? formatDateSafe(docsMeta.validFrom, locale) : t('common.labels.not_available')
                  } else if (columnKey === 'docsFiles') {
                    const hasFiles = docsMeta?.hasFiles
                    cellContent = hasFiles !== undefined ? (hasFiles ? '✓' : '—') : t('common.labels.not_available')
                  }
                  
                  return (
                    <td
                      key={columnKey}
                      className={clsx(
                        "px-4 py-3 border-r border-slate-200 overflow-hidden",
                        isFocused ? "bg-brand-100" : "bg-white",
                        columnKey === 'name' && "sticky font-medium z-[5]"
                      )}
                      style={{
                        ...stickyProps,
                        width: `${getColumnWidth(columnKey)}px`,
                        minWidth: `${getColumnWidth(columnKey)}px`,
                        maxWidth: `${getColumnWidth(columnKey)}px`
                      } as React.CSSProperties}
                    >
                      <div className="min-w-0 overflow-hidden" title={typeof cellContent === 'string' ? cellContent : undefined}>
                        {cellContent}
                      </div>
                    </td>
                  )
                })}
              </>
            )
          }}
          components={{
            Table: forwardRef<HTMLTableElement, React.ComponentPropsWithoutRef<'table'>>(
              ({ className, ...props }, ref) => (
                <table
                  {...props}
                  ref={ref}
                  className={clsx('min-w-full text-sm border-separate border-spacing-0', className)}
                />
              )
            ),
            TableHead: forwardRef<HTMLTableSectionElement, React.ComponentPropsWithoutRef<'thead'>>(
              ({ className, style, ...props }, ref) => (
                <thead 
                  ref={ref} 
                  style={{ ...style, position: 'sticky', top: 0, zIndex: 15, backgroundColor: '#f9fafb' }} 
                  className={clsx('bg-slate-50 border-b-2 border-slate-200', className)} 
                  {...props} 
                />
              )
            ),
            TableBody: forwardRef<HTMLTableSectionElement, React.ComponentPropsWithoutRef<'tbody'>>(
              ({ style, ...props }, ref) => <tbody ref={ref} style={style} {...props} />
            ),
            TableRow: forwardRef<
              HTMLTableRowElement,
              React.ComponentPropsWithoutRef<'tr'> & { item?: AugmentedCandidate; 'data-index'?: number }
            >(({ className, style, item, 'data-index': dataIndex, ...props }, ref) => {
              const id = item?.id
              const index = typeof dataIndex === 'number' ? dataIndex : (id ? displayedItems.findIndex(c => c.id === id) : -1)
              const isFocused = focusedRowIndex === index && index >= 0
              
              return (
                <tr
                  ref={(node) => {
                    if (typeof ref === 'function') {
                      ref(node)
                    } else if (ref) {
                      ref.current = node
                    }
                    if (isFocused && node) {
                      focusedRowRef.current = node
                      // Скроллим к выбранной строке при фокусе
                      setTimeout(() => {
                        node.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
                      }, 50)
                    }
                  }}
                  style={style}
                  data-candidate-id={id}
                  data-index={index}
                  tabIndex={-1}
                  onClick={(e) => {
                    if (!id) return
                    const target = e.target as HTMLElement | null
                    if (target?.closest('a,button,input,select,textarea,[role="button"]')) return
                    setSelectedCandidateId(id)
                    setPreviewTab('composer')
                    setSidebarOpen(true)
                  }}
                  onContextMenu={(e) => {
                    if (id && canManage) {
                      e.preventDefault()
                      setContextMenu({ x: e.clientX, y: e.clientY, candidateId: id })
                    }
                  }}
                  className={clsx(
                    'border-t border-slate-200 transition-all duration-150 cursor-pointer',
                    isFocused && 'ring-2 ring-brand-500 ring-inset outline-none',
                    !isFocused && 'hover:bg-brand-50/50',
                    id && selectedCandidateId === id && !isFocused && 'bg-brand-50',
                    id && recentlyOpenedId === id && !isFocused && 'bg-amber-50/60',
                    id && (items.find(c => c.id === id)?.is_favorite) && !isFocused && 'bg-yellow-50/40 border-l-2 border-l-yellow-400',
                    className
                  )}
                  {...props}
                />
              )
            }),
          }}
          />
        </div>
        {loading && displayedItems.length === 0 && (
          <div className="px-4 py-12 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600 mb-3"></div>
            <div className="text-sm text-slate-600 font-medium">{t('common.loading')}</div>
            <div className="text-xs text-slate-400 mt-1">{t('app.candidates.table.loading_hint') || 'Загрузка кандидатов...'}</div>
          </div>
        )}
        {!loading && displayedItems.length === 0 && !errorText && (
          <div className="px-4 py-12 text-center">
            <div className="mb-3 inline-flex text-slate-400"><IconClipboardList size={34} /></div>
            {items.length === 0 && total > 0 ? (
              <>
                <div className="text-sm font-medium text-slate-700 mb-1">
                  {t('app.candidates.table.empty_partial', { count: total, defaultValue: `Список не загрузился полностью (всего: ${total}). Повторить?` })}
                </div>
                <button
                  type="button"
                  className="mt-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm hover:bg-brand-700"
                  onClick={() => void load({ force: true, allowCache: false })}
                >
                  {t('common.retry', { defaultValue: 'Повторить' })}
                </button>
              </>
            ) : (
              <>
                <div className="mx-auto max-w-2xl">
                  <EmptyStatePanel
                    compact
                    title={t('app.candidates.table.empty_title', { defaultValue: 'No candidates found' })}
                    description={
                      hasActiveTableFilters
                        ? t('app.candidates.table.empty_with_filters_desc', {
                            defaultValue: 'Current filters returned no results. Reset filters or adjust conditions.',
                          })
                        : t('app.candidates.table.empty_no_data_desc', {
                            defaultValue: 'Add the first lead or candidate to start pipeline operations.',
                          })
                    }
                    primaryAction={
                      hasActiveTableFilters
                        ? {
                            label: t('app.candidates.table.empty_cta_reset', { defaultValue: 'Reset filters' }),
                            onClick: handleResetFilters,
                          }
                        : {
                            label: t('app.candidates.table.empty_cta_leads', { defaultValue: 'Open leads' }),
                            to: '/app/leads',
                          }
                    }
                    secondaryAction={
                      hasActiveTableFilters
                        ? {
                            label: t('app.candidates.table.empty_cta_leads', { defaultValue: 'Open leads' }),
                            to: '/app/leads',
                          }
                        : {
                            label: t('app.candidates.table.empty_cta_pipeline', { defaultValue: 'Open pipeline' }),
                            to: '/app/pipeline',
                          }
                    }
                  />
                </div>
              </>
            )}
          </div>
        )}
          </div>

          <div className="text-sm text-slate-500 p-4">
            {showsFilteredCount
              ? t('app.candidates.table.total_filtered', {
                  values: { shown: visibleCandidatesCount, total },
                  defaultValue: `Показано: ${visibleCandidatesCount} из ${total}`,
                })
              : t('app.candidates.table.total', { values: { count: visibleCandidatesCount } })}
          </div>
        </div>
      </div>

      {/* Контекстное меню для строк */}
      {contextMenu && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setContextMenu(null)}
            onContextMenu={(e) => {
              e.preventDefault()
              setContextMenu(null)
            }}
          />
          <div
            ref={contextMenuRef}
            className="fixed z-50 w-56 rounded-lg border border-slate-200 bg-white p-2 shadow-xl"
            style={{ left: contextMenu.x, top: contextMenu.y }}
            onClick={(e) => e.stopPropagation()}
          >
            {(() => {
              const candidate = displayedItems.find(c => c.id === contextMenu.candidateId)
              if (!candidate || !canManage) return null
              
              return (
                <div className="space-y-1">
                  <button
                    className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2"
                    onClick={() => {
                      handleCandidateOpen(candidate.id)
                      navigate(`/app/candidates/${candidate.id}`)
                      setContextMenu(null)
                    }}
                  >
                    {t('app.candidates.context.open_card')}
                  </button>
                  <button
                    className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2"
                    onClick={() => {
                      toggle(candidate.id)
                      setContextMenu(null)
                    }}
                  >
                    {checked[candidate.id] 
                      ? t('app.candidates.context.deselect')
                      : t('app.candidates.context.select')
                    }
                  </button>
                  <div className="border-t border-slate-200 my-1" />
                  <button
                    className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2"
                    onClick={() => {
                      setChecked({ [candidate.id]: true })
                      setBulkStage(stageOptions[0] || 'new')
                      setBulkReasons([])
                      setBulkOpen(true)
                      setContextMenu(null)
                    }}
                  >
                    {t('app.candidates.context.change_stage')}
                  </button>
                  <button
                    className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2"
                    onClick={() => {
                      setChecked({ [candidate.id]: true })
                      setBulkManagerId(preferredManagerId)
                      setBulkManagerOpen(true)
                      setContextMenu(null)
                    }}
                  >
                    {t('app.candidates.context.assign_manager')}
                  </button>
                  <button
                    className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2"
                    onClick={() => {
                      setChecked({ [candidate.id]: true })
                      setBulkVacancyId(vacancies[0]?.id || '')
                      setBulkVacancyOpen(true)
                      setContextMenu(null)
                    }}
                  >
                    {t('app.candidates.context.assign_vacancy')}
                  </button>
                </div>
              )
            })()}
          </div>
        </>
      )}

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
          <div className="text-xs text-slate-500">
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
                    opsMode: opsModeFilter,
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
            <button className="btn-secondary" onClick={()=>setSaveViewOpen(false)}>{t('common.actions.cancel')}</button>
          </div>
        </div>
      </Modal>

      <BulkManagerModal
        open={bulkManagerOpen}
        onClose={() => !bulkOperationLoading && setBulkManagerOpen(false)}
        managers={managers}
        bulkManagerId={bulkManagerId}
        onManagerIdChange={setBulkManagerId}
        onApply={doBulkAssign}
        loading={bulkOperationLoading === 'manager'}
        canManage={canManage}
      />

      <BulkVacancyModal
        open={bulkVacancyOpen}
        onClose={() => !bulkOperationLoading && setBulkVacancyOpen(false)}
        vacancies={vacancies}
        bulkVacancyId={bulkVacancyId}
        onVacancyIdChange={setBulkVacancyId}
        onApply={doBulkAssignVacancy}
        loading={bulkOperationLoading === 'vacancy'}
        canManage={canManage}
      />

      <BulkHandoffModal
        open={bulkHandoffOpen}
        onClose={() => !bulkOperationLoading && setBulkHandoffOpen(false)}
        clients={handoffClients}
        clientsLoading={handoffClientsLoading}
        selectedClient={bulkHandoffClientId}
        onSelectedClientChange={setBulkHandoffClientId}
        onApply={doBulkHandoff}
        loading={bulkOperationLoading === 'handoff'}
        canManage={canManage}
        count={Object.values(checked).filter(Boolean).length}
      />

      <BulkTagsModal
        open={bulkTagsOpen}
        onClose={() => !bulkOperationLoading && setBulkTagsOpen(false)}
        bulkTagsOperation={bulkTagsOperation}
        bulkTagsList={bulkTagsList}
        onOperationChange={setBulkTagsOperation}
        onTagsListChange={setBulkTagsList}
        onApply={doBulkTags}
        loading={bulkOperationLoading === 'tags'}
        canManage={canManage}
      />

      <BulkDeleteModal
        open={bulkDeleteOpen}
        onClose={() => !bulkOperationLoading && setBulkDeleteOpen(false)}
        onApply={doBulkDelete}
        loading={bulkOperationLoading === 'delete'}
        count={Object.values(checked).filter(Boolean).length}
        canManage={canManage}
      />

      <BulkStageModal
        open={bulkOpen}
        onClose={() => {
          if (!bulkOperationLoading) {
            setBulkOpen(false)
            setBulkReasons([])
          }
        }}
        stageOptions={stageOptions}
        bulkStage={bulkStage}
        bulkReasons={bulkReasons}
        onStageChange={setBulkStage}
        onReasonsChange={setBulkReasons}
        onApply={doBulk}
        loading={bulkOperationLoading === 'stage'}
        meta={meta}
        canManage={canManage}
      />

      {/* Боковое меню справа */}
      <div
        className={clsx(
          "fixed top-0 right-0 h-full w-96 bg-gradient-to-b from-slate-50 to-white border-l-2 border-slate-300 shadow-2xl z-40 transition-transform duration-300 ease-in-out overflow-y-auto",
          sidebarOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div className="p-4 space-y-4 pt-16">
          {/* Summary Hero */}
          <div className="mb-1">
            {summaryHero}
          </div>

          {selectedCandidate && (
            <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-slate-900">
                    {selectedCandidate.masked === true
                      ? selectedCandidate.short_id
                        ? t('app.candidates.table.masked_label_short_id', {
                            defaultValue: 'Кандидат {short_id}',
                            values: { short_id: selectedCandidate.short_id },
                          })
                        : t('app.candidates.table.masked_label', {
                            defaultValue: 'Кандидат #{id}',
                            values: { id: (selectedCandidate.id ?? '').slice(0, 8) },
                          })
                      : `${selectedCandidate.first_name ?? ''} ${selectedCandidate.last_name ?? ''}`.trim() || t('common.labels.not_available')}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <StageTag code={selectedCandidate.stage} />
                    <span className="text-[11px] text-slate-500">
                      {(selectedCandidate as any).__extra?.companyName || (selectedCandidate as any).company_name || '—'}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-secondary h-8 rounded-lg px-2 text-xs"
                  onClick={() => setSelectedCandidateId(null)}
                >
                  {t('common.actions.close', { defaultValue: 'Close' })}
                </button>
              </div>

              <div className="flex flex-wrap gap-2">
                <button type="button" className="btn-primary btn-xs" onClick={() => navigate(`/app/candidates/${selectedCandidate.id}`)}>
                  {t('common.actions.open', { defaultValue: 'Open' })}
                </button>
                <button
                  type="button"
                  className="btn-secondary btn-xs"
                  onClick={() => navigate(`/app/candidates/${selectedCandidate.id}/documents`)}
                >
                  {t('app.nav.items.documents', { defaultValue: 'Documents' })}
                </button>
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  className={previewTab === 'composer' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                  onClick={() => setPreviewTab('composer')}
                >
                  {t('app.candidates.preview.tabs.composer', { defaultValue: 'Composer' })}
                </button>
                <button
                  type="button"
                  className={previewTab === 'focus' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                  onClick={() => setPreviewTab('focus')}
                >
                  {t('app.candidates.preview.tabs.focus', { defaultValue: 'Focus' })}
                </button>
                <button
                  type="button"
                  className={previewTab === 'history' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                  onClick={() => setPreviewTab('history')}
                >
                  {t('app.candidates.preview.tabs.history', { defaultValue: 'History' })}
                </button>
              </div>

              {previewTab === 'composer' && (
                <div className="space-y-2">
                  <input
                    className="input h-9 w-full rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                    value={previewReminderTitle}
                    onChange={(e) => setPreviewReminderTitle(e.target.value)}
                    placeholder={t('app.reminders.fields.title', { defaultValue: 'Title' })}
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <label className="text-xs font-medium text-slate-600">
                      <div className="mb-1">{t('app.reminders.fields.due_at', { defaultValue: 'Due' })}</div>
                      <input
                        type="datetime-local"
                        className="input h-9 w-full rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                        value={previewReminderDueAt}
                        onChange={(e) => setPreviewReminderDueAt(e.target.value)}
                      />
                    </label>
                    <label className="text-xs font-medium text-slate-600">
                      <div className="mb-1">{t('app.reminders.fields.remind_before', { defaultValue: 'Remind before (min)' })}</div>
                      <input
                        type="number"
                        min={0}
                        className="input h-9 w-full rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                        value={previewReminderOffset}
                        onChange={(e) => setPreviewReminderOffset(Number(e.target.value) || 0)}
                      />
                    </label>
                  </div>
                  <button
                    type="button"
                    className="btn-primary h-9 w-full rounded-lg text-sm disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={!previewReminderTitle || !previewReminderDueAt}
                    onClick={() => void handleCreatePreviewReminder()}
                  >
                    {t('app.reminders.actions.create', { defaultValue: 'Create reminder' })}
                  </button>
                  {previewRemindersError ? <div className="text-xs text-red-600">{previewRemindersError}</div> : null}
                </div>
              )}

              {previewTab === 'focus' && (
                <div className="space-y-2">
                  {previewRemindersLoading ? (
                    <div className="py-2 text-center text-xs text-slate-500">{t('common.loading')}</div>
                  ) : previewReminders.length === 0 ? (
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
                      {t('app.reminders.states.empty', { defaultValue: 'No reminders yet.' })}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {previewReminders.slice(0, 10).map((r) => (
                        <div key={r.id} className="rounded-lg border border-slate-200 bg-white p-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium text-slate-900">
                                {r.title || t('app.reminders.item.untitled', { defaultValue: 'Untitled' })}
                              </div>
                              <div className="mt-0.5 text-xs text-slate-600">
                                <span className="font-medium">{t('app.reminders.fields.due_at', { defaultValue: 'Due' })}:</span>{' '}
                                {formatDateSafe(r.due_at, locale) || r.due_at}
                              </div>
                            </div>
                            <button
                              type="button"
                              className="btn-secondary h-8 rounded-lg px-2 text-xs"
                              onClick={() => void handleCompletePreviewReminder(r.id)}
                            >
                              {t('app.reminders.actions.complete', { defaultValue: 'Done' })}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  {previewRemindersError ? <div className="text-xs text-red-600">{previewRemindersError}</div> : null}
                </div>
              )}

              {previewTab === 'history' && (
                <div className="space-y-2 text-xs">
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <div className="grid grid-cols-1 gap-1">
                      <div>
                        <span className="text-slate-500">{t('app.candidates.columns.stage', { defaultValue: 'Stage' })}:</span>{' '}
                        <span className="font-medium text-slate-800">{String(selectedCandidate.stage || '—')}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">{t('app.candidates.columns.manager', { defaultValue: 'Manager' })}:</span>{' '}
                        <span className="font-medium text-slate-800">{resolveManagerLabel(selectedCandidate) || '—'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">{t('app.candidates.columns.docs', { defaultValue: 'Docs' })}:</span>{' '}
                        <span className="font-medium text-slate-800">{String(selectedCandidate.__docsMeta?.readinessKey || '—')}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">{t('app.candidates.columns.phone', { defaultValue: 'Phone' })}:</span>{' '}
                        <span className="font-medium text-slate-800">{selectedCandidate.masked === true ? '—' : selectedCandidate.phone || '—'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">{t('app.candidates.columns.email', { defaultValue: 'Email' })}:</span>{' '}
                        <span className="font-medium text-slate-800">{selectedCandidate.masked === true ? '—' : selectedCandidate.email || '—'}</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {t('app.candidates.preview.history_note', {
                      defaultValue: 'History v1 shows key metadata. Next step: unify events into a timeline.',
                    })}
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Поиск и фильтры */}
          <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3">
              <div className="flex-1">
                <label className="block text-xs font-medium text-slate-600 mb-1.5" htmlFor="cand-search">
                  {t('app.candidates.search.label')}
                </label>
                <input
                  id="cand-search"
                  ref={searchRef}
                  className="input w-full text-sm py-2 px-3 border border-slate-300 focus:border-brand-500 focus:ring-1 focus:ring-brand-200"
                  value={q}
                  onChange={(e)=>setQ(e.target.value)}
                  placeholder={t('app.candidates.search.placeholder')}
                />
                <p className="mt-1.5 text-[10px] text-slate-400 leading-relaxed">{t('app.candidates.search.hint')}</p>
              </div>
              <div className="space-y-2 pt-2 border-t border-slate-200">
                <label className="block text-xs font-medium text-slate-600">
                  {t('app.candidates.filters.handoff_status_menu', { defaultValue: 'Przekazanie' })}
                </label>
                <select
                  className="input w-full text-sm py-1.5"
                  value={handoffStatusFilter}
                  onChange={(e) => setHandoffStatusFilter(e.target.value)}
                >
                  <option value="">{t('app.candidates.filters.any', { defaultValue: '— dowolne —' })}</option>
                  <option value="none">{t('app.candidates.filters.handoff_none', { defaultValue: 'Bez przekazania' })}</option>
                  <option value="pending">{t('app.candidates.filters.handoff_pending', { defaultValue: 'Oczekuje' })}</option>
                  <option value="accepted">{t('app.candidates.filters.handoff_accepted', { defaultValue: 'Przekazano' })}</option>
                  <option value="returned">{t('app.candidates.filters.handoff_returned', { defaultValue: 'Zwrócono' })}</option>
                </select>
                <label className="block text-xs font-medium text-slate-600">
                  {t('app.candidates.filters.contact_attempts_menu', { defaultValue: 'Próby kontaktu' })}
                </label>
                <select
                  className="input w-full text-sm py-1.5"
                  value={contactAttemptsFilter}
                  onChange={(e) => setContactAttemptsFilter(e.target.value)}
                >
                  <option value="">{t('app.candidates.filters.any', { defaultValue: '— dowolne —' })}</option>
                  <option value="none">{t('app.candidates.filters.contact_none', { defaultValue: 'Bez prób' })}</option>
                  <option value="some">{t('app.candidates.filters.contact_some', { defaultValue: '1–2 próby' })}</option>
                  <option value="limit_reached">{t('app.candidates.filters.contact_limit', { defaultValue: '3+ (limit)' })}</option>
                </select>
                <label className="block text-xs font-medium text-slate-600">
                  {t('app.candidates.filters.ops_mode_menu')}
                </label>
                <select
                  className="input w-full text-sm py-1.5"
                  value={opsModeFilter[0] || ''}
                  onChange={(e) => {
                    const value = String(e.target.value || '').trim() as CandidateOpsMode | ''
                    if (!value) {
                      setOpsModeFilter([])
                      return
                    }
                    if (value === 'in_work' || value === 'later' || value === 'no_reply_needed' || value === 'escalated') {
                      setOpsModeFilter([value])
                    }
                  }}
                >
                  <option value="">{t('app.candidates.filters.any')}</option>
                  {(opsModeOptions.length > 0
                    ? opsModeOptions
                    : [
                        { value: 'in_work', label: opsModeLabelMap.in_work },
                        { value: 'later', label: opsModeLabelMap.later },
                        { value: 'no_reply_needed', label: opsModeLabelMap.no_reply_needed },
                        { value: 'escalated', label: opsModeLabelMap.escalated },
                      ]
                  ).map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200">
                {viewToggle}
                <button
                  className={secondaryBtn}
                  onClick={()=>load({ force: true })}
                  disabled={loading}
                  title={t('app.candidates.actions.refresh_title')}
                >
                  {loading ? t('app.candidates.actions.refreshing') : t('app.candidates.actions.refresh')}
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
                    <div className="absolute right-0 z-20 mt-2 w-64 rounded-md border border-slate-200 bg-white p-3 shadow-lg">
                      <div className="space-y-0.5">
                        <button
                          className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2"
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
                                manager: resolveManagerLabel(c) || '',
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
                            setActionsMenuOpen(false)
                          }}
                        >
                          {t('app.candidates.actions.export')}
                        </button>
                        <button
                          className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2 disabled:opacity-60"
                          onClick={() => {
                            handleResetFilters()
                            setActionsMenuOpen(false)
                          }}
                          disabled={!hasFilterBadges}
                        >
                          {t('app.candidates.actions.reset_filters')}
                        </button>
                        <button
                          className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2 disabled:opacity-60"
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
                      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mt-3 pt-2 border-t border-slate-100">
                        {t('app.candidates.table.columns.title')}
                      </div>
                      <div className="mt-1.5 max-h-48 space-y-0.5 overflow-auto">
                        {columnToggleKeys.map((key) => (
                          <label key={key} className="flex items-center gap-1.5 text-xs py-0.5">
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
                    </div>
                  )}
                </div>
                {canManage && (
                  <Link 
                    className="btn-primary text-xs py-1.5 px-2.5 font-medium" 
                    to="/app/candidates/new" 
                    title={t('app.candidates.actions.new_candidate_title')}
                  >
                    {t('app.candidates.actions.new_candidate')}
                  </Link>
                )}
              </div>
            </div>
            <div className="pt-2.5 border-t border-slate-200">
              <h3 className="text-xs font-semibold text-slate-600 mb-2 uppercase tracking-wide">{t('app.candidates.filters.quick_title')}</h3>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsFavoriteFilter(prev => prev === true ? null : true)}
                  className={[
                    'rounded-md px-2.5 py-1.5 text-xs font-medium transition-all',
                    isFavoriteFilter === true
                      ? 'bg-brand-600 text-white shadow-sm hover:bg-brand-700'
                      : 'bg-white text-brand-700 border border-brand-200 hover:bg-brand-50 hover:border-brand-300',
                  ].join(' ')}
                >
                  {t('app.candidates.filters.only_favorites')}
                </button>
                {(quickFiltersExpanded ? quickDocFilters : quickDocFilters.slice(0, 3)).map((filter) => (
                  <button
                    key={filter.key}
                    type="button"
                    onClick={() => toggleQuickDocFilter(filter.statuses, filter.active)}
                    className={[
                      'rounded-md px-2.5 py-1.5 text-xs font-medium transition-all',
                      filter.active 
                        ? 'bg-brand-600 text-white shadow-sm hover:bg-brand-700' 
                        : 'bg-white text-brand-700 border border-brand-200 hover:bg-brand-50 hover:border-brand-300',
                    ].join(' ')}
                  >
                    {filter.label}
                  </button>
                ))}
                {quickDocFilters.length > 3 && (
                  <button
                    type="button"
                    className="rounded-md px-2.5 py-1.5 text-xs font-medium border border-slate-300 text-slate-700 hover:bg-slate-50 hover:border-slate-400 transition-all"
                    onClick={() => setQuickFiltersExpanded((prev) => !prev)}
                  >
                    {quickFiltersExpanded ? t('app.candidates.filters.quick_less') : t('app.candidates.filters.quick_more')}
                  </button>
                )}
              </div>
            </div>
          </section>

          {/* Сохраненные виды */}
          {savedViews.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
              <details className="relative">
                <summary className="text-xs font-semibold text-slate-600 cursor-pointer select-none hover:text-brand-600 transition-colors pb-2 border-b border-slate-200 uppercase tracking-wide" title={t('app.candidates.views.manage_title')}>
                  {t('app.candidates.views.toggle')}
                </summary>
                <div className="mt-3 space-y-1.5 max-h-64 overflow-auto">
                  {savedViews.map(v => (
                    <div key={v.id} className="flex items-center justify-between gap-1.5 p-1.5 rounded-md hover:bg-slate-50 transition-colors">
                      <button
                        className="btn-secondary text-left justify-start flex-1 truncate text-xs font-medium px-1.5 py-1"
                        title={t('app.candidates.views.apply_title', { values: { name: v.name } })}
                        onClick={()=>applyView(v)}
                      >{v.name}</button>
                      <button
                        className="btn-danger btn-xs"
                        title={t('app.candidates.views.delete_title')}
                        onClick={(e)=>{ e.preventDefault(); void deleteView(v.id) }}
                      >×</button>
                    </div>
                  ))}
                  {savedViews.length === 0 && (
                    <div className="text-[10px] text-slate-400 text-center py-3">{t('app.candidates.views.empty')}</div>
                  )}
                </div>
              </details>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
