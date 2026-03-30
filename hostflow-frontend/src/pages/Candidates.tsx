// src/pages/Candidates.tsx
import clsx from 'clsx'
import type { ReactNode } from 'react'
import { useCallback, useEffect, useMemo, useRef, useState, forwardRef } from 'react'
import { createPortal } from 'react-dom'
import { Link, useSearchParams, useLocation, useNavigate } from 'react-router-dom'
import {
  IconArrowRight,
  IconBookmark,
  IconBookmarkFilled,
  IconClipboardList,
  IconListCheck,
  IconMail,
  IconPhone,
} from '@tabler/icons-react'
import api, {
  completeActivity,
  completeReminder,
  createActivity,
  createBulkActivities,
  createReminder,
  withTenant,
  snoozeActivity,
} from '../api/client'
import { recordPerfMeasurement } from '../api/analytics'
import { useCurrentTenantId } from '../contexts/CurrentTenant'
import type { Candidate, UserSavedView, Vacancy } from '../api/types'
import type { ReminderRecord } from '../api/types/notification'
import { Modal } from '../components/Modal'
import { ActivitiesPanel } from '../components/activities/ActivitiesPanel'
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
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import Pipeline from './Pipeline'
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
  APP_SCROLL_SELECTOR,
  EMPTY_OPTION_VALUE,
  SORTABLE_KEYS,
  DEFAULT_VISIBLE_COLS,
  DEFAULT_COLUMN_ORDER,
  CANDIDATES_WORK_PANEL_RAIL_WIDTH_PX,
} from '../modules/candidates/constants'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
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
  CandidatesListInsights,
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
  BulkActivitiesModal,
  BulkDeleteModal,
  ColumnFilterMenu,
  FilterBadges,
  CandidatesSummaryHero,
  CandidatesQuickViewsBar,
  CandidatesWorkPanel,
  CandidatesSelectedPanel,
  CandidatesLeftRailPanel,
  CandidatesTableCheckboxCell,
  CandidatesTableRowNamePreview,
  CandidatesTableRowStageCell,
} from '../modules/candidates/components'
import { useCandidatesWorkPanel } from '../modules/candidates/hooks/useCandidatesWorkPanel'
import { useCandidatesInsightsHero } from '../modules/candidates/hooks/useCandidatesInsightsHero'
import { useCandidatesSavedViews } from '../modules/candidates/hooks/useCandidatesSavedViews'
import { useCandidatesQuickViews } from '../modules/candidates/hooks/useCandidatesQuickViews'
import { useCandidatesTableData } from '../modules/candidates/hooks/useCandidatesTableData'
import { useCandidatesTableKeyboardNavigation } from '../modules/candidates/hooks/useCandidatesTableKeyboardNavigation'
import { useCandidatesTableColumnsDnDResize } from '../modules/candidates/hooks/useCandidatesTableColumnsDnDResize'
import { useCandidatesScrollRestoration } from '../modules/candidates/hooks/useCandidatesScrollRestoration'
import { getAvailableClients, createBulkHandoff, type AvailableClientOut } from '../api/handoffs'

// Cache for candidate lists
const candidateListCache = new Map<string, CandidateListCacheEntry>()

function normalizeListInsights(raw: unknown): CandidatesListInsights | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  return {
    total: Number(o.total) || 0,
    new_count: Number(o.new_count) || 0,
    docs_ready: Number(o.docs_ready) || 0,
    docs_attention: Number(o.docs_attention) || 0,
    docs_ordered: Number(o.docs_ordered) || 0,
  }
}

