// src/pages/Pipeline.tsx
import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { PipelineOut, Vacancy } from '../api/types'
import StageTag from '../components/StageTag'
import { usePermissions } from '../hooks/usePermissions'

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

// Helper types (loose) to be resilient to backend shapes
type AnyObj = Record<string, any>

type ManagerItem = { id: string; name: string }

// Canonical Kanban columns (backend constants/stages.py)
const KANBAN_ORDER = [
  'new',
  'interview',
  'hiring',
  'employed',
  'probation',
  'rejected',
] as const

const DEFAULT_COLUMN_STAGES: Record<string, string[]> = {
  new: ['new'],
  interview: ['contacted', 'docs_wait', 'docs_got'],
  hiring: ['permit_ordered', 'permit_received', 'visa', 'red_paper', 'trip_plan', 'at_client', 'on_trip'],
  employed: ['employed'],
  probation: ['probation_ok'],
  rejected: ['rejected'],
}

const DEFAULT_COLUMN_ORDER = Object.keys(DEFAULT_COLUMN_STAGES)
const DEFAULT_STAGE_SEQUENCE = DEFAULT_COLUMN_ORDER.flatMap(column => DEFAULT_COLUMN_STAGES[column] || [])
const DEFAULT_STAGE_BY_COLUMN: Record<string, string> = Object.fromEntries(
  DEFAULT_COLUMN_ORDER.map(column => [column, (DEFAULT_COLUMN_STAGES[column] || [column])[0]])
)

export const TERMINAL_STAGE_CODES = new Set(['probation_ok', 'rejected'])

export function sanitizeStagePath(
  stages: string[],
  targetStage: string,
  terminalStages: ReadonlySet<string> = TERMINAL_STAGE_CODES
): string[]{
  if (!stages.length) return []
  return stages.filter(stage => stage === targetStage || !terminalStages.has(stage))
}

function normalizeStageCode(value: unknown): string | undefined{
  if (value == null) return undefined
  const str = String(value).trim()
  return str ? str.toLowerCase() : undefined
}

// ---- small helpers for card mini-details
function parseJSONMaybe(v: any){
  try{
    if (v && typeof v === 'string') return JSON.parse(v)
    if (v && typeof v === 'object') return v
  }catch{/* ignore */}
  return null
}

function pickMiniFields(item: any){
  const c = item?.candidate || item || {}
  const extra = parseJSONMaybe(c.extra) || parseJSONMaybe(item?.extra) || {}
  const docs = parseJSONMaybe(c.docs_progress) || parseJSONMaybe(item?.docs_progress) || {}

  const phone: string | undefined =
    c.phone || extra.phone || extra.phone_number || undefined

  const citizenship: string | undefined =
    extra.citizenship || extra.passport_country || extra.country || undefined

  let docsBadge: string | undefined = undefined
  let docsStats: { total:number; done:number } | undefined
  if (docs && typeof docs === 'object'){
    const keys = Object.keys(docs)
    if (keys.length){
      const done = keys.filter(k => docs[k] === true || docs[k] === 'done' || docs[k] === 'ok').length
      docsBadge = `${done}/${keys.length}`
      docsStats = { total: keys.length, done }
    } else {
      docsStats = { total: 0, done: 0 }
    }
  }

  return { phone, citizenship, docsBadge, docsStats }
}

function parseISODateMaybe(v?: string){
  if (!v) return null
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? null : d
}

