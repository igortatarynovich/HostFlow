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
  IconLayoutSidebarLeftExpand,
  IconListCheck,
  IconMail,
  IconPhone,
  IconX,
} from '@tabler/icons-react'
import api, {
  completeActivity,
  completeReminder,
  createActivity,
  createBulkActivities,
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
import { isPostRecruitmentStageCode } from '../constants/recruitmentStageBoundary'
import { filterRecruitmentVisibleStageCodes } from '../constants/recruitmentStageSurface'
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
import { QuotaNearLimitBanner } from '../components/billing/QuotaNearLimitBanner'
import { useBillingQuotaWarnings } from '../hooks/useBillingQuotaWarnings'
import { PageBreadcrumb } from '../components/nav/PageBreadcrumb'
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
  phoneTextMatches,
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
  CandidatesFiltersToolbar,
  CandidateQuickTaskModal,
} from '../modules/candidates/components'
import { CandidatesDebugPanel } from '../modules/candidates/components/CandidatesDebugPanel'
import { CandidatesBulkModalsCluster } from '../modules/candidates/components/CandidatesBulkModalsCluster'
import { CandidatesTableRowCells } from '../modules/candidates/components/CandidatesTableRowCells'
import { CandidatesTableColumnHeaderContent } from '../modules/candidates/components/CandidatesTableColumnHeaderContent'
import { filterCandidates as filterCandidatesPure } from '../modules/candidates/candidateFilters'
import {
  normalizeArrayFilter,
  normalizeRangeFilter,
  normalizeReasonList,
  normalizeTextFilterState,
  normalizeOpsModeList,
} from '../modules/candidates/filterNormalizers'
import { useCandidatesFiltersState } from '../modules/candidates/hooks/useCandidatesFiltersState'
import { useCandidatesFilterOptions } from '../modules/candidates/hooks/useCandidatesFilterOptions'
import { useCandidatesUrlSync } from '../modules/candidates/hooks/useCandidatesUrlSync'
import { useCandidatesFiltersPersistence } from '../modules/candidates/hooks/useCandidatesFiltersPersistence'
import { useCandidatesUpdateListener } from '../modules/candidates/hooks/useCandidatesUpdateListener'
import { useCandidatesWorkPanel } from '../modules/candidates/hooks/useCandidatesWorkPanel'
import { useCandidatesInsightsHero } from '../modules/candidates/hooks/useCandidatesInsightsHero'
import { useCandidatesSavedViews } from '../modules/candidates/hooks/useCandidatesSavedViews'
import { useCandidatesQuickViews } from '../modules/candidates/hooks/useCandidatesQuickViews'
import { useCandidatesTableData } from '../modules/candidates/hooks/useCandidatesTableData'
import { useCandidatesTableKeyboardNavigation } from '../modules/candidates/hooks/useCandidatesTableKeyboardNavigation'
import { useCandidatesTableColumnsDnDResize } from '../modules/candidates/hooks/useCandidatesTableColumnsDnDResize'
import { useCandidatesScrollRestoration } from '../modules/candidates/hooks/useCandidatesScrollRestoration'
import {
  useCandidatesManagersCatalog,
  useCandidatesVacanciesCatalog,
  useCandidatesHandoffClientsLazy,
} from '../modules/candidates/hooks/useCandidatesCatalogs'
import { useCandidatesBulkActions } from '../modules/candidates/hooks/useCandidatesBulkActions'
import { createBulkHandoff, type AvailableClientOut } from '../api/handoffs'
import {
  candidateListCache,
  normalizeListInsights,
  getWithFallbacks,
  parseRiskShadowMinBand,
  TEAM_WORK_PANEL_ASSIGNEE_ROLES,
  WP_ASSIGNEE_STORAGE_KEY,
} from '../modules/candidates/internal'
import {
  fetchCandidateListAvailableStatuses,
  type CandidateListAvailableStatuses,
} from '../api/candidatesFacets'

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
  const [candidateRowStatusFilter, setCandidateRowStatusFilter] = useState<string[]>([])
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

  const [taskQuickModal, setTaskQuickModal] = useState<{ id: string; label: string } | null>(null)

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
  const [sortKey, setSortKey] = useState<SortKey>('created_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [polandBasisFilter, setPolandBasisFilter] = useState<string[]>([])
  const [trailerTypesFilter, setTrailerTypesFilter] = useState<string[]>([])
  const [createdRange, setCreatedRange] = useState<DateRangeFilter>({ from: null, to: null })
  const [firstContactRange, setFirstContactRange] = useState<DateRangeFilter>({ from: null, to: null })
  const [docsValidRange, setDocsValidRange] = useState<DateRangeFilter>({ from: null, to: null })
  const [docsHasFilesFilter, setDocsHasFilesFilter] = useState<string[]>([])
  const [handoffStatusFilter, setHandoffStatusFilter] = useState<string>('')
  const [contactAttemptsFilter, setContactAttemptsFilter] = useState<string>('')
  const [processorFilter, setProcessorFilter] = useState<string>('')
  const [intakeApplicationKindFilter, setIntakeApplicationKindFilter] = useState<'client' | 'candidate' | ''>('')
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
    if (raw === 'no_next_action') return 'no_next_action'
    const filt = (searchParams.get('filter') || '').trim().toLowerCase()
    if (filt === 'action_required') return 'no_next_action'
    return null
  }, [searchParams])
  const recruiterUnassignedOnly = useMemo(() => {
    const v = (searchParams.get('recruiter_unassigned') || '').trim().toLowerCase()
    return v === '1' || v === 'true'
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
      intake_application_kind: intakeApplicationKindFilter || '',
      operational_queue: operationalQueue || '',
      recruiter_unassigned: recruiterUnassignedOnly ? '1' : '',
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
    intakeApplicationKindFilter,
    operationalQueue,
    recruiterUnassignedOnly,
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

  useCandidatesHandoffClientsLazy(
    bulkHandoffOpen,
    setHandoffClients,
    setHandoffClientsLoading,
    setBulkHandoffClientId,
  )

  const [filtersHydrated, setFiltersHydrated] = useState(false)
  const persistedFiltersRef = useRef(false)

  /** Заполняется после хука колонок — применение tableLayout из сохранённого вида. */
  const applyTableLayoutFromViewRef = useRef<(filters: Record<string, any> | undefined) => void>(() => {})

  const {
    applyViewFilters,
    resetCandidatesFiltersCore,
    handleResetFilters,
  } = useCandidatesFiltersState({
    setQ, setStageFilter, setCandidateRowStatusFilter, setVacancyFilter, setManagerFilter, setStatusReasonFilter,
    setTagsFilter, setIsFavoriteFilter, setDocsStatusFilter, setDocsOrderedFilter,
    setPreferredChannelFilter, setInPolandFilter, setOpsModeFilter, setPolandBasisFilter,
    setTrailerTypesFilter, setDocsHasFilesFilter,
    setCreatedRange, setFirstContactRange, setDocsValidRange,
    setHandoffStatusFilter, setContactAttemptsFilter, setProcessorFilter,
    setIntakeApplicationKindFilter,
    setTextFilters,
    setSortKey, setSortDir,
    filterStorageKey, persistedFiltersRef, applyTableLayoutFromViewRef,
    searchParams, setSearchParams,
  })

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

  const [saveViewIncludeTableLayout, setSaveViewIncludeTableLayout] = useState(true)

  const [listColumnFacets, setListColumnFacets] = useState<CandidateListAvailableStatuses | null>(null)

  const meta = useMetaStages()
  const { role, isClientTenant } = usePermissions()
  const isClientRole = isClientTenant && role !== 'administrator'

  const stageOptions = useMemo(() => {
    const base = (meta?.order || meta?.codes || []).map((c) => String(c))
    let list = base
    if (meta?.meta && isClientRole) {
      list = base.filter((code) => meta.meta?.[code]?.visible_for_client)
    }
    return filterRecruitmentVisibleStageCodes(list)
  }, [meta, isClientRole])

  const recruitmentListStageFilterActive = Boolean(
    meta?.recruiter_handoff_stage_filter || meta?.stage_visibility_mode === 'recruitment_handoff',
  )

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
      intakeKind: t('app.candidates.table.columns.intake_kind', { defaultValue: 'Intake' }),
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
    'intakeKind',
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
    columnOrder,
    columnWidths,
    orderedVisibleColumns,
    getColumnWidth,
    draggingColumn,
    setDraggingColumn,
    dragOverColumn,
    setDragOverColumn,
    reorderColumns,
    handleResizeStart,
    applyPersistedLayout,
    resetColumnLayout,
    moveColumnRelative,
  } = useCandidatesTableColumnsDnDResize({
    visibleCols,
    columnWidthsStorageKey,
    columnOrderStorageKey,
  })

  useEffect(() => {
    applyTableLayoutFromViewRef.current = (filters) => {
      const tl = filters?.tableLayout
      if (!tl || typeof tl !== 'object' || Array.isArray(tl)) return
      if (tl.visibleCols && typeof tl.visibleCols === 'object' && !Array.isArray(tl.visibleCols)) {
        const merged = { ...DEFAULT_VISIBLE_COLS, ...tl.visibleCols }
        setVisibleCols(merged)
        try {
          localStorage.setItem(visibleColsStorageKey, JSON.stringify(merged))
        } catch {
          /* ignore */
        }
      }
      applyPersistedLayout({
        order: Array.isArray(tl.columnOrder) && tl.columnOrder.length > 0 ? tl.columnOrder : null,
        widths:
          tl.columnWidths && typeof tl.columnWidths === 'object' && !Array.isArray(tl.columnWidths)
            ? tl.columnWidths
            : null,
      })
    }
  }, [applyPersistedLayout, visibleColsStorageKey])

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


  const handleSortChange = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'created_at' || key === 'risk_score' ? 'desc' : 'asc')
    }
  }
  const searchRef = useRef<HTMLInputElement>(null)
  const scrollContainerRef = useRef<HTMLElement | null>(null)
  const outerScrollRef = useRef<HTMLElement | null>(null)
  const { can } = usePermissions()
  const planLimitModal = usePlanLimitModal()
  const { warningFor: quotaWarningFor } = useBillingQuotaWarnings()
  const candidatesQuotaWarning = quotaWarningFor('candidates_active')
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
    candidateRowStatusFilter,
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
    intakeApplicationKindFilter,
    currentTenantId,
    meTenantId: me?.tenant_id,
    restoredScrollRef,
    operationalQueue,
    recruiterUnassignedFilter: recruiterUnassignedOnly,
  })

  useCandidatesUrlSync({
    searchParams, setSearchParams,
    setViewMode, operationalQueue,
    filtersHydrated, resetCandidatesFiltersCore,
    setQ, setStageFilter, setCandidateRowStatusFilter, setVacancyFilter, setStatusReasonFilter,
    setTextFilter, setManagerFilter, setPreferredChannelFilter,
    setOpsModeFilter, setInPolandFilter,
    setHandoffStatusFilter, setContactAttemptsFilter,
  })


  useCandidatesFiltersPersistence({
    storageKey: filterStorageKey,
    filtersHydrated, setFiltersHydrated, persistedFiltersRef,
    setQ, setStageFilter, setCandidateRowStatusFilter, setVacancyFilter, setManagerFilter, setStatusReasonFilter,
    setDocsStatusFilter, setDocsOrderedFilter, setPreferredChannelFilter,
    setInPolandFilter, setOpsModeFilter, setPolandBasisFilter, setTrailerTypesFilter,
    setCreatedRange, setFirstContactRange, setDocsValidRange, setDocsHasFilesFilter,
    setHandoffStatusFilter, setContactAttemptsFilter, setProcessorFilter,
    setTextFilters, setIsFavoriteFilter, setIntakeApplicationKindFilter,
    setSortKey, setSortDir,
    q, stageFilter, candidateRowStatusFilter, vacancyFilter, managerFilter, statusReasonFilter, tagsFilter,
    docsStatusFilter, docsOrderedFilter, preferredChannelFilter, inPolandFilter,
    opsModeFilter, polandBasisFilter, trailerTypesFilter,
    createdRange, firstContactRange, docsValidRange, docsHasFilesFilter,
    handoffStatusFilter, contactAttemptsFilter, processorFilter,
    textFilters, isFavoriteFilter, intakeApplicationKindFilter,
    sortKey, sortDir,
  })




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
      rowStatuses: candidateRowStatusFilter,
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
      candidateRowStatusFilter,
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

  const filterCandidates = useCallback(
    (source: AugmentedCandidate[], snapshot: CandidateFilterSnapshot) =>
      filterCandidatesPure(source, snapshot, { debug: showDebugPanel }),
    [showDebugPanel],
  )

  const buildFilterSource = useCallback(
    (overrides: Partial<CandidateFilterSnapshot>) =>
      filterCandidates(enrichedItems, { ...filterSnapshot, ...overrides }),
    [enrichedItems, filterSnapshot, filterCandidates]
  )

  const stagePresence = useMemo(() => {
    // Stages on the loaded page (fallback until tenant facets load).
    const set = new Set<string>()
    enrichedItems.forEach((item) => {
      if (item.stage) set.add(String(item.stage))
    })
    return set
  }, [enrichedItems])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const scopeTid = currentTenantId ?? me?.tenant_id
        const data = await fetchCandidateListAvailableStatuses(
          scopeTid ? { scope_tenant_id: String(scopeTid) } : undefined,
        )
        if (!cancelled) setListColumnFacets(data)
      } catch {
        if (!cancelled) setListColumnFacets(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tenantScopeKey, currentTenantId, me?.tenant_id])

  const stageFilterOptions = useMemo(() => {
    const allowStage = (code: string) =>
      !recruitmentListStageFilterActive || !isPostRecruitmentStageCode(code)

    const facetStages = listColumnFacets?.stages?.length
      ? listColumnFacets.stages
      : Array.from(stagePresence)
    const presentNorm = new Set<string>()
    const rawByNorm = new Map<string, string>()
    const ingest = (raw: string) => {
      const trimmed = String(raw || '').trim()
      const n = trimmed.toLowerCase()
      if (!n) return
      presentNorm.add(n)
      if (!rawByNorm.has(n)) rawByNorm.set(n, trimmed)
    }
    facetStages.forEach(ingest)
    stageFilter.forEach(ingest)

    const ordered: string[] = []
    const seen = new Set<string>()
    const push = (code: string) => {
      const trimmed = String(code || '').trim()
      const n = trimmed.toLowerCase()
      if (!n || seen.has(n)) return
      if (!allowStage(trimmed)) return
      if (!presentNorm.has(n)) return
      seen.add(n)
      ordered.push(trimmed)
    }
    for (const code of stageOptions) {
      push(code)
    }
    for (const n of [...presentNorm].sort()) {
      if (seen.has(n)) continue
      push(rawByNorm.get(n) ?? n)
    }
    return ordered.map((code) => ({
      value: code,
      label: translateStageLabel(t, code, stageLabelMap[code] || code),
    }))
  }, [
    stageOptions,
    stagePresence,
    stageLabelMap,
    t,
    stageFilter,
    recruitmentListStageFilterActive,
    listColumnFacets?.stages,
  ])

  const pruneSelectionByOptions = useCallback(
    (selected: string[], options: Array<{ value: string }>) => {
      if (!selected.length) return selected
      const allowed = new Set(options.map((opt) => String(opt.value)))
      return selected.filter((value) => allowed.has(String(value)))
    },
    [],
  )

  const filteredItems = useMemo(() => {
    const filtered = filterCandidates(enrichedItems, filterSnapshot)
    // Добавляем недавно обновленных кандидатов, чтобы они оставались видимыми даже если не проходят фильтры.
    // Date.now() здесь — намеренный side-effect: окно «60 сек после правки» вычисляется на момент рендера.
    // eslint-disable-next-line react-hooks/purity
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

  const selectedCandidateCitizenship =
    (selectedCandidate as any)?.__extra?.citizenship ?? null
  const docsOwnerContext = useMemo(() => {
    const citizenship = String(selectedCandidateCitizenship || '')
    return { citizenship }
  }, [selectedCandidateCitizenship])

  // Preview side-panel state + handlers are centralized in `useCandidatesWorkPanelPreview`.

  const allVisibleSelected =
    displayedItems.length > 0 && displayedItems.every((candidate) => checked[candidate.id])

  const {
    vacancyFilterOptions,
    managerFilterOptions,
    reasonFilterOptions,
    docsStatusPresence,
    allDocsStatusOptions,
    docsStatusFilterOptions,
    docsOrderPresence,
    docsOrderFilterOptions,
    docsHasFilesOptions,
    preferredChannelOptions,
    inPolandOptions,
    opsModeOptions,
    polandBasisOptions,
    trailerTypesOptions,
  } = useCandidatesFilterOptions({
    t, enrichedItems,
    vacancyLabelMap, managerLabelMap, resolveManagerLabel,
    preferredChannelLabelMap, inPolandLabelMap, opsModeLabelMap,
    getPolandBasisLabel, getTrailerTypeLabel,
    reasonOptions,
    vacancyFilter, managerFilter, statusReasonFilter, docsStatusFilter,
    docsOrderedFilter, docsHasFilesFilter, preferredChannelFilter,
    inPolandFilter, opsModeFilter,     polandBasisFilter, trailerTypesFilter,
    facetVacancyIds: listColumnFacets?.vacancy_ids ?? [],
    facetAssigneeIds: listColumnFacets?.assignee_ids ?? [],
  })

  const quickStageOptions = useMemo(
    () => stageFilterOptions.map((option) => option.value),
    [stageFilterOptions],
  )
  const quickManagers = useMemo(
    () => managerFilterOptions.map((option) => ({ id: option.value, name: option.label })),
    [managerFilterOptions],
  )
  const quickVacancies = useMemo(
    () => vacancyFilterOptions.map((option) => ({ id: option.value, title: option.label })),
    [vacancyFilterOptions],
  )

  useEffect(() => {
    const next = pruneSelectionByOptions(stageFilter, stageFilterOptions)
    if (next.length !== stageFilter.length) setStageFilter(next)
  }, [stageFilter, stageFilterOptions, setStageFilter, pruneSelectionByOptions])

  useEffect(() => {
    const next = pruneSelectionByOptions(vacancyFilter, vacancyFilterOptions)
    if (next.length !== vacancyFilter.length) setVacancyFilter(next)
  }, [vacancyFilter, vacancyFilterOptions, setVacancyFilter, pruneSelectionByOptions])

  useEffect(() => {
    const next = pruneSelectionByOptions(managerFilter, managerFilterOptions)
    if (next.length !== managerFilter.length) setManagerFilter(next)
  }, [managerFilter, managerFilterOptions, setManagerFilter, pruneSelectionByOptions])

  useEffect(() => {
    const next = pruneSelectionByOptions(statusReasonFilter, reasonFilterOptions)
    if (next.length !== statusReasonFilter.length) setStatusReasonFilter(next)
  }, [statusReasonFilter, reasonFilterOptions, setStatusReasonFilter, pruneSelectionByOptions])

  useEffect(() => {
    const next = pruneSelectionByOptions(docsStatusFilter, docsStatusFilterOptions)
    if (next.length !== docsStatusFilter.length) setDocsStatusFilter(next)
  }, [docsStatusFilter, docsStatusFilterOptions, setDocsStatusFilter, pruneSelectionByOptions])

  useEffect(() => {
    const next = pruneSelectionByOptions(docsOrderedFilter, docsOrderFilterOptions)
    if (next.length !== docsOrderedFilter.length) setDocsOrderedFilter(next)
  }, [docsOrderedFilter, docsOrderFilterOptions, setDocsOrderedFilter, pruneSelectionByOptions])

  useEffect(() => {
    const next = pruneSelectionByOptions(docsHasFilesFilter, docsHasFilesOptions)
    if (next.length !== docsHasFilesFilter.length) setDocsHasFilesFilter(next)
  }, [docsHasFilesFilter, docsHasFilesOptions, setDocsHasFilesFilter, pruneSelectionByOptions])

  useEffect(() => {
    const next = pruneSelectionByOptions(preferredChannelFilter, preferredChannelOptions)
    if (next.length !== preferredChannelFilter.length) setPreferredChannelFilter(next)
  }, [preferredChannelFilter, preferredChannelOptions, setPreferredChannelFilter, pruneSelectionByOptions])

  useEffect(() => {
    const next = pruneSelectionByOptions(inPolandFilter, inPolandOptions)
    if (next.length !== inPolandFilter.length) setInPolandFilter(next)
  }, [inPolandFilter, inPolandOptions, setInPolandFilter, pruneSelectionByOptions])

  useEffect(() => {
    const allowed = new Set(opsModeOptions.map((option) => String(option.value)))
    const next = opsModeFilter.filter((value) => allowed.has(String(value)))
    if (next.length !== opsModeFilter.length) setOpsModeFilter(next)
  }, [opsModeFilter, opsModeOptions, setOpsModeFilter])

  useEffect(() => {
    const next = pruneSelectionByOptions(polandBasisFilter, polandBasisOptions)
    if (next.length !== polandBasisFilter.length) setPolandBasisFilter(next)
  }, [polandBasisFilter, polandBasisOptions, setPolandBasisFilter, pruneSelectionByOptions])

  useEffect(() => {
    const next = pruneSelectionByOptions(trailerTypesFilter, trailerTypesOptions)
    if (next.length !== trailerTypesFilter.length) setTrailerTypesFilter(next)
  }, [trailerTypesFilter, trailerTypesOptions, setTrailerTypesFilter, pruneSelectionByOptions])

  const tagOptions = useMemo(() => {
    const all = new Set<string>()
    enrichedItems.forEach((item) => {
      const tags = Array.isArray(item.tags) ? item.tags : []
      tags.forEach((tag) => {
        const value = String(tag || '').trim()
        if (value) all.add(value)
      })
    })
    return Array.from(all).sort().map((value) => ({ value, label: value }))
  }, [enrichedItems])

  useEffect(() => {
    const next = pruneSelectionByOptions(tagsFilter, tagOptions)
    if (next.length !== tagsFilter.length) setTagsFilter(next)
  }, [tagsFilter, tagOptions, setTagsFilter, pruneSelectionByOptions])

  const candidateRowStatusFilterOptions = useMemo(() => {
    const map = new Map<string, string>()
    const labelFor = (value: string) =>
      t(`app.candidates.row_status.${value}`, { defaultValue: value })
    const add = (raw: string | null | undefined) => {
      const v = raw != null && String(raw).trim() !== '' ? String(raw).trim() : null
      if (!v || map.has(v)) return
      map.set(v, labelFor(v))
    }
    ;(listColumnFacets?.statuses ?? []).forEach((s) => add(s))
    enrichedItems.forEach((item) => {
      add((item as { row_status?: string | null }).row_status)
    })
    candidateRowStatusFilter.forEach((code) => add(code))
    return Array.from(map.entries())
      .sort((a, b) => a[1].localeCompare(b[1]))
      .map(([value, label]) => ({ value, label }))
  }, [enrichedItems, candidateRowStatusFilter, t, listColumnFacets?.statuses])

  const candidateRowStatusLabel = useCallback(
    (code: string) => {
      const v = String(code || '').trim()
      if (!v) {
        return t('app.candidates.filters.row_status_legacy', { defaultValue: 'Unknown / legacy status' })
      }
      return t(`app.candidates.row_status.${v}`, { defaultValue: v })
    },
    [t],
  )

  useEffect(() => {
    const next = pruneSelectionByOptions(candidateRowStatusFilter, candidateRowStatusFilterOptions)
    if (next.length !== candidateRowStatusFilter.length) setCandidateRowStatusFilter(next)
  }, [
    candidateRowStatusFilter,
    candidateRowStatusFilterOptions,
    setCandidateRowStatusFilter,
    pruneSelectionByOptions,
  ])

  // Функция для рендеринга содержимого заголовка колонки
  const columnHeaderCtx = useMemo(() => ({
    t,
    sortKey, sortDir, handleSortChange,
    textFilters, setTextFilter,
    columnLabelMap,
    allVisibleSelected, canManage, setChecked, displayedItems,
    vacancyFilterOptions, vacancyFilter, setVacancyFilter,
    managerFilterOptions, managerFilter, setManagerFilter,
    stageFilterOptions, stageFilter, setStageFilter,
    candidateRowStatusFilterOptions, candidateRowStatusFilter, setCandidateRowStatusFilter,
    preferredChannelOptions, preferredChannelFilter, setPreferredChannelFilter,
    inPolandOptions, inPolandFilter, setInPolandFilter,
    polandBasisOptions, polandBasisFilter, setPolandBasisFilter,
    trailerTypesOptions, trailerTypesFilter, setTrailerTypesFilter,
    reasonFilterOptions, statusReasonFilter, setStatusReasonFilter,
    intakeApplicationKindFilter, setIntakeApplicationKindFilter,
    docsStatusFilterOptions, docsStatusFilter, setDocsStatusFilter,
    docsOrderFilterOptions, docsOrderedFilter, setDocsOrderedFilter,
    docsHasFilesOptions, docsHasFilesFilter, setDocsHasFilesFilter,
    tagsFilter, setTagsFilter,
    createdRange, setCreatedRange,
    firstContactRange, setFirstContactRange,
    docsValidRange, setDocsValidRange,
    enrichedItems,
  }), [
    t,
    sortKey, sortDir, handleSortChange,
    textFilters, setTextFilter,
    columnLabelMap,
    allVisibleSelected, canManage, setChecked, displayedItems,
    vacancyFilterOptions, vacancyFilter, setVacancyFilter,
    managerFilterOptions, managerFilter, setManagerFilter,
    stageFilterOptions, stageFilter, setStageFilter,
    candidateRowStatusFilterOptions, candidateRowStatusFilter, setCandidateRowStatusFilter,
    preferredChannelOptions, preferredChannelFilter, setPreferredChannelFilter,
    inPolandOptions, inPolandFilter, setInPolandFilter,
    polandBasisOptions, polandBasisFilter, setPolandBasisFilter,
    trailerTypesOptions, trailerTypesFilter, setTrailerTypesFilter,
    reasonFilterOptions, statusReasonFilter, setStatusReasonFilter,
    intakeApplicationKindFilter, setIntakeApplicationKindFilter,
    docsStatusFilterOptions, docsStatusFilter, setDocsStatusFilter,
    docsOrderFilterOptions, docsOrderedFilter, setDocsOrderedFilter,
    docsHasFilesOptions, docsHasFilesFilter, setDocsHasFilesFilter,
    tagsFilter, setTagsFilter,
    createdRange, setCreatedRange,
    firstContactRange, setFirstContactRange,
    docsValidRange, setDocsValidRange,
    enrichedItems,
  ])

  // Компонент для перетаскиваемого заголовка колонки
  const DraggableColumnHeader = ({ columnKey, isSticky, stickyLeft }: {
    columnKey: string
    isSticky?: boolean
    stickyLeft?: string
  }) => {
    const className = clsx(
      'group py-2.5 border-r border-slate-200 align-middle whitespace-nowrap',
      columnKey === 'checkbox' ? 'px-4' : tableLayoutCustomize ? 'pl-2 pr-4' : 'px-4',
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

    const content = <CandidatesTableColumnHeaderContent columnKey={columnKey} ctx={columnHeaderCtx} />

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
          e.stopPropagation()
          e.dataTransfer.dropEffect = 'move'
          if (dragOverColumn !== columnKey) setDragOverColumn(columnKey)
        }}
        onDragEnter={(e) => {
          if (!draggingColumn || draggingColumn === columnKey) return
          e.preventDefault()
        }}
        onDrop={(e) => {
          e.preventDefault()
          e.stopPropagation()
          const from =
            draggingColumn ||
            e.dataTransfer.getData('text/plain') ||
            e.dataTransfer.getData('application/x-hostflow-column')
          if (from) reorderColumns(from, columnKey)
          setDragOverColumn(null)
          setDraggingColumn(null)
        }}
        onDragLeave={(e) => {
          // Игнорируем уход во вложенные узлы — иначе подсветка мигает (Win/Chrome)
          const next = e.relatedTarget as Node | null
          if (next && (e.currentTarget as HTMLElement).contains(next)) return
          if (dragOverColumn === columnKey) setDragOverColumn(null)
        }}
      >
        <div className="flex min-h-[34px] items-stretch justify-between gap-1">
          <div className="flex min-h-[34px] min-w-0 flex-1 items-center gap-1.5 overflow-hidden">
            <span
              role="button"
              tabIndex={0}
              draggable
              className="inline-flex h-8 w-7 shrink-0 cursor-grab select-none items-center justify-center rounded-md border border-slate-200 bg-slate-100/95 text-slate-600 shadow-sm hover:border-brand-300 hover:bg-brand-50 hover:text-brand-800 active:cursor-grabbing"
              title={t('app.candidates.table.reorder_column') || 'Перетащите, чтобы поменять порядок колонок'}
              onDragStart={(e) => {
                setDraggingColumn(columnKey)
                setDragOverColumn(null)
                e.dataTransfer.effectAllowed = 'move'
                e.dataTransfer.setData('text/plain', columnKey)
                e.dataTransfer.setData('application/x-hostflow-column', columnKey)
                // Пустой drag image — меньше глюков на Windows / HiDPI
                try {
                  const canvas = document.createElement('canvas')
                  canvas.width = 1
                  canvas.height = 1
                  e.dataTransfer.setDragImage(canvas, 0, 0)
                } catch {
                  /* ignore */
                }
              }}
              onDragEnd={() => {
                setDraggingColumn(null)
                setDragOverColumn(null)
              }}
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                }
              }}
            >
              <svg
                width="14"
                height="18"
                viewBox="0 0 14 18"
                fill="currentColor"
                className="opacity-90"
                aria-hidden
              >
                <circle cx="4" cy="3.5" r="1.35" />
                <circle cx="10" cy="3.5" r="1.35" />
                <circle cx="4" cy="9" r="1.35" />
                <circle cx="10" cy="9" r="1.35" />
                <circle cx="4" cy="14.5" r="1.35" />
                <circle cx="10" cy="14.5" r="1.35" />
              </svg>
            </span>
            <div className="flex min-h-8 min-w-0 flex-1 items-center gap-1.5 overflow-hidden whitespace-nowrap">
              {content}
            </div>
          </div>
        </div>
        <ColumnResizeHandle columnKey={columnKey} />
      </th>
    )
  }

  const visibleColumnsCount = 1 + Object.values(visibleCols).filter(Boolean).length

  useCandidatesManagersCatalog(me, setManagers)
  useCandidatesVacanciesCatalog(setVacancies)

  useEffect(() => {
    if (bulkManagerId) return
    if (preferredManagerId) {
      setBulkManagerId(preferredManagerId)
    }
  }, [bulkManagerId, preferredManagerId])



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
  useCandidatesUpdateListener({
    pathname: location.pathname,
    prevLocationRef,
    cacheKey,
    listStorageKey,
    load,
    recentlyUpdatedIdsRef,
    lastUpdateTimeRef,
    updateInProgressRef,
  })



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
    intakeApplicationKindFilter,
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

  const {
    doBulkActivities,
    doBulk,
    doBulkAssign,
    doBulkAssignVacancy,
    doBulkHandoff,
    doBulkTags,
    doBulkDelete,
  } = useCandidatesBulkActions({
    allSelected,
    items,
    recentlyUpdatedIdsRef,
    load,
    cacheKey,
    listStorageKey,
    meta,
    t,
    planLimitModal,
    setBulkOperationLoading,
    bulkStage,
    bulkReasons,
    setBulkOpen,
    setBulkReasons,
    setChecked,
    bulkManagerId,
    preferredManagerId,
    setBulkManagerOpen,
    setBulkManagerId,
    bulkVacancyId,
    setBulkVacancyOpen,
    setBulkVacancyId,
    bulkHandoffClientId,
    setBulkHandoffOpen,
    setBulkHandoffClientId,
    bulkTagsList,
    bulkTagsOperation,
    setBulkTagsOpen,
    setBulkTagsList,
    bulkActivityTitle,
    bulkActivityDueAt,
    bulkActivityOffsetMinutes,
    bulkActivityType,
    setBulkActivitiesOpen,
    setBulkDeleteOpen,
  })


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
    setStageFilter,
  })

  // Reusable secondary button style for top/filter actions
  const secondaryBtn = "inline-flex items-center gap-2 px-3 py-2 rounded-md border border-slate-300 text-slate-800 bg-white hover:bg-slate-100 active:bg-slate-200 transition-colors cursor-pointer";

  const hasFilterBadges =
    Boolean(q) ||
    stageFilter.length > 0 ||
    candidateRowStatusFilter.length > 0 ||
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
    intakeApplicationKindFilter === 'client' ||
    intakeApplicationKindFilter === 'candidate' ||
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

  const tableRowCellsCtx = useMemo(
    () => ({
      t, locale,
      focusedRowIndex, workPanelOpen, selectedCandidateId,
      setSelectedCandidateId, setSidebarOpen,
      checked, toggle, canManage, canViewActivities,
      orderedVisibleColumns, visibleCols, getColumnWidth,
      vacancyLabelMap, preferredChannelLabelMap, inPolandLabelMap, reasonLabelMap,
      resolveManagerLabel, getPolandBasisLabel, getTrailerTypeLabel, asTelHref,
      navigate, handleCandidateOpen, setItems, setTaskQuickModal, planLimitModal,
    }),
    [
      t, locale,
      focusedRowIndex, workPanelOpen, selectedCandidateId,
      setSelectedCandidateId, setSidebarOpen,
      checked, toggle, canManage, canViewActivities,
      orderedVisibleColumns, visibleCols, getColumnWidth,
      vacancyLabelMap, preferredChannelLabelMap, inPolandLabelMap, reasonLabelMap,
      resolveManagerLabel, getPolandBasisLabel, getTrailerTypeLabel, asTelHref,
      navigate, handleCandidateOpen, setItems, setTaskQuickModal, planLimitModal,
    ],
  )

  if (isKanban) {
    return <Pipeline />
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
          {showDebugPanel && (
            <CandidatesDebugPanel
              t={t}
              onForceTwoApplied={() => load({ force: true })}
              debugHit={debugHit}
              debugClickHit={debugClickHit}
              debugMouseUpHit={debugMouseUpHit}
              debugClickHitBubble={debugClickHitBubble}
              debugMouseUpHitBubble={debugMouseUpHitBubble}
              sidebarOpen={sidebarOpen}
              selectedCandidateId={selectedCandidateId}
            />
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

          <div className="mx-4 mb-1.5 shrink-0 flex items-center justify-between gap-2">
            <PageBreadcrumb />
            <button
              type="button"
              onClick={() => {
                const next = !workPanelOpen
                setSidebarOpen(next)
                if (!next) setSelectedCandidateId(null)
              }}
              className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-700 transition hover:bg-slate-50"
              title={workPanelOpen ? t('app.candidates.menu.close') : t('app.candidates.menu.open')}
              aria-label={workPanelOpen ? t('app.candidates.menu.close') : t('app.candidates.menu.open')}
            >
              {workPanelOpen ? (
                <>
                  <IconX size={18} stroke={2} />
                  <span className="hidden sm:inline">{t('app.candidates.menu.close')}</span>
                </>
              ) : (
                <>
                  <IconLayoutSidebarLeftExpand size={18} stroke={2} />
                  <span className="hidden sm:inline">{t('app.candidates.menu.open')}</span>
                </>
              )}
            </button>
          </div>

          {candidatesQuotaWarning ? (
            <div className="mx-4 mb-2 shrink-0">
              <QuotaNearLimitBanner
                kind="candidates_active"
                percentUsed={candidatesQuotaWarning.percentUsed}
              />
            </div>
          ) : null}

          <CandidatesFiltersToolbar
            t={t}
            locale={locale}
            q={q}
            setQ={setQ}
            searchRef={searchRef}
            quickViewParam={quickViewParam}
            applyQuickViewFilters={applyQuickViewFilters}
            isFavoriteFilter={isFavoriteFilter}
            setIsFavoriteFilter={setIsFavoriteFilter}
            quickDocFilters={quickDocFilters}
            quickFiltersExpanded={quickFiltersExpanded}
            toggleQuickDocFilter={toggleQuickDocFilter}
            setQuickFiltersExpanded={setQuickFiltersExpanded}
            savedViews={savedViews}
            applyView={applyView}
            deleteView={deleteView}
            stageOptions={quickStageOptions}
            stageLabelMap={stageLabelMap}
            managers={quickManagers}
            vacancies={quickVacancies}
            stageFilter={stageFilter}
            setStageFilter={setStageFilter}
            candidateRowStatusFilter={candidateRowStatusFilter}
            setCandidateRowStatusFilter={setCandidateRowStatusFilter}
            candidateRowStatusLabel={candidateRowStatusLabel}
            managerFilter={managerFilter}
            setManagerFilter={setManagerFilter}
            vacancyFilter={vacancyFilter}
            setVacancyFilter={setVacancyFilter}
            hasFilterBadges={hasFilterBadges}
            textFilters={textFilters}
            setTextFilter={setTextFilter}
            statusReasonFilter={statusReasonFilter}
            setStatusReasonFilter={setStatusReasonFilter}
            docsStatusFilter={docsStatusFilter}
            setDocsStatusFilter={setDocsStatusFilter}
            docsOrderedFilter={docsOrderedFilter}
            setDocsOrderedFilter={setDocsOrderedFilter}
            preferredChannelFilter={preferredChannelFilter}
            setPreferredChannelFilter={setPreferredChannelFilter}
            inPolandFilter={inPolandFilter}
            setInPolandFilter={setInPolandFilter}
            opsModeFilter={opsModeFilter}
            setOpsModeFilter={setOpsModeFilter}
            polandBasisFilter={polandBasisFilter}
            setPolandBasisFilter={setPolandBasisFilter}
            trailerTypesFilter={trailerTypesFilter}
            setTrailerTypesFilter={setTrailerTypesFilter}
            createdRange={createdRange}
            setCreatedRange={setCreatedRange}
            firstContactRange={firstContactRange}
            setFirstContactRange={setFirstContactRange}
            docsValidRange={docsValidRange}
            setDocsValidRange={setDocsValidRange}
            docsHasFilesFilter={docsHasFilesFilter}
            setDocsHasFilesFilter={setDocsHasFilesFilter}
            handoffStatusFilter={handoffStatusFilter}
            setHandoffStatusFilter={setHandoffStatusFilter}
            contactAttemptsFilter={contactAttemptsFilter}
            setContactAttemptsFilter={setContactAttemptsFilter}
            processorFilter={processorFilter}
            setProcessorFilter={setProcessorFilter}
            intakeApplicationKindFilter={intakeApplicationKindFilter}
            setIntakeApplicationKindFilter={setIntakeApplicationKindFilter}
            vacancyLabelMap={vacancyLabelMap}
            managerLabelMap={managerLabelMap}
            reasonLabelMap={reasonLabelMap}
            reasonStageMap={reasonStageMap}
            preferredChannelLabelMap={preferredChannelLabelMap}
            inPolandLabelMap={inPolandLabelMap}
            opsModeLabelMap={opsModeLabelMap}
            getPolandBasisLabel={getPolandBasisLabel}
            getTrailerTypeLabel={getTrailerTypeLabel}
            docsStatusFilterOptions={docsStatusFilterOptions}
            docsOrderFilterOptions={docsOrderFilterOptions}
          />

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
              defaultValue:
                'Layout mode: drag the dotted grip on the left of each header to reorder columns; drag the right edge of a header to resize width.',
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
                    <CandidatesTableRowCells index={index} c={c} ctx={tableRowCellsCtx} />
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
                    whyHint={
                      hasActiveTableFilters
                        ? undefined
                        : t('app.candidates.table.empty_why', {
                            defaultValue:
                              'Candidates are people you actively work with — qualified leads, contacted prospects, hires in pipeline. Convert a lead from the Leads inbox or import a list to start.',
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
            className="flex h-full min-h-0 min-w-0 w-full flex-col overflow-hidden"
            style={{ maxWidth: CANDIDATES_WORK_PANEL_RAIL_WIDTH_PX }}
          >
            <CandidatesWorkPanel
              summaryHero={summaryHero}
              previewVisible={false}
              previewSlot={null}
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
              setSaveViewIncludeTableLayout(true)
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
            orderedVisibleColumns={orderedVisibleColumns}
            moveColumnRelative={moveColumnRelative}
            onResetColumnLayout={resetColumnLayout}
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
                      defaultValue: 'Open preview and the reminders window.',
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

      <Modal
        open={Boolean(selectedCandidate)}
        onClose={() => {
          setSelectedCandidateId(null)
          setSidebarOpen(false)
        }}
        title={t('app.candidates.preview_modal.shell_title', { defaultValue: 'Candidate preview' })}
        size="2xl"
      >
        {selectedCandidate ? (
          <CandidatesSelectedPanel
            t={t}
            locale={locale}
            selectedCandidate={selectedCandidate}
            selectedCandidateId={selectedCandidateId}
            stageSummaryLabel={translateStageLabel(
              t,
              String((selectedCandidate as any).stage || ''),
              String((selectedCandidate as any).stage_label || ''),
            )}
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
        ) : null}
      </Modal>

      {taskQuickModal ? (
        <CandidateQuickTaskModal
          open
          onClose={() => setTaskQuickModal(null)}
          candidateId={taskQuickModal.id}
          candidateLabel={taskQuickModal.label}
          t={t}
        />
      ) : null}

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
          <label className="flex cursor-pointer items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="mt-0.5 shrink-0"
              checked={saveViewIncludeTableLayout}
              onChange={(e) => setSaveViewIncludeTableLayout(e.currentTarget.checked)}
            />
            <span>
              {t('app.candidates.views.save_modal.include_table_layout', {
                defaultValue: 'Include visible columns, order, and widths in this view',
              })}
            </span>
          </label>
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
                    intakeApplicationKind: intakeApplicationKindFilter,
                    ...(saveViewIncludeTableLayout
                      ? {
                          tableLayout: {
                            visibleCols,
                            columnOrder,
                            columnWidths,
                          },
                        }
                      : {}),
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

      <CandidatesBulkModalsCluster
        t={t}
        canManage={canManage}
        canViewActivities={canViewActivities}
        bulkOperationLoading={bulkOperationLoading}
        checked={checked}
        actions={{
          doBulkActivities,
          doBulk,
          doBulkAssign,
          doBulkAssignVacancy,
          doBulkHandoff,
          doBulkTags,
          doBulkDelete,
        }}
        bulkManagerOpen={bulkManagerOpen}
        setBulkManagerOpen={setBulkManagerOpen}
        managers={managers}
        bulkManagerId={bulkManagerId}
        setBulkManagerId={setBulkManagerId}
        bulkVacancyOpen={bulkVacancyOpen}
        setBulkVacancyOpen={setBulkVacancyOpen}
        vacancies={vacancies}
        bulkVacancyId={bulkVacancyId}
        setBulkVacancyId={setBulkVacancyId}
        bulkHandoffOpen={bulkHandoffOpen}
        setBulkHandoffOpen={setBulkHandoffOpen}
        handoffClients={handoffClients}
        handoffClientsLoading={handoffClientsLoading}
        bulkHandoffClientId={bulkHandoffClientId}
        setBulkHandoffClientId={setBulkHandoffClientId}
        bulkTagsOpen={bulkTagsOpen}
        setBulkTagsOpen={setBulkTagsOpen}
        bulkTagsOperation={bulkTagsOperation}
        setBulkTagsOperation={setBulkTagsOperation}
        bulkTagsList={bulkTagsList}
        setBulkTagsList={setBulkTagsList}
        bulkActivitiesOpen={bulkActivitiesOpen}
        setBulkActivitiesOpen={setBulkActivitiesOpen}
        bulkActivityTitle={bulkActivityTitle}
        setBulkActivityTitle={setBulkActivityTitle}
        bulkActivityDueAt={bulkActivityDueAt}
        setBulkActivityDueAt={setBulkActivityDueAt}
        bulkActivityOffsetMinutes={bulkActivityOffsetMinutes}
        setBulkActivityOffsetMinutes={setBulkActivityOffsetMinutes}
        bulkActivityType={bulkActivityType}
        setBulkActivityType={setBulkActivityType}
        bulkDeleteOpen={bulkDeleteOpen}
        setBulkDeleteOpen={setBulkDeleteOpen}
        bulkOpen={bulkOpen}
        setBulkOpen={setBulkOpen}
        bulkStage={bulkStage}
        setBulkStage={setBulkStage}
        bulkReasons={bulkReasons}
        setBulkReasons={setBulkReasons}
        stageOptions={stageOptions}
        meta={meta}
        activitiesModalOpen={activitiesModalOpen}
        setActivitiesModalOpen={setActivitiesModalOpen}
        activitiesModalRefresh={activitiesModalRefresh}
      />

    </div>
  )
}
