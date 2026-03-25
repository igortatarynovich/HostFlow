import clsx from 'clsx'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import StageTag from '../components/StageTag'
import { getRegionDisplayName } from '../utils/catalogLocale'
import {
  getHandoffsWithCandidates,
  acceptHandoff,
  rejectHandoff,
  returnHandoff,
  type PendingHandoffWithCandidate,
} from '../api/handoffs'
import { api } from '../api/client'
import { useToast } from '../components/Toast'
import { useAuth } from '../store/useAuth'
import { usePermissions } from '../hooks/usePermissions'
import { useMetaStages } from '../store/useMeta'
import { formatDateTime } from '../utils/dateFormat'
import { toCSV, formatDateSafe } from '../modules/candidates/candidateUtils'
import { canonicalStageKey, translateStageLabel } from '../utils/stageLabels'
import { ColumnFilterMenu } from '../modules/candidates/components'

type CompanyOption = { id: string; name: string }

type TabKey = 'do-procesowania' | 'w-procesie' | 'historia-decyzji'
type SortDirection = 'asc' | 'desc'
type SortKey =
  | 'candidate'
  | 'short_id'
  | 'phone'
  | 'citizenship'
  | 'stage'
  | 'vacancy'
  | 'created_at'
  | 'requested_at'
  | 'status'
  | 'decision'
  | 'who'
  | 'reason'

type HeaderFilters = {
  citizenship: string[]
  stage: string[]
  vacancy: string[]
  created_from: string
  created_to: string
  requested_from: string
  requested_to: string
  status: string[]
  decision: string[]
  who: string[]
}

type Row = {
  handoff: PendingHandoffWithCandidate['handoff']
  candidate: PendingHandoffWithCandidate['candidate']
  name: string
  short_id: string
  phone: string
  email: string
  citizenship: string
  citizenship_display: string
  stage_code: string
  stage_display: string
  vacancy: string
  created_at: string
  requested_at: string
  decision_at: string
  requested_ts: number
  created_ts: number
  decision_ts: number
  status_code: string
  status_display: string
  decision_code: string
  decision_display: string
  who: string
  reason: string
}

const TABS: TabKey[] = ['do-procesowania', 'w-procesie', 'historia-decyzji']

const EMPLOYER_IN_PROGRESS_STAGE_CODES = new Set([
  'processing_by_client',
  'docs_submitted_permit',
  'permit_received',
  'on_trip',
])

const EMPLOYER_DECISION_STAGE_CODES = new Set([
  'handoff_returned',
  'rejected',
  'declined',
  'employed',
])

const EMPTY_FILTERS: HeaderFilters = {
  citizenship: [],
  stage: [],
  vacancy: [],
  created_from: '',
  created_to: '',
  requested_from: '',
  requested_to: '',
  status: [],
  decision: [],
  who: [],
}

const HANDOFF_TABLE_STATE_STORAGE_KEY = 'hf:handoff:table'

type TabStateSnapshot = {
  globalSearch: string
  filters: HeaderFilters
  sortKey: SortKey
  sortDirection: SortDirection
}

type PersistedHandoffTableState = {
  selectedCompanyId: string | null
  tabs: Partial<Record<TabKey, TabStateSnapshot>>
}

function asTelHref(phone: string): string {
  const digits = phone.replace(/\D/g, '')
  return digits ? `tel:+${digits}` : ''
}

function dateInputToTsFrom(value: string): number | null {
  if (!value) return null
  const ts = Date.parse(`${value}T00:00:00Z`)
  return Number.isFinite(ts) ? ts : null
}

function dateInputToTsTo(value: string): number | null {
  if (!value) return null
  const ts = Date.parse(`${value}T23:59:59Z`)
  return Number.isFinite(ts) ? ts : null
}

function toLower(value: string): string {
  return value.trim().toLowerCase()
}