export default function Pipeline(){
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [vacancyId, setVacancyId] = useState<string>('')
  const [data, setData] = useState<PipelineOut | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [columnOrder, setColumnOrder] = useState<string[]>(DEFAULT_COLUMN_ORDER)
  const [columnStages, setColumnStages] = useState<Record<string, string[]>>(DEFAULT_COLUMN_STAGES)
  const [stageSequence, setStageSequence] = useState<string[]>(DEFAULT_STAGE_SEQUENCE)
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
  const [filters, setFilters] = useState<{ manager:string; citizenship:string; docs:string; from:string; to:string }>({
    manager: '',
    citizenship: '',
    docs: '', // '', 'yes', 'partial', 'no'
    from: '', // yyyy-mm-dd
    to: '',   // yyyy-mm-dd
  })
  const { can } = usePermissions()
  const canManage = can('candidates.manage')
  const canViewPipeline = canManage || can('candidates.pipeline')

  // --- initialize from URL search params
  useEffect(() => {
    const v = searchParams.get('vacancy') || ''
    const manager = searchParams.get('m') || ''
    const citizenship = searchParams.get('c') || ''
    const docs = searchParams.get('d') || ''
    const from = searchParams.get('from') || ''
    const to = searchParams.get('to') || ''
    if (v) setVacancyId(v)
    setFilters({ manager, citizenship, docs, from, to })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // For DnD: keep a local registry of draggable id -> {candidateId, fromStage}
  const dragRegistry = useRef<Record<string, { candidateId: string; fromColumn: string; stage?: string }>>({})
  const suppressClickAfterDragRef = useRef<Set<string>>(new Set())

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
    const keys = ['vacancy', 'm', 'c', 'd', 'from', 'to']
    keys.forEach((key) => next.delete(key))
    if (vacancyId) next.set('vacancy', vacancyId)
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
      let baseOrder: string[] = columnOrder.length ? [...columnOrder] : Array.from(KANBAN_ORDER)
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
        setError('Не удалось загрузить пайплайн')
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
      if (results.some(result => result.status === 'rejected')){
        hadErrors = true
      }
    } finally {
      clearSelection()
      await load()
      if (hadErrors){
        setError('Не удалось обновить этапы для части кандидатов')
      }
    }
  }

  async function bulkAssignManager(managerId: string){
    if (!canManage) return
    if (!managerId || selectedIds.length === 0) return
    try{
      await Promise.allSettled(selectedIds.map(id => api.patch(`/candidates/${id}`, { manager: managerId })))
    } finally {
      clearSelection()
      await load()
    }
  }

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
      await load()
    } finally {
      setSavingIds(s => ({ ...s, [candidateId]: false }))
      if (hadError){
        setError('Не удалось обновить этап кандидата')
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
      const arr = data.columns?.[code] || []
      res[code] = filters.manager || filters.citizenship || filters.docs || filters.from || filters.to
        ? arr.filter(matches)
        : arr
    }
    return res
  }, [data, filters, columnsOrder])

  const totalInPipeline = useMemo(() => {
    if (!filteredColumns) return 0
    return (columnsOrder || []).reduce((acc, code) => acc + (filteredColumns?.[code]?.length || 0), 0)
  }, [filteredColumns, columnsOrder])

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

  if (!canViewPipeline) {
    return (
      <div className="card p-4 text-sm text-amber-800 bg-amber-50 border border-amber-200">
        Нет доступа к пайплайну кандидатов. Обратитесь к администратору или супервайзеру для выдачи прав.
      </div>
    )
  }

  return (
    <div className="min-h-[520px] h-auto flex flex-col gap-4">
      <div className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b">
        <div className="grid grid-cols-12 gap-3 p-3">
          {/* Vacancy selector (left) */}
          <div className="col-span-12 md:col-span-4 lg:col-span-3 flex items-end gap-3">
            <div className="flex-1">
              <div className="label">Вакансия</div>
              <select className="input" value={vacancyId} onChange={e=>setVacancyId(e.target.value)}>
                {vacancies.map(v => <option key={v.id} value={v.id}>{(v as any).title || 'Без названия'}</option>)}
              </select>
            </div>
            <button className="btn-ghost h-[38px]" onClick={load} disabled={loading || !vacancyId}>
              {loading ? 'Обновляю…' : 'Обновить'}
            </button>
          </div>

          {/* Filters (right) */}
          <div className="col-span-12 md:col-span-8 lg:col-span-9">
            <div className="grid grid-cols-2 md:grid-cols-6 lg:grid-cols-7 gap-3 items-end">
              <div className="col-span-2 md:col-span-2">
                <div className="label">Менеджер</div>
                <select className="input" value={filters.manager} onChange={e=>setFilters(f=>({...f, manager: e.target.value}))}>
                  <option value="">Любой</option>
                  {managers.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
              <div>
                <div className="label">Гражданство (ISO)</div>
                <input className="input w-[120px]" placeholder="RU/UA/PL…" value={filters.citizenship} onChange={e=>setFilters(f=>({...f, citizenship: e.target.value.toUpperCase()}))}/>
              </div>
              <div>
                <div className="label">Документы</div>
                <select className="input" value={filters.docs} onChange={e=>setFilters(f=>({...f, docs: e.target.value}))}>
                  <option value="">Любые</option>
                  <option value="yes">Готовы</option>
                  <option value="partial">Частично</option>
                  <option value="no">Нет</option>
                </select>
              </div>
              <div>
                <div className="label">С даты</div>
                <input type="date" className="input" value={filters.from} onChange={e=>setFilters(f=>({...f, from: e.target.value}))}/>
              </div>
              <div>
                <div className="label">По дату</div>
                <input type="date" className="input" value={filters.to} onChange={e=>setFilters(f=>({...f, to: e.target.value}))}/>
              </div>
              <div className="col-span-2 md:col-span-1">
                <button className="btn-ghost w-full md:w-auto" onClick={()=>setFilters({ manager:'', citizenship:'', docs:'', from:'', to:'' })}>Сбросить</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="card p-3 text-sm text-red-600">{error}</div>
      )}

      {totalInPipeline === 0 && !loading && (
        <div className="card p-4 text-sm text-gray-600">
          Нет кандидатов по текущим фильтрам/вакансии. Измените фильтры или добавьте кандидата в вакансию.
        </div>
      )}

      {canManage && selectedIds.length > 0 && (
        <div className="card p-3 flex flex-wrap items-center gap-3">
          <div className="text-sm">Выбрано: <span className="font-medium">{selectedIds.length}</span></div>
          <div className="flex items-center gap-2">
            <label className="label m-0">Перенести в этап</label>
            <select className="input" onChange={(e)=>{ const v=e.target.value; if(v) bulkMoveStage(v); e.currentTarget.selectedIndex = 0 }}>
              <option value="">— выбрать этап —</option>
              {(columnsOrder || []).map(code => (
                <option key={code} value={code}>{code}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="label m-0">Назначить менеджера</label>
            <select className="input" onChange={(e)=>{ const v=e.target.value; if(v) bulkAssignManager(v); e.currentTarget.selectedIndex = 0 }}>
              <option value="">— выбрать менеджера —</option>
              {managers.map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>
          <div className="flex-1" />
          <button className="btn-ghost" onClick={clearSelection}>Снять выделение</button>
          <button className="btn" onClick={bulkArchive}>В архив</button>
        </div>
      )}

      <DndContext
        sensors={canManage ? sensors : undefined}
        collisionDetection={closestCenter}
        onDragStart={canManage ? handleDragStart : undefined}
        onDragEnd={canManage ? handleDragEnd : undefined}
      >
        <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-4 overflow-x-auto">
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
                      <span>Все</span>
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
                  >
                    {(() => {
                      const meta = pickMiniFields(item)
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
                              {item.candidate?.name || item.candidate_name || 'Без имени'}
                            </Link>
                          </div>
                          <div className="text-xs text-gray-500 mb-2">{item.candidate?.email || item.candidate_email || '—'}</div>
                          <div className="text-xs text-gray-600 space-y-1">
                            {meta.phone && <div>📞 {meta.phone}</div>}
                            {meta.citizenship && <div>🛂 {meta.citizenship}</div>}
                            {meta.docsBadge && <div>📄 Документы: {meta.docsBadge}</div>}
                          </div>
                        </div>
                      )
                    })()}
                  </DraggableCard>
                )
              })}
              {(filteredColumns?.[code] || []).length === 0 && (
                <div className="text-sm text-gray-400 py-6 text-center">Пусто</div>
              )}
            </DroppableColumn>
          ))}
        </div>
      </DndContext>
    </div>
  )
}