// универсальный фетчер (tenantId = X-Tenant-Id для запроса, чтобы список совпадал с аналитикой для клиента)
async function getWithFallbacks<T = any>(
  path: string,
  params: Record<string, any>,
  tenantId?: string | null
) {
  const client = tenantId ? withTenant(tenantId) : api
  const limit = params.limit ?? 50
  const offset = params.offset ?? 0
  // Пробрасываем все query-параметры (фильтры, include_insights, compact, …), а не урезанный common
  const baseParams = { ...params }

  const attempts = [
    { ...baseParams, limit, offset },
    { ...baseParams, limit, skip: offset },
    { ...baseParams, page: Math.floor(offset / limit) + 1, per_page: limit },
    { ...baseParams, limit },
    { ...baseParams },
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

const RISK_SHADOW_MIN_BANDS = new Set<string>(['low', 'medium', 'high', 'critical'])

function parseRiskShadowMinBand(raw: string | null | undefined): string | null {
  if (raw == null || raw === '') return null
  const v = String(raw).trim().toLowerCase()
  return RISK_SHADOW_MIN_BANDS.has(v) ? v : null
}

/** Align with Reminders inbox: managers can load team-scoped candidate reminders in the work panel. */
const TEAM_WORK_PANEL_ASSIGNEE_ROLES = new Set([
  'administrator',
  'supervisor',
  'superadmin',
  'admin',
  'manager',
])

const WP_ASSIGNEE_STORAGE_KEY = 'hf:candidates:workPanelAssigneeScope'

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

  const [limit] = useState(200)
  // items/total/loading/errorText/listInsights are managed by SSOT hook.

  const { me: meForWorkPanel } = useAuth()
  const tenantIdForWorkPanel = useCurrentTenantId()
  const tenantScopeKeyForWorkPanel = (tenantIdForWorkPanel ?? meForWorkPanel?.tenant_id)
    ? String(tenantIdForWorkPanel ?? meForWorkPanel?.tenant_id)
    : 'default'
  const canUseTeamWorkPanelAssigneeScope = useMemo(() => {
    const r = String(meForWorkPanel?.role || '').trim().toLowerCase()
    return TEAM_WORK_PANEL_ASSIGNEE_ROLES.has(r)
  }, [meForWorkPanel?.role])
  const [workPanelAssigneeScope, setWorkPanelAssigneeScopeState] = useState<'mine' | 'team'>('mine')
  useEffect(() => {
    try {
      const raw = localStorage.getItem(`${WP_ASSIGNEE_STORAGE_KEY}:${tenantScopeKeyForWorkPanel}`)
      if (raw === 'team' || raw === 'mine') setWorkPanelAssigneeScopeState(raw)
      else setWorkPanelAssigneeScopeState('mine')
    } catch {
      setWorkPanelAssigneeScopeState('mine')
    }
  }, [tenantScopeKeyForWorkPanel])
  useEffect(() => {
    if (!canUseTeamWorkPanelAssigneeScope && workPanelAssigneeScope === 'team') {
      setWorkPanelAssigneeScopeState('mine')
    }
  }, [canUseTeamWorkPanelAssigneeScope, workPanelAssigneeScope])
  const setWorkPanelAssigneeScope = useCallback(
    (next: 'mine' | 'team') => {
      if (next === 'team' && !canUseTeamWorkPanelAssigneeScope) return
      setWorkPanelAssigneeScopeState(next)
      try {
        localStorage.setItem(`${WP_ASSIGNEE_STORAGE_KEY}:${tenantScopeKeyForWorkPanel}`, next)
      } catch {
        /* ignore */
      }
    },
    [canUseTeamWorkPanelAssigneeScope, tenantScopeKeyForWorkPanel],
  )

  const {
    // Work panel selection + open/close state.
    selectedCandidateId,
    setSelectedCandidateId,
    sidebarOpen,
    setSidebarOpen,
    workPanelOpen,

    // Preview state + handlers.
    nextActionDetailsOpenTrigger,
    bumpNextActionDetailsOpen,
    previewReminders,
    previewRemindersLoading,
    previewRemindersError,
    previewReminderBusy,
    previewReminderTitle,
    previewReminderDueAt,
    previewReminderOffset,
    setPreviewReminderTitle,
    setPreviewReminderDueAt,
    setPreviewReminderOffset,
    previewTimelineItems,
    previewTimelineLoading,
    previewTimelineError,
    previewTimelineExpanded,
    setPreviewTimelineExpanded,
    loadPreviewTimeline,
    docsBlockers,
    docsBlockersLoading,
    setDocsBlockers,
    setDocsBlockersLoading,
    handleCreatePreviewReminder,
    handleDocsRequestCreate,
    handleCompletePreviewReminder,
    handlePreviewReminderSnooze,
    previewCandidateExtra,
    previewDocumentsSummarySnapshot,
    previewCommsLinks,
  } = useCandidatesWorkPanel({ t, workPanelAssigneeScope })

  const docsRailEmbeddedSummary = useMemo(
    () => ({
      ready: !previewRemindersLoading,
      summary: previewDocumentsSummarySnapshot,
    }),
    [previewRemindersLoading, previewDocumentsSummarySnapshot],
  )

  // Keep the latest values for stable row click/context handlers.
  const sidebarOpenRef = useRef<boolean>(sidebarOpen)
  const selectedCandidateIdRef = useRef<string | null>(selectedCandidateId)
  useEffect(() => {
    sidebarOpenRef.current = sidebarOpen
  }, [sidebarOpen])
  useEffect(() => {
    selectedCandidateIdRef.current = selectedCandidateId
  }, [selectedCandidateId])

  const PREVIEW_TIMELINE_COLLAPSED_COUNT = 15

  const [debugClientView, setDebugClientView] = useState<Record<string, unknown> | null>(null)
  const [debugClientViewLoading, setDebugClientViewLoading] = useState(false)
  const [debugClientViewError, setDebugClientViewError] = useState<string | null>(null)
  const showDebugPanel = searchParams.get('debug') === '1'
  const [debugHit, setDebugHit] = useState<{
    tag?: string
    className?: string
    pointerEvents?: string
    insideTable?: boolean
  } | null>(null)
  const [debugClickHit, setDebugClickHit] = useState<typeof debugHit>(null)
  const [debugMouseUpHit, setDebugMouseUpHit] = useState<typeof debugHit>(null)
  const [debugClickHitBubble, setDebugClickHitBubble] = useState<typeof debugHit>(null)
  const [debugMouseUpHitBubble, setDebugMouseUpHitBubble] = useState<typeof debugHit>(null)

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

  const [bulkActivitiesOpen, setBulkActivitiesOpen] = useState(false)
  const [bulkActivityTitle, setBulkActivityTitle] = useState('')
  const [bulkActivityDueAt, setBulkActivityDueAt] = useState(() =>
    new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16),
  )
  const [bulkActivityOffsetMinutes, setBulkActivityOffsetMinutes] = useState(60)
  const [bulkActivityType, setBulkActivityType] = useState('custom')

  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)
  const [activitiesModalOpen, setActivitiesModalOpen] = useState(false)
  const [activitiesModalRefresh, setActivitiesModalRefresh] = useState(0)

  const [bulkHandoffOpen, setBulkHandoffOpen] = useState(false)
  const [handoffClients, setHandoffClients] = useState<AvailableClientOut[]>([])
  const [handoffClientsLoading, setHandoffClientsLoading] = useState(false)
  const [bulkHandoffClientId, setBulkHandoffClientId] = useState('')

  const { me, preferences, updatePreferences } = useAuth()
  const currentTenantId = useCurrentTenantId()
  const tenantScopeKey = (currentTenantId ?? me?.tenant_id) ? String(currentTenantId ?? me?.tenant_id) : 'default'
  const digestShadowBucket = useMemo(() => searchParams.get('shadow_bucket')?.trim() || null, [searchParams])
  const digestShadowMinBand = useMemo(() => {
    const explicit =
      parseRiskShadowMinBand(searchParams.get('shadow_min_band')) ??
      parseRiskShadowMinBand(searchParams.get('shadow_bucket_min_band'))
    if (!digestShadowBucket) return null
    return explicit ?? 'high'
  }, [searchParams, digestShadowBucket])
  /** §2.14: same list shell as main Candidates; data via GET /candidates/no-next-action (see useCandidatesTableData). */
  const operationalQueue = useMemo<'no_next_action' | null>(() => {
    const raw = (searchParams.get('queue') || searchParams.get('quick_view') || '').trim().toLowerCase()
    return raw === 'no_next_action' ? 'no_next_action' : null
  }, [searchParams])
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
      shadow_bucket: digestShadowBucket || '',
      shadow_min_band: digestShadowMinBand || '',
      created_from: createdRange.from || '',
      created_to: createdRange.to || '',
      is_favorite: isFavoriteFilter === null ? '' : String(isFavoriteFilter),
      operational_queue: operationalQueue || '',
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
    digestShadowBucket,
    digestShadowMinBand,
    createdRange.from,
    createdRange.to,
    isFavoriteFilter,
    operationalQueue,
  ])
  const cacheKey = useMemo(
    () => `candidates:list:${tenantScopeKey}:${filterSignature}`,
    [tenantScopeKey, filterSignature]
  )
  const scrollKey = useMemo(() => `${SCROLL_STATE_KEY}:${tenantScopeKey}:${viewMode}`, [tenantScopeKey, viewMode])

  const [actionsMenuOpen, setActionsMenuOpen] = useState(false)
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

  const {
    savedViews,
    saveViewOpen,
    setSaveViewOpen,
    saveViewName,
    setSaveViewName,
    syncCandidateViews,
    applyView,
    deleteView,
  } = useCandidatesSavedViews({
    preferences,
    updatePreferences,
    filtersHydrated,
    // If user already restored persisted filters, don't auto-apply default view.
    applyViewFilters,
    skipDefaultView: persistedFiltersRef.current,
  })

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
      risk: t('app.candidates.table.columns.risk', { defaultValue: 'Risk' }) || 'Risk',
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
    'risk',
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

  /** R1.5 Phase C: DnD + column resize only in this mode (default off). */
  const [tableLayoutCustomize, setTableLayoutCustomize] = useState(() => {
    try {
      return localStorage.getItem('hf:candidates:tableLayoutCustomize') === '1'
    } catch {
      return false
    }
  })
  useEffect(() => {
    try {
      localStorage.setItem('hf:candidates:tableLayoutCustomize', tableLayoutCustomize ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [tableLayoutCustomize])

  const {
    orderedVisibleColumns,
    getColumnWidth,
    draggingColumn,
    setDraggingColumn,
    dragOverColumn,
    setDragOverColumn,
    reorderColumns,
    handleResizeStart,
  } = useCandidatesTableColumnsDnDResize({
    visibleCols,
    columnWidthsStorageKey,
    columnOrderStorageKey,
  })

  useEffect(() => {
    if (tableLayoutCustomize) return
    setDraggingColumn(null)
    setDragOverColumn(null)
  }, [tableLayoutCustomize, setDraggingColumn, setDragOverColumn])

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
      setSortDir(key === 'created_at' || key === 'risk_score' ? 'desc' : 'asc')
    }
  }
  const renderSortButton = (label: string, key: SortKey) => (
    <button
      type="button"
      className="inline-flex h-5 min-w-0 shrink items-center gap-1 whitespace-nowrap font-semibold leading-none text-left text-slate-700 hover:text-brand-600 transition-colors group/sort relative"
      onClick={() => handleSortChange(key)}
      title={
        sortKey === key
          ? t('app.candidates.table.sort_by', { values: { column: label, dir: sortDir === 'asc' ? t('common.sort.asc') : t('common.sort.desc') } }) || `Сортировка по ${label} (${sortDir === 'asc' ? '↑' : '↓'})`
          : t('app.candidates.table.click_to_sort', { values: { column: label } }) || `Кликните для сортировки по ${label}`
      }
    >
      <span className="truncate">{label}</span>
      {sortKey === key && (
        <span
          className="inline-flex h-4 w-4 items-center justify-center text-[11px] text-brand-600/90 font-semibold"
          title={sortDir === 'asc' ? t('common.sort.asc') || 'По возрастанию' : t('common.sort.desc') || 'По убыванию'}
        >
          {sortDir === 'asc' ? '▲' : '▼'}
        </span>
      )}
      {sortKey !== key && (
        <span className="inline-flex h-4 w-4 items-center justify-center text-[10px] text-slate-300 opacity-0 transition-opacity group-hover/sort:opacity-100 group-focus-visible/sort:opacity-100">↕</span>
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
  const { can } = usePermissions()
  const planLimitModal = usePlanLimitModal()
  const canManage = can('candidates.manage')
  const canViewActivities = can('notifications.view')
  const [recentlyOpenedId, setRecentlyOpenedId] = useState<string | null>(null)
  const restoredScrollRef = useRef(false)
  const restoreAttemptsRef = useRef(0)
  const pendingFullReloadRef = useRef(false)
  const loadDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retriedEmptyItemsRef = useRef(false)
  const loadIdRef = useRef(0)
  const loadInProgressRef = useRef(false)
  const lastSuccessfulListRef = useRef<{
    items: UICandidate[]
    total: number
    insights?: CandidatesListInsights
  } | null>(null)
  const tableContainerRef = useRef<HTMLDivElement | null>(null)
  const getScrollContainer = useCallback((): HTMLElement | null => {
    return scrollContainerRef.current
  }, [])

  const {
    items,
    setItems,
    total,
    setTotal,
    listInsights,
    setListInsights,
    loading,
    setLoading,
    errorText,
    setErrorText,
    load,
  } = useCandidatesTableData({
    candidateListCache,
    cacheKey,
    listStorageKey,
    filtersHydrated,
    limit,
    t,
    q,
    stageFilter,
    statusReasonFilter,
    tagsFilter,
    vacancyFilter,
    managerFilter,
    docsOrderedFilter,
    handoffStatusFilter,
    contactAttemptsFilter,
    processorFilter,
    shadowBucketFilter: digestShadowBucket,
    shadowBucketMinBand: digestShadowMinBand,
    createdRange,
    isFavoriteFilter,
    currentTenantId,
    meTenantId: me?.tenant_id,
    restoredScrollRef,
    operationalQueue,
  })

  useEffect(() => {
    setViewMode(searchParams.get('view') === 'kanban' ? 'kanban' : 'table')
  }, [searchParams])

  useEffect(() => {
    if (!operationalQueue) return
    if (searchParams.get('view') !== 'kanban') return
    const next = new URLSearchParams(searchParams)
    next.delete('view')
    setSearchParams(next, { replace: true })
    setViewMode('table')
  }, [operationalQueue, searchParams, setSearchParams])

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
          if (['none', 'pending', 'accepted', 'returned', 'rejected'].includes(restoredHandoffStatus)) {
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

  const resetCandidatesFiltersCore = useCallback(() => {
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
    } catch {
      /* ignore */
    }
  }, [filterStorageKey])

  const handleResetFilters = useCallback(() => {
    resetCandidatesFiltersCore()
    try {
      const next = new URLSearchParams(searchParams)
      let changed = false
      for (const k of ['shadow_bucket', 'shadow_min_band', 'shadow_bucket_min_band', 'qv'] as const) {
        if (next.has(k)) {
          next.delete(k)
          changed = true
        }
      }
      if (changed) setSearchParams(next, { replace: true })
    } catch {
      /* ignore */
    }
  }, [resetCandidatesFiltersCore, searchParams, setSearchParams])

  // Deep-link from Dashboard pivot: apply URL params.
  // Keep it robust to allow drill-down from Overview/Dashboard widgets.
  useEffect(() => {
    if (!filtersHydrated) return
    const qParam = searchParams.get('q') || searchParams.get('query')
    const stageParam = searchParams.get('stage')
    const vacancyParam = searchParams.get('vacancy_id') || searchParams.get('vacancy')
    const reasonParam = searchParams.get('status_reason')
    const citizenshipParam = searchParams.get('citizenship')
    const managerParam = searchParams.get('manager_id') || searchParams.get('manager')
    const preferredChannelParam = searchParams.get('preferred_channel')
    const opsModeParam = searchParams.get('ops_mode') || searchParams.get('opsMode')
    const inPolandParam = searchParams.get('in_poland')
    const handoffStatusParam = searchParams.get('handoff_status') || searchParams.get('handoffStatus')
    const contactAttemptsParam = searchParams.get('contact_attempts') || searchParams.get('contactAttempts')
    const shadowBucketParam = searchParams.get('shadow_bucket')?.trim() || ''

    const hasDeepLink =
      Boolean(qParam && String(qParam).trim()) ||
      stageParam ||
      vacancyParam ||
      reasonParam ||
      citizenshipParam ||
      managerParam ||
      preferredChannelParam ||
      opsModeParam ||
      inPolandParam ||
      handoffStatusParam ||
      contactAttemptsParam ||
      Boolean(shadowBucketParam)
    if (!hasDeepLink) return
    // Drill-down must be deterministic: ignore previously persisted filters.
    // Do not strip shadow_bucket here (digest drill-down); full reset uses handleResetFilters.
    resetCandidatesFiltersCore()
    if (qParam && String(qParam).trim()) setQ(String(qParam).trim())
    if (stageParam) setStageFilter(normalizeArrayFilter([stageParam]))
    if (vacancyParam) setVacancyFilter(normalizeArrayFilter([vacancyParam]))
    if (reasonParam) setStatusReasonFilter(normalizeReasonList([reasonParam]))
    if (citizenshipParam) setTextFilter('citizenship', String(citizenshipParam).trim())

    if (managerParam) setManagerFilter(normalizeArrayFilter([managerParam]))
    if (preferredChannelParam) setPreferredChannelFilter(normalizeArrayFilter([preferredChannelParam]))
    if (opsModeParam) setOpsModeFilter(normalizeOpsModeList([opsModeParam]))
    if (inPolandParam) setInPolandFilter(normalizeArrayFilter([inPolandParam]))

    if (handoffStatusParam) {
      const v = String(handoffStatusParam).trim()
      if (['none', 'pending', 'accepted', 'returned', 'rejected'].includes(v)) setHandoffStatusFilter(v)
    }
    if (contactAttemptsParam) {
      const v = String(contactAttemptsParam).trim()
      if (['none', 'some', 'limit_reached'].includes(v)) setContactAttemptsFilter(v)
    }
  }, [
    filtersHydrated,
    searchParams,
    normalizeArrayFilter,
    normalizeReasonList,
    normalizeOpsModeList,
    setTextFilter,
    setQ,
    setManagerFilter,
    setPreferredChannelFilter,
    setOpsModeFilter,
    setInPolandFilter,
    setHandoffStatusFilter,
    setContactAttemptsFilter,
    resetCandidatesFiltersCore,
  ])

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
      if (showDebugPanel) {
        console.info('[Candidates] enrichedItems computed: items.length=', items.length, 'enrichedItems.length=', result.length)
      }
      return result
    },
    [items, deriveReasonData, showDebugPanel]
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

    const debugFiltering = showDebugPanel

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
        const candidateManager = getCandidateManagerId(item)
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
  }, [showDebugPanel])

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
        if (showDebugPanel) {
          console.info(
            '[Candidates] filteredItems computed: enrichedItems.length=',
            enrichedItems.length,
            'filtered.length=',
            filtered.length,
            'result.length=',
            result.length,
          )
        }
        return result
      }
    }

    if (showDebugPanel && enrichedItems.length > 0 && filtered.length === 0) {
      console.warn('[Candidates] ALL items filtered out! Active filters:', JSON.stringify(filterSnapshot, null, 2))
      const sampleItem = enrichedItems[0]
      const sampleIsFavorite = sampleItem.is_favorite ?? false
      console.warn('[Candidates] Sample item for debugging:', {
        id: sampleItem.id,
        stage: sampleItem.stage,
        vacancy_id: (sampleItem as any)?.vacancy_id || (sampleItem as any)?.vacancy?.id,
        manager_id: getCandidateManagerId(sampleItem),
        tags: sampleItem.tags,
        is_favorite: sampleItem.is_favorite,
        is_favorite_raw: sampleItem.is_favorite,
        filter_isFavorite: filterSnapshot.isFavorite,
        matches_isFavorite:
          filterSnapshot.isFavorite === null ||
          filterSnapshot.isFavorite === undefined ||
          filterSnapshot.isFavorite === sampleIsFavorite,
        created_at: sampleItem.created_at,
        __docsMeta: sampleItem.__docsMeta,
        __extra: sampleItem.__extra,
      })
      const favoriteCount = enrichedItems.filter((item) => (item.is_favorite ?? false) === true).length
      console.warn('[Candidates] Items with is_favorite=true:', favoriteCount, 'out of', enrichedItems.length)
    }
    if (showDebugPanel) {
      console.info('[Candidates] filteredItems computed: enrichedItems.length=', enrichedItems.length, 'filtered.length=', filtered.length)
    }
    return filtered
  }, [enrichedItems, filterSnapshot, filterCandidates, showDebugPanel])

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

  /** Карточки инсайтов: с сервера по фильтрам списка; иначе fallback по загруженным строкам (старый API без include_insights). */
  const insightSource = useMemo(() => {
    if (listInsights) {
      return {
        total: listInsights.total,
        newCount: listInsights.new_count,
        docsReady: listInsights.docs_ready,
        docsAttention: listInsights.docs_attention,
      }
    }
    return {
      total: candidateInsights.total,
      newCount: candidateInsights.newCount,
      docsReady: candidateInsights.docsReady,
      docsAttention: candidateInsights.docsAttention,
    }
  }, [listInsights, candidateInsights])

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
        case 'risk_score':
          // backend may send null; treat as 0 for sorting
          cmp = compareNumbers(a.risk_score ?? 0, b.risk_score ?? 0)
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
    if (showDebugPanel) {
      console.info('[Candidates] displayedItems computed: filteredItems.length=', filteredItems.length, 'sorted.length=', sorted.length)
    }
    return sorted
  }, [filteredItems, sortKey, sortDir, showDebugPanel])

  const selectedCandidate = useMemo(() => {
    const base =
      selectedCandidateId ? displayedItems.find((c) => c.id === selectedCandidateId) ?? null : null
    if (!base) return null
    if (!previewCandidateExtra) return base
    const ex = previewCandidateExtra
    return {
      ...base,
      contact_policy_enabled: ex.contact_policy_enabled,
      contact_attempt_count: ex.contact_attempt_count,
      risk_score: ex.risk_score !== undefined ? ex.risk_score : (base as any).risk_score,
      risk_band: ex.risk_band !== undefined ? ex.risk_band : (base as any).risk_band,
      risk_drivers: ex.risk_drivers !== undefined ? ex.risk_drivers : (base as any).risk_drivers,
      risk_updated_at: ex.risk_updated_at !== undefined ? ex.risk_updated_at : (base as any).risk_updated_at,
      risk_version: ex.risk_version !== undefined ? ex.risk_version : (base as any).risk_version,
    }
  }, [displayedItems, selectedCandidateId, previewCandidateExtra])

  const openActivitiesModal = useCallback(() => {
    setActivitiesModalRefresh((n) => n + 1)
    setActivitiesModalOpen(true)
  }, [])

  const docsOwnerContext = useMemo(() => {
    const citizenship = String((selectedCandidate as any)?.__extra?.citizenship || '')
    return { citizenship }
  }, [(selectedCandidate as any)?.__extra?.citizenship])

  // Preview side-panel state + handlers are centralized in `useCandidatesWorkPanelPreview`.

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
      case 'risk':
        return <>{renderSortButton(columnLabelMap.risk, 'risk_score')}</>
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
    const className = clsx(
      'group py-2.5 border-r border-slate-200 align-middle whitespace-nowrap',
      columnKey === 'checkbox' ? 'px-4' : tableLayoutCustomize ? 'pl-7 pr-4' : 'px-4',
      isSticky ? 'sticky bg-slate-50 z-[25]' : 'relative',
      'cursor-default',
      tableLayoutCustomize &&
        dragOverColumn === columnKey &&
        draggingColumn &&
        draggingColumn !== columnKey &&
        'bg-brand-100/70',
      // thead с pointer-events:none — интерактив в ячейках должен снова ловить события
      'pointer-events-auto',
    )

    const dynamicStyle: React.CSSProperties = {
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

    if (!tableLayoutCustomize) {
      return (
        <th className={className} style={dynamicStyle}>
          <div className="flex h-5 min-w-0 w-full items-center gap-1.5 overflow-hidden whitespace-nowrap">{content}</div>
        </th>
      )
    }

    return (
      <th
        className={className}
        style={dynamicStyle}
        onDragOver={(e) => {
          if (!draggingColumn || draggingColumn === columnKey) return
          e.preventDefault()
          e.dataTransfer.dropEffect = 'move'
          if (dragOverColumn !== columnKey) setDragOverColumn(columnKey)
        }}
        onDrop={(e) => {
          e.preventDefault()
          const from = draggingColumn || e.dataTransfer.getData('text/plain')
          if (from) reorderColumns(from, columnKey)
          setDragOverColumn(null)
          setDraggingColumn(null)
        }}
        onDragLeave={() => {
          if (dragOverColumn === columnKey) setDragOverColumn(null)
        }}
      >
        <div className="flex h-5 items-center justify-between gap-2">
          <div className="flex h-5 min-w-0 w-full items-center gap-1.5 overflow-hidden whitespace-nowrap">
            <span
              role="button"
              tabIndex={0}
              draggable
              className="absolute left-1 top-1/2 inline-flex h-5 w-5 -translate-y-1/2 cursor-grab select-none items-center justify-center rounded text-slate-300 opacity-0 transition hover:bg-slate-200 hover:text-slate-600 group-hover:opacity-100 active:cursor-grabbing"
              title={t('app.candidates.table.reorder_column') || 'Перетащите, чтобы поменять порядок колонок'}
              onDragStart={(e) => {
                setDraggingColumn(columnKey)
                setDragOverColumn(null)
                e.dataTransfer.effectAllowed = 'move'
                e.dataTransfer.setData('text/plain', columnKey)
              }}
              onDragEnd={() => {
                setDraggingColumn(null)
                setDragOverColumn(null)
              }}
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                }
              }}
            >
              ⋮⋮
            </span>
            <div className="flex h-5 min-w-0 items-center gap-1.5 overflow-hidden whitespace-nowrap">{content}</div>
          </div>
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

  const legacyLoad = useCallback(async (options?: { force?: boolean; allowCache?: boolean }) => {
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
      setListInsights(cached.insights ?? null)
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
    const perfT0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
    let perfOk = true
    try{
      let nextOffset = 0
      let accumulated: UICandidate[] = []
      let totalCount: number | null = null
      let keepFetching = true
      /** Агрегаты с сервера — только с первой страницы (include_insights). */
      let normalizedInsights: CandidatesListInsights | null = null

      while (keepFetching) {
        const params: Record<string, any> = {
          limit,
          offset: nextOffset,
          order_by: 'created_at',
          desc: true,
          compact: true,
          include_risk: true,
          include_insights: nextOffset === 0,
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
        if (digestShadowBucket && digestShadowMinBand) {
          params.shadow_bucket_start = digestShadowBucket
          params.shadow_bucket_min_band = digestShadowMinBand
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
        const effectiveBatch =
          limit > 1 && typeof dataAny?.total === 'number' && dataAny.total > 1 && batch.length === 1
            ? []
            : batch
        if (effectiveBatch.length === 0 && batch.length === 1) {
          console.warn('[Candidates] ignoring response with 1 item (requested limit=', limit, ', total=', dataAny?.total, ')')
        }

        if (nextOffset === 0) {
          normalizedInsights = normalizeListInsights(dataAny?.insights)
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
      const persistOk = finalTotal === 0 || accumulated.length > 0
      if (persistOk) {
        const cachedEntry: CandidateListCacheEntry = {
          items: accumulated,
          total: finalTotal,
          timestamp: Date.now(),
          ...(normalizedInsights ? { insights: normalizedInsights } : {}),
        }
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
        setItems(accumulated)
        setListInsights(normalizedInsights)
      } else {
        console.warn('[Candidates] NOT applying state: myLoadId', myLoadId, '!= current', loadIdRef.current)
      }
      if (accumulated.length > 0) {
        lastSuccessfulListRef.current = {
          items: accumulated,
          total: finalTotal,
          ...(normalizedInsights ? { insights: normalizedInsights } : {}),
        }
        const toApply = accumulated.slice()
        const tot = finalTotal
        const ins = normalizedInsights
        queueMicrotask(() => {
          setItems(toApply)
          setTotal(tot)
          setListInsights(ins)
        })
      }
    } catch (e: any) {
      perfOk = false
      const errorInfo = getErrorInfo(e)
      if (myLoadId === loadIdRef.current) {
        setErrorText(
          getFriendlyErrorInfo(
            e,
            t('app.candidates.messages.load_failed') || 'Не удалось загрузить список кандидатов',
            t,
          ),
        )
        setItems([])
        setTotal(0)
        setListInsights(null)
      }
      console.error('[Candidates] Load error:', errorInfo)
    } finally {
      const durationMs = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - perfT0
      if (willRefetch) {
        void recordPerfMeasurement({
          metricKey: 'candidates.list.load',
          durationMs,
          route: typeof window !== 'undefined' ? `${window.location.pathname}${window.location.search}` : undefined,
          meta: { ok: perfOk, limit, cache: !willRefetch ? 'fresh' : 'refetch' },
        }).catch(() => {})
      }
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
    digestShadowBucket,
    digestShadowMinBand,
    createdRange,
    firstContactRange,
    docsValidRange,
    isFavoriteFilter,
  ])

  // Transitional: legacy load implementation is kept for now,
  // but real fetches now go through the SSOT hook `useCandidatesTableData.load`.
  void legacyLoad

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

  // Обновляем список при возврате на страницу (например, после редактирования кандидата)
  useEffect(() => {
    const currentPath = location.pathname
    const prevPath = prevLocationRef.current
    
    // Если вернулись на страницу списка с другой страницы (например, с карточки кандидата)
    if (prevPath && prevPath !== currentPath && currentPath === CRM_APP_PATHS.candidates) {
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

  const { persistScrollState, restoreScrollState } = useCandidatesScrollRestoration({
    displayedItems,
    setRecentlyOpenedId,
    getScrollContainer,
    outerScrollRef,
    scrollKey,
    restoredScrollRef,
    restoreAttemptsRef,
  })

  const handleCandidateOpen = useCallback(
    (id: string) => {
      setRecentlyOpenedId(id)
      persistScrollState(id)
    },
    [persistScrollState]
  )

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
  }, [])

  // Сбрасываем флаг восстановления при изменении пути (возврат к списку)
  // И читаем returnFromCandidateId из location.state (при возврате из CandidateCard)
  useEffect(() => {
    const isOnCandidatesList = location.pathname === CRM_APP_PATHS.candidates
    if (isOnCandidatesList) {
      restoredScrollRef.current = false
      restoreAttemptsRef.current = 0
      const returnId = (location.state as { returnFromCandidateId?: string } | null)?.returnFromCandidateId
      if (returnId) setRecentlyOpenedId(returnId)
    }
  }, [location.pathname, location.state])

  // (debug removed)

  useEffect(() => {
    if (!filtersHydrated) return
    if (loading) return
    // При открытом превью кандидата не восстанавливаем скролл по сохраненному
    // состоянию: это вызывает scrollTo/scrollIntoView и провоцирует
    // пере-рендер/виртуализацию ровно в момент взаимодействия с таблицей.
    if (selectedCandidateId) return
    restoreScrollState()
  }, [filtersHydrated, loading, restoreScrollState, items.length, recentlyOpenedId, selectedCandidateId])

  // Диагностика "что перекрывает таблицу":
  // при ?debug=1 на клик показываем DOM-элемент под курсором.
  // ВАЖНО: не вызывать setState синхронно в capture на window для mousedown —
  // это перерисовывает Candidates до фазы target, TableVirtuoso пересобирает DOM,
  // и onMouseDown/onClick на кнопках в таблице не срабатывают (ложный "оверлей").
  useEffect(() => {
    if (!showDebugPanel) return
    const onMouseDownCapture = (e: MouseEvent) => {
      const x = e.clientX
      const y = e.clientY
      queueMicrotask(() => {
        const hit = document.elementFromPoint(x, y) as HTMLElement | null
        const table = tableContainerRef.current
        const insideTable = hit ? Boolean(table?.contains(hit)) : false
        const style = hit ? window.getComputedStyle(hit) : null
        setDebugHit({
          tag: hit?.tagName,
          className: hit?.className ? String(hit.className).slice(0, 120) : undefined,
          pointerEvents: style?.pointerEvents,
          insideTable,
        })
      })
    }

    const onClickCapture = (e: MouseEvent) => {
      const x = e.clientX
      const y = e.clientY
      queueMicrotask(() => {
        const hit = document.elementFromPoint(x, y) as HTMLElement | null
        const table = tableContainerRef.current
        const insideTable = hit ? Boolean(table?.contains(hit)) : false
        const style = hit ? window.getComputedStyle(hit) : null
        setDebugClickHit({
          tag: hit?.tagName,
          className: hit?.className ? String(hit.className).slice(0, 120) : undefined,
          pointerEvents: style?.pointerEvents,
          insideTable,
        })
      })
    }

    const onClickBubble = (e: MouseEvent) => {
      const x = e.clientX
      const y = e.clientY
      queueMicrotask(() => {
        const hit = document.elementFromPoint(x, y) as HTMLElement | null
        const table = tableContainerRef.current
        const insideTable = hit ? Boolean(table?.contains(hit)) : false
        const style = hit ? window.getComputedStyle(hit) : null
        setDebugClickHitBubble({
          tag: hit?.tagName,
          className: hit?.className ? String(hit.className).slice(0, 120) : undefined,
          pointerEvents: style?.pointerEvents,
          insideTable,
        })
      })
    }

    const onMouseUpCapture = (e: MouseEvent) => {
      const x = e.clientX
      const y = e.clientY
      queueMicrotask(() => {
        const hit = document.elementFromPoint(x, y) as HTMLElement | null
        const table = tableContainerRef.current
        const insideTable = hit ? Boolean(table?.contains(hit)) : false
        const style = hit ? window.getComputedStyle(hit) : null
        setDebugMouseUpHit({
          tag: hit?.tagName,
          className: hit?.className ? String(hit.className).slice(0, 120) : undefined,
          pointerEvents: style?.pointerEvents,
          insideTable,
        })
      })
    }

    const onMouseUpBubble = (e: MouseEvent) => {
      const x = e.clientX
      const y = e.clientY
      queueMicrotask(() => {
        const hit = document.elementFromPoint(x, y) as HTMLElement | null
        const table = tableContainerRef.current
        const insideTable = hit ? Boolean(table?.contains(hit)) : false
        const style = hit ? window.getComputedStyle(hit) : null
        setDebugMouseUpHitBubble({
          tag: hit?.tagName,
          className: hit?.className ? String(hit.className).slice(0, 120) : undefined,
          pointerEvents: style?.pointerEvents,
          insideTable,
        })
      })
    }

    window.addEventListener('mousedown', onMouseDownCapture, true)
    window.addEventListener('click', onClickCapture, true)
    window.addEventListener('click', onClickBubble, false)
    window.addEventListener('mouseup', onMouseUpCapture, true)
    window.addEventListener('mouseup', onMouseUpBubble, false)
    return () => {
      window.removeEventListener('mousedown', onMouseDownCapture, true)
      window.removeEventListener('click', onClickCapture, true)
      window.removeEventListener('click', onClickBubble, false)
      window.removeEventListener('mouseup', onMouseUpCapture, true)
      window.removeEventListener('mouseup', onMouseUpBubble, false)
    }
  }, [showDebugPanel])

  // Состояние для клавиатурной навигации
  // На случай drag-to-select: запоминаем координаты mousedown на строке,
  // чтобы onClick по строке не срабатывал после выделения текста.
  const lastRowMouseDownRef = useRef<{ x: number; y: number; t: number } | null>(null)

  const toggle = useCallback((id: string) => {
    if (!canManage) return
    setChecked((s) => ({ ...s, [id]: !s[id] }))
  }, [canManage])

  const { focusedRowIndex, focusedRowRef } = useCandidatesTableKeyboardNavigation({
    searchRef,
    canManage,
    displayedItems,
    checked,
    setChecked,
    toggle,
    handleCandidateOpen,
    navigate,
  })

  // (toggle moved above keyboard hook)

  const allSelected = useCallback(() => {
    return items.filter(i => checked[i.id]).map(i => i.id)
  }, [items, checked])

  const [bulkOperationLoading, setBulkOperationLoading] = useState<string | null>(null) // 'stage' | 'manager' | 'vacancy' | 'handoff' | 'tags' | 'activities' | null

  async function doBulkActivities() {
    const ids = allSelected()
    if (ids.length === 0 || !bulkActivityTitle.trim() || !bulkActivityDueAt) return
    setBulkOperationLoading('activities')
    try {
      const due = new Date(bulkActivityDueAt)
      const remindAt = new Date(due.getTime() - bulkActivityOffsetMinutes * 60 * 1000)
      const res = await createBulkActivities({
        title: bulkActivityTitle.trim(),
        description: '',
        type: bulkActivityType,
        entity_type: 'candidate',
        entity_ids: ids,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        source: 'bulk',
        priority: 'normal',
      })
      const results: Array<{ entity_id?: string; ok?: boolean; error?: string }> = Array.isArray(res?.results) ? res.results : []
      const failures = results.filter((r) => r && r.ok === false)
      setBulkActivitiesOpen(false)
      if (failures.length > 0) {
        alert(
          t('app.candidates.messages.bulk_activities_partial', {
            defaultValue: 'Created with errors: {{failed}} failed out of {{total}}.',
            values: { failed: failures.length, total: ids.length },
          }),
        )
      } else {
        setChecked({})
      }
    } catch (e: any) {
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          e,
          t('app.candidates.messages.bulk_activities_failed', { defaultValue: 'Failed to create activities' }),
        )
      ) {
        return
      }
      alert(
        formatErrorForDisplay(e, {
          fallback: t('app.candidates.messages.bulk_activities_failed', { defaultValue: 'Failed to create activities' }),
          includeStatusCode: false,
        }),
      )
    } finally {
      setBulkOperationLoading(null)
    }
  }

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
        const contactAttemptFailures = failures.filter((item) => {
          const parsed = parseErrorObject(item?.error)
          return String(parsed?.code || '') === 'stage_blocked_by_contact_attempt'
        })
        const vacancyGateFailures = failures.filter((item) => {
          const parsed = parseErrorObject(item?.error)
          return String(parsed?.code || '') === 'stage_blocked_by_vacancy'
        })
        const pipelineDocFailures = failures.filter((item) => {
          const parsed = parseErrorObject(item?.error)
          return String(parsed?.code || '') === 'stage_blocked_by_documents'
        })
        const riskGateFailures = failures.filter((item) => {
          const parsed = parseErrorObject(item?.error)
          return String(parsed?.code || '') === 'stage_blocked_by_risk_gate'
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
        } else if (contactAttemptFailures.length > 0) {
          alert(
            t('app.candidates.messages.bulk_stage_contact_attempt_blocked', {
              defaultValue:
                '{contact} candidate(s) need a logged contact attempt (client policy) out of {total} failures. Open cards, register an attempt, then retry.',
              values: { contact: contactAttemptFailures.length, total: failures.length },
            }),
          )
        } else if (vacancyGateFailures.length > 0) {
          alert(
            t('app.candidates.messages.bulk_stage_vacancy_blocked', {
              defaultValue:
                '{vacancy} candidate(s) must be linked to a vacancy before that stage change ({total} failures). Assign vacancy on the card, then retry.',
              values: { vacancy: vacancyGateFailures.length, total: failures.length },
            }),
          )
        } else if (pipelineDocFailures.length > 0) {
          alert(
            t('app.candidates.messages.bulk_stage_pipeline_docs_blocked', {
              defaultValue:
                '{docs} candidate(s) are blocked by required documents ({total} failures). Fix documents on the card, then retry.',
              values: { docs: pipelineDocFailures.length, total: failures.length },
            }),
          )
        } else if (riskGateFailures.length > 0) {
          alert(
            t('app.candidates.messages.bulk_stage_risk_gate_blocked', {
              defaultValue:
                '{risk} candidate(s) are blocked by risk policy: add a next-action reminder or adjust risk_model_v1.stage_gate ({total} failures).',
              values: { risk: riskGateFailures.length, total: failures.length },
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
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          e,
          t('app.candidates.messages.bulk_stage_failed') || 'Не удалось изменить этап кандидатов',
        )
      ) {
        return
      }
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
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          e,
          t('app.candidates.messages.bulk_manager_failed') || 'Не удалось назначить менеджера',
        )
      ) {
        return
      }
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
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          e,
          t('app.candidates.messages.bulk_vacancy_failed') || 'Не удалось назначить вакансию',
        )
      ) {
        return
      }
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
        candidate_ids: ids,
        client_company_id: bulkHandoffClientId,
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
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          e,
          t('app.candidates.modals.handoff.failed', { defaultValue: 'Nie udało się przekazać do klienta' }),
        )
      ) {
        return
      }
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
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          e,
          t('app.candidates.messages.bulk_tags_failed') || 'Не удалось обновить теги',
        )
      ) {
        return
      }
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
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          e,
          t('app.candidates.messages.bulk_delete_failed') || 'Не удалось удалить кандидатов',
        )
      ) {
        return
      }
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

  const {
    quickViewParam,
    quickFiltersExpanded,
    setQuickFiltersExpanded,
    quickDocFilters,
    toggleQuickDocFilter,
    applyQuickViewFilters,
  } = useCandidatesQuickViews({
    t,
    navigate,
    searchParams,
    setSearchParams,
    filtersHydrated,
    handleResetFilters,
    preferredManagerId,
    docsStatusFilter,
    setDocsStatusFilter,
    setManagerFilter,
    setCreatedRange,
    setHandoffStatusFilter,
  })

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
    Boolean(digestShadowBucket) ||
    !!processorFilter ||
    Boolean(operationalQueue) ||
    isRangeActive(createdRange) ||
    isRangeActive(firstContactRange) ||
    isRangeActive(docsValidRange) ||
    Object.values(textFilters).some((value) => value.trim().length > 0)

  const changeView = (mode: 'table' | 'kanban') => {
    if (mode === 'kanban' && operationalQueue) return
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
          isKanban ? 'bg-brand-600 text-white shadow-sm' : 'text-brand-700 hover:bg-brand-50',
          operationalQueue && 'cursor-not-allowed opacity-50',
        )}
        disabled={Boolean(operationalQueue)}
        title={
          operationalQueue
            ? t('app.candidates.no_next_action.kanban_disabled_hint', {
                defaultValue: 'Pipeline view is unavailable for this queue. Clear the queue filter to use kanban.',
              })
            : undefined
        }
        onClick={() => changeView('kanban')}
      >
        {t('app.candidates.views.kanban')}
      </button>
    </div>
  )
  const {
    heroExpanded,
    setHeroExpanded,
    insightCards,
    handleInsightDrillDown,
  } = useCandidatesInsightsHero({
    t,
    insightSource,
    enrichedItems,
    handleResetFilters,
    setStageFilter,
    setDocsStatusFilter,
  })

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
  useEffect(() => {
    if (!contextMenu) return
    const exists = displayedItems.some((candidate) => candidate.id === contextMenu.candidateId)
    if (!exists) setContextMenu(null)
  }, [contextMenu, displayedItems])

  const summaryHero = (
    <CandidatesSummaryHero
      title={t('app.candidates.insights.title')}
      subtitle={t('app.candidates.insights.subtitle')}
      expandLabel={t('common.actions.expand')}
      collapseLabel={t('common.actions.collapse')}
      expanded={heroExpanded}
      cards={insightCards}
      onToggleExpanded={() => setHeroExpanded((prev) => !prev)}
      onCardClick={(key) => handleInsightDrillDown(key as 'total' | 'new' | 'docs_ready' | 'docs_attention')}
      headerActions={
        canViewActivities ? (
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold text-slate-700 shadow-sm hover:border-brand-300 hover:bg-brand-50/50"
            onClick={openActivitiesModal}
            title={t('app.nav.items.tasks', { defaultValue: 'Tasks' })}
          >
            <IconListCheck size={14} className="text-slate-500" aria-hidden />
            {t('app.nav.items.tasks', { defaultValue: 'Tasks' })}
          </button>
        ) : null
      }
    />
  )

  const visibleCandidatesCount = displayedItems.length
  const hasActiveTableFilters =
    hasFilterBadges ||
    isFavoriteFilter === true ||
    isFavoriteFilter === false ||
    Boolean(quickViewParam) ||
    Boolean(operationalQueue)
  const showsFilteredCount = total > 0 && visibleCandidatesCount !== total

  if (isKanban) {
    return <Pipeline />
  }

  const renderCandidateRowTds = (index: number, item: AugmentedCandidate) => {
            const c = item as AugmentedCandidate
            const docsMeta = c.__docsMeta
            const reasonTags = c.__reasonCodes
            const fallbackReasons = c.__reasonFallbackLabels
            const isFocused = focusedRowIndex === index
            const isWorkPanelRow = Boolean(workPanelOpen && selectedCandidateId === c.id)
            return (
              <>
                {/* Без sticky на body-cells: любой sticky у tbody + sticky thead в Virtuoso давал битый hit-testing (клики/mouseup уходили в шапку). */}
                <CandidatesTableCheckboxCell
                  c={c}
                  isFocused={isFocused}
                  isWorkPanelRow={isWorkPanelRow}
                  checked={checked}
                  canManage={canManage}
                  toggle={toggle}
                  t={t}
                />
                {orderedVisibleColumns.map((columnKey) => {
                  if (!visibleCols[columnKey]) return null
                  
                  let cellContent: ReactNode = null

                  if (columnKey === 'name') {
                    const candidateLabel =
                      (c as AugmentedCandidate).masked === true
                        ? (c.short_id
                            ? t('app.candidates.table.masked_label_short_id', { defaultValue: 'Кандидат {short_id}', values: { short_id: c.short_id } })
                            : t('app.candidates.table.masked_label', { defaultValue: 'Кандидат #{id}', values: { id: (c.id ?? '').slice(0, 8) } }))
                        : `${c.first_name ?? ''} ${c.last_name ?? ''}`.trim() || t('common.labels.not_available')
                    const isMasked = (c as AugmentedCandidate).masked === true
                    const cardHref = `${CRM_APP_PATHS.candidates}/${c.id}`
                    const emailForActions = !isMasked ? String(c.email || '').trim() : ''
                    const phoneForTel =
                      !isMasked && c.phone && String(c.phone).trim() !== '' ? asTelHref(c.phone) : undefined
                    const tasksSearchQ = encodeURIComponent(
                      String(candidateLabel || c.id || '').slice(0, 80),
                    )
                    const tasksHref = `${CRM_APP_PATHS.tasks}?tab=tasks&t_status=active&t_entity=candidate&t_q=${tasksSearchQ}`
                    const rowActionBtnClass =
                      'inline-flex items-center gap-0.5 rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-800 shadow-sm hover:border-brand-300 hover:bg-brand-50/80'
                    cellContent = (
                      <div className="group/name flex min-w-0 flex-col gap-1">
                        <div className="flex min-w-0 items-center gap-1.5">
                          <div className="min-w-0 flex-1 overflow-hidden">
                            <Link
                              to={cardHref}
                              className="block truncate whitespace-nowrap font-medium text-brand-600 hover:text-brand-700 hover:underline"
                              onClick={(e) => {
                                e.preventDefault()
                                handleCandidateOpen(c.id)
                                navigate(cardHref)
                              }}
                              title={
                                t('app.candidates.table.open_card') ||
                                ((c as AugmentedCandidate).masked === true
                                  ? t('app.candidates.table.open_card_masked', { defaultValue: 'Открыть карточку кандидата' })
                                  : `Открыть карточку кандидата ${c.first_name} ${c.last_name}`)
                              }
                            >
                              {candidateLabel}
                            </Link>
                          </div>
                          <CandidatesTableRowNamePreview
                            c={c}
                            isFocused={isFocused}
                            selectedCandidateId={selectedCandidateId}
                            workPanelOpen={workPanelOpen}
                            setSelectedCandidateId={setSelectedCandidateId}
                            setSidebarOpen={setSidebarOpen}
                            t={t}
                          />
                        </div>
                        {isMasked ? (
                          <div
                            className="truncate text-xs text-slate-500"
                            title={
                              c.short_id || ((c as AugmentedCandidate).masked && (c.id ?? '').slice(0, 8))
                                ? `Short ID: ${c.short_id || (c.id ?? '').slice(0, 8)}`
                                : undefined
                            }
                          >
                            {c.short_id ? `ID ${c.short_id}` : `ID ${(c.id ?? '').slice(0, 8)}`}
                          </div>
                        ) : null}
                        <div className="mt-1 flex flex-wrap gap-1 border-t border-slate-100 pt-1.5">
                          {phoneForTel ? (
                            <a href={phoneForTel} className={rowActionBtnClass}>
                              <IconPhone size={11} stroke={2} className="shrink-0 text-slate-600" aria-hidden />
                              {t('app.candidates.pipeline.action_call', { defaultValue: 'Call' })}
                            </a>
                          ) : null}
                          {emailForActions ? (
                            <a href={`mailto:${emailForActions}`} className={rowActionBtnClass}>
                              <IconMail size={11} stroke={2} className="shrink-0 text-slate-600" aria-hidden />
                              {t('app.candidates.pipeline.action_write', { defaultValue: 'Email' })}
                            </a>
                          ) : null}
                          <Link
                            to={cardHref}
                            className={rowActionBtnClass}
                            onClick={(e) => {
                              e.preventDefault()
                              handleCandidateOpen(c.id)
                              navigate(cardHref)
                            }}
                          >
                            <IconArrowRight size={11} stroke={2} className="shrink-0 text-slate-600" aria-hidden />
                            {t('app.candidates.pipeline.action_open_card', { defaultValue: 'Open' })}
                          </Link>
                          {canViewActivities ? (
                            <Link to={tasksHref} className={rowActionBtnClass}>
                              {t('app.candidates.pipeline.action_tasks', { defaultValue: 'Tasks' })}
                            </Link>
                          ) : null}
                        </div>
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
                    cellContent = <CandidatesTableRowStageCell candidate={c} />
                  } else if (columnKey === 'risk') {
                    const score = (c as any).risk_score
                    const bandRaw: string | null | undefined = (c as any).risk_band
                    const band =
                      bandRaw ||
                      (typeof score === 'number'
                        ? score >= 85
                          ? 'critical'
                          : score >= 65
                            ? 'high'
                            : score >= 35
                              ? 'medium'
                              : 'low'
                        : null)

                    const bandLabel =
                      band === 'critical'
                        ? 'Критический'
                        : band === 'high'
                          ? 'Высокий'
                          : band === 'medium'
                            ? 'Средний'
                            : band === 'low'
                              ? 'Низкий'
                              : '—'

                    const drivers: string[] = Array.isArray((c as any).risk_drivers) ? (c as any).risk_drivers : []
                    const tooltip = drivers.length ? drivers.join(' | ') : undefined
                    const badgeCls =
                      band === 'critical'
                        ? 'bg-red-50 text-red-700 border-red-200'
                        : band === 'high'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : band === 'medium'
                            ? 'bg-amber-50 text-amber-700 border-amber-200'
                            : band === 'low'
                              ? 'bg-slate-100 text-slate-700 border-slate-200'
                              : 'bg-slate-50 text-slate-500 border-slate-200'

                    cellContent =
                      typeof score === 'number' ? (
                        <div className="flex items-center gap-2">
                          <span className={clsx('text-[11px] px-2 py-0.5 rounded border font-medium truncate', badgeCls)} title={tooltip}>
                            {bandLabel}
                          </span>
                          <span className="text-[11px] text-slate-500">{score}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )
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
                            if (
                              planLimitModal?.showPlanLimitIfNeeded(
                                err,
                                t('app.candidates.messages.favorite_toggle_failed'),
                              )
                            ) {
                              return
                            }
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
                      const readinessKey = String(docsMeta.readinessState)
                      const meta = DOC_READINESS_META[readinessKey] || DOC_READINESS_META.pending
                      const docsRequestTitle = t('app.candidate_card.next_action.docs_request_title', {
                        defaultValue: 'Request documents',
                      })

                      // Operational hint: when docs are not ready, the next loop is typically requesting/processing documents.
                      const showNextHint = readinessKey !== 'ready' && readinessKey !== 'ordered'

                      cellContent = (
                        <div className="flex flex-col gap-0.5 min-w-0">
                          <span className={clsx('text-xs px-2 py-0.5 rounded', meta.className)}>
                            {t(meta.labelKey)}
                          </span>
                          {showNextHint ? (
                            <span className="text-[10px] text-slate-500 truncate">→ {docsRequestTitle}</span>
                          ) : null}
                        </div>
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
                        'border-r border-slate-200',
                        // Name column: quick actions stay inside the cell (no bleed into neighbors).
                        'overflow-hidden',
                        // Compact operational defaults: reduce padding in the most-used columns.
                        ['stage', 'docsStatus', 'vacancy', 'manager'].includes(columnKey)
                          ? 'px-3 py-2.5 align-middle'
                          : 'px-4 py-2.5 align-middle',
                        isFocused ? 'bg-brand-100' : isWorkPanelRow ? 'bg-brand-50/90' : 'bg-white',
                        columnKey === 'name' && "font-medium"
                      )}
                      style={{
                        width: `${getColumnWidth(columnKey)}px`,
                        minWidth: `${getColumnWidth(columnKey)}px`,
                        maxWidth: `${getColumnWidth(columnKey)}px`
                      } as React.CSSProperties}
                    >
                      <div
                        className="min-w-0 overflow-hidden"
                        title={typeof cellContent === 'string' ? cellContent : undefined}
                      >
                        {cellContent}
                      </div>
                    </td>
                  )
                })}
              </>
            )
  }

  return (
    <div
      data-hf-ui="candidates-native-table-v7-grid-rail"
      className="relative flex min-h-0 flex-1 flex-col overflow-hidden"
    >
      {/* R1.P0: отдельная grid-колонка под rail, без absolute — стабильный hit-testing. Ширина: `CANDIDATES_WORK_PANEL_RAIL_WIDTH_PX`. */}
      <div
        className="grid min-h-0 min-w-0 flex-1"
        style={
          workPanelOpen
            ? {
                gridTemplateColumns: `minmax(0, 1fr) ${CANDIDATES_WORK_PANEL_RAIL_WIDTH_PX}px`,
              }
            : undefined
        }
      >
        <div className="flex min-h-0 min-w-0 flex-col overflow-hidden">
        <div
          ref={tableContainerRef}
          className="flex-1 min-h-0 overflow-hidden flex flex-col"
          data-candidates-table-container
        >
          {/* Debug: client view handoffs (only when ?debug=1, uses same auth as list) */}
          {showDebugPanel && (
            <div className="mx-4 mt-2 mb-2 p-3 rounded-lg border border-amber-200 bg-amber-50 text-sm">
              <div className="font-medium text-amber-900 mb-2">
                {t('app.candidates.debug.client_view', { defaultValue: 'Debug: client view' })}
              </div>
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
                      setDebugClientViewError(e?.response?.data?.detail ?? e?.message ?? t('common.errors.request_failed', { defaultValue: 'Request failed' }))
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
                      setDebugClientViewError(e?.response?.data?.detail ?? e?.message ?? t('common.errors.request_failed', { defaultValue: 'Request failed' }))
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

              {debugHit && (
                <div className="mt-2 p-2 rounded border border-amber-200 bg-amber-100/50">
                  <div className="text-xs font-semibold text-amber-900 mb-1">
                    {t('app.candidates.debug.mousedown_hit', { defaultValue: 'Debug: mousedown hit' })}
                  </div>
                  <div className="text-[11px] text-amber-900">
                    <div>
                      tag: <span className="font-mono">{debugHit.tag ?? '—'}</span>
                    </div>
                    <div>
                      pointer-events: <span className="font-mono">{debugHit.pointerEvents ?? '—'}</span>
                    </div>
                    <div>
                      insideTable: <span className="font-mono">{String(Boolean(debugHit.insideTable))}</span>
                    </div>
                    {debugHit.className ? (
                      <div className="mt-1">
                        class: <span className="font-mono">{debugHit.className}</span>
                      </div>
                    ) : null}
                  </div>
                </div>
              )}

              {debugClickHit && (
                <div className="mt-2 p-2 rounded border border-indigo-200 bg-indigo-100/40">
                  <div className="text-xs font-semibold text-indigo-900 mb-1">
                    {t('app.candidates.debug.click_after_mousedown', { defaultValue: 'Debug: click AFTER mousedown' })}
                  </div>
                  <div className="text-[11px] text-indigo-900">
                    <div>
                      tag: <span className="font-mono">{debugClickHit.tag ?? '—'}</span>
                    </div>
                    <div>
                      pointer-events: <span className="font-mono">{debugClickHit.pointerEvents ?? '—'}</span>
                    </div>
                    <div>
                      insideTable: <span className="font-mono">{String(Boolean(debugClickHit.insideTable))}</span>
                    </div>
                    {debugClickHit.className ? (
                      <div className="mt-1">
                        class: <span className="font-mono">{debugClickHit.className}</span>
                      </div>
                    ) : null}
                  </div>
                </div>
              )}

              {showDebugPanel && (
                <div className="mt-2 p-2 rounded border border-slate-200 bg-white/60">
                  <div className="text-xs font-semibold text-slate-900 mb-1">
                    {t('app.candidates.debug.current_preview_state', { defaultValue: 'Debug: current preview state' })}
                  </div>
                  <div className="text-[11px] text-slate-900">
                    <div>
                      sidebarOpen: <span className="font-mono">{String(sidebarOpen)}</span>
                    </div>
                    <div>
                      selectedCandidateId: <span className="font-mono">{selectedCandidateId ?? 'null'}</span>
                    </div>
                  </div>
                </div>
              )}

              {debugMouseUpHit && (
                <div className="mt-2 p-2 rounded border border-cyan-200 bg-cyan-100/30">
                  <div className="text-xs font-semibold text-cyan-900 mb-1">
                    {t('app.candidates.debug.mouseup_hit', { defaultValue: 'Debug: mouseup hit' })}
                  </div>
                  <div className="text-[11px] text-cyan-900">
                    <div>
                      tag: <span className="font-mono">{debugMouseUpHit.tag ?? '—'}</span>
                    </div>
                    <div>
                      pointer-events: <span className="font-mono">{debugMouseUpHit.pointerEvents ?? '—'}</span>
                    </div>
                    <div>
                      insideTable: <span className="font-mono">{String(Boolean(debugMouseUpHit.insideTable))}</span>
                    </div>
                    {debugMouseUpHit.className ? (
                      <div className="mt-1">
                        class: <span className="font-mono">{debugMouseUpHit.className}</span>
                      </div>
                    ) : null}
                  </div>
                </div>
              )}

              {debugClickHitBubble && (
                <div className="mt-2 p-2 rounded border border-violet-200 bg-violet-100/30">
                  <div className="text-xs font-semibold text-violet-900 mb-1">
                    {t('app.candidates.debug.click_hit_bubble', { defaultValue: 'Debug: click hit (bubble)' })}
                  </div>
                  <div className="text-[11px] text-violet-900">
                    <div>
                      tag: <span className="font-mono">{debugClickHitBubble.tag ?? '—'}</span>
                    </div>
                    <div>
                      pointer-events: <span className="font-mono">{debugClickHitBubble.pointerEvents ?? '—'}</span>
                    </div>
                    <div>
                      insideTable: <span className="font-mono">{String(Boolean(debugClickHitBubble.insideTable))}</span>
                    </div>
                  </div>
                </div>
              )}

              {debugMouseUpHitBubble && (
                <div className="mt-2 p-2 rounded border border-sky-200 bg-sky-100/20">
                  <div className="text-xs font-semibold text-sky-900 mb-1">
                    {t('app.candidates.debug.mouseup_hit_bubble', { defaultValue: 'Debug: mouseup hit (bubble)' })}
                  </div>
                  <div className="text-[11px] text-sky-900">
                    <div>
                      tag: <span className="font-mono">{debugMouseUpHitBubble.tag ?? '—'}</span>
                    </div>
                    <div>
                      pointer-events: <span className="font-mono">{debugMouseUpHitBubble.pointerEvents ?? '—'}</span>
                    </div>
                    <div>
                      insideTable: <span className="font-mono">{String(Boolean(debugMouseUpHitBubble.insideTable))}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {digestShadowBucket ? (
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-indigo-200 bg-indigo-50/60 px-3 py-2 text-sm text-slate-800">
              <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
                <span className="font-medium">
                  {t('app.candidates.digest_shadow.banner', { defaultValue: 'Risk digest cohort' })}
                </span>
                <span className="text-xs text-slate-600">
                  {t('app.candidates.digest_shadow.bucket', {
                    defaultValue: 'Hourly bucket: {t}',
                    values: { t: new Date(digestShadowBucket).toLocaleString(locale) },
                  })}
                </span>
                <label className="flex items-center gap-1.5 text-xs text-slate-700">
                  <span className="shrink-0">
                    {t('app.candidates.digest_shadow.min_band', { defaultValue: 'Band floor' })}
                  </span>
                  <select
                    className="rounded border border-slate-300 bg-white px-1.5 py-0.5 text-xs"
                    value={digestShadowMinBand ?? 'high'}
                    onChange={(e) => {
                      const next = new URLSearchParams(searchParams)
                      next.set('shadow_min_band', e.target.value)
                      setSearchParams(next, { replace: true })
                    }}
                  >
                    {(['low', 'medium', 'high', 'critical'] as const).map((b) => (
                      <option key={b} value={b}>
                        {b}+
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button
                type="button"
                className="btn-secondary btn-sm shrink-0"
                onClick={() => {
                  const next = new URLSearchParams(searchParams)
                  next.delete('shadow_bucket')
                  next.delete('shadow_min_band')
                  next.delete('shadow_bucket_min_band')
                  setSearchParams(next, { replace: true })
                }}
              >
                {t('app.candidates.digest_shadow.clear', { defaultValue: 'Clear digest filter' })}
              </button>
            </div>
          ) : null}

          {operationalQueue === 'no_next_action' ? (
            <div className="mx-4 mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-200 bg-amber-50/80 px-3 py-2 text-sm text-slate-800">
              <div className="min-w-0">
                <div className="font-medium text-slate-900">{t('app.candidates.no_next_action.title')}</div>
                <div className="text-xs text-slate-600">{t('app.candidates.no_next_action.subtitle')}</div>
              </div>
              <button
                type="button"
                className="btn-secondary btn-sm shrink-0"
                onClick={() => {
                  const next = new URLSearchParams(searchParams)
                  next.delete('queue')
                  next.delete('quick_view')
                  setSearchParams(next, { replace: true })
                }}
              >
                {t('app.candidates.no_next_action.clear_queue', { defaultValue: 'Show all candidates' })}
              </button>
            </div>
          ) : null}

          <div className="mx-4 mb-1.5 shrink-0 rounded-xl border border-slate-200/90 bg-gradient-to-b from-white to-slate-50/90 px-3 py-2.5 shadow-sm">
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
              <input
                id="candidates-search"
                ref={searchRef}
                className="input min-h-[40px] min-w-0 flex-1 rounded-lg border-slate-200/90 bg-white py-2 text-sm shadow-sm focus:border-brand-400 focus:ring-2 focus:ring-brand-500/15"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={t('app.candidates.search.placeholder')}
                autoComplete="off"
                aria-label={t('app.candidates.search.label')}
              />
              <CandidatesQuickViewsBar
                variant="tableToolbar"
                t={t}
                quickViewParam={quickViewParam}
                onApplyQuickViewFilters={(key) => {
                  void applyQuickViewFilters(key as any, { syncUrl: true })
                }}
                isFavoriteFilter={isFavoriteFilter}
                onFavoriteFilterToggle={() => setIsFavoriteFilter((prev) => (prev === true ? null : true))}
                quickDocFilters={quickDocFilters}
                quickFiltersExpanded={quickFiltersExpanded}
                onToggleQuickDocFilter={toggleQuickDocFilter}
                onQuickFiltersExpandedChange={setQuickFiltersExpanded}
                savedViews={savedViews}
                onApplySavedView={applyView}
                onDeleteSavedView={(id) => {
                  void deleteView(id)
                }}
              />
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-slate-200/80 pt-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                {t('app.candidates.quick_filters.label', { defaultValue: 'Quick filters' })}
              </span>
              <select
                className="input h-9 max-w-[11rem] py-1 text-xs"
                aria-label={t('app.candidates.quick_filters.stage', { defaultValue: 'Stage' })}
                value={stageFilter.length === 1 ? stageFilter[0] : ''}
                onChange={(e) => {
                  const v = e.target.value.trim()
                  setStageFilter(v ? [v] : [])
                }}
              >
                <option value="">{t('app.candidates.quick_filters.all_stages', { defaultValue: 'All stages' })}</option>
                {stageOptions.map((s) => (
                  <option key={s} value={s}>
                    {stageLabelMap[s] ?? s}
                  </option>
                ))}
              </select>
              <select
                className="input h-9 max-w-[11rem] py-1 text-xs"
                aria-label={t('app.candidates.quick_filters.manager', { defaultValue: 'Manager' })}
                value={managerFilter.length === 1 ? managerFilter[0] : ''}
                onChange={(e) => {
                  const v = e.target.value.trim()
                  setManagerFilter(v ? [v] : [])
                }}
              >
                <option value="">{t('app.candidates.quick_filters.all_managers', { defaultValue: 'All managers' })}</option>
                {managers.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label || m.id}
                  </option>
                ))}
              </select>
              <select
                className="input h-9 max-w-[12rem] py-1 text-xs"
                aria-label={t('app.candidates.quick_filters.vacancy', { defaultValue: 'Vacancy' })}
                value={vacancyFilter.length === 1 ? vacancyFilter[0] : ''}
                onChange={(e) => {
                  const v = e.target.value.trim()
                  setVacancyFilter(v ? [v] : [])
                }}
              >
                <option value="">{t('app.candidates.quick_filters.all_vacancies', { defaultValue: 'All vacancies' })}</option>
                {vacancies.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.title || v.id}
                  </option>
                ))}
              </select>
            </div>
            {hasFilterBadges ? (
              <div className="mt-2 border-t border-slate-200/90 pt-2">
                <FilterBadges
                  embedded
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
              </div>
            ) : null}
          </div>

          {/* Bulk actions appear only when there is a selection */}
          {canManage && Object.values(checked).some(Boolean) && (
            <div className="mx-4 mb-2 flex flex-wrap items-center gap-2 rounded-xl border border-slate-200/90 bg-gradient-to-b from-slate-50/95 to-white px-3 py-2.5 shadow-sm">
              <span className="inline-flex items-center rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-900 ring-1 ring-brand-200/60">
                {t('app.candidates.bulk.selected', { values: { count: Object.values(checked).filter(Boolean).length } })}
              </span>
              <button
                className="inline-flex items-center rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-brand-700"
                title={t('app.candidates.bulk.stage.title')}
                onClick={() => {
                  setBulkStage(stageOptions[0] || 'new')
                  setBulkReasons([])
                  setBulkOpen(true)
                }}
              >
                {t('app.candidates.bulk.stage.action')}
              </button>
              <button
                className="inline-flex items-center rounded-lg border border-slate-200/90 bg-white px-2.5 py-2 text-xs font-medium text-slate-700 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50"
                title={t('app.candidates.bulk.manager.title')}
                onClick={() => {
                  setBulkManagerId(preferredManagerId)
                  setBulkManagerOpen(true)
                }}
              >
                {t('app.candidates.bulk.manager.action')}
              </button>
              <button
                className="inline-flex items-center rounded-lg border border-slate-200/90 bg-white px-2.5 py-2 text-xs font-medium text-slate-700 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50"
                title={t('app.candidates.bulk.vacancy.title')}
                onClick={() => {
                  setBulkVacancyId(vacancies[0]?.id || '')
                  setBulkVacancyOpen(true)
                }}
              >
                {t('app.candidates.bulk.vacancy.action')}
              </button>
              <button
                className="inline-flex items-center rounded-lg border border-slate-200/90 bg-white px-2.5 py-2 text-xs font-medium text-slate-700 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50"
                title={t('app.candidates.bulk.handoff.title', { defaultValue: 'Przekaż wybranych do klienta' })}
                onClick={() => setBulkHandoffOpen(true)}
              >
                {t('app.candidates.bulk.handoff.action', { defaultValue: 'Przekaż do klienta (wybrani)' })}
              </button>
              <button
                className="inline-flex items-center rounded-lg border border-slate-200/90 bg-white px-2.5 py-2 text-xs font-medium text-slate-700 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50"
                title={t('app.candidates.bulk.tags.title')}
                onClick={() => {
                  setBulkTagsOperation('add')
                  setBulkTagsList('')
                  setBulkTagsOpen(true)
                }}
              >
                {t('app.candidates.bulk.tags.action')}
              </button>
              <button
                className="inline-flex items-center rounded-lg border border-slate-200/90 bg-white px-2.5 py-2 text-xs font-medium text-slate-700 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50"
                title={t('app.candidates.bulk.activities.title', { defaultValue: 'Create activities for selected' })}
                onClick={() => {
                  setBulkActivityTitle(t('app.candidates.bulk.activities.default_title', { defaultValue: 'Follow up' }))
                  setBulkActivityDueAt(new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16))
                  setBulkActivityOffsetMinutes(60)
                  setBulkActivitiesOpen(true)
                }}
              >
                {t('app.candidates.bulk.activities.action', { defaultValue: 'Create activity' })}
              </button>
              <button
                className="inline-flex items-center rounded-lg border border-red-200/90 bg-white px-2.5 py-2 text-xs font-medium text-red-700 shadow-sm transition-colors hover:border-red-300 hover:bg-red-50"
                title={t('app.candidates.bulk.delete.title')}
                onClick={() => {
                  setBulkDeleteOpen(true)
                }}
              >
                {t('app.candidates.bulk.delete.action')}
              </button>
              <div className="min-w-[1rem] flex-1" />
              <button
                className="inline-flex items-center rounded-lg border border-slate-200/90 bg-slate-50 px-2.5 py-2 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:bg-slate-100"
                title={t('app.candidates.bulk.clear_title')}
                onClick={() => setChecked({})}
              >
                {t('app.candidates.bulk.clear_action')}
              </button>
            </div>
          )}

          {errorText && (
            <div className="m-4">
              <ErrorRecoveryBanner
                info={errorText}
                onRetry={() => void load({ force: true })}
                retryLabel={t('app.candidates.errors.retry') || 'Повторить попытку'}
                {...friendlyErrorBannerSecondary(
                  errorText,
                  CRM_APP_PATHS.candidates,
                  t('app.nav.items.candidates', { defaultValue: 'Candidates' }),
                )}
              />
            </div>
          )}

          <div className="card m-0 relative flex-1 min-h-0 flex flex-col rounded-lg border border-slate-200 bg-white shadow-sm">
        {tableLayoutCustomize ? (
          <div className="border-b border-brand-200/80 bg-brand-50 px-3 py-1.5 text-[11px] font-medium text-brand-900">
            {t('app.candidates.table.customize_banner', {
              defaultValue: 'Layout mode on: drag ⋮⋮ on headers to reorder; drag the right edge of a header to resize.',
            })}
          </div>
        ) : null}
        {loading && displayedItems.length > 0 && (
          <div className="absolute top-2 right-2 z-30 bg-white/95 backdrop-blur-sm border border-slate-200 rounded-lg px-3 py-1.5 shadow-lg">
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-brand-600"></div>
              <span className="font-medium">{t('app.candidates.table.updating') || 'Обновление...'}</span>
            </div>
          </div>
        )}
        <div className="min-h-0 flex-1 overflow-auto overscroll-contain rounded-b-xl">
          <table className="min-w-full text-sm border-separate border-spacing-0">
            <thead className="sticky top-0 z-10 bg-slate-50 shadow-[inset_0_-1px_0_0_rgb(226_232_240)]">
              <tr className="h-11 bg-slate-50 text-left">
                <DraggableColumnHeader columnKey="checkbox" />
                {orderedVisibleColumns.map((columnKey) => (
                  <DraggableColumnHeader key={columnKey} columnKey={columnKey} />
                ))}
              </tr>
            </thead>
            <tbody>
              {displayedItems.map((item, dataIndex) => {
                const c = item as AugmentedCandidate
                const id = c.id
                const index = dataIndex
                const isFocused = focusedRowIndex === index && index >= 0
                const isWorkPanelRow = Boolean(workPanelOpen && id && selectedCandidateId === id)
                return (
                  <tr
                    key={id}
                    ref={(node) => {
                      if (isFocused && node) focusedRowRef.current = node
                    }}
                    data-candidate-id={id}
                    data-index={index}
                    data-work-panel-row={isWorkPanelRow ? 'true' : undefined}
                    aria-current={isWorkPanelRow ? 'true' : undefined}
                    tabIndex={-1}
                    onMouseDown={(e) => {
                      if (e.button !== 0) return
                      lastRowMouseDownRef.current = { x: e.clientX, y: e.clientY, t: Date.now() }
                    }}
                    onClick={(e) => {
                      if (!id) return
                      const md = lastRowMouseDownRef.current
                      if (md) {
                        const dx = Math.abs(e.clientX - md.x)
                        const dy = Math.abs(e.clientY - md.y)
                        const dt = Date.now() - md.t
                        if ((dx + dy) > 6 && dt < 1200) return
                      }
                      const target = e.target as HTMLElement | null
                      if (target?.closest('a,button,input[type="checkbox"],select,textarea')) return
                      if (sidebarOpenRef.current || selectedCandidateIdRef.current != null) {
                        const nextId = id
                        window.requestAnimationFrame(() => {
                          setSelectedCandidateId(nextId)
                          setSidebarOpen(true)
                        })
                      }
                    }}
                    onContextMenu={(e) => {
                      if (id && canManage) {
                        e.preventDefault()
                        setContextMenu({ x: e.clientX, y: e.clientY, candidateId: id })
                      }
                    }}
                    className={clsx(
                      'border-t border-slate-200/90 transition-colors duration-150 cursor-pointer',
                      isWorkPanelRow && 'border-l-[3px] border-l-brand-600 bg-brand-50/90 shadow-[inset_0_0_0_1px_rgb(191_219_254_/_0.35)]',
                      isFocused && 'ring-2 ring-brand-500 ring-inset outline-none',
                      !isFocused && !isWorkPanelRow && 'hover:bg-brand-50/50',
                      id &&
                        recentlyOpenedId === id &&
                        !isFocused &&
                        !isWorkPanelRow &&
                        'bg-amber-50/60',
                      id &&
                        (items.find((row) => row.id === id)?.is_favorite) &&
                        !isFocused &&
                        !isWorkPanelRow &&
                        'bg-yellow-50/40 border-l-2 border-l-yellow-400',
                    )}
                  >
                    {renderCandidateRowTds(index, c)}
                  </tr>
                )
              })}
            </tbody>
          </table>
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
                  {t('app.candidates.table.empty_partial', {
                    values: { count: total },
                    defaultValue: `Список не загрузился полностью (всего: ${total}). Повторить?`,
                  })}
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
                            to: CRM_APP_PATHS.leads,
                          }
                    }
                    secondaryAction={
                      hasActiveTableFilters
                        ? {
                            label: t('app.candidates.table.empty_cta_leads', { defaultValue: 'Open leads' }),
                            to: CRM_APP_PATHS.leads,
                          }
                        : {
                            label: t('app.candidates.table.empty_cta_pipeline', { defaultValue: 'Open pipeline' }),
                            to: CRM_APP_PATHS.pipeline,
                          }
                    }
                  />
                </div>
              </>
            )}
          </div>
        )}
          <div className="text-sm leading-6 text-slate-600 px-4 pt-3 pb-4 border-t border-slate-200/80">
            {showsFilteredCount
              ? t('app.candidates.table.total_filtered', {
                  values: { shown: visibleCandidatesCount, total },
                  defaultValue: `Показано: ${visibleCandidatesCount} из ${total}`,
                })
              : t('app.candidates.table.total', { values: { count: visibleCandidatesCount } })}
          </div>
          </div>
        </div>
      </div>
        {workPanelOpen ? (
          <div
            className={clsx(
              'flex min-w-0 w-full flex-col overflow-hidden',
              selectedCandidate ? 'h-full min-h-0' : 'max-h-full self-start',
            )}
            style={{ maxWidth: CANDIDATES_WORK_PANEL_RAIL_WIDTH_PX }}
          >
            <CandidatesWorkPanel
              summaryHero={summaryHero}
              previewVisible={Boolean(selectedCandidate)}
              previewSlot={
          <CandidatesSelectedPanel
            t={t}
            locale={locale}
            selectedCandidate={selectedCandidate}
            selectedCandidateId={selectedCandidateId}
            stageSummaryLabel={
              selectedCandidate
                ? translateStageLabel(
                    t,
                    String((selectedCandidate as any).stage || ''),
                    String((selectedCandidate as any).stage_label || ''),
                  )
                : null
            }
            previewReminders={previewReminders}
            previewRemindersLoading={previewRemindersLoading}
            previewRemindersError={previewRemindersError}
            previewReminderBusy={previewReminderBusy}
            previewReminderTitle={previewReminderTitle}
            previewReminderDueAt={previewReminderDueAt}
            previewReminderOffset={previewReminderOffset}
            nextActionDetailsOpenTrigger={nextActionDetailsOpenTrigger}
            docsBlockers={docsBlockers}
            docsBlockersLoading={docsBlockersLoading}
            docsRailEmbeddedSummary={docsRailEmbeddedSummary}
            canUseTeamWorkPanelAssigneeScope={canUseTeamWorkPanelAssigneeScope}
            workPanelAssigneeScope={workPanelAssigneeScope}
            onWorkPanelAssigneeScopeChange={setWorkPanelAssigneeScope}
            docsOwnerContext={docsOwnerContext}
            previewTimelineItems={previewTimelineItems}
            previewTimelineLoading={previewTimelineLoading}
            previewTimelineError={previewTimelineError}
            previewTimelineExpanded={previewTimelineExpanded}
            previewTimelineCollapsedCount={PREVIEW_TIMELINE_COLLAPSED_COUNT}
            onClose={() => {
              setSelectedCandidateId(null)
              setSidebarOpen(false)
            }}
            onOpenCandidate={(candidateId) => navigate(`${CRM_APP_PATHS.candidates}/${candidateId}`)}
            onOpenDocuments={(candidateId) =>
              navigate(`${CRM_APP_PATHS.candidates}/${candidateId}/documents`)
            }
            workPanelCommsLinks={previewCommsLinks}
            onReminderTitleChange={setPreviewReminderTitle}
            onReminderDueAtChange={setPreviewReminderDueAt}
            onReminderOffsetChange={setPreviewReminderOffset}
            onReminderCreate={() => void handleCreatePreviewReminder()}
            onReminderComplete={(id) => void handleCompletePreviewReminder(id)}
            onReminderSnooze={(id, minutes) => void handlePreviewReminderSnooze(id, minutes)}
            onDocsRequestCreate={handleDocsRequestCreate}
            onDocsLoadedBlockers={(b) =>
              setDocsBlockers({
                missing: b.missing,
                problematic: b.problematic,
                inProgress: b.inProgress ?? [],
              })
            }
            onDocsLoadingChange={setDocsBlockersLoading}
            onDocsSelectType={(candidateId, typeCode) =>
              navigate(
                `${CRM_APP_PATHS.candidates}/${candidateId}/documents?type=${encodeURIComponent(typeCode)}`,
              )
            }
            onTimelineRefresh={(candidateId) => void loadPreviewTimeline(candidateId)}
            onTimelineExpandedChange={setPreviewTimelineExpanded}
          />
              }
              controlsSlot={
          <CandidatesLeftRailPanel
            t={t}
            handoffStatusFilter={handoffStatusFilter}
            onHandoffStatusFilterChange={setHandoffStatusFilter}
            contactAttemptsFilter={contactAttemptsFilter}
            onContactAttemptsFilterChange={setContactAttemptsFilter}
            opsModeFilter={opsModeFilter}
            onOpsModeFilterChange={setOpsModeFilter}
            opsModeOptions={opsModeOptions as any}
            opsModeLabelMap={opsModeLabelMap}
            viewToggle={viewToggle}
            secondaryBtn={secondaryBtn}
            onRefresh={() => load({ force: true })}
            loading={loading}
            actionsMenuRef={actionsMenuRef}
            actionsMenuOpen={actionsMenuOpen}
            onActionsMenuOpenChange={setActionsMenuOpen}
            displayedItems={displayedItems}
            resolveManagerLabel={resolveManagerLabel}
            onResetFilters={handleResetFilters}
            hasFilterBadges={hasFilterBadges}
            onOpenSaveView={() => {
              setSaveViewName('')
              setSaveViewOpen(true)
            }}
            columnToggleKeys={columnToggleKeys}
            visibleCols={visibleCols}
            onVisibleColsChange={setVisibleCols}
            visibleColsStorageKey={visibleColsStorageKey}
            columnLabelMap={columnLabelMap}
            canManage={canManage}
            quickViewParam={quickViewParam}
            onApplyQuickViewFilters={(key) => {
              void applyQuickViewFilters(key as any, { syncUrl: true })
            }}
            isFavoriteFilter={isFavoriteFilter}
            onFavoriteFilterToggle={() => setIsFavoriteFilter((prev) => (prev === true ? null : true))}
            quickDocFilters={quickDocFilters}
            quickFiltersExpanded={quickFiltersExpanded}
            onToggleQuickDocFilter={toggleQuickDocFilter}
            onQuickFiltersExpandedChange={setQuickFiltersExpanded}
            savedViews={savedViews}
            onApplySavedView={applyView}
            onDeleteSavedView={(id) => {
              void deleteView(id)
            }}
            viewSaveEnabled={hasActiveTableFilters}
            tableLayoutCustomize={tableLayoutCustomize}
            onTableLayoutCustomizeChange={setTableLayoutCustomize}
          />
              }
            />
          </div>
        ) : null}
      </div>
      {/* Контекстное меню для строк */}
      {contextMenu && (
        <>
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
                      navigate(`${CRM_APP_PATHS.candidates}/${candidate.id}`)
                      setContextMenu(null)
                    }}
                  >
                    {t('app.candidates.context.open_card')}
                  </button>
                  <button
                    className="btn-secondary w-full justify-start text-left text-xs py-1.5 px-2"
                    title={t('app.candidates.context.preview_next_action_hint', {
                      defaultValue: 'Open the right panel and expand the next-action block.',
                    })}
                    onClick={() => {
                      setSelectedCandidateId(candidate.id)
                      setSidebarOpen(true)
                      window.requestAnimationFrame(() => bumpNextActionDetailsOpen())
                      setContextMenu(null)
                    }}
                  >
                    {t('app.candidates.context.preview_next_action', {
                      defaultValue: 'Preview — next action',
                    })}
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

      <BulkActivitiesModal
        open={bulkActivitiesOpen}
        onClose={() => !bulkOperationLoading && setBulkActivitiesOpen(false)}
        title={bulkActivityTitle}
        dueAt={bulkActivityDueAt}
        offsetMinutes={bulkActivityOffsetMinutes}
        onTitleChange={setBulkActivityTitle}
        onDueAtChange={setBulkActivityDueAt}
        onOffsetMinutesChange={setBulkActivityOffsetMinutes}
        onApply={doBulkActivities}
        loading={bulkOperationLoading === 'activities'}
        canManage={canManage}
        activityType={bulkActivityType}
        onActivityTypeChange={setBulkActivityType}
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

      {canViewActivities ? (
        <Modal
          open={activitiesModalOpen}
          onClose={() => setActivitiesModalOpen(false)}
          title={t('app.activities.title', { defaultValue: 'Activities' })}
          size="2xl"
          surfaceClassName="max-h-[min(92vh,900px)] flex flex-col"
        >
          <p className="mb-3 text-sm text-slate-600">
            {t('app.candidates.activities_modal.subtitle', {
              defaultValue: 'Your planned work — same list as on the Tasks page.',
            })}
          </p>
          <div className="min-h-0 flex-1 overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <ActivitiesPanel embedded compact showFullPageLink refreshToken={activitiesModalRefresh} />
          </div>
        </Modal>
      ) : null}

    </div>
  )
}