export default function DoProcesowaniaPage() {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const { me } = useAuth()
  const meta = useMetaStages()
  const { role, isClientTenant } = usePermissions()
  const isClientRole = isClientTenant && role !== 'administrator'

  const [searchParams, setSearchParams] = useSearchParams()
  const tabFromUrl = searchParams.get('tab')
  const [activeTab, setActiveTab] = useState<TabKey>(TABS.includes(tabFromUrl as TabKey) ? (tabFromUrl as TabKey) : 'do-procesowania')

  const tenantId = (me as { tenant_id?: string })?.tenant_id ?? 'default'
  const tableStateStorageKey = useMemo(
    () => `${HANDOFF_TABLE_STATE_STORAGE_KEY}:${tenantId}`,
    [tenantId]
  )
  const [companies, setCompanies] = useState<CompanyOption[]>([])
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null)
  const [items, setItems] = useState<PendingHandoffWithCandidate[]>([])
  const [loading, setLoading] = useState(true)

  const [checked, setChecked] = useState<Record<string, boolean>>({})
  const [submitting, setSubmitting] = useState(false)
  const [rejectModal, setRejectModal] = useState<{ handoffId: string; candidateName: string } | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [returnModal, setReturnModal] = useState<{ handoffId: string; candidateName: string } | null>(null)
  const [returnReason, setReturnReason] = useState('')
  const [bulkReturnActive, setBulkReturnActive] = useState(false)
  const [bulkRejectActive, setBulkRejectActive] = useState(false)

  const [sortKey, setSortKey] = useState<SortKey>('requested_at')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [globalSearch, setGlobalSearch] = useState('')
  const [filters, setFilters] = useState<HeaderFilters>(EMPTY_FILTERS)
  const [tableStateHydrated, setTableStateHydrated] = useState(false)
  const restoringTableStateRef = useRef(false)

  const employerVisibleStageCodes = useMemo(() => {
    const stageMeta = meta?.meta || {}
    const ordered = meta?.order || []
    return ordered.filter((code) => Boolean(stageMeta?.[code]?.visible_for_client))
  }, [meta])

  useEffect(() => {
    const next = TABS.includes(tabFromUrl as TabKey) ? (tabFromUrl as TabKey) : 'do-procesowania'
    setActiveTab(next)
  }, [tabFromUrl])

  const restoreTableState = useCallback(
    (tab: TabKey) => {
      restoringTableStateRef.current = true
      try {
        const raw = localStorage.getItem(tableStateStorageKey)
        if (!raw) {
          setGlobalSearch('')
          setFilters(EMPTY_FILTERS)
          setSortKey('requested_at')
          setSortDirection('desc')
          return
        }

        const parsed = JSON.parse(raw) as PersistedHandoffTableState
        if (parsed && typeof parsed === 'object') {
          if (Object.prototype.hasOwnProperty.call(parsed, 'selectedCompanyId')) {
            setSelectedCompanyId((prev) => (prev == null ? parsed.selectedCompanyId ?? null : prev))
          }
          const tabState = parsed.tabs?.[tab]
          if (tabState) {
            setGlobalSearch(typeof tabState.globalSearch === 'string' ? tabState.globalSearch : '')
            setFilters(tabState.filters ? { ...EMPTY_FILTERS, ...tabState.filters } : EMPTY_FILTERS)
            setSortKey(tabState.sortKey ?? 'requested_at')
            setSortDirection(tabState.sortDirection ?? 'desc')
          } else {
            setGlobalSearch('')
            setFilters(EMPTY_FILTERS)
            setSortKey('requested_at')
            setSortDirection('desc')
          }
        }
      } catch {
        setGlobalSearch('')
        setFilters(EMPTY_FILTERS)
        setSortKey('requested_at')
        setSortDirection('desc')
      } finally {
        setChecked({})
        setTableStateHydrated(true)
        queueMicrotask(() => {
          restoringTableStateRef.current = false
        })
      }
    },
    [tableStateStorageKey]
  )

  useEffect(() => {
    restoreTableState(activeTab)
  }, [activeTab, restoreTableState])

  useEffect(() => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', activeTab)
    setSearchParams(next, { replace: true })
  }, [activeTab, searchParams, setSearchParams])

  const loadCompanies = useCallback(async () => {
    if (isClientRole) {
      setCompanies([])
      setSelectedCompanyId(null)
      return
    }
    try {
      const { data } = await api.get('/companies/', { params: { limit: 100, offset: 0 } })
      const list: Array<{ id: string; name: string }> = Array.isArray(data)
        ? data
        : data?.items || data?.results || data || []
      setCompanies(list)
      if (list.length > 0 && !selectedCompanyId && role !== 'administrator') {
        setSelectedCompanyId(list[0].id)
      }
    } catch {
      setCompanies([])
    }
  }, [isClientRole, role, selectedCompanyId])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      let clientCompanyId: string | undefined
      let clientTenantId: string | undefined

      if (isClientRole && tenantId) {
        clientTenantId = tenantId
      } else if (role === 'administrator' && tenantId) {
        if (selectedCompanyId) {
          clientCompanyId = selectedCompanyId
        } else {
          clientTenantId = tenantId
        }
      } else if (selectedCompanyId) {
        clientCompanyId = selectedCompanyId
      }

      if (!clientCompanyId && !clientTenantId) {
        setItems([])
        return
      }

      const statusForRequest =
        activeTab === 'do-procesowania'
          ? ['pending']
          : activeTab === 'w-procesie'
          ? ['accepted']
          : ['accepted', 'rejected', 'returned']

      const stageCodesForRequest =
        activeTab === 'w-procesie'
          ? Array.from(EMPLOYER_IN_PROGRESS_STAGE_CODES)
          : undefined

      const pageSize = 500
      let offset = 0
      let total = 0
      const collected: PendingHandoffWithCandidate[] = []
      do {
        const response = await getHandoffsWithCandidates({
          clientCompanyId,
          clientTenantId,
          status: statusForRequest,
          // Important: without explicit fromDays backend defaults to 30 days.
          // For Do Procesowania / history we need full timeline.
          fromDays: 0,
          stageCodes: stageCodesForRequest,
          limit: pageSize,
          offset,
        })
        total = Number(response.total || 0)
        if (Array.isArray(response.items) && response.items.length > 0) {
          collected.push(...response.items)
        }
        offset += pageSize
      } while (offset < total)
      setItems(collected)
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [activeTab, isClientRole, role, selectedCompanyId, tenantId])

  useEffect(() => {
    void loadCompanies()
  }, [loadCompanies])

  useEffect(() => {
    void loadData()
  }, [loadData])

  useEffect(() => {
    if (!tableStateHydrated || restoringTableStateRef.current) return
    try {
      const raw = localStorage.getItem(tableStateStorageKey)
      const parsed = raw ? (JSON.parse(raw) as PersistedHandoffTableState) : null
      const next: PersistedHandoffTableState = {
        selectedCompanyId,
        tabs: {
          ...(parsed?.tabs || {}),
          [activeTab]: {
            globalSearch,
            filters,
            sortKey,
            sortDirection,
          },
        },
      }
      localStorage.setItem(tableStateStorageKey, JSON.stringify(next))
    } catch {
      /* ignore storage errors */
    }
  }, [
    activeTab,
    filters,
    globalSearch,
    selectedCompanyId,
    sortDirection,
    sortKey,
    tableStateHydrated,
    tableStateStorageKey,
  ])

  const rows = useMemo<Row[]>(() => {
    return items.map(({ handoff, candidate }) => {
      const fn = candidate.first_name_latin || candidate.first_name
      const ln = candidate.last_name_latin || candidate.last_name
      const name = [fn, ln].filter(Boolean).join(' ') || '—'
      const stageCode = canonicalStageKey(candidate.stage || '', candidate.stage || '') || ''
      const stageDisplay = stageCode
        ? translateStageLabel(t, stageCode, meta?.labels?.[stageCode] || stageCode)
        : '—'

      const cit = candidate.citizenship || ''
      const citizenshipDisplay = cit
        ? /^[A-Z]{2}$/.test(String(cit).toUpperCase())
          ? getRegionDisplayName(cit, locale)
          : cit
        : '—'

      const statusCode = handoff.status
      const statusDisplay =
        statusCode === 'pending_review'
          ? t('app.handoff.status.pending')
          : statusCode === 'accepted'
          ? t('app.handoff.status.accepted')
          : statusCode === 'rejected'
          ? t('app.handoff.status.rejected')
          : statusCode === 'returned'
          ? t('app.handoff.status.returned')
          : statusCode

      let decisionCode = ''
      if (statusCode === 'returned' || stageCode === 'handoff_returned') decisionCode = 'returned'
      else if (statusCode === 'rejected' || stageCode === 'rejected') decisionCode = 'rejected'
      else if (stageCode === 'declined') decisionCode = 'declined'
      else if (stageCode === 'employed') decisionCode = 'employed'

      const decisionDisplay =
        decisionCode === 'returned'
          ? t('app.handoff.decisions.returned')
          : decisionCode === 'rejected'
          ? t('app.handoff.decisions.rejected')
          : decisionCode === 'declined'
          ? t('app.handoff.decisions.declined')
          : decisionCode === 'employed'
          ? t('app.handoff.decisions.employed')
          : '—'

      const requestedTs = handoff.requested_at ? Date.parse(handoff.requested_at) : 0
      const createdTs = candidate.created_at ? Date.parse(candidate.created_at) : 0
      const decisionTs = handoff.reviewed_at ? Date.parse(handoff.reviewed_at) : 0

      return {
        handoff,
        candidate,
        name,
        short_id: candidate.short_id || '',
        phone: candidate.phone || '',
        email: candidate.email || '',
        citizenship: cit,
        citizenship_display: citizenshipDisplay,
        stage_code: stageCode,
        stage_display: stageDisplay,
        vacancy: candidate.vacancy_title || '',
        created_at: candidate.created_at ? formatDateSafe(candidate.created_at, locale) : '—',
        requested_at: handoff.requested_at ? formatDateTime(handoff.requested_at) : '—',
        decision_at: handoff.reviewed_at ? formatDateTime(handoff.reviewed_at) : '—',
        requested_ts: Number.isFinite(requestedTs) ? requestedTs : 0,
        created_ts: Number.isFinite(createdTs) ? createdTs : 0,
        decision_ts: Number.isFinite(decisionTs) ? decisionTs : 0,
        status_code: statusCode,
        status_display: statusDisplay,
        decision_code: decisionCode,
        decision_display: decisionDisplay,
        who: handoff.reviewed_by_user_id || '',
        reason: handoff.rejection_reason || handoff.return_reason || '',
      }
    })
  }, [items, locale, meta?.labels, t])

  const tabRows = useMemo(() => {
    if (activeTab === 'do-procesowania') {
      return rows.filter((row) => row.status_code === 'pending_review')
    }
    if (activeTab === 'w-procesie') {
      return rows.filter(
        (row) => row.status_code === 'accepted' && EMPLOYER_IN_PROGRESS_STAGE_CODES.has(row.stage_code),
      )
    }
    return rows.filter((row) => row.status_code !== 'pending_review')
  }, [activeTab, rows])

  const filteredRows = useMemo(() => {
    const searchNeedle = toLower(globalSearch)
    const applySearch = searchNeedle.length >= 3

    const createdFromTs = dateInputToTsFrom(filters.created_from)
    const createdToTs = dateInputToTsTo(filters.created_to)
    const requestedFromTs = dateInputToTsFrom(filters.requested_from)
    const requestedToTs = dateInputToTsTo(filters.requested_to)

    return tabRows.filter((row) => {
      if (applySearch) {
        const searchable = [row.name, row.short_id, row.phone, row.email].map(toLower)
        if (!searchable.some((value) => value.includes(searchNeedle))) return false
      }

      if (filters.citizenship.length > 0 && !filters.citizenship.includes(row.citizenship)) return false
      if (filters.stage.length > 0 && !filters.stage.includes(row.stage_code)) return false
      if (filters.vacancy.length > 0 && !filters.vacancy.includes(row.vacancy)) return false
      if (filters.status.length > 0 && !filters.status.includes(row.status_code)) return false
      if (filters.decision.length > 0 && !filters.decision.includes(row.decision_code)) return false
      if (filters.who.length > 0 && !filters.who.includes(row.who)) return false

      if (createdFromTs !== null && row.created_ts > 0 && row.created_ts < createdFromTs) return false
      if (createdToTs !== null && row.created_ts > 0 && row.created_ts > createdToTs) return false
      if (requestedFromTs !== null && row.requested_ts > 0 && row.requested_ts < requestedFromTs) return false
      if (requestedToTs !== null && row.requested_ts > 0 && row.requested_ts > requestedToTs) return false

      return true
    })
  }, [filters, globalSearch, tabRows])

  const sortedRows = useMemo(() => {
    const list = [...filteredRows]
    list.sort((a, b) => {
      const pick = (row: Row): string | number => {
        switch (sortKey) {
          case 'candidate':
            return row.name.toLowerCase()
          case 'short_id':
            return row.short_id.toLowerCase()
          case 'phone':
            return row.phone.toLowerCase()
          case 'citizenship':
            return row.citizenship_display.toLowerCase()
          case 'stage':
            return row.stage_display.toLowerCase()
          case 'vacancy':
            return row.vacancy.toLowerCase()
          case 'created_at':
            return row.created_ts
          case 'requested_at':
            return row.requested_ts
          case 'status':
            return row.status_display.toLowerCase()
          case 'decision':
            return row.decision_display.toLowerCase()
          case 'who':
            return row.who.toLowerCase()
          case 'reason':
            return row.reason.toLowerCase()
          default:
            return row.requested_ts
        }
      }

      const left = pick(a)
      const right = pick(b)
      if (left === right) return 0
      if (typeof left === 'number' && typeof right === 'number') {
        return sortDirection === 'asc' ? left - right : right - left
      }
      return sortDirection === 'asc'
        ? String(left).localeCompare(String(right))
        : String(right).localeCompare(String(left))
    })
    return list
  }, [filteredRows, sortDirection, sortKey])

  const pendingRows = useMemo(
    () => sortedRows.filter((row) => row.handoff.status === 'pending_review'),
    [sortedRows],
  )

  const checkedIds = useMemo(() => Object.keys(checked).filter((id) => checked[id]), [checked])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDirection('asc')
  }

  const updateFilter = <K extends keyof HeaderFilters>(key: K, value: HeaderFilters[K]) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  const toggleChecked = (handoffId: string) => {
    setChecked((prev) => ({ ...prev, [handoffId]: !prev[handoffId] }))
  }

  const toggleAllPending = () => {
    if (checkedIds.length >= pendingRows.length) {
      setChecked({})
      return
    }
    const next: Record<string, boolean> = {}
    pendingRows.forEach((row) => {
      next[row.handoff.id] = true
    })
    setChecked(next)
  }

  const handleAccept = async (handoffId: string) => {
    setSubmitting(true)
    try {
      await acceptHandoff(handoffId)
      notify({ title: t('app.handoff.accepted'), variant: 'success' })
      await loadData()
    } catch (e: any) {
      notify({ title: e?.response?.data?.detail ?? t('common.errors.unknown'), variant: 'error' })
    } finally {
      setSubmitting(false)
    }
  }

  const handleBulkAccept = useCallback(async () => {
    if (checkedIds.length === 0) return
    setSubmitting(true)
    let ok = 0
    let errCount = 0
    try {
      for (const id of checkedIds) {
        try {
          await acceptHandoff(id)
          ok++
        } catch {
          errCount++
        }
      }
      setChecked({})
      notify({
        title: t('app.handoff.bulk_done', { values: { ok, total: checkedIds.length } }),
        variant: errCount > 0 ? 'warning' : 'success',
      })
      await loadData()
    } finally {
      setSubmitting(false)
    }
  }, [checkedIds, loadData, notify, t])

  const handleReturnSubmit = async () => {
    if (!returnReason.trim()) return
    if (!bulkReturnActive && !returnModal) return
    const ids = bulkReturnActive ? checkedIds : returnModal ? [returnModal.handoffId] : []
    if (ids.length === 0) return

    setSubmitting(true)
    let ok = 0
    let errCount = 0
    try {
      for (const id of ids) {
        try {
          await returnHandoff(id, returnReason.trim())
          ok++
        } catch {
          errCount++
        }
      }
      setReturnModal(null)
      setReturnReason('')
      setBulkReturnActive(false)
      setChecked({})
      notify({
        title: ok === ids.length ? t('app.handoff.returned') : t('app.handoff.bulk_done', { values: { ok, total: ids.length } }),
        variant: errCount > 0 ? 'warning' : 'success',
      })
      await loadData()
    } catch (e: any) {
      notify({ title: e?.response?.data?.detail ?? t('common.errors.unknown'), variant: 'error' })
    } finally {
      setSubmitting(false)
    }
  }

  const handleRejectSubmit = async () => {
    if (!rejectReason.trim()) return
    if (!bulkRejectActive && !rejectModal) return
    const ids = bulkRejectActive ? checkedIds : rejectModal ? [rejectModal.handoffId] : []
    if (ids.length === 0) return

    setSubmitting(true)
    let ok = 0
    let errCount = 0
    try {
      for (const id of ids) {
        try {
          await rejectHandoff(id, rejectReason.trim())
          ok++
        } catch {
          errCount++
        }
      }
      setRejectModal(null)
      setRejectReason('')
      setBulkRejectActive(false)
      setChecked({})
      notify({
        title: ok === ids.length ? t('app.handoff.rejected') : t('app.handoff.bulk_done', { values: { ok, total: ids.length } }),
        variant: errCount > 0 ? 'warning' : 'success',
      })
      await loadData()
    } catch (e: any) {
      notify({ title: e?.response?.data?.detail ?? t('common.errors.unknown'), variant: 'error' })
    } finally {
      setSubmitting(false)
    }
  }

  const handleExportCSV = useCallback(() => {
    const csvRows = sortedRows.map((row) => ({
      candidate: row.name,
      short_id: row.short_id,
      phone: row.phone,
      citizenship: row.citizenship_display,
      stage: row.stage_display,
      vacancy: row.vacancy,
      created_at: row.created_at,
      requested_at: row.requested_at,
      status: row.status_display,
      decision: row.decision_display,
      who: row.who,
      reason: row.reason,
    }))

    const headers = [
      { key: 'candidate', title: t('app.handoff.table.columns.candidate') },
      { key: 'short_id', title: t('app.handoff.table.columns.short_id') },
      { key: 'phone', title: t('app.handoff.table.columns.phone') },
      { key: 'citizenship', title: t('app.handoff.table.columns.citizenship') },
      { key: 'stage', title: t('app.handoff.table.columns.stage') },
      { key: 'vacancy', title: t('app.handoff.columns.position') },
      { key: 'created_at', title: t('app.handoff.table.columns.created') },
      { key: 'requested_at', title: t('app.handoff.table.columns.requested') },
      { key: 'status', title: t('app.handoff.table.columns.status') },
      { key: 'decision', title: t('app.handoff.table.columns.decision') },
      { key: 'who', title: t('app.handoff.table.columns.decision_by') },
      { key: 'reason', title: t('app.handoff.table.columns.reason') },
    ]

    const csv = toCSV(csvRows, headers)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `handoffs_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [sortedRows, t])

  const citizenshipOptions = useMemo(
    () => Array.from(new Set(tabRows.map((row) => row.citizenship).filter(Boolean))).sort(),
    [tabRows],
  )
  const stageOptions = useMemo(
    () =>
      employerVisibleStageCodes
        .filter((code) => tabRows.some((row) => row.stage_code === code))
        .map((code) => ({
          code,
          label: translateStageLabel(t, code, meta?.labels?.[code] || code),
        })),
    [employerVisibleStageCodes, meta?.labels, t, tabRows],
  )
  const vacancyOptions = useMemo(
    () => Array.from(new Set(tabRows.map((row) => row.vacancy).filter(Boolean))).sort((a, b) => a.localeCompare(b)),
    [tabRows],
  )
  const whoOptions = useMemo(
    () => Array.from(new Set(tabRows.map((row) => row.who).filter(Boolean))).sort((a, b) => a.localeCompare(b)),
    [tabRows],
  )
  const searchTooShort = globalSearch.trim().length > 0 && globalSearch.trim().length < 3
  const hasActiveFilters =
    globalSearch.trim().length > 0 ||
    filters.citizenship.length > 0 ||
    filters.stage.length > 0 ||
    filters.vacancy.length > 0 ||
    filters.status.length > 0 ||
    filters.decision.length > 0 ||
    filters.who.length > 0 ||
    Boolean(filters.created_from) ||
    Boolean(filters.created_to) ||
    Boolean(filters.requested_from) ||
    Boolean(filters.requested_to)
  const emptyStateColSpan = pendingRows.length > 0 ? 14 : 13

  const originPath = `/app/procesowani?tab=${activeTab}`

  const HeaderButton = ({ col, label }: { col: SortKey; label: string }) => (
    <button
      type="button"
      onClick={() => toggleSort(col)}
      className="inline-flex items-center gap-1 text-left text-sm font-semibold text-slate-700 hover:text-slate-900"
    >
      <span>{label}</span>
      {sortKey === col ? <span>{sortDirection === 'asc' ? '↑' : '↓'}</span> : <span className="text-slate-300">↕</span>}
    </button>
  )

  return (
    <div className="w-full max-w-none p-0" style={{ width: '100%', maxWidth: 'none' }}>
      <h1 className="text-2xl font-semibold text-slate-900">{t('app.handoff.do_procesowania')}</h1>
      <p className="mt-1 text-sm text-slate-500">{t('app.handoff.do_procesowania_subtitle')}</p>

      {isClientTenant && !selectedCompanyId ? (
        <div className="mt-4 space-y-3">
          <p className="text-sm text-slate-600">{t('app.handoff.your_org')}</p>
          {role === 'administrator' && companies.length > 0 && (
            <div>
              <label className="label">{t('app.handoff.filter_by_company')}</label>
              <select
                value={selectedCompanyId ?? ''}
                onChange={(e) => setSelectedCompanyId(e.target.value || null)}
                className="input mt-1 max-w-xs"
              >
                <option value="">—</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      ) : (
        <div className="mt-4">
          <label className="label">{t('app.handoff.company')}</label>
          <select
            value={selectedCompanyId ?? ''}
            onChange={(e) => setSelectedCompanyId(e.target.value || null)}
            className="input mt-1 max-w-xs"
          >
            <option value="">—</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1 text-sm">
          {TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={clsx(
                'rounded-lg px-3 py-1.5',
                activeTab === tab ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600',
              )}
            >
              {tab === 'do-procesowania' && t('app.handoff.tabs.to_process')}
              {tab === 'w-procesie' && t('app.handoff.tabs.in_process')}
              {tab === 'historia-decyzji' && t('app.handoff.tabs.history')}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <input
              className="input w-72 pr-8"
              value={globalSearch}
              onChange={(e) => setGlobalSearch(e.target.value)}
              placeholder={t('app.handoff.search_placeholder')}
            />
            <span className="pointer-events-none absolute right-2 top-1.5 text-slate-400">⌕</span>
          </div>
          {pendingRows.length > 0 && checkedIds.length > 0 && (
            <>
              <button type="button" onClick={() => void handleBulkAccept()} disabled={submitting} className="btn-primary btn-sm">
                {t('app.handoff.accept_btn')} ({checkedIds.length})
              </button>
              <button type="button" onClick={() => setBulkReturnActive(true)} disabled={submitting} className="btn-secondary btn-sm">
                {t('app.handoff.return_btn')} ({checkedIds.length})
              </button>
              <button type="button" onClick={() => setBulkRejectActive(true)} disabled={submitting} className="btn-danger btn-sm">
                {t('app.handoff.reject_btn')} ({checkedIds.length})
              </button>
            </>
          )}
          <button type="button" onClick={handleExportCSV} disabled={sortedRows.length === 0} className="btn-secondary btn-sm">
            CSV
          </button>
        </div>
      </div>
      {searchTooShort && (
        <p className="mt-2 text-xs text-amber-700">{t('app.handoff.search_min')}</p>
      )}

      <div className="mt-4 card overflow-hidden">
        {loading ? (
          <p className="p-4 text-sm text-slate-500">{t('common.loading')}</p>
        ) : (
          <div className="overflow-auto">
          <table className="min-w-full border-separate border-spacing-0 text-sm [&_th]:border-r [&_th]:border-slate-200 [&_th:last-child]:border-r-0 [&_td]:border-r [&_td]:border-slate-100 [&_td:last-child]:border-r-0">
            <thead className="align-top border-b-2 border-slate-200 bg-slate-50">
              <tr>
                {pendingRows.length > 0 && (
                  <th className="px-4 py-3 text-left w-10">
                    <input
                      type="checkbox"
                      checked={checkedIds.length > 0 && checkedIds.length >= pendingRows.length}
                      onChange={toggleAllPending}
                      title={t('app.handoff.select_all')}
                    />
                  </th>
                )}
                <th className="px-4 py-3">
                  <HeaderButton col="candidate" label={t('app.handoff.table.columns.candidate')} />
                </th>
                <th className="px-4 py-3">
                  <HeaderButton col="short_id" label={t('app.handoff.table.columns.short_id')} />
                </th>
                <th className="px-4 py-3">
                  <HeaderButton col="phone" label={t('app.handoff.table.columns.phone')} />
                </th>
                <th className="px-4 py-3">
                  <div className="inline-flex items-center gap-1">
                    <HeaderButton col="citizenship" label={t('app.handoff.table.columns.citizenship')} />
                    <ColumnFilterMenu
                      title={t('app.handoff.table.columns.citizenship')}
                      selected={filters.citizenship}
                      options={citizenshipOptions.map((value) => ({
                        value,
                        label: /^[A-Z]{2}$/.test(String(value).toUpperCase())
                          ? getRegionDisplayName(value, locale)
                          : value,
                      }))}
                      onChange={(next) => updateFilter('citizenship', next)}
                    />
                  </div>
                </th>
                <th className="px-4 py-3">
                  <div className="inline-flex items-center gap-1">
                    <HeaderButton col="stage" label={t('app.handoff.table.columns.stage')} />
                    <ColumnFilterMenu
                      title={t('app.handoff.table.columns.stage')}
                      selected={filters.stage}
                      options={stageOptions.map((option) => ({ value: option.code, label: option.label }))}
                      onChange={(next) => updateFilter('stage', next)}
                    />
                  </div>
                </th>
                <th className="px-4 py-3">
                  <div className="inline-flex items-center gap-1">
                    <HeaderButton col="vacancy" label={t('app.handoff.columns.position')} />
                    <ColumnFilterMenu
                      title={t('app.handoff.columns.position')}
                      selected={filters.vacancy}
                      options={vacancyOptions.map((value) => ({ value, label: value }))}
                      onChange={(next) => updateFilter('vacancy', next)}
                    />
                  </div>
                </th>
                <th className="px-4 py-3">
                  <div className="inline-flex items-center gap-1">
                    <HeaderButton col="created_at" label={t('app.handoff.table.columns.created')} />
                    <ColumnFilterMenu title={t('app.handoff.table.columns.created')} count={filters.created_from || filters.created_to ? 1 : 0}>
                      {(close) => (
                        <div className="space-y-2">
                          <label className="text-xs font-medium text-slate-600">
                            {t('app.handoff.filters.date_from')}
                            <input
                              type="date"
                              className="input mt-1 w-full"
                              value={filters.created_from}
                              onChange={(e) => updateFilter('created_from', e.target.value)}
                            />
                          </label>
                          <label className="text-xs font-medium text-slate-600">
                            {t('app.handoff.filters.date_to')}
                            <input
                              type="date"
                              className="input mt-1 w-full"
                              value={filters.created_to}
                              onChange={(e) => updateFilter('created_to', e.target.value)}
                            />
                          </label>
                          <div className="mt-2 flex justify-end gap-2 border-t pt-2">
                            <button
                              type="button"
                              className="btn-secondary btn-xs"
                              onClick={() => {
                                updateFilter('created_from', '')
                                updateFilter('created_to', '')
                                close()
                              }}
                            >
                              {t('app.candidates.filters.reset')}
                            </button>
                            <button type="button" className="btn-primary btn-xs" onClick={close}>
                              {t('common.actions.apply')}
                            </button>
                          </div>
                        </div>
                      )}
                    </ColumnFilterMenu>
                  </div>
                </th>
                <th className="px-4 py-3">
                  <div className="inline-flex items-center gap-1">
                    <HeaderButton col="requested_at" label={t('app.handoff.table.columns.requested')} />
                    <ColumnFilterMenu title={t('app.handoff.table.columns.requested')} count={filters.requested_from || filters.requested_to ? 1 : 0}>
                      {(close) => (
                        <div className="space-y-2">
                          <label className="text-xs font-medium text-slate-600">
                            {t('app.handoff.filters.date_from')}
                            <input
                              type="date"
                              className="input mt-1 w-full"
                              value={filters.requested_from}
                              onChange={(e) => updateFilter('requested_from', e.target.value)}
                            />
                          </label>
                          <label className="text-xs font-medium text-slate-600">
                            {t('app.handoff.filters.date_to')}
                            <input
                              type="date"
                              className="input mt-1 w-full"
                              value={filters.requested_to}
                              onChange={(e) => updateFilter('requested_to', e.target.value)}
                            />
                          </label>
                          <div className="mt-2 flex justify-end gap-2 border-t pt-2">
                            <button
                              type="button"
                              className="btn-secondary btn-xs"
                              onClick={() => {
                                updateFilter('requested_from', '')
                                updateFilter('requested_to', '')
                                close()
                              }}
                            >
                              {t('app.candidates.filters.reset')}
                            </button>
                            <button type="button" className="btn-primary btn-xs" onClick={close}>
                              {t('common.actions.apply')}
                            </button>
                          </div>
                        </div>
                      )}
                    </ColumnFilterMenu>
                  </div>
                </th>
                <th className="px-4 py-3">
                  <div className="inline-flex items-center gap-1">
                    <HeaderButton col="status" label={t('app.handoff.table.columns.status')} />
                    <ColumnFilterMenu
                      title={t('app.handoff.table.columns.status')}
                      selected={filters.status}
                      options={[
                        { value: 'pending_review', label: t('app.handoff.status.pending') },
                        { value: 'accepted', label: t('app.handoff.status.accepted') },
                        { value: 'rejected', label: t('app.handoff.status.rejected') },
                        { value: 'returned', label: t('app.handoff.status.returned') },
                      ]}
                      onChange={(next) => updateFilter('status', next)}
                    />
                  </div>
                </th>
                <th className="px-4 py-3">
                  <div className="inline-flex items-center gap-1">
                    <HeaderButton col="decision" label={t('app.handoff.table.columns.decision')} />
                    <ColumnFilterMenu
                      title={t('app.handoff.table.columns.decision')}
                      selected={filters.decision}
                      options={[
                        { value: 'employed', label: t('app.handoff.decisions.employed') },
                        { value: 'rejected', label: t('app.handoff.decisions.rejected') },
                        { value: 'declined', label: t('app.handoff.decisions.declined') },
                        { value: 'returned', label: t('app.handoff.decisions.returned') },
                      ]}
                      onChange={(next) => updateFilter('decision', next)}
                    />
                  </div>
                </th>
                <th className="px-4 py-3">
                  <div className="inline-flex items-center gap-1">
                    <HeaderButton col="who" label={t('app.handoff.table.columns.decision_by')} />
                    <ColumnFilterMenu
                      title={t('app.handoff.table.columns.decision_by')}
                      selected={filters.who}
                      options={whoOptions.map((value) => ({ value, label: value }))}
                      onChange={(next) => updateFilter('who', next)}
                    />
                  </div>
                </th>
                <th className="px-4 py-3">
                  <HeaderButton col="reason" label={t('app.handoff.table.columns.reason')} />
                </th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-slate-600">{t('app.handoff.table.columns.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedRows.length === 0 ? (
                <tr>
                  <td colSpan={emptyStateColSpan} className="px-4 py-8 text-center">
                    <div className="space-y-3 text-sm text-slate-500">
                      <p>{t('app.handoff.no_pending')}</p>
                      {hasActiveFilters && (
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() => {
                            setFilters(EMPTY_FILTERS)
                            setGlobalSearch('')
                          }}
                        >
                          {t('app.candidates.filters.reset')}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                sortedRows.map((row) => {
                  const phoneHref = row.phone ? asTelHref(row.phone) : ''
                  const pending = row.handoff.status === 'pending_review'
                  return (
                    <tr key={row.handoff.id} className="align-top">
                      {pendingRows.length > 0 && (
                        <td className="px-4 py-3">
                          {pending ? (
                            <input type="checkbox" checked={!!checked[row.handoff.id]} onChange={() => toggleChecked(row.handoff.id)} />
                          ) : null}
                        </td>
                      )}
                      <td className="px-4 py-3">
                        <Link
                          to={`/app/candidates/${row.candidate.id}`}
                          state={{ originPath }}
                          className="font-medium text-brand-600 hover:underline"
                        >
                          {row.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{row.short_id || '—'}</td>
                      <td className="px-4 py-3">
                        {phoneHref ? (
                          <a href={phoneHref} className="text-brand-600 hover:underline">{row.phone}</a>
                        ) : (
                          <span className="text-slate-500">{row.phone || '—'}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-600">{row.citizenship_display}</td>
                      <td className="px-4 py-3"><StageTag code={row.stage_code || ''} /></td>
                      <td className="px-4 py-3 text-slate-600">{row.vacancy || '—'}</td>
                      <td className="px-4 py-3 text-slate-600 whitespace-nowrap">{row.created_at}</td>
                      <td className="px-4 py-3 text-slate-600 whitespace-nowrap">{row.requested_at}</td>
                      <td className="px-4 py-3 text-slate-700">{row.status_display}</td>
                      <td className="px-4 py-3 text-slate-700">{row.decision_display}</td>
                      <td className="px-4 py-3 text-slate-600">{row.who || '—'}</td>
                      <td className="px-4 py-3 text-slate-600">{row.reason || '—'}</td>
                      <td className="px-4 py-3">
                        {pending ? (
                          <div className="flex justify-end gap-2">
                            <button type="button" onClick={() => void handleAccept(row.handoff.id)} disabled={submitting} className="btn-primary btn-xs">
                              {t('app.handoff.accept_btn')}
                            </button>
                            <button
                              type="button"
                              onClick={() => setReturnModal({ handoffId: row.handoff.id, candidateName: row.name })}
                              disabled={submitting}
                              className="btn-secondary btn-xs"
                            >
                              {t('app.handoff.return_btn')}
                            </button>
                            <button
                              type="button"
                              onClick={() => setRejectModal({ handoffId: row.handoff.id, candidateName: row.name })}
                              disabled={submitting}
                              className="btn-danger btn-xs"
                            >
                              {t('app.handoff.reject_btn')}
                            </button>
                          </div>
                        ) : (
                          <div className="text-right text-sm text-slate-400">—</div>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
          </div>
        )}
      </div>

      {(returnModal || bulkReturnActive) && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => !submitting && (setReturnModal(null), setBulkReturnActive(false), setReturnReason(''))}
        >
          <div className="card w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-medium text-slate-900">
              {bulkReturnActive
                ? t('app.handoff.return_bulk_title', { values: { count: checkedIds.length } })
                : `${t('app.handoff.return_title')} — ${returnModal?.candidateName ?? ''}`}
            </h3>
            <label className="label mt-3">{t('app.handoff.return_reason')}</label>
            <textarea
              value={returnReason}
              onChange={(e) => setReturnReason(e.target.value)}
              rows={3}
              className="textarea mt-1"
              placeholder={t('app.handoff.return_reason_placeholder')}
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setReturnModal(null)
                  setBulkReturnActive(false)
                  setReturnReason('')
                }}
                disabled={submitting}
                className="btn-secondary btn-sm"
              >
                {t('common.cancel')}
              </button>
              <button
                type="button"
                onClick={() => void handleReturnSubmit()}
                disabled={submitting || !returnReason.trim()}
                className="btn-secondary btn-sm"
              >
                {t('app.handoff.return_btn')}
              </button>
            </div>
          </div>
        </div>
      )}

      {(rejectModal || bulkRejectActive) && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => !submitting && (setRejectModal(null), setBulkRejectActive(false), setRejectReason(''))}
        >
          <div className="card w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-medium text-slate-900">
              {bulkRejectActive
                ? t('app.handoff.reject_bulk_title', { values: { count: checkedIds.length } })
                : `${t('app.handoff.reject_title')} — ${rejectModal?.candidateName ?? ''}`}
            </h3>
            <label className="label mt-3">{t('app.handoff.rejection_reason')}</label>
            <textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} rows={3} className="textarea mt-1" />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setRejectModal(null)
                  setBulkRejectActive(false)
                  setRejectReason('')
                }}
                disabled={submitting}
                className="btn-secondary btn-sm"
              >
                {t('common.cancel')}
              </button>
              <button
                type="button"
                onClick={() => void handleRejectSubmit()}
                disabled={submitting || !rejectReason.trim()}
                className="btn-danger btn-sm"
              >
                {t('app.handoff.reject_btn')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
