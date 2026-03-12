// src/pages/Pipeline.tsx
import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { IconCalendar, IconFileText, IconMapPin, IconPhone, IconUser, IconBriefcase } from '@tabler/icons-react'
import { api } from '../api/client'
import type { PipelineOut, Vacancy } from '../api/types'
import StageTag from '../components/StageTag'
import EmptyStatePanel from '../components/EmptyStatePanel'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { usePermissions } from '../hooks/usePermissions'
import { useI18n } from '../i18n'
import { useMetaStages } from '../store/useMeta'
import {
  BulkStageModal,
  BulkManagerModal,
  BulkVacancyModal,
} from '../modules/candidates/components'

// --- dnd-kit ---
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  useDraggable,
  useDroppable,
} from '@dnd-kit/core'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'

import {
  KANBAN_ORDER,
  DEFAULT_COLUMN_STAGES,
  DEFAULT_COLUMN_ORDER,
  DEFAULT_STAGE_SEQUENCE,
  DEFAULT_STAGE_BY_COLUMN,
  TERMINAL_STAGE_CODES,
} from '../modules/pipeline/constants'
import type { AnyObj, ManagerItem } from '../modules/pipeline/types'
import {
  sanitizeStagePath,
  normalizeStageCode,
  parseJSONMaybe,
  pickMiniFields,
  parseISODateMaybe,
} from '../modules/pipeline/utils'
import { normalizeSearchValue, textMatches } from '../modules/candidates/candidateUtils'

// Re-export for backward compatibility
export { TERMINAL_STAGE_CODES, sanitizeStagePath }