// ----- DnD primitives
function DroppableColumn({ id, title, count, total, children, headerRight }:{
  id:string; title:React.ReactNode; count:number; total?:number; children:React.ReactNode; headerRight?: React.ReactNode
}){
  const { setNodeRef, isOver } = useDroppable({ id })
  return (
    <div ref={setNodeRef} className={`card p-3 transition-colors ${isOver ? 'ring-2 ring-blue-300' : ''}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="font-medium">{title}</div>
        <div className="flex items-center gap-2">
          <div className="text-xs text-gray-500">
            {typeof total === 'number' ? `${count} / ${total}` : count}
          </div>
          {headerRight}
        </div>
      </div>
      <div className="space-y-2 min-h-[40px]">{children}</div>
    </div>
  )
}

function DraggableCard({ id, children, saving, selected, onToggleSelect, canManage }:{ id:string; children:React.ReactNode; saving:boolean; selected:boolean; onToggleSelect:()=>void; canManage:boolean }){
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id, disabled: !canManage })
  const dragProps = canManage ? { ...attributes, ...listeners } : {}
  const style: React.CSSProperties = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : {}
  return (
    <div
      ref={setNodeRef}
      {...dragProps}
      style={style}
      className={`rounded-lg border p-3 bg-white ${canManage ? 'hover:bg-gray-50 cursor-grab active:cursor-grabbing' : 'cursor-default'} ${selected ? 'border-blue-400 ring-1 ring-blue-200' : 'border-gray-200'} ${isDragging ? 'opacity-80 shadow' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div />
        {canManage && (
          <label className="inline-flex items-center gap-2 select-none text-xs text-gray-500" onClick={(e)=>{ e.stopPropagation() }}>
            <input
              type="checkbox"
              checked={selected}
              onChange={(e)=>{ e.stopPropagation(); onToggleSelect() }}
              onClick={(e)=>{ e.stopPropagation() }}
            />
            <span>Выбрать</span>
          </label>
        )}
      </div>
      {children}
      {saving && (
        <div className="flex items-center gap-2 mt-2">
          <span className="text-xs text-gray-400">сохраняю…</span>
        </div>
      )}
    </div>
  )
}
