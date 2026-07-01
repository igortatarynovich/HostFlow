// src/pages/Pipeline.tsx
import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { PipelineOut, Vacancy } from '../api/types'
import { usePermissions } from '../hooks/usePermissions'
import { useTeamTierFeatures } from '../hooks/useTeamTierFeatures'
import { useI18n } from '../i18n'
import { useMetaStages } from '../store/useMeta'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { getFriendlyErrorInfo } from '../utils/friendlyError'
import { isCandidateRecruiterIdCanonEnabled } from '../utils/featureFlags'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'

import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'

import {
  KANBAN_ORDER,
  DEFAULT_COLUMN_STAGES,
  DEFAULT_COLUMN_ORDER,
  DEFAULT_STAGE_SEQUENCE,
} from '../modules/pipeline/constants'
import type { AnyObj, ManagerItem } from '../modules/pipeline/types'
import { normalizeStageCode } from '../modules/pipeline/utils'
import { PipelineOverlays } from '../modules/pipeline/PipelineOverlays'
import { PipelineBulkSelectionBar } from '../modules/pipeline/PipelineBulkSelectionBar'
import { PipelineKanbanBoard } from '../modules/pipeline/PipelineKanbanBoard'
import { PipelineKanbanWorkspace } from '../modules/pipeline/PipelineKanbanWorkspace'
import { PipelineInspectorDrawer } from '../modules/pipeline/PipelineInspectorDrawer'
import {
  formatMissingPipelineDocTypes,
  parseStageTransitionError,
} from '../modules/pipeline/pipelineStageErrors'
import {
  buildFilteredPipelineColumns,
  computePipelineColumnInsights,
} from '../modules/pipeline/filterPipelineColumns'
import {
  normalizeVacancyPipelinePayload,
  rebuildPipelineColumnsFromCandidates,
} from '../modules/pipeline/normalizeVacancyPipelinePayload'
import { filterRecruitmentVisibleStageCodes } from '../constants/recruitmentStageSurface'
import { parseMetaStagesApiResponse } from '../modules/pipeline/parseMetaStagesApiResponse'
import { parseVacancyPipelineProfileStagesPatch } from '../modules/pipeline/parseVacancyPipelineProfilePatch'
import {
  applyOptimisticBulkSelectionMove,
  applyOptimisticDndCardMove,
  buildBulkColumnStagePlansFromMatrix,
  summarizeBulkStageRejectionStats,
} from '../modules/pipeline/pipelineKanbanMutations'
import { usePipelineStagePath } from '../modules/pipeline/usePipelineStagePath'
export default function Pipeline(){
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [vacancyId, setVacancyId] = useState<string>('')
  const [data, setData] = useState<PipelineOut | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [columnOrder, setColumnOrder] = useState<string[]>(DEFAULT_COLUMN_ORDER)
  const [columnStages, setColumnStages] = useState<Record<string, string[]>>(DEFAULT_COLUMN_STAGES)
  const [stageSequence, setStageSequence] = useState<string[]>(DEFAULT_STAGE_SEQUENCE)
  const [profileStages, setProfileStages] = useState<{
    stage_codes?: string[]
    stage_labels?: Record<string, Record<string, string>>
    stage_columns?: Record<string, string[]>
    column_order?: string[]
  } | null>(null)
  const { orderedStageCodes, stageToColumn, resolveColumnStage, buildStagePath } =
    usePipelineStagePath(columnStages, stageSequence, columnOrder)
  const [savingIds, setSavingIds] = useState<Record<string, boolean>>({})

  // selection & managers (for bulk actions)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [managers, setManagers] = useState<ManagerItem[]>([])

  const [searchParams, setSearchParams] = useSearchParams()

  // simple filters
  const [filters, setFilters] = useState<{ search:string; manager:string; citizenship:string; docs:string; from:string; to:string }>({
    search: '', // search by name, email, phone
    manager: '',
    citizenship: '',
    docs: '', // '', 'yes', 'partial', 'no'
    from: '', // yyyy-mm-dd
    to: '',   // yyyy-mm-dd
  })
  const { can } = usePermissions()
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const navigate = useNavigate()
  const meta = useMetaStages()
  const canManage = can('candidates.manage')
  const canViewPipeline = canManage || can('candidates.pipeline')
  const canViewTasks = can('notifications.view')
  const canViewSettings = can('settings.view')
  const { allowsTeamFeatures, planLoading: planTierLoading } = useTeamTierFeatures()

  const formatMissingDocTypes = useCallback(
    (codes: string[]) =>
      formatMissingPipelineDocTypes(codes, (code) =>
        t(`admin.documents.types.${code}`, { defaultValue: code }),
      ),
    [t],
  )

  // Sidebar state - синхронизируется с Candidates.tsx через события
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
  }, [sidebarOpen])

  
  // Context menu state
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; candidateId: string } | null>(null)
  const contextMenuRef = useRef<HTMLDivElement | null>(null)
  
  // Bulk modals state
  const [bulkOpen, setBulkOpen] = useState(false)
  const [bulkStage, setBulkStage] = useState<string>('')
  const [bulkReasons, setBulkReasons] = useState<string[]>([])
  const [bulkManagerOpen, setBulkManagerOpen] = useState(false)
  const [bulkManagerId, setBulkManagerId] = useState('')
  const [bulkVacancyOpen, setBulkVacancyOpen] = useState(false)
  const [bulkVacancyId, setBulkVacancyId] = useState('')
  const [bulkOperationLoading, setBulkOperationLoading] = useState<'stage' | 'manager' | 'vacancy' | null>(null)
  
  // Stage options for bulk modal
  const stageOptions = useMemo(() => {
    const raw = meta?.order || meta?.codes || orderedStageCodes || []
    const list = Array.isArray(raw) ? raw.map((c) => String(c)) : []
    return filterRecruitmentVisibleStageCodes(list)
  }, [meta, orderedStageCodes])

  // --- initialize from URL search params
  useEffect(() => {
    const v = searchParams.get('vacancy') || ''
    const search = searchParams.get('q') || ''
    const manager = searchParams.get('m') || ''
    const citizenship = searchParams.get('c') || ''
    const docs = searchParams.get('d') || ''
    const from = searchParams.get('from') || ''
    const to = searchParams.get('to') || ''
    if (v) setVacancyId(v)
    setFilters({ search, manager, citizenship, docs, from, to })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // For DnD: keep a local registry of draggable id -> {candidateId, fromStage}
  const dragRegistry = useRef<Record<string, { candidateId: string; fromColumn: string; stage?: string }>>({})
  const suppressClickAfterDragRef = useRef<Set<string>>(new Set())
  const tableContainerRef = useRef<HTMLDivElement>(null)

  const registerSuppressClick = useCallback((candidateId: string) => {
    suppressClickAfterDragRef.current.add(candidateId)
    window.setTimeout(() => suppressClickAfterDragRef.current.delete(candidateId), 120)
  }, [])

  const shouldSuppressLinkClick = useCallback(
    (candidateId: string) => suppressClickAfterDragRef.current.has(candidateId),
    [],
  )

  useEffect(() => {
    if (!canManage) {
      setSelectedIds([])
    }
  }, [canManage])

  // --- sync vacancy/filters to URL
  useEffect(() => {
    const next = new URLSearchParams(searchParams)
    const keys = ['vacancy', 'q', 'm', 'c', 'd', 'from', 'to']
    keys.forEach((key) => next.delete(key))
    if (vacancyId) next.set('vacancy', vacancyId)
    if (filters.search) next.set('q', filters.search)
    if (filters.manager) next.set('m', filters.manager)
    if (filters.citizenship) next.set('c', filters.citizenship)
    if (filters.docs) next.set('d', filters.docs)
    if (filters.from) next.set('from', filters.from)
    if (filters.to) next.set('to', filters.to)
    setSearchParams(next, { replace: true })
  }, [filters, searchParams, setSearchParams, vacancyId])

  // --- load stages meta to know canonical order/codes
  useEffect(() => {
    api
      .get('/meta/stages')
      .then(({ data }) => {
        const patch = parseMetaStagesApiResponse(data);
        if (patch.columnStages) setColumnStages(patch.columnStages);
        if (patch.columnOrder) setColumnOrder(patch.columnOrder);
        if (patch.stageSequence) setStageSequence(patch.stageSequence);
      })
      .catch(() => {
        /* silent */
      });
  }, [])

  // --- load vacancies list (accept array or {items})
  useEffect(() => {
    api.get('/vacancies/').then(({data}) => {
      const items: Vacancy[] = Array.isArray(data) ? data : (data?.items || [])
      setVacancies(items)
      if (!vacancyId && items?.[0]?.id) setVacancyId(items[0].id)
    }).catch(()=>{/* ignore */})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // --- load managers for bulk-assign (accept array or {items})
  useEffect(() => {
    api.get('/catalogs/managers', { params: { roles: 'recruiter' } })
      .then(({ data }) => {
        const list: any[] = Array.isArray(data) ? data : (data?.items || [])
        const mapped: ManagerItem[] = list.map((it:any) => ({ id: it?.id || it?.user_id || it?.uid, name: it?.name || it?.email || '—' }))
          .filter(m => m.id)
        setManagers(mapped)
      })
      .catch(() => {/* ignore */})
  }, [])

  // --- selection helpers
  const isSelected = useCallback((id:string) => selectedIds.includes(id), [selectedIds])
  const toggleSelected = useCallback((id:string) => {
    if (!canManage) return
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x=>x!==id) : [...prev, id])
  }, [canManage])
  const clearSelection = useCallback(() => {
    if (!canManage) return
    setSelectedIds([])
  }, [canManage])

  async function load(){
    if (!vacancyId) return
    setLoading(true)
    setError(null)
    try{
      const resp = await api.get(
        `/vacancies/${vacancyId}/pipeline`,
        { validateStatus: status => status === 200 || status === 404 }
      )
      if (resp.status === 404) {
        setData({ columns: {}, statuses: [] } as PipelineOut)
        return
      }
      const raw: AnyObj = resp.data || {}

      const profilePatch = parseVacancyPipelineProfileStagesPatch(raw)
      setProfileStages(profilePatch.profile)
      if (profilePatch.profile) {
        if (profilePatch.columnOrder?.length) setColumnOrder(profilePatch.columnOrder)
        if (profilePatch.columnStages && Object.keys(profilePatch.columnStages).length) {
          setColumnStages(profilePatch.columnStages)
        }
        if (profilePatch.stageSequence?.length) setStageSequence(profilePatch.stageSequence)
      }

      const { normalized, total } = normalizeVacancyPipelinePayload(raw, columnOrder)

      if (total === 0) {
        try {
          let candData: any
          try {
            const candResp = await api.get('/candidates?limit=200&offset=0')
            candData = candResp.data
          } catch {
            const candResp = await api.get('/candidates/')
            candData = candResp.data
          }
          const list: any[] = Array.isArray(candData) ? candData : (candData?.items || [])
          const filtered = list.filter((c: any) => {
            const vid = c?.vacancy_id ?? c?.vacancy ?? c?.vacancy?.id
            return String(vid || '') === String(vacancyId || '')
          })
          const normalizedFromCandidates = rebuildPipelineColumnsFromCandidates(
            raw,
            filtered,
            normalized.statuses,
            stageToColumn,
          )
          setData(normalizedFromCandidates)
          console.debug('[pipeline] rebuilt from candidates', normalizedFromCandidates)
        } catch {
          setData(normalized)
        }
      } else {
        setData(normalized)
      }

      console.debug('[pipeline] raw', raw)
      console.debug('[pipeline] normalized payload', normalized)
    } catch (err: any){
      if (err?.response?.status === 404){
        const statuses = columnOrder
        const emptyCols = Object.fromEntries((statuses || []).map((s)=>[s, []]))
        setData({ columns: emptyCols, statuses } as any)
      } else if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.candidates.pipeline.error_load'))) {
        setError(null)
        setData(null)
      } else {
        setError(getFriendlyErrorInfo(err, t('app.candidates.pipeline.error_load'), t))
        setData(null)
      }
    } finally {
      setLoading(false)
    }
  }

  // --- bulk actions
  async function bulkMoveStage(toColumn: string){
    if (!canManage) return
    if (!toColumn || selectedIds.length === 0 || !vacancyId) return
    let stagePlans: Record<string, { targetStage: string; stages: string[] }> = {}
    setData((prev) => {
      const { next, stagePlans: plans } = applyOptimisticBulkSelectionMove(
        prev,
        selectedIds,
        toColumn,
        buildStagePath,
      )
      stagePlans = plans
      return next
    })
    let hadErrors = false
    let rodoBlocked = 0
    let docsBlocked = 0
    const missingByDocs: string[] = []
    let rejectedResults: PromiseRejectedResult[] = []
    try{
      const results = await Promise.allSettled(
        selectedIds
          .map(async id => {
          const plan = stagePlans[id] || buildStagePath(undefined, toColumn)
          if (!plan.stages.length) return
          for (const stage of plan.stages){
            await api.patch(`/candidates/${id}`, { stage, vacancy_id: vacancyId })
          }
        })
      )
      const rejected = results.filter((result): result is PromiseRejectedResult => result.status === 'rejected')
      rejectedResults = rejected
      if (rejected.length > 0){
        hadErrors = true
        const stats = summarizeBulkStageRejectionStats(rejected)
        rodoBlocked = stats.rodoBlocked
        docsBlocked = stats.docsBlocked
        missingByDocs.push(...stats.missingByDocs)
      }
    } finally {
      clearSelection()
      await load()
      if (hadErrors){
        const retryHint = t('app.common.retry_hint')
        if (rodoBlocked > 0) {
          setError({
            title: t('app.candidates.messages.bulk_stage_rodo_blocked', {
              values: { rodo: rodoBlocked, total: selectedIds.length },
            }),
            hint: retryHint,
          })
        } else if (missingByDocs.length > 0) {
          setError({
            title: t('app.candidates.messages.bulk_stage_handoff_docs_blocked', {
              values: { docs: docsBlocked, total: selectedIds.length, missing: formatMissingDocTypes(missingByDocs) },
            }),
            hint: retryHint,
          })
        } else {
          const raw = rejectedResults[0]?.reason
          const handledByPlanLimit = planLimitModal?.showPlanLimitIfNeeded(
            raw,
            t('app.candidates.pipeline.error_update_stages'),
          )
          if (!handledByPlanLimit) {
            setError(getFriendlyErrorInfo(raw, t('app.candidates.pipeline.error_update_stages'), t))
          }
        }
      }
    }
  }

  async function bulkAssignManager(managerId: string){
    if (!canManage) return
    if (!managerId || selectedIds.length === 0) return
    setBulkOperationLoading('manager')
    try{
      // Phase 2.6.G-5 Stage F — canonical assignee field on the PATCH
      // body is ``recruiter_id``. We keep ``manager`` for rollback /
      // older backends; the two columns stay in lock-step by design.
      await Promise.allSettled(
        selectedIds.map(id => {
          const patchBody: Record<string, string> = isCandidateRecruiterIdCanonEnabled()
            ? { recruiter_id: managerId, manager: managerId }
            : { manager: managerId }
          return api.patch(`/candidates/${id}`, patchBody)
        })
      )
    } finally {
      setBulkOperationLoading(null)
      setBulkManagerOpen(false)
      clearSelection()
      await load()
    }
  }
  
  async function bulkAssignVacancy(vacancyId: string){
    if (!canManage) return
    if (!vacancyId || selectedIds.length === 0) return
    setBulkOperationLoading('vacancy')
    try{
      await Promise.allSettled(selectedIds.map(id => api.patch(`/candidates/${id}`, { vacancy_id: vacancyId })))
    } finally {
      setBulkOperationLoading(null)
      setBulkVacancyOpen(false)
      clearSelection()
      await load()
    }
  }
  
  async function doBulkStage(){
    if (!canManage || !bulkStage || selectedIds.length === 0 || !vacancyId) return
    setBulkOperationLoading('stage')
    try {
      const stagePlans = buildBulkColumnStagePlansFromMatrix(
        data?.columns as Record<string, unknown[]> | undefined,
        selectedIds,
        bulkStage,
        buildStagePath,
      )

      const results = await Promise.allSettled(
        selectedIds.map(async id => {
          const plan = stagePlans[id] || buildStagePath(undefined, bulkStage)
          if (!plan.stages.length) return
          for (const stage of plan.stages){
            await api.patch(`/candidates/${id}`, { 
              stage, 
              vacancy_id: vacancyId,
              status_reason: bulkReasons.length > 0 ? bulkReasons : undefined
            })
          }
        })
      )
      
      const rejected = results.filter((result): result is PromiseRejectedResult => result.status === 'rejected')
      if (rejected.length > 0){
        const { rodoBlocked, docsBlocked, missingByDocs } = summarizeBulkStageRejectionStats(rejected)
        const retryHintBulk = t('app.common.retry_hint')
        if (rodoBlocked > 0) {
          setError({
            title: t('app.candidates.messages.bulk_stage_rodo_blocked', {
              values: { rodo: rodoBlocked, total: selectedIds.length },
            }),
            hint: retryHintBulk,
          })
        } else if (missingByDocs.length > 0) {
          setError({
            title: t('app.candidates.messages.bulk_stage_handoff_docs_blocked', {
              values: { docs: docsBlocked, total: selectedIds.length, missing: formatMissingDocTypes(missingByDocs) },
            }),
            hint: retryHintBulk,
          })
        } else {
          const raw = rejected[0]?.reason
          if (planLimitModal?.showPlanLimitIfNeeded(raw, t('app.candidates.pipeline.error_update_stages'))) {
            return
          }
          setError(getFriendlyErrorInfo(raw, t('app.candidates.pipeline.error_update_stages'), t))
        }
      }
    } finally {
      setBulkOperationLoading(null)
      setBulkOpen(false)
      setBulkReasons([])
      clearSelection()
      await load()
    }
  }
  
  async function doBulkAssign(){
    await bulkAssignManager(bulkManagerId)
  }
  
  async function doBulkAssignVacancy(){
    await bulkAssignVacancy(bulkVacancyId)
  }
  
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

  async function bulkArchive(){
    if (!canManage) return
    if (selectedIds.length === 0) return
    try{
      await Promise.allSettled(selectedIds.map(id => api.patch(`/candidates/${id}`, { is_archived: true })))
    } finally {
      clearSelection()
      await load()
    }
  }

  async function moveCandidate(candidateId: string, toColumn: string, currentStage?: string){
    if (!canManage) return
    if (!vacancyId) return
    const normalizedCurrent = normalizeStageCode(currentStage)
    const plan = buildStagePath(normalizedCurrent, toColumn)
    console.debug('[pipeline] move plan', { candidateId, from: normalizedCurrent, toColumn, plan })
    const targetStage = plan.targetStage
    setData((prev) => applyOptimisticDndCardMove(prev, candidateId, toColumn, targetStage))

    setSavingIds(s => ({ ...s, [candidateId]: true }))
    let hadError = false
    let specificErrorSet = false
    let lastMoveErr: unknown = null
    try{
      if (plan.stages.length){
        for (const stage of plan.stages){
          await api.patch(`/candidates/${candidateId}`, {
            stage,
            vacancy_id: vacancyId,
          })
        }
      }
    } catch (e){
      lastMoveErr = e
      hadError = true
      const parsed = parseStageTransitionError(e)
      const dndRetryHint = t('app.common.retry_hint')
      if (parsed.kind === 'rodo') {
        specificErrorSet = true
        setError({
          title: t('app.candidate_card.messages.rodo_stage_blocked', {
            defaultValue: 'RODO must be sent before moving to contact stage.',
          }),
          hint: dndRetryHint,
        })
      } else if (parsed.kind === 'handoff_docs') {
        specificErrorSet = true
        setError({
          title:
            t('app.candidate_card.messages.handoff_docs_incomplete', {
              defaultValue: "Cannot move to 'Ready for handoff': required documents checklist is incomplete.",
            }) + ` ${formatMissingDocTypes(parsed.missingTypes)}`,
          hint: dndRetryHint,
        })
      }
      await load()
    } finally {
      setSavingIds(s => ({ ...s, [candidateId]: false }))
      if (hadError){
        if (!specificErrorSet) {
          if (!planLimitModal?.showPlanLimitIfNeeded(lastMoveErr, t('app.candidates.pipeline.error_update_stage'))) {
            setError(getFriendlyErrorInfo(lastMoveErr, t('app.candidates.pipeline.error_update_stage'), t))
          }
        }
      }
    }
  }

  // Helper: select/deselect all cards in a column
  function toggleAllInColumn(colIds: string[], select: boolean){
    if (!canManage) return
    setSelectedIds(prev => {
      const set = new Set(prev)
      if (select){
        for (const id of colIds) set.add(id)
      } else {
        for (const id of colIds) set.delete(id)
      }
      return Array.from(set)
    })
  }

  useEffect(() => { load() }, [vacancyId, columnOrder.join(',')])

  // ESC clears selection
  useEffect(() => {
    function onKey(e: KeyboardEvent){ if (e.key === 'Escape') clearSelection() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [clearSelection])

  const columnsOrder = useMemo(() => {
    const base = data?.statuses?.length
      ? data.statuses
      : (columnOrder.length ? columnOrder : Array.from(KANBAN_ORDER))
    const extras = Array.from(
      new Set([
        ...columnOrder,
        ...Object.keys(columnStages || {}),
      ])
    ).filter((code) => !base.includes(code))
    return [...base, ...extras]
  }, [data, columnOrder, columnStages])

  const filteredColumns = useMemo(
    () => buildFilteredPipelineColumns(data, columnsOrder, filters),
    [data, filters, columnsOrder],
  )

  const pipelineInsights = useMemo(
    () => computePipelineColumnInsights(filteredColumns, columnsOrder),
    [filteredColumns, columnsOrder],
  )

  // --- DnD handlers ---
  function handleDragStart(_e: DragStartEvent){
    if (!canManage) return
    // registry is filled during render
  }

  async function handleDragEnd(e: DragEndEvent){
    if (!canManage) return
    const activeId = String(e.active.id)
    const overId = e.over ? String(e.over.id) : null
    if (!overId) return

    const entry = dragRegistry.current[activeId]
    if (!entry) return

    const { candidateId, fromColumn, stage } = entry
    registerSuppressClick(candidateId)
    if (fromColumn !== overId){
      await moveCandidate(candidateId, overId, stage)
    }
  }

  const switchToTable = useCallback(() => {
    const next = new URLSearchParams(searchParams)
    next.delete('view')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  if (!canViewPipeline) {
    return (
      <div className="card p-4 text-sm text-amber-800 bg-amber-50 border border-amber-200">
        {t('app.candidates.pipeline.access_denied')}
      </div>
    )
  }

  return (
    <div className="relative flex h-full min-h-0 w-full flex-1 flex-col">
      <PipelineKanbanWorkspace
        sidebarOpen={sidebarOpen}
        tableContainerRef={tableContainerRef}
        onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        closeSidebarLabel={t('app.candidates.menu.close')}
        openSidebarLabel={t('app.candidates.menu.open')}
        error={error}
        onRetryLoad={() => void load()}
        retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
        candidatesNavLabel={t('app.nav.items.candidates', { defaultValue: 'Candidates' })}
        showMainEmpty={pipelineInsights.total === 0}
        loading={loading}
        bulkBar={
          canManage && selectedIds.length > 0 ? (
            <PipelineBulkSelectionBar
              selectedCount={selectedIds.length}
              columnsOrder={columnsOrder}
              managers={managers}
              onMoveStage={bulkMoveStage}
              onAssignManager={bulkAssignManager}
              onClearSelection={clearSelection}
              onArchive={bulkArchive}
              planTierLoading={planTierLoading}
              allowsTeamFeatures={allowsTeamFeatures}
              canViewSettings={canViewSettings}
            />
          ) : null
        }
        kanban={
          <PipelineKanbanBoard
            canManage={canManage}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            columnsOrder={columnsOrder}
            resolveColumnStage={resolveColumnStage}
            vacancyId={vacancyId}
            filteredColumns={filteredColumns}
            data={data}
            columnStages={columnStages}
            selectedIds={selectedIds}
            onToggleAllInColumn={toggleAllInColumn}
            dragRegistry={dragRegistry}
            savingIds={savingIds}
            isSelected={isSelected}
            onToggleSelected={toggleSelected}
            onCardContextMenu={(clientX, clientY, candidateId) =>
              setContextMenu({ x: clientX, y: clientY, candidateId })
            }
            managers={managers}
            vacancies={vacancies}
            canViewTasks={canViewTasks}
            shouldSuppressLinkClick={shouldSuppressLinkClick}
          />
        }
      />

      <PipelineInspectorDrawer
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onSwitchToTable={switchToTable}
        insights={pipelineInsights}
        vacancyId={vacancyId}
        onVacancyChange={setVacancyId}
        vacancies={vacancies}
        filters={filters}
        setFilters={setFilters}
        managers={managers}
        onRefresh={() => void load()}
        loading={loading}
        canManage={canManage}
      />

      <PipelineOverlays
        contextMenu={contextMenu}
        contextMenuRef={contextMenuRef}
        filteredColumns={filteredColumns}
        canManage={canManage}
        onDismissContextMenu={() => setContextMenu(null)}
        onOpenCandidateFromMenu={(candidateId) => {
          navigate(`${CRM_APP_PATHS.candidates}/${candidateId}`)
          setContextMenu(null)
        }}
        onToggleSelectFromMenu={(candidateId) => {
          toggleSelected(candidateId)
          setContextMenu(null)
        }}
        isSelected={isSelected}
        onBeginBulkStageFromMenu={(candidateId) => {
          setSelectedIds([candidateId])
          setBulkStage(stageOptions[0] || 'new')
          setBulkReasons([])
          setBulkOpen(true)
          setContextMenu(null)
        }}
        onBeginBulkManagerFromMenu={(candidateId, item) => {
          setSelectedIds([candidateId])
          const row = item as AnyObj
          const c = (row?.candidate || row || {}) as AnyObj
          const managerId = c.manager_id || c.manager || row?.manager || row?.manager_id
          setBulkManagerId(managerId || managers[0]?.id || '')
          setBulkManagerOpen(true)
          setContextMenu(null)
        }}
        onBeginBulkVacancyFromMenu={(candidateId) => {
          setSelectedIds([candidateId])
          setBulkVacancyId(vacancyId || vacancies[0]?.id || '')
          setBulkVacancyOpen(true)
          setContextMenu(null)
        }}
        bulkStageOpen={bulkOpen}
        onBulkStageClose={() => {
          if (!bulkOperationLoading) {
            setBulkOpen(false)
            setBulkReasons([])
          }
        }}
        stageOptions={stageOptions}
        bulkStage={bulkStage}
        bulkReasons={bulkReasons}
        onBulkStageChange={setBulkStage}
        onBulkReasonsChange={setBulkReasons}
        onBulkStageApply={doBulkStage}
        bulkStageLoading={bulkOperationLoading === 'stage'}
        meta={meta}
        bulkManagerOpen={bulkManagerOpen}
        onBulkManagerClose={() => !bulkOperationLoading && setBulkManagerOpen(false)}
        managers={managers}
        bulkManagerId={bulkManagerId}
        onBulkManagerIdChange={setBulkManagerId}
        onBulkManagerApply={doBulkAssign}
        bulkManagerLoading={bulkOperationLoading === 'manager'}
        bulkVacancyOpen={bulkVacancyOpen}
        onBulkVacancyClose={() => !bulkOperationLoading && setBulkVacancyOpen(false)}
        vacancies={vacancies}
        bulkVacancyId={bulkVacancyId}
        onBulkVacancyIdChange={setBulkVacancyId}
        onBulkVacancyApply={doBulkAssignVacancy}
        bulkVacancyLoading={bulkOperationLoading === 'vacancy'}
      />
    </div>
  )
}