export default function Pipeline(){
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [vacancyId, setVacancyId] = useState<string>('')
  const [data, setData] = useState<PipelineOut | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [columnOrder, setColumnOrder] = useState<string[]>(DEFAULT_COLUMN_ORDER)
  const [columnStages, setColumnStages] = useState<Record<string, string[]>>(DEFAULT_COLUMN_STAGES)
  const [stageSequence, setStageSequence] = useState<string[]>(DEFAULT_STAGE_SEQUENCE)
  const [profileStages, setProfileStages] = useState<{
    stage_codes?: string[]
    stage_labels?: Record<string, Record<string, string>>
    stage_columns?: Record<string, string[]>
    column_order?: string[]
  } | null>(null)
  const stageDefaults = useMemo(() => {
    const map: Record<string, string> = { ...DEFAULT_STAGE_BY_COLUMN }
    Object.entries(columnStages || {}).forEach(([column, codes]) => {
      if (!column) return
      if (Array.isArray(codes) && codes.length){
        map[column] = String(codes[0])
      }
    })
    return map
  }, [columnStages])
  const orderedStageCodes = useMemo(() => {
    const seq = Array.from(new Set(stageSequence.filter(Boolean)))
    if (seq.length) return seq
    const fallback = columnOrder.flatMap(column => columnStages[column] || [])
    if (fallback.length) return Array.from(new Set(fallback.filter(Boolean)))
    return DEFAULT_STAGE_SEQUENCE
  }, [stageSequence, columnOrder, columnStages])
  const stageIndexMap = useMemo(() => {
    const map: Record<string, number> = {}
    orderedStageCodes.forEach((code, idx) => { map[code] = idx })
    return map
  }, [orderedStageCodes])
  const stageToColumn = useMemo(() => {
    const map: Record<string, string> = {}
    Object.entries(DEFAULT_COLUMN_STAGES).forEach(([column, stages]) => {
      stages.forEach(stage => {
        if (stage) map[stage] = column
      })
    })
    Object.entries(columnStages).forEach(([column, stages]) => {
      stages.forEach(stage => {
        if (stage) map[stage] = column
      })
    })
    return map
  }, [columnStages])
  const resolveColumnStage = useCallback((column: string) => {
    const key = String(column || '').trim()
    if (!key) return ''
    const codes = columnStages[key]
    if (Array.isArray(codes) && codes.length){
      return codes[0]
    }
    return stageDefaults[key] || key
  }, [columnStages, stageDefaults])
  const buildStagePath = useCallback((fromStage: string | undefined, column: string) => {
    const targetStage = resolveColumnStage(column)
    if (!targetStage){
      return { targetStage: column, stages: [] as string[] }
    }
    if (!fromStage){
      return { targetStage, stages: [targetStage] }
    }
    if (fromStage === targetStage){
      return { targetStage, stages: [] as string[] }
    }
    const fromIdx = stageIndexMap[fromStage]
    const targetIdx = stageIndexMap[targetStage]
    if (fromIdx === undefined || targetIdx === undefined){
      return { targetStage, stages: [targetStage] }
    }
    if (targetIdx <= fromIdx){
      return { targetStage, stages: [targetStage] }
    }
    const stages: string[] = []
    for (let idx = fromIdx + 1; idx <= targetIdx; idx += 1){
      const stage = orderedStageCodes[idx]
      if (stage){
        stages.push(stage)
      }
    }
    const sanitizedStages = sanitizeStagePath(stages, targetStage)
    if (!sanitizedStages.length){
      sanitizedStages.push(targetStage)
    }
    return { targetStage, stages: sanitizedStages }
  }, [orderedStageCodes, resolveColumnStage, stageIndexMap])
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
  const navigate = useNavigate()
  const meta = useMetaStages()
  const canManage = can('candidates.manage')
  const canViewPipeline = canManage || can('candidates.pipeline')

  const parseStageTransitionError = useCallback((rawError: unknown): { kind: 'rodo' | 'handoff_docs' | 'other'; missingTypes: string[] } => {
    const err: any = rawError as any
    const detailRaw = err?.response?.data?.detail
    const toMissing = (val: any): string[] =>
      Array.isArray(val) ? val.map((x) => String(x || '').trim()).filter(Boolean) : []

    const parseDetailObject = (value: unknown): Record<string, any> | null => {
      if (value && typeof value === 'object') return value as Record<string, any>
      if (typeof value !== 'string') return null
      const text = value.trim()
      if (!text.startsWith('{')) return null
      try {
        const parsed = JSON.parse(text)
        return parsed && typeof parsed === 'object' ? (parsed as Record<string, any>) : null
      } catch {
        return null
      }
    }

    const detailObj = parseDetailObject(detailRaw)
    const detailText = String(detailRaw || '').toLowerCase()
    if (detailObj && String(detailObj.code || '') === 'handoff_docs_incomplete') {
      return { kind: 'handoff_docs', missingTypes: toMissing(detailObj.missing_types) }
    }
    if (detailText.includes('handoff_docs_incomplete')) {
      return { kind: 'handoff_docs', missingTypes: toMissing(detailObj?.missing_types) }
    }
    if (detailText.includes('rodo must be sent') || detailText.includes('contact/screening stage')) {
      return { kind: 'rodo', missingTypes: [] }
    }
    return { kind: 'other', missingTypes: [] }
  }, [])

  const formatMissingDocTypes = useCallback((codes: string[]): string => {
    const unique = Array.from(new Set(codes.map((c) => String(c || '').trim()).filter(Boolean)))
    if (!unique.length) return '—'
    return unique
      .map((code) => t(`admin.documents.types.${code}`, { defaultValue: code }))
      .join(', ')
  }, [t])
  
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
    // Отправляем состояние в Topbar (как в Candidates.tsx)
    window.dispatchEvent(new CustomEvent('candidates-sidebar-state', { detail: { open: sidebarOpen } }))
  }, [sidebarOpen])

  // Слушаем события от Topbar (как в Candidates.tsx)
  const sidebarOpenRef = useRef(sidebarOpen)
  useEffect(() => {
    sidebarOpenRef.current = sidebarOpen
  }, [sidebarOpen])

  useEffect(() => {
    const handleToggle = (e: CustomEvent<{ open: boolean }>) => {
      setSidebarOpen(e.detail.open)
    }

    const handleRequestState = () => {
      window.dispatchEvent(new CustomEvent('candidates-sidebar-state', { detail: { open: sidebarOpenRef.current } }))
    }

    window.addEventListener('candidates-sidebar-toggle', handleToggle as EventListener)
    window.addEventListener('candidates-sidebar-request-state', handleRequestState)

    return () => {
      window.removeEventListener('candidates-sidebar-toggle', handleToggle as EventListener)
      window.removeEventListener('candidates-sidebar-request-state', handleRequestState)
    }
  }, [])
  
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
    return meta?.order || meta?.codes || orderedStageCodes || []
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

  useEffect(() => {
    if (!canManage) {
      setSelectedIds([])
    }
  }, [canManage])

  // --- sensors (pointer with small activation distance so clicks still work)
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  )

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
    api.get('/meta/stages')
      .then(({ data }) => {
        if (Array.isArray(data)){
          const codes = data
            .map((it: any) => (typeof it === 'string' ? it : it?.code))
            .map((code: any) => (code != null ? String(code).trim() : ''))
            .filter(Boolean)
          if (codes.length) setStageSequence(codes)
          return
        }

        if (!data || typeof data !== 'object'){
          return
        }

        const metaObj = data as Record<string, unknown>
        const orderCandidates = Array.isArray(metaObj.order)
          ? metaObj.order
          : Array.isArray(metaObj.codes)
            ? metaObj.codes
            : []
        const explicitSequence = Array.from(
          new Set(
            orderCandidates
              .map((code: any) => (code != null ? String(code).trim() : ''))
              .filter(Boolean)
          )
        )

        let groups: Record<string, string[]> = {}
        if (metaObj.groups && typeof metaObj.groups === 'object'){
          for (const [column, list] of Object.entries(metaObj.groups as Record<string, any>)){
            const key = String(column || '').trim()
            if (!key) continue
            const values = Array.from(
              new Set(
                (Array.isArray(list) ? list : [])
                  .map((code: any) => (code != null ? String(code).trim() : ''))
                  .filter(Boolean)
              )
            )
            if (values.length){
              groups[key] = values
            }
          }
        }

        if (!Object.keys(groups).length && metaObj.column_of && typeof metaObj.column_of === 'object'){
          const derived: Record<string, string[]> = {}
          for (const [stageCode, column] of Object.entries(metaObj.column_of as Record<string, any>)){
            const colKey = String(column || '').trim()
            const stageKey = String(stageCode || '').trim()
            if (!colKey || !stageKey) continue
            derived[colKey] = derived[colKey] || []
            if (!derived[colKey].includes(stageKey)){
              derived[colKey].push(stageKey)
            }
          }
          if (Object.keys(derived).length){
            groups = derived
          }
        }

        if (Object.keys(groups).length){
          const mergedGroups: Record<string, string[]> = {}
          Object.entries(DEFAULT_COLUMN_STAGES).forEach(([column, stages]) => {
            mergedGroups[column] = Array.isArray(stages) ? [...stages] : []
          })
          Object.entries(groups).forEach(([column, stages]) => {
            mergedGroups[column] = Array.isArray(stages) ? [...stages] : []
          })

          setColumnStages(mergedGroups)

          const metaColumns = Object.keys(groups)
          const orderedColumns = Array.from(new Set([
            ...metaColumns,
            ...KANBAN_ORDER.filter(column => !metaColumns.includes(column as any)),
          ]))
          if (orderedColumns.length){
            setColumnOrder(orderedColumns)
          }
          const flattened = orderedColumns.flatMap(column => mergedGroups[column] || [])
          if (explicitSequence.length){
            setStageSequence(explicitSequence)
          } else if (flattened.length){
            setStageSequence(Array.from(new Set(flattened)))
          }
          return
        }

        if (explicitSequence.length){
          setStageSequence(explicitSequence)
        }
      })
      .catch(() => {/* silent */})
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
    api.get('/catalogs/managers')
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

      // Profile-specific stages override meta when vacancy has profile with stage_codes
      const ps = raw?.profile_stages
      if (ps && typeof ps === 'object') {
        setProfileStages(ps)
        const colOrder = Array.isArray(ps.column_order) ? ps.column_order : (ps.stage_columns && Object.keys(ps.stage_columns)) || []
        const colStages = ps.stage_columns && typeof ps.stage_columns === 'object' ? ps.stage_columns : {}
        const seq = Array.isArray(ps.stage_codes) ? ps.stage_codes : []
        if (colOrder.length) setColumnOrder(colOrder)
        if (Object.keys(colStages).length) setColumnStages(colStages)
        if (seq.length) setStageSequence(seq)
      } else {
        setProfileStages(null)
      }

      // --- Normalize possible shapes from backend ---
      function groupByStage(links: any[], stageKey: string){
        const acc: Record<string, any[]> = {}
        for (const it of links){
          const code = it?.[stageKey] ?? it?.stage ?? it?.status ?? it?.stage_code
          if (!code) continue
          if (!acc[code]) acc[code] = []
          acc[code].push(it)
        }
        return acc
      }

      let columnsIn: any = raw?.columns ?? raw?.columns_by_status ?? raw?.data ?? raw?.pipeline
      let statusesIn: string[] = raw?.statuses ?? raw?.status_order ?? raw?.stages ?? []

      if (Array.isArray(columnsIn)){
        const obj: Record<string, any[]> = {}
        for (const col of columnsIn){
          const code = col?.code || col?.status || col?.stage || col?.stage_code
          if (!code) continue
          const items = col?.items ?? col?.rows ?? col?.candidates ?? []
          obj[code] = Array.isArray(items) ? items : []
        }
        columnsIn = obj
        if (!statusesIn?.length) statusesIn = Object.keys(obj)
      }

      if (!columnsIn && Array.isArray(raw?.links)){
        const grouped = groupByStage(raw.links, 'stage')
        columnsIn = Object.keys(grouped).length ? grouped : groupByStage(raw.links, 'status')
        if (!statusesIn?.length) statusesIn = Object.keys(columnsIn || {})
      }

      if (!columnsIn || typeof columnsIn !== 'object'){
        columnsIn = {}
      }

      const backendKeys = columnsIn && typeof columnsIn === 'object' ? Object.keys(columnsIn) : []
      const profileColOrder = ps?.column_order ?? (ps?.stage_columns && Object.keys(ps.stage_columns))
      let baseOrder: string[] = Array.isArray(profileColOrder) && profileColOrder.length
        ? profileColOrder
        : columnOrder.length ? [...columnOrder] : Array.from(KANBAN_ORDER)
      const extra = backendKeys.filter(k => !baseOrder.includes(k))
      const statuses: string[] = [...baseOrder, ...extra]

      const columns: Record<string, any[]> = {}
      ;(statuses || []).forEach(code => {
        const rawCol = columnsIn?.[code]
        const arr = Array.isArray(rawCol)
          ? rawCol
          : (rawCol?.items ?? rawCol?.rows ?? rawCol?.candidates ?? [])
        const items = Array.isArray(arr)
          ? arr.map(it => ({
              id: it?.link_id || it?.id,
              candidate_id: it?.candidate_id || it?.candidate?.id,
              candidate_name:
                it?.candidate_name ||
                it?.candidate?.name ||
                [it?.candidate?.first_name, it?.candidate?.last_name].filter(Boolean).join(' ') ||
                it?.name,
              candidate_email: it?.candidate_email || it?.candidate?.email,
              candidate: it?.candidate || undefined,
              ...it,
            }))
          : []
        columns[code] = items
      })

      const normalized: PipelineOut = { ...(raw as any), columns, statuses } as PipelineOut

      let total = 0
      for (const s of statuses) total += (normalized.columns?.[s]?.length || 0)

      if (total === 0) {
        try {
          let candData: any
          try{
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

          const grouped: Record<string, any[]> = {}
          for (const c of filtered) {
            const code = c?.stage ?? c?.status ?? c?.stage_code ?? 'new'
            const columnKey = stageToColumn[code] || (KANBAN_ORDER.includes(code as any) ? code : 'new')
            if (!grouped[columnKey]) grouped[columnKey] = []
            grouped[columnKey].push({
              id: c?.id,
              candidate_id: c?.id,
              candidate_name: c?.name || [c?.first_name, c?.last_name].filter(Boolean).join(' ') || '—',
              candidate_email: c?.email,
              candidate: {
                id: c?.id,
                name: c?.name || [c?.first_name, c?.last_name].filter(Boolean).join(' '),
                email: c?.email,
                stage: code,
                status: code,
              },
              stage: code,
              status: code,
            })
          }

          const finalStatuses = [...new Set([...statuses, ...Object.keys(grouped)])]
          const rebuilt: Record<string, any[]> = {}
          for (const s of finalStatuses) {
            rebuilt[s] = grouped[s] || []
          }

          const normalizedFromCandidates: PipelineOut = { ...(raw as any), columns: rebuilt, statuses: finalStatuses } as PipelineOut
          setData(normalizedFromCandidates)
          console.debug('[pipeline] rebuilt from candidates', normalizedFromCandidates)
        } catch (e) {
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
      } else {
        setError(t('app.candidates.pipeline.error_load'))
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
    const stagePlans: Record<string, { targetStage: string; stages: string[] }> = {}
    // optimistic UI
    setData(prev => {
      if (!prev) return prev
      const next = { ...prev, columns: { ...prev.columns } as Record<string, any[]> }
      // pull out selected cards from all columns
      let movedCards: any[] = []
      for (const key of Object.keys(next.columns)){
        const col = next.columns[key] || []
        const keep: any[] = []
        for (const card of col){
          const cid = String(card?.candidate?.id || card?.candidate_id)
          if (selectedIds.includes(cid)){
            const currentStageRaw = card?.stage ?? card?.status ?? card?.candidate?.stage ?? card?.candidate?.status
            const normalizedCurrent = normalizeStageCode(currentStageRaw)
            movedCards.push(card)
            const plan = buildStagePath(normalizedCurrent, toColumn)
            stagePlans[cid] = plan
          } else {
            keep.push(card)
          }
        }
        next.columns[key] = keep
      }
      const normalizedCards = movedCards.map(card => {
        const cid = String(card?.candidate?.id || card?.candidate_id)
        const plan = stagePlans[cid] || buildStagePath(undefined, toColumn)
        const finalStage = plan.targetStage
        const candidateData = card?.candidate
          ? { ...card.candidate, stage: finalStage, status: finalStage }
          : card?.candidate
        return {
          ...card,
          stage: finalStage,
          status: finalStage,
          candidate: candidateData,
        }
      })
      next.columns[toColumn] = [...(next.columns[toColumn] || []), ...normalizedCards]
      return next
    })
    let hadErrors = false
    let rodoBlocked = 0
    let docsBlocked = 0
    const missingByDocs: string[] = []
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
      if (rejected.length > 0){
        hadErrors = true
        for (const rej of rejected) {
          const parsed = parseStageTransitionError((rej as PromiseRejectedResult).reason)
          if (parsed.kind === 'rodo') {
            rodoBlocked += 1
          } else if (parsed.kind === 'handoff_docs') {
            docsBlocked += 1
            missingByDocs.push(...parsed.missingTypes)
          }
        }
      }
    } finally {
      clearSelection()
      await load()
      if (hadErrors){
        if (rodoBlocked > 0) {
          setError(
            t('app.candidates.messages.bulk_stage_rodo_blocked', {
              values: { rodo: rodoBlocked, total: selectedIds.length },
            }),
          )
        } else if (missingByDocs.length > 0) {
          setError(
            t('app.candidates.messages.bulk_stage_handoff_docs_blocked', {
              values: { docs: docsBlocked, total: selectedIds.length, missing: formatMissingDocTypes(missingByDocs) },
            }),
          )
        } else {
          setError(t('app.candidates.pipeline.error_update_stages'))
        }
      }
    }
  }

  async function bulkAssignManager(managerId: string){
    if (!canManage) return
    if (!managerId || selectedIds.length === 0) return
    setBulkOperationLoading('manager')
    try{
      await Promise.allSettled(selectedIds.map(id => api.patch(`/candidates/${id}`, { manager: managerId })))
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
      const stagePlans: Record<string, { targetStage: string; stages: string[] }> = {}
      for (const id of selectedIds) {
        const item = Object.values(data?.columns || {}).flat().find((c: any) => String(c?.candidate?.id || c?.candidate_id) === id)
        const currentStageRaw = (item as any)?.stage ?? (item as any)?.status ?? (item as any)?.candidate?.stage ?? (item as any)?.candidate?.status
        const normalizedCurrent = normalizeStageCode(currentStageRaw)
        const plan = buildStagePath(normalizedCurrent, bulkStage)
        stagePlans[id] = plan
      }
      
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
        let rodoBlocked = 0
        let docsBlocked = 0
        const missingByDocs: string[] = []
        for (const rej of rejected) {
          const parsed = parseStageTransitionError((rej as PromiseRejectedResult).reason)
          if (parsed.kind === 'rodo') {
            rodoBlocked += 1
          } else if (parsed.kind === 'handoff_docs') {
            docsBlocked += 1
            missingByDocs.push(...parsed.missingTypes)
          }
        }
        if (rodoBlocked > 0) {
          setError(
            t('app.candidates.messages.bulk_stage_rodo_blocked', {
              values: { rodo: rodoBlocked, total: selectedIds.length },
            }),
          )
        } else if (missingByDocs.length > 0) {
          setError(
            t('app.candidates.messages.bulk_stage_handoff_docs_blocked', {
              values: { docs: docsBlocked, total: selectedIds.length, missing: formatMissingDocTypes(missingByDocs) },
            }),
          )
        } else {
          setError(t('app.candidates.pipeline.error_update_stages'))
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
    setData(prev => {
      if (!prev) return prev
      const next = { ...prev, columns: { ...prev.columns } as Record<string, any[]> }
      let card: any = null
      for (const key of Object.keys(next.columns)){
        const col = next.columns[key] || []
        const idx = col.findIndex(it => (it.candidate?.id || it.candidate_id) === candidateId)
        if (idx > -1){
          card = col[idx]
        }
        next.columns[key] = col.filter(it => (it.candidate?.id || it.candidate_id) !== candidateId)
      }
      if (!card){ card = { id: candidateId, candidate_id: candidateId } }
      const candidateData = card?.candidate
        ? { ...card.candidate, stage: targetStage, status: targetStage }
        : card?.candidate
      const updatedCard = { ...card, stage: targetStage, status: targetStage, candidate: candidateData }
      next.columns[toColumn] = [...(next.columns[toColumn] || []), updatedCard]
      return next
    })

    setSavingIds(s => ({ ...s, [candidateId]: true }))
    let hadError = false
    let specificErrorSet = false
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
      hadError = true
      const parsed = parseStageTransitionError(e)
      if (parsed.kind === 'rodo') {
        specificErrorSet = true
        setError(
          t('app.candidate_card.messages.rodo_stage_blocked', {
            defaultValue: 'RODO must be sent before moving to contact stage.',
          }),
        )
      } else if (parsed.kind === 'handoff_docs') {
        specificErrorSet = true
        setError(
          t('app.candidate_card.messages.handoff_docs_incomplete', {
            defaultValue: "Cannot move to 'Ready for handoff': required documents checklist is incomplete.",
          }) + ` ${formatMissingDocTypes(parsed.missingTypes)}`,
        )
      }
      await load()
    } finally {
      setSavingIds(s => ({ ...s, [candidateId]: false }))
      if (hadError){
        if (!specificErrorSet) {
          setError(t('app.candidates.pipeline.error_update_stage'))
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

  const columnsOrder = useMemo(
    () => (data?.statuses?.length ? data.statuses : (columnOrder.length ? columnOrder : Array.from(KANBAN_ORDER))),
    [data, columnOrder]
  )

  // Filtered view of columns according to current filters
  const filteredColumns = useMemo(() => {
    if (!data?.columns) return {}
    const res: Record<string, any[]> = {}
    const from = filters.from ? new Date(filters.from + 'T00:00:00') : null
    const to = filters.to ? new Date(filters.to + 'T23:59:59') : null
    const wantCit = filters.citizenship.trim().toUpperCase()

    function matches(item:any){
      const c = item?.candidate || item || {}
      
      // search filter (by name, email, phone)
      if (filters.search){
        const normalizedQuery = normalizeSearchValue(filters.search)
        const name = `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.name || item.candidate_name || ''
        const email = c.email || item.candidate_email || ''
        const phone = c.phone || item.candidate_phone || ''
        const haystacks = [name, email, phone]
        const match = haystacks.some((value) => textMatches(value, normalizedQuery))
        if (!match) return false
      }
      
      // manager filter (accept various fields)
      if (filters.manager){
        const mid = c.manager_id || c.manager || item?.manager || item?.manager_id
        if (String(mid || '') !== String(filters.manager)) return false
      }
      // citizenship filter (via extra)
      if (wantCit){
        const { citizenship } = pickMiniFields(item)
        if ((citizenship || '').toUpperCase() !== wantCit) return false
      }
      // docs readiness filter
      if (filters.docs){
        const { docsStats } = pickMiniFields(item)
        const total = docsStats?.total ?? 0
        const done = docsStats?.done ?? 0
        const all = total > 0 && done === total
        const none = total > 0 && done === 0
        const some = total > 0 && done > 0 && done < total
        if (filters.docs === 'yes' && !all) return false
        if (filters.docs === 'no' && !none) return false
        if (filters.docs === 'partial' && !some) return false
      }
      // date filter (created_at on candidate or link)
      if (from || to){
        const dtStr = c.created_at || item?.created_at
        const d = parseISODateMaybe(dtStr)
        if (from && d && d < from) return false
        if (to && d && d > to) return false
      }
      return true
    }

    for (const code of (columnsOrder || [])){
      let arr = data.columns?.[code] || []
      arr = filters.search || filters.manager || filters.citizenship || filters.docs || filters.from || filters.to
        ? arr.filter(matches)
        : arr
      
      // Sort by created_at (newest first)
      arr = [...arr].sort((a, b) => {
        const cA = a?.candidate || a || {}
        const cB = b?.candidate || b || {}
        const dateA = parseISODateMaybe((cA as any).created_at || (a as any).created_at)
        const dateB = parseISODateMaybe((cB as any).created_at || (b as any).created_at)
        if (!dateA && !dateB) return 0
        if (!dateA) return 1
        if (!dateB) return -1
        return dateB.getTime() - dateA.getTime() // newest first
      })
      
      res[code] = arr
    }
    return res
  }, [data, filters, columnsOrder])

  const totalInPipeline = useMemo(() => {
    if (!filteredColumns) return 0
    return (columnsOrder || []).reduce((acc, code) => acc + (filteredColumns?.[code]?.length || 0), 0)
  }, [filteredColumns, columnsOrder])

  // Pipeline insights
  const pipelineInsights = useMemo(() => {
    if (!filteredColumns) return { total: 0, newCount: 0, docsReady: 0, docsAttention: 0 }
    
    let newCount = 0
    let docsReady = 0
    let docsAttention = 0
    
    for (const code of (columnsOrder || [])) {
      const items = filteredColumns?.[code] || []
      items.forEach((item: any) => {
        const stage = item?.stage ?? item?.status ?? item?.candidate?.stage ?? item?.candidate?.status
        if (stage === 'new' || stage?.startsWith('new_')) {
          newCount++
        }
        
        const { docsStats } = pickMiniFields(item)
        if (docsStats) {
          const { total, done } = docsStats
          if (total > 0) {
            if (done === total) {
              docsReady++
            } else if (done < total) {
              docsAttention++
            }
          }
        }
      })
    }
    
    const total = totalInPipeline
    return { total, newCount, docsReady, docsAttention }
  }, [filteredColumns, columnsOrder, totalInPipeline])

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

  // Summary Hero для бокового меню
  const summaryHero = (
    <section className="rounded-xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-3 text-white shadow-sm">
      <div className="flex flex-col gap-2">
        <h2 className="text-sm font-bold">{t('app.candidates.insights.title')}</h2>
        <p className="text-[10px] text-white/80 leading-tight">{t('app.candidates.insights.subtitle')}</p>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1.5">
        {[
          { label: t('app.candidates.insights.total'), value: pipelineInsights.total, hint: t('app.candidates.insights.total_hint', { values: { count: pipelineInsights.total } }) },
          { label: t('app.candidates.insights.new'), value: pipelineInsights.newCount, hint: t('app.candidates.insights.new_hint', { values: { count: pipelineInsights.newCount } }) },
          { label: t('app.candidates.insights.docs_ready'), value: pipelineInsights.docsReady, hint: t('app.candidates.insights.docs_ready_hint', { values: { count: pipelineInsights.docsReady } }) },
          { label: t('app.candidates.insights.docs_attention'), value: pipelineInsights.docsAttention, hint: t('app.candidates.insights.docs_attention_hint', { values: { count: pipelineInsights.docsAttention } }) },
        ].map((card) => (
          <div key={card.label} className="rounded-lg border border-white/30 bg-white/10 px-2 py-1.5 shadow-inner backdrop-blur">
            <div className="text-[9px] uppercase tracking-wide text-white/80 leading-tight">{card.label}</div>
            <div className="text-lg font-semibold leading-tight">{card.value}</div>
            <div className="text-[9px] text-white/70 leading-tight mt-0.5">{card.hint}</div>
          </div>
        ))}
      </div>
    </section>
  )

  return (
    <div className="relative flex flex-col -mx-6 -my-6" style={{ height: 'calc(100vh - 4rem)', minHeight: 0 }}>
      {/* Основной контент - Kanban */}
      <div className={clsx("flex-1 transition-all duration-300 min-h-0 flex flex-col overflow-hidden", sidebarOpen ? "mr-96" : "mr-0")}>
        <div ref={tableContainerRef} className="flex-1 min-h-0 overflow-hidden flex flex-col p-6">
      {error && (
        <ErrorRecoveryBanner
          info={{
            title: error,
            hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
          }}
          onRetry={() => void load()}
          retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
          compact
        />
      )}

      {totalInPipeline === 0 && !loading && (
        <div className="card p-4">
          <EmptyStatePanel
            compact
            title={t('app.candidates.pipeline.empty_title', { defaultValue: 'Pipeline is empty' })}
            description={t('app.candidates.pipeline.empty_desc', {
              defaultValue: 'No candidates are currently in pipeline. Add candidates from leads or open candidates list.',
            })}
            primaryAction={{
              label: t('app.candidates.pipeline.empty_cta_candidates', { defaultValue: 'Open candidates' }),
              to: '/app/candidates',
            }}
            secondaryAction={{
              label: t('app.candidates.pipeline.empty_cta_leads', { defaultValue: 'Open leads' }),
              to: '/app/leads',
            }}
          />
        </div>
      )}

      {canManage && selectedIds.length > 0 && (
        <div className="card p-3 flex flex-wrap items-center gap-3">
          <div className="text-sm">{t('app.candidates.pipeline.bulk_selected', { values: { count: selectedIds.length } })}</div>
          <div className="flex items-center gap-2">
            <label className="label m-0">{t('app.candidates.pipeline.bulk_move_stage_label')}</label>
            <select className="input" onChange={(e)=>{ const v=e.target.value; if(v) bulkMoveStage(v); e.currentTarget.selectedIndex = 0 }}>
              <option value="">{t('app.candidates.pipeline.bulk_move_stage_select')}</option>
              {(columnsOrder || []).map(code => (
                <option key={code} value={code}>{code}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="label m-0">{t('app.candidates.pipeline.bulk_assign_manager_label')}</label>
            <select className="input" onChange={(e)=>{ const v=e.target.value; if(v) bulkAssignManager(v); e.currentTarget.selectedIndex = 0 }}>
              <option value="">{t('app.candidates.pipeline.bulk_assign_manager_select')}</option>
              {managers.map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>
          <div className="flex-1" />
          <button className="btn-secondary" onClick={clearSelection}>{t('app.candidates.pipeline.bulk_clear_selection')}</button>
          <button className="btn" onClick={bulkArchive}>{t('app.candidates.pipeline.bulk_archive')}</button>
        </div>
      )}

      <DndContext
        sensors={canManage ? sensors : undefined}
        collisionDetection={closestCenter}
        onDragStart={canManage ? handleDragStart : undefined}
        onDragEnd={canManage ? handleDragEnd : undefined}
      >
        <div className="grid grid-flow-col auto-cols-[280px] gap-3 overflow-x-auto pb-2">
          {(columnsOrder || []).map(code => (
            <DroppableColumn
              key={code}
              id={code}
              title={<StageTag code={code} />}
              count={filteredColumns?.[code]?.length || 0}
              total={data?.columns?.[code]?.length || 0}
              headerRight={canManage ? (
                (() => {
                  const colItems = (filteredColumns?.[code] || [])
                  const colIds = colItems.map((it:any) => String(it.candidate?.id || it.candidate_id))
                  const selectedInCol = colIds.filter((cid:string) => selectedIds.includes(cid)).length
                  const allInColSelected = colIds.length > 0 && selectedInCol === colIds.length
                  const someSelected = selectedInCol > 0 && !allInColSelected
                  return (
                    <label className="inline-flex items-center gap-1 text-xs select-none">
                      <input
                        type="checkbox"
                        checked={allInColSelected}
                        ref={el => { if (el) el.indeterminate = someSelected }}
                        onChange={() => toggleAllInColumn(colIds, !allInColSelected)}
                      />
                      <span>{t('app.candidates.pipeline.column_select_all')}</span>
                    </label>
                  )
                })()
              ) : null}
            >
              {(filteredColumns?.[code] || []).map((item: any) => {
                const candidateId = String(item.candidate?.id || item.candidate_id)
                const dragId = `card:${candidateId}`
                const rawStage = item?.stage ?? item?.status ?? item?.candidate?.stage ?? item?.candidate?.status
                const itemStage = normalizeStageCode(rawStage)
                dragRegistry.current[dragId] = { candidateId, fromColumn: code, stage: itemStage }
                const selected = isSelected(candidateId)
                const onToggle = () => toggleSelected(candidateId)
                return (
                  <DraggableCard
                    key={dragId}
                    id={dragId}
                    saving={!!savingIds[candidateId]}
                    selected={selected}
                    onToggleSelect={onToggle}
                    canManage={canManage}
                    t={t}
                    onContextMenu={(e: React.MouseEvent) => {
                      if (canManage) {
                        e.preventDefault()
                        e.stopPropagation()
                        setContextMenu({ x: e.clientX, y: e.clientY, candidateId })
                      }
                    }}
                  >
                    {(() => {
                      const meta = pickMiniFields(item)
                      const c = item?.candidate || item || {}
                      const managerId = c.manager_id || c.manager || item?.manager || item?.manager_id
                      const manager = managers.find(m => m.id === managerId)
                      const vacancyTitle = item?.vacancy?.title || item?.vacancy_title || (vacancies.find(v => v.id === vacancyId) as any)?.title
                      const createdDate = c.created_at || item?.created_at
                      const formattedDate = createdDate ? new Date(createdDate).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }) : null
                      
                      return (
                        <div className="mt-1">
                          <div className="font-medium">
                            <Link
                              className="hover:underline"
                              to={`/app/candidates/${candidateId}`}
                              onClick={(evt)=>{
                                if (suppressClickAfterDragRef.current.has(candidateId)){
                                  evt.preventDefault()
                                  evt.stopPropagation()
                                }
                              }}
                            >
                              {item.candidate?.name || item.candidate_name || t('app.candidates.pipeline.candidate_no_name')}
                            </Link>
                          </div>
                          <div className="text-xs text-slate-500 mb-2">{item.candidate?.email || item.candidate_email || '—'}</div>
                          <div className="text-xs text-slate-600 space-y-1">
                            {meta.phone && <div className="inline-flex items-center gap-1"><IconPhone size={12} /> {meta.phone}</div>}
                            {meta.citizenship && <div className="inline-flex items-center gap-1"><IconMapPin size={12} /> {meta.citizenship}</div>}
                            {manager && <div className="inline-flex items-center gap-1"><IconUser size={12} /> {manager.name}</div>}
                            {vacancyTitle && vacancyId && vacancies.length > 1 && <div className="inline-flex items-center gap-1"><IconBriefcase size={12} /> {vacancyTitle}</div>}
                            {formattedDate && <div className="inline-flex items-center gap-1"><IconCalendar size={12} /> {formattedDate}</div>}
                            {meta.docsBadge && <div className="inline-flex items-center gap-1"><IconFileText size={12} /> {t('app.candidates.pipeline.docs_label')}: {meta.docsBadge}</div>}
                          </div>
                        </div>
                      )
                    })()}
                  </DraggableCard>
                )
              })}
              {(filteredColumns?.[code] || []).length === 0 && (
                <div className="py-4">
                  <EmptyStatePanel
                    compact
                    title={t('app.candidates.pipeline.column_empty_title', { defaultValue: 'No candidates in this stage' })}
                    description={t('app.candidates.pipeline.column_empty_desc', {
                      defaultValue: 'Move candidates to this stage or adjust filters.',
                    })}
                    primaryAction={{
                      label: t('app.candidates.pipeline.column_empty_cta_candidates', { defaultValue: 'Open candidates' }),
                      to: '/app/candidates',
                    }}
                  />
                </div>
              )}
            </DroppableColumn>
          ))}
        </div>
      </DndContext>
        </div>
      </div>

      {/* Боковое меню справа */}
      <div
        className={clsx(
          "fixed top-0 right-0 h-full w-96 bg-gradient-to-b from-slate-50 to-white border-l-2 border-slate-300 shadow-2xl z-40 transition-transform duration-300 ease-in-out overflow-y-auto",
          sidebarOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div className="p-4 space-y-4 pt-16">
          {/* Header с кнопкой закрытия */}
          <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <h2 className="text-lg font-semibold">{t('app.candidates.views.kanban')}</h2>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn-secondary text-sm p-1"
                onClick={() => setSidebarOpen(false)}
                title={t('app.candidates.pipeline.hide_filters')}
              >
                ×
              </button>
              <button
                type="button"
                className="btn-secondary text-sm"
                onClick={switchToTable}
              >
                {t('app.candidates.pipeline.switch_to_table')}
              </button>
            </div>
          </div>

          {/* Summary Hero */}
          <div className="mb-1">
            {summaryHero}
          </div>

          {/* Поиск и фильтры */}
          <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3">
              {/* Vacancy selector */}
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5" htmlFor="pipeline-vacancy">
                  {t('app.candidates.pipeline.vacancy_label')}
                </label>
                <select 
                  id="pipeline-vacancy"
                  className="input w-full text-sm" 
                  value={vacancyId} 
                  onChange={e=>setVacancyId(e.target.value)}
                >
                  {vacancies.map(v => <option key={v.id} value={v.id}>{(v as any).title || t('app.candidates.pipeline.vacancy_untitled')}</option>)}
                </select>
              </div>
              
              <div className="flex-1">
                <label className="block text-xs font-medium text-slate-600 mb-1.5" htmlFor="pipeline-search">
                  {t('app.candidates.search.label')}
                </label>
                <input
                  id="pipeline-search"
                  className="input w-full text-sm py-2 px-3 border border-slate-300 focus:border-brand-500 focus:ring-1 focus:ring-brand-200"
                  value={filters.search}
                  onChange={e=>setFilters(f=>({...f, search: e.target.value}))}
                  placeholder={t('app.candidates.search.placeholder')}
                />
                <p className="mt-1.5 text-[10px] text-slate-400 leading-relaxed">{t('app.candidates.search.hint')}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200">
                <button
                  className="btn-secondary text-xs py-1.5 px-2"
                  onClick={()=>load()}
                  disabled={loading || !vacancyId}
                  title={t('app.candidates.actions.refresh_title')}
                >
                  {loading ? t('app.candidates.actions.refreshing') : t('app.candidates.actions.refresh')}
                </button>
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
            
            {/* Фильтры */}
            <div className="pt-2.5 border-t border-slate-200 space-y-3">
              <h3 className="text-xs font-semibold text-slate-600 mb-2 uppercase tracking-wide">{t('app.candidates.filters.menu_label')}</h3>
              
              <div>
                <div className="label text-xs">{t('app.candidates.pipeline.manager_label')}</div>
                <select className="input text-sm" value={filters.manager} onChange={e=>setFilters(f=>({...f, manager: e.target.value}))}>
                  <option value="">{t('app.candidates.pipeline.manager_any')}</option>
                  {managers.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
              
              <div>
                <div className="label text-xs">{t('app.candidates.pipeline.citizenship_label')}</div>
                <input 
                  className="input text-sm w-full" 
                  placeholder={t('app.candidates.pipeline.citizenship_placeholder')} 
                  value={filters.citizenship} 
                  onChange={e=>setFilters(f=>({...f, citizenship: e.target.value.toUpperCase()}))}
                />
              </div>
              
              <div>
                <div className="label text-xs">{t('app.candidates.pipeline.docs_label')}</div>
                <select className="input text-sm" value={filters.docs} onChange={e=>setFilters(f=>({...f, docs: e.target.value}))}>
                  <option value="">{t('app.candidates.pipeline.docs_any')}</option>
                  <option value="yes">{t('app.candidates.pipeline.docs_ready')}</option>
                  <option value="partial">{t('app.candidates.pipeline.docs_partial')}</option>
                  <option value="no">{t('app.candidates.pipeline.docs_none')}</option>
                </select>
              </div>
              
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="label text-xs">{t('app.candidates.pipeline.date_from_label')}</div>
                  <input type="date" className="input text-sm" value={filters.from} onChange={e=>setFilters(f=>({...f, from: e.target.value}))}/>
                </div>
                <div>
                  <div className="label text-xs">{t('app.candidates.pipeline.date_to_label')}</div>
                  <input type="date" className="input text-sm" value={filters.to} onChange={e=>setFilters(f=>({...f, to: e.target.value}))}/>
                </div>
              </div>
              
              <button 
                className="btn-secondary w-full text-xs py-1.5" 
                onClick={()=>setFilters({ search:'', manager:'', citizenship:'', docs:'', from:'', to:'' })}
              >
                {t('app.candidates.pipeline.reset_filters')}
              </button>
            </div>
          </section>
        </div>
      </div>

      {/* Контекстное меню для карточек */}
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
              const candidateId = contextMenu.candidateId
              const item = Object.values(filteredColumns || {}).flat().find((c: any) => String(c?.candidate?.id || c?.candidate_id) === candidateId)
              if (!item || !canManage) return null
              
              return (
                <div className="space-y-1">
                  <button
                    className="btn-secondary w-full text-left text-xs py-1.5 px-2 hover:bg-slate-100"
                    onClick={() => {
                      navigate(`/app/candidates/${candidateId}`)
                      setContextMenu(null)
                    }}
                  >
                    {t('app.candidates.context.open_card')}
                  </button>
                  <button
                    className="btn-secondary w-full text-left text-xs py-1.5 px-2 hover:bg-slate-100"
                    onClick={() => {
                      toggleSelected(candidateId)
                      setContextMenu(null)
                    }}
                  >
                    {isSelected(candidateId)
                      ? t('app.candidates.context.deselect')
                      : t('app.candidates.context.select')
                    }
                  </button>
                  <div className="border-t border-slate-200 my-1" />
                  <button
                    className="btn-secondary w-full text-left text-xs py-1.5 px-2 hover:bg-slate-100"
                    onClick={() => {
                      setSelectedIds([candidateId])
                      setBulkStage(stageOptions[0] || 'new')
                      setBulkReasons([])
                      setBulkOpen(true)
                      setContextMenu(null)
                    }}
                  >
                    {t('app.candidates.context.change_stage')}
                  </button>
                  <button
                    className="btn-secondary w-full text-left text-xs py-1.5 px-2 hover:bg-slate-100"
                    onClick={() => {
                      setSelectedIds([candidateId])
                      const c = item?.candidate || item || {}
                      const managerId = c.manager_id || c.manager || item?.manager || item?.manager_id
                      setBulkManagerId(managerId || managers[0]?.id || '')
                      setBulkManagerOpen(true)
                      setContextMenu(null)
                    }}
                  >
                    {t('app.candidates.context.assign_manager')}
                  </button>
                  <button
                    className="btn-secondary w-full text-left text-xs py-1.5 px-2 hover:bg-slate-100"
                    onClick={() => {
                      setSelectedIds([candidateId])
                      setBulkVacancyId(vacancyId || vacancies[0]?.id || '')
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

      {/* Bulk модальные окна */}
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
        onApply={doBulkStage}
        loading={bulkOperationLoading === 'stage'}
        meta={meta}
        canManage={canManage}
      />

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
    </div>
  )
}

// ----- DnD primitives
function DroppableColumn({ id, title, count, total, children, headerRight }:{
  id:string; title:React.ReactNode; count:number; total?:number; children:React.ReactNode; headerRight?: React.ReactNode
}){
  const { setNodeRef, isOver } = useDroppable({ id })
  return (
    <div ref={setNodeRef} className={`rounded-xl border border-slate-200 bg-slate-50/70 p-2.5 transition-colors ${isOver ? 'ring-2 ring-brand-300' : ''}`}>
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-800">{title}</div>
        <div className="flex items-center gap-2">
          <div className="text-[11px] text-slate-500">
            {typeof total === 'number' ? `${count} / ${total}` : count}
          </div>
          {headerRight}
        </div>
      </div>
      <div className="space-y-2 min-h-[36px]">{children}</div>
    </div>
  )
}

function DraggableCard({ id, children, saving, selected, onToggleSelect, canManage, t, onContextMenu }:{ id:string; children:React.ReactNode; saving:boolean; selected:boolean; onToggleSelect:()=>void; canManage:boolean; t:(key:string)=>string; onContextMenu?:(e:React.MouseEvent)=>void }){
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id, disabled: !canManage })
  const dragProps = canManage ? { ...attributes, ...listeners } : {}
  const style: React.CSSProperties = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : {}
  return (
    <div
      ref={setNodeRef}
      {...dragProps}
      style={style}
      onContextMenu={onContextMenu}
      className={`rounded-lg border border-slate-200 bg-white p-2.5 ${canManage ? 'cursor-grab hover:bg-slate-50 active:cursor-grabbing' : 'cursor-default'} ${selected ? 'border-brand-400 ring-1 ring-brand-200' : ''} ${isDragging ? 'opacity-80 shadow' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div />
        {canManage && (
          <label className="inline-flex items-center gap-2 select-none text-xs text-slate-500" onClick={(e)=>{ e.stopPropagation() }}>
            <input
              type="checkbox"
              checked={selected}
              onChange={(e)=>{ e.stopPropagation(); onToggleSelect() }}
              onClick={(e)=>{ e.stopPropagation() }}
            />
            <span>{t('app.candidates.context.select')}</span>
          </label>
        )}
      </div>
      {children}
      {saving && (
        <div className="flex items-center gap-2 mt-2">
          <span className="text-xs text-slate-400">{t('app.candidates.pipeline.card_saving')}</span>
        </div>
      )}
    </div>
  )
}
