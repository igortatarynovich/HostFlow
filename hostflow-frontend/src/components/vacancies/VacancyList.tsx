import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { enUS, pl as plFns, ru as ruFns } from 'date-fns/locale'
import { useAuth } from '../../store/useAuth'
import { useI18n } from '../../i18n'
import type { LocaleCode } from '../../i18n'
import { patchUserMe } from '../../api/users'
import type { UserSavedView } from '../../api/types'
import { resolveApiBase, settings as clientSettings, DEFAULT_TENANT, getStoredAccessToken } from '../../api/client'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { useCurrentTenantId } from '../../contexts/CurrentTenant'
import { PageHeader } from '../nav/PageHeader'
import { PageShell, PageShellHeader, Toolbar, DataTable, type DataTableColumn } from '../layout'
import EntityListBulkBar from '../surfaces/EntityListBulkBar'
import EntityListPagination from '../surfaces/EntityListPagination'
import EntityListShell from '../surfaces/EntityListShell'
import EntityListTableFrame from '../surfaces/EntityListTableFrame'
import EmptyStatePanel from '../EmptyStatePanel'

// Unify button styles with Candidates page
const primaryBtn = 'btn-primary'
const secondaryBtn = 'btn-secondary'
const NEXT_PAGE_GLYPH = '\u2192'

const API_BASE: string = resolveApiBase().replace(/\/+$/, '')
const API_BASE_WITH_SLASH = `${API_BASE}/`

let API_BASE_URL: URL
try {
  API_BASE_URL = new URL(API_BASE_WITH_SLASH)
} catch (_err) {
  API_BASE_URL = new URL('http://localhost:8000/api/v1/')
}

function safeStorageGet(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function sanitizeTenant(raw: string | null | undefined): string | null {
  if (!raw) return null
  const first = raw.split(',')[0]?.trim() ?? ''
  if (!first) return null
  return first
}

function getAuthHeaders(tenantOverride?: string | null) {
  const token = getStoredAccessToken() || ''

  const candidates = [
    sanitizeTenant(tenantOverride ?? null),
    sanitizeTenant(((import.meta as any).env?.VITE_TENANT_ID as string) ?? null),
    sanitizeTenant(safeStorageGet('X-Tenant-Id')),
    sanitizeTenant(safeStorageGet('x-tenant-id')),
    sanitizeTenant(safeStorageGet('tenant_id')),
    sanitizeTenant(clientSettings.get?.() ?? null),
  ]
  let tenantId = candidates.find(Boolean) || DEFAULT_TENANT
  clientSettings.set(tenantId)

  const headers: Record<string, string> = { Accept: 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  headers['X-Tenant-Id'] = tenantId
  return headers
}

async function getJSON<T = any>(path: string, params?: Record<string, any>, tenantOverride?: string | null): Promise<T> {
  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  const url = new URL(cleanPath, API_BASE_URL)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v))
    })
  }
  const res = await fetch(url.toString(), {
    credentials: 'include',
    headers: getAuthHeaders(tenantOverride),
  })
  if (!res.ok) {
    const raw = await res.text()
    let detail: unknown = raw
    try {
      const j = JSON.parse(raw)
      if (j && typeof j === 'object' && 'detail' in j) {
        detail = (j as { detail: unknown }).detail
      }
    } catch {
      /* keep raw text */
    }
    const message =
      typeof detail === 'string'
        ? detail
        : detail && typeof detail === 'object'
          ? JSON.stringify(detail)
          : `HTTP ${res.status}`
    const err = new Error(message) as Error & { response?: { status: number; data: { detail: unknown } } }
    err.response = { status: res.status, data: { detail } }
    throw err
  }
  return res.json()
}

async function patchJSON<T = any>(path: string, body: Record<string, any>, tenantOverride?: string | null): Promise<T> {
  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  const url = new URL(cleanPath, API_BASE_URL).toString()
  const res = await fetch(url, {
    method: 'PATCH',
    credentials: 'include',
    headers: { ...getAuthHeaders(tenantOverride), 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const raw = await res.text()
    let detail: unknown = raw
    try {
      const j = JSON.parse(raw)
      if (j && typeof j === 'object' && 'detail' in j) {
        detail = (j as { detail: unknown }).detail
      }
    } catch {
      /* keep raw text */
    }
    const message =
      typeof detail === 'string'
        ? detail
        : detail && typeof detail === 'object'
          ? JSON.stringify(detail)
          : `HTTP ${res.status}`
    const err = new Error(message) as Error & { response?: { status: number; data: { detail: unknown } } }
    err.response = { status: res.status, data: { detail } }
    throw err
  }
  return res.json()
}

// ---- types (loose-safe)
type Vacancy = {
  id: string
  title: string
  status?: string
  company_id?: string
  company_name?: string
  candidate_count?: number
  headcount_target?: number | null
  candidate_profile_name?: string | null
  last_candidate_activity_at?: string | null
  created_at?: string
  updated_at?: string
  is_archived?: boolean
}

const DATE_FNS_LOCALES: Record<LocaleCode, typeof enUS> = {
  en: enUS,
  pl: plFns,
  ru: ruFns,
}

type ListResponse = {
  items: Vacancy[]
  total: number
  limit: number
  offset: number
}

function StatusBadge({ value, archived, label }: { value?: string; archived?: boolean; label: string }) {
  const v = archived ? 'archived' : (value || '').toLowerCase()
  // Phase 2.6.D Stage C — `filled` and `cancelled` are canonical
  // terminal codes (`docs/specs/vacancy-statuses.md`). `filled`
  // celebrates a successful hire (success-blue), `cancelled` is a
  // soft negative (ghost) — distinct from `closed` which is a generic
  // shutdown. Legacy `paused` is normalized at the API boundary but
  // we still recognise it here as defence-in-depth for the rollout
  // window before the Stage B alembic backfill runs.
  const badgeClass = archived
    ? 'badge badge-ghost'
    : v === 'open'
    ? 'badge badge-success'
    : v === 'on_hold' || v === 'paused'
    ? 'badge badge-warning'
    : v === 'closed'
    ? 'badge badge-error'
    : v === 'filled'
    ? 'badge badge-info'
    : v === 'cancelled'
    ? 'badge badge-ghost'
    : 'badge'
  return <span className={badgeClass}>{label}</span>
}

// ----- helpers for CSV + views
function toCSV(rows: any[], headers: { key: string; label: string }[]) {
  const esc = (v: any) => {
    if (v === null || v === undefined) return ''
    const s = String(v)
    if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"'
    return s
  }
  const head = headers.map(h => esc(h.label)).join(',')
  const body = rows.map(r => headers.map(h => esc((r as any)[h.key])).join(',')).join('\n')
  return head + '\n' + body
}

export default function VacancyList() {
  const [search, setSearch] = useSearchParams()
  const navigate = useNavigate()
  const { me, preferences, updatePreferences } = useAuth()
  const currentTenantId = useCurrentTenantId()
  const effectiveTenantId = (currentTenantId || '').trim() || null
  const { t, locale } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const dateFnsLocale = DATE_FNS_LOCALES[locale] ?? enUS

  const [data, setData] = useState<ListResponse>({ items: [], total: 0, limit: 20, offset: 0 })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [refreshTick, setRefreshTick] = useState(0)
  const [selected, setSelected] = useState<string[]>([])
  const statusOptions = useMemo(
    () => [
      { value: '', label: t('app.vacancies.list.status.all') },
      { value: 'open', label: t('app.vacancies.list.status.open') },
      { value: 'on_hold', label: t('app.vacancies.list.status.on_hold') },
      { value: 'closed', label: t('app.vacancies.list.status.closed') },
      // Phase 2.6.D Stage C — surface the new canonical terminals
      // alongside `closed`. `archived` stays at the bottom because
      // it's an orthogonal boolean (soft-delete) rather than a
      // status, and is rendered last to match the badge ordering
      // operators are used to.
      { value: 'filled', label: t('app.vacancies.list.status.filled') },
      { value: 'cancelled', label: t('app.vacancies.list.status.cancelled') },
      { value: 'archived', label: t('app.vacancies.list.status.archived') },
    ],
    [t]
  )
  const statusLabelMap = useMemo(
    () => ({
      open: t('app.vacancies.list.status.open'),
      on_hold: t('app.vacancies.list.status.on_hold'),
      closed: t('app.vacancies.list.status.closed'),
      filled: t('app.vacancies.list.status.filled'),
      cancelled: t('app.vacancies.list.status.cancelled'),
      archived: t('app.vacancies.list.status.archived'),
    }),
    [t]
  )
  const statusLabel = useCallback(
    (value?: string, archived?: boolean) => {
      const key = archived ? 'archived' : (value || '')
      return statusLabelMap[key as keyof typeof statusLabelMap] || t('common.labels.not_available')
    },
    [statusLabelMap, t]
  )

  // Search hotkey (Cmd/Ctrl + K)
  const searchRef = useRef<HTMLInputElement>(null)
  const actionsMenuRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        if (searchRef.current) {
          searchRef.current.focus()
          searchRef.current.select()
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // columns visibility
  const [actionsMenuOpen, setActionsMenuOpen] = useState(false)
  const [visibleCols, setVisibleCols] = useState<{
    title: boolean
    company: boolean
    status: boolean
    updated: boolean
    candidates: boolean
    headcount: boolean
    profile: boolean
    lastActivity: boolean
  }>({
    title: true,
    company: true,
    status: true,
    updated: true,
    candidates: true,
    headcount: true,
    profile: false,
    lastActivity: true,
  })

  const allSelected = useMemo(()=> selected.length > 0 && selected.length === (data.items?.length || 0), [selected, data.items])
  const toggleOne = (id: string) => setSelected(prev => prev.includes(id) ? prev.filter(x=>x!==id) : [...prev, id])
  const toggleAll = () => setSelected(() => (allSelected ? [] : (data.items || []).map(i => i.id)))

  // Saved views (global preferences)
  const views = useMemo(() => preferences?.saved_views?.vacancies ?? [], [preferences?.saved_views?.vacancies])
  const defaultVacancyViewApplied = useRef<string | null>(null)
  const candidateViews = useMemo(() => preferences?.saved_views?.candidates ?? [], [preferences?.saved_views?.candidates])

  // URL state
  const q = search.get('q') || ''
  const status = search.get('status') || ''
  const company = search.get('company') || ''
  const page = parseInt(search.get('page') || '1', 10)
  const sort = (search.get('sort') || 'created_at')
  const dir = ((search.get('dir') || 'desc') === 'asc' ? 'asc' : 'desc') as 'asc' | 'desc'

  const limit = 20
  const offset = (page - 1) * limit

  const params = useMemo(() => {
    const p: Record<string, string | number> = { limit, offset, order_by: sort, desc: dir === 'desc' ? 1 : 0 }
    if (q) p.q = q
    if (status) p.status = status
    if (company) p.company_id = company
    if ((status || '').toLowerCase() === 'archived') {
      p.include_archived = 1
    }
    return p
  }, [q, status, company, sort, dir, limit, offset])

  useEffect(() => {
    const role = String(me?.role || '').trim().toLowerCase()
    if (role === 'superadmin') return
    const defaultCompanyId = preferences?.defaults?.company_id
    if (defaultCompanyId && !company) {
      const next = new URLSearchParams(search)
      next.set('company', defaultCompanyId)
      next.set('page', '1')
      setSearch(next, { replace: true })
    }
  }, [me?.role, preferences?.defaults?.company_id, company, search, setSearch])

  // load
  useEffect(() => {
    setLoading(true)
    setError(null)
    getJSON<ListResponse | Vacancy[]>('/vacancies/', params, effectiveTenantId)
      .then((data) => {
        if (Array.isArray(data)) {
          setData({ items: data, total: data.length, limit, offset })
        } else {
          setData({
            items: (data as ListResponse).items ?? (data as any).results ?? [],
            total: (data as ListResponse).total ?? (data as any).count ?? 0,
            limit: (data as ListResponse).limit ?? limit,
            offset: (data as ListResponse).offset ?? offset,
          })
        }
      })
      .catch((err: any) => {
        console.error('[vacancies/list] failed', err)
        const unauthorized =
          err?.message === 'HTTP 401' || /Unauthorized|Missing Authorization/i.test(err?.message || '')
        if (unauthorized) {
          setError({
            title: t('app.vacancies.list.errors.unauthorized'),
            hint: t('app.common.retry_hint'),
          })
        } else if (
          planLimitModal?.showPlanLimitIfNeeded(err, t('app.vacancies.list.errors.load_failed'))
        ) {
          setError(null)
        } else {
          setError(getFriendlyErrorInfo(err, t('app.vacancies.list.errors.load_failed'), t))
        }
      })
      .finally(() => {
        setLoading(false)
        setSelected([])
      })
  }, [params, refreshTick, planLimitModal, t, effectiveTenantId])


  // client-side сортировка (fallback)
  const items = useMemo(() => {
    const arr = [...(data.items || [])]
    const get = (v: Vacancy, key: string) => {
      if (key === 'title') return (v.title || '').toLowerCase()
      if (key === 'company_name') return (v.company_name || '').toLowerCase()
      if (key === 'status') return (v.is_archived ? 'archived' : (v.status || ''))
      if (key === 'updated_at' || key === 'created_at') return v[key as 'updated_at' | 'created_at'] || ''
      if (key === 'candidate_count') return Number(v.candidate_count ?? 0)
      if (key === 'headcount_target') return Number(v.headcount_target ?? 0)
      if (key === 'last_candidate_activity_at') return v.last_candidate_activity_at || ''
      if (key === 'candidate_profile_name') return (v.candidate_profile_name || '').toLowerCase()
      return (v as any)[key] ?? ''
    }
    arr.sort((a,b) => {
      const av = get(a, sort)
      const bv = get(b, sort)
      if (av === bv) return 0
      if (typeof av === 'number' && typeof bv === 'number') {
        return av === bv ? 0 : (av > bv ? 1 : -1) * (dir === 'asc' ? 1 : -1)
      }
      return (String(av) > String(bv) ? 1 : -1) * (dir === 'asc' ? 1 : -1)
    })
    return arr
  }, [data.items, sort, dir])

  // actions
  const onSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget as HTMLFormElement
    const formData = new FormData(form)
    const next = new URLSearchParams(search)
    next.set('q', String(formData.get('q') || ''))
    next.set('company', String(formData.get('company') || ''))
    next.set('status', String(formData.get('status') || ''))
    next.set('page', '1')
    setSearch(next, { replace: true })
  }

  const goPage = (n: number) => {
    const next = new URLSearchParams(search)
    next.set('page', String(n))
    setSearch(next, { replace: true })
  }

  const setSort = (field: string) => {
    const next = new URLSearchParams(search)
    const currentField = next.get('sort') || 'created_at'
    const currentDir = (next.get('dir') || 'desc') as 'asc' | 'desc'
    if (currentField === field) {
      next.set('dir', currentDir === 'asc' ? 'desc' : 'asc')
    } else {
      next.set('sort', field)
      const descDefault =
        field === 'created_at' ||
        field === 'updated_at' ||
        field === 'last_candidate_activity_at' ||
        field === 'candidate_count' ||
        field === 'headcount_target'
      next.set('dir', descDefault ? 'desc' : 'asc')
    }
    setSearch(next, { replace: true })
  }

  const refresh = () => setRefreshTick(t => t + 1)

  const resetFilters = () => {
    const next = new URLSearchParams(search)
    next.set('q', '')
    next.set('company', '')
    next.set('status', '')
    next.set('page', '1')
    setSearch(next, { replace: true })
  }

  const exportCSV = () => {
    const headers = [
      { key: 'title', label: t('app.vacancies.list.col_title') },
      { key: 'company_name', label: t('app.vacancies.list.col_company') },
      { key: 'status', label: t('app.vacancies.list.col_status') },
      { key: 'candidate_count', label: t('app.vacancies.list.col_candidates') },
      { key: 'headcount_target', label: t('app.vacancies.list.col_headcount') },
      { key: 'candidate_profile_name', label: t('app.vacancies.list.col_profile') },
      { key: 'last_candidate_activity_at', label: t('app.vacancies.list.col_last_activity') },
      { key: 'updated_at', label: t('app.vacancies.list.col_updated') },
      { key: 'created_at', label: t('app.vacancies.list.col_created') },
    ]
    const rows = items.map(v => ({
      title: v.title || t('app.vacancies.list.untitled'),
      company_name: v.company_name || '',
      status: statusLabel(v.status, v.is_archived),
      candidate_count: String(v.candidate_count ?? 0),
      headcount_target:
        v.headcount_target != null && v.headcount_target > 0 ? String(v.headcount_target) : '',
      candidate_profile_name: v.candidate_profile_name || '',
      last_candidate_activity_at: v.last_candidate_activity_at
        ? new Date(v.last_candidate_activity_at).toLocaleString()
        : '',
      updated_at: v.updated_at ? new Date(v.updated_at).toLocaleString() : '',
      created_at: v.created_at ? new Date(v.created_at).toLocaleString() : '',
    }))
    const csv = toCSV(rows, headers)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'vacancies.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const bulkSetStatus = async (status: 'open'|'on_hold'|'closed'|'filled'|'cancelled') => {
    if (selected.length === 0) return
    // optimistic UI
    setData(prev => ({...prev, items: (prev.items || []).map(v => selected.includes(v.id) ? {...v, status, is_archived: false} : v)}))
    try{
      await Promise.allSettled(
        selected.map((id) => {
          const row = (data.items || []).find((v) => v.id === id)
          const tenantForRow = String((row as any)?.tenant_id || '').trim() || effectiveTenantId
          return patchJSON(`/vacancies/${id}`, { status }, tenantForRow)
        }),
      )
    } catch (_){}
    setSelected([])
    refresh()
  }

  const bulkArchive = async () => {
    if (selected.length === 0) return
    setData(prev => ({...prev, items: (prev.items || []).map(v => selected.includes(v.id) ? {...v, is_archived: true} : v)}))
    try{
      await Promise.allSettled(
        selected.map((id) => {
          const row = (data.items || []).find((v) => v.id === id)
          const tenantForRow = String((row as any)?.tenant_id || '').trim() || effectiveTenantId
          return patchJSON(`/vacancies/${id}`, { is_archived: true }, tenantForRow)
        }),
      )
    } catch(_){}
    setSelected([])
    refresh()
  }

  const toggleCol = (k: keyof typeof visibleCols) => setVisibleCols((s) => ({ ...s, [k]: !s[k] }))

  const syncVacancyViews = useCallback(async (next: UserSavedView[]) => {
    try {
      const result = await patchUserMe({
        preferences: {
          saved_views: {
            candidates: candidateViews,
            vacancies: next,
          },
        },
      })
      updatePreferences(result.preferences)
    } catch (err) {
      console.warn('[Vacancies] failed to persist saved views', err)
    }
  }, [candidateViews, updatePreferences])

  const saveView = () => {
    const name = window.prompt(t('app.vacancies.list.view_name_prompt'))?.trim()
    if (!name) return
    const filters = { q, company, status, sort, dir }
    const newView: UserSavedView = {
      id: (typeof crypto !== 'undefined' && 'randomUUID' in crypto) ? crypto.randomUUID() : String(Date.now()),
      name,
      filters,
    }
    const next = [...views.filter((v) => v.name !== name), newView]
    void syncVacancyViews(next)
  }

  const applyView = (view: UserSavedView) => {
    const next = new URLSearchParams(search)
    Object.entries(view.filters ?? {}).forEach(([key, value]) => {
      if (value === undefined || value === null) {
        next.delete(key)
      } else {
        next.set(key, String(value))
      }
    })
    next.set('page', '1')
    setSearch(next, { replace: true })
  }

  useEffect(() => {
    const defaultView = views.find((view) => view.is_default)
    if (defaultView && defaultVacancyViewApplied.current !== defaultView.id) {
      applyView(defaultView)
      defaultVacancyViewApplied.current = defaultView.id
    }
  }, [views])

  useEffect(() => {
    if (!actionsMenuOpen) return
    const handler = (event: MouseEvent) => {
      if (actionsMenuRef.current && !actionsMenuRef.current.contains(event.target as Node)) {
        setActionsMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [actionsMenuOpen])

  const removeView = (id: string) => {
    const next = views.filter((view) => view.id !== id)
    void syncVacancyViews(next)
  }

  const resetDisabled = !q && !company && !status
  const visibleColumnCount =
    (visibleCols.title ? 1 : 0) +
    (visibleCols.company ? 1 : 0) +
    (visibleCols.status ? 1 : 0) +
    (visibleCols.updated ? 1 : 0) +
    (visibleCols.candidates ? 1 : 0) +
    (visibleCols.headcount ? 1 : 0) +
    (visibleCols.profile ? 1 : 0) +
    (visibleCols.lastActivity ? 1 : 0)
  const tableColSpan = visibleColumnCount + 2

  const pageStatusMix = useMemo(() => {
    const arr = items
    const open = arr.filter((v) => !v.is_archived && (v.status || '').toLowerCase() === 'open').length
    const on_hold = arr.filter((v) => !v.is_archived && (v.status || '').toLowerCase() === 'on_hold').length
    const closed = arr.filter((v) => !v.is_archived && (v.status || '').toLowerCase() === 'closed').length
    const archived = arr.filter((v) => v.is_archived).length
    return { open, on_hold, closed, archived }
  }, [items])

  const formatLastCandidateActivity = useCallback(
    (iso: string | null | undefined) => {
      if (!iso) return '—'
      try {
        return formatDistanceToNow(new Date(iso), { addSuffix: true, locale: dateFnsLocale })
      } catch {
        return '—'
      }
    },
    [dateFnsLocale]
  )

  const sortHeader = (field: string, label: string) => {
    const active = sort === field
    return (
      <button
        type="button"
        className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 transition hover:text-slate-900"
        onClick={() => setSort(field)}
      >
        {label}
        {active && <span>{dir === 'asc' ? '▲' : '▼'}</span>}
      </button>
    )
  }
  const stop = (e: React.MouseEvent) => e.stopPropagation()

  const vacancyColumns: DataTableColumn<Vacancy>[] = []
  if (visibleCols.title) {
    vacancyColumns.push({
      key: 'title',
      header: sortHeader('title', t('app.vacancies.list.col_title')),
      cellClassName: 'font-medium',
      render: (v) => (
        <Link className="text-brand-700 hover:underline" to={`${CRM_APP_PATHS.vacancies}/${v.id}`} onClick={stop}>
          {v.title || t('app.vacancies.list.untitled')}
        </Link>
      ),
    })
  }
  if (visibleCols.company) {
    vacancyColumns.push({
      key: 'company',
      header: sortHeader('company_name', t('app.vacancies.list.col_company')),
      render: (v) => v.company_name || '—',
    })
  }
  if (visibleCols.status) {
    vacancyColumns.push({
      key: 'status',
      header: sortHeader('status', t('app.vacancies.list.col_status')),
      render: (v) => (
        <StatusBadge value={v.status || ''} archived={v.is_archived} label={statusLabel(v.status, v.is_archived)} />
      ),
    })
  }
  if (visibleCols.candidates) {
    vacancyColumns.push({
      key: 'candidates',
      header: sortHeader('candidate_count', t('app.vacancies.list.col_candidates')),
      align: 'right',
      tabularNums: true,
      render: (v) => (
        <Link
          className="font-medium text-brand-700 hover:underline"
          to={`${CRM_APP_PATHS.vacancies}/${v.id}/candidates`}
          onClick={stop}
        >
          {v.candidate_count ?? 0}
        </Link>
      ),
    })
  }
  if (visibleCols.headcount) {
    vacancyColumns.push({
      key: 'headcount',
      header: sortHeader('headcount_target', t('app.vacancies.list.col_headcount')),
      align: 'right',
      tabularNums: true,
      cellClassName: 'text-slate-700',
      render: (v) =>
        v.headcount_target != null && v.headcount_target > 0 ? (
          <span title={t('app.vacancies.list.headcount_title')}>
            {v.candidate_count ?? 0}/{v.headcount_target}
          </span>
        ) : (
          '—'
        ),
    })
  }
  if (visibleCols.profile) {
    vacancyColumns.push({
      key: 'profile',
      header: sortHeader('candidate_profile_name', t('app.vacancies.list.col_profile')),
      cellClassName: 'text-slate-600',
      render: (v) => v.candidate_profile_name || '—',
    })
  }
  if (visibleCols.lastActivity) {
    vacancyColumns.push({
      key: 'lastActivity',
      header: sortHeader('last_candidate_activity_at', t('app.vacancies.list.col_last_activity')),
      cellClassName: 'text-slate-600',
      render: (v) => formatLastCandidateActivity(v.last_candidate_activity_at),
    })
  }
  if (visibleCols.updated) {
    vacancyColumns.push({
      key: 'updated',
      header: sortHeader('updated_at', t('app.vacancies.list.col_updated')),
      render: (v) =>
        v.updated_at
          ? new Date(v.updated_at).toLocaleDateString()
          : v.created_at
            ? new Date(v.created_at).toLocaleDateString()
            : '—',
    })
  }
  // Row click opens detail — no separate actions column (matches Candidates / Clients lists).

  const tableStatus = loading ? 'loading' : error ? 'error' : items.length === 0 ? 'empty' : 'ready'

  const errorBanner = error ? (
    <ErrorRecoveryBanner
      info={error}
      onRetry={() => refresh()}
      retryLabel={t('common.actions.retry')}
      {...friendlyErrorBannerSecondary(
        error,
        CRM_APP_PATHS.vacancies,
        t('app.nav.items.vacancies', { defaultValue: 'Vacancies' }),
      )}
      compact
    />
  ) : null

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          primaryAction={
            <Link to={CRM_APP_PATHS.vacancyNew} className="btn-primary btn-sm">
              {t('app.vacancies.list.new_vacancy')}
            </Link>
          }
        />
      </PageShellHeader>

      <EntityListShell
        className="min-h-0 flex-1"
        resourceLabel={t('app.nav.items.vacancies', { defaultValue: 'Vacancies' })}
        selection={{
          selectedCount: selected.length,
          onClearSelection: () => setSelected([]),
        }}
        zones={{
          toolbar: (
            <Toolbar>
              <form onSubmit={onSearch} className="flex flex-wrap items-center gap-2">
                <input
                  name="q"
                  ref={searchRef}
                  defaultValue={q}
                  placeholder={t('app.vacancies.list.search_placeholder')}
                  className="input min-h-[40px] min-w-[200px] flex-1 rounded-lg border-slate-200/90 bg-white py-2 text-sm shadow-sm focus:border-brand-400 focus:ring-2 focus:ring-brand-500/15"
                />
                <input
                  name="company"
                  defaultValue={company}
                  placeholder={t('app.vacancies.list.company_placeholder')}
                  className="input min-h-[40px] w-48 py-2 text-sm"
                />
                {statusOptions.map((s) => (
                  <button
                    key={s.value || 'all'}
                    type="button"
                    className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
                      status === s.value
                        ? 'border-brand-600 bg-brand-50 text-brand-800 shadow-sm'
                        : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-800'
                    }`}
                    onClick={() => {
                      const next = new URLSearchParams(search)
                      if (!s.value) next.delete('status')
                      else next.set('status', s.value)
                      next.set('page', '1')
                      setSearch(next, { replace: true })
                    }}
                  >
                    {s.label}
                  </button>
                ))}
                <button type="submit" className={secondaryBtn}>
                  {t('common.actions.apply')}
                </button>
                <button
                  type="button"
                  className={secondaryBtn}
                  onClick={resetFilters}
                  disabled={resetDisabled}
                  title={t('app.vacancies.list.reset_filters_title')}
                >
                  {t('common.actions.reset')}
                </button>
                <button
                  type="button"
                  className={secondaryBtn}
                  onClick={refresh}
                  disabled={loading}
                  title={t('app.vacancies.list.refresh_title')}
                >
                  {loading ? t('common.loading') : t('common.actions.refresh')}
                </button>
                <button
                  type="button"
                  className={secondaryBtn}
                  onClick={exportCSV}
                  title={t('app.vacancies.list.export_csv_title')}
                >
                  {t('app.vacancies.list.export_csv')}
                </button>
                <div className="relative" ref={actionsMenuRef}>
                  <button
                    type="button"
                    className={secondaryBtn}
                    onClick={() => setActionsMenuOpen((prev) => !prev)}
                    title={t('common.actions.more')}
                  >
                    ⋯
                  </button>
                  {actionsMenuOpen && (
                    <div className="absolute right-0 z-20 mt-2 w-56 rounded-lg border border-slate-200 bg-white p-3 shadow-md">
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                        {t('app.vacancies.list.columns')}
                      </div>
                      <div className="mt-2 space-y-1">
                        <label className="flex items-center gap-2 py-1 text-sm">
                          <input type="checkbox" checked={visibleCols.title} onChange={() => toggleCol('title')} />{' '}
                          {t('app.vacancies.list.col_title')}
                        </label>
                        <label className="flex items-center gap-2 py-1 text-sm">
                          <input type="checkbox" checked={visibleCols.company} onChange={() => toggleCol('company')} />{' '}
                          {t('app.vacancies.list.col_company')}
                        </label>
                        <label className="flex items-center gap-2 py-1 text-sm">
                          <input type="checkbox" checked={visibleCols.status} onChange={() => toggleCol('status')} />{' '}
                          {t('app.vacancies.list.col_status')}
                        </label>
                        <label className="flex items-center gap-2 py-1 text-sm">
                          <input type="checkbox" checked={visibleCols.updated} onChange={() => toggleCol('updated')} />{' '}
                          {t('app.vacancies.list.col_updated')}
                        </label>
                        <label className="flex items-center gap-2 py-1 text-sm">
                          <input type="checkbox" checked={visibleCols.candidates} onChange={() => toggleCol('candidates')} />{' '}
                          {t('app.vacancies.list.col_candidates')}
                        </label>
                        <label className="flex items-center gap-2 py-1 text-sm">
                          <input type="checkbox" checked={visibleCols.headcount} onChange={() => toggleCol('headcount')} />{' '}
                          {t('app.vacancies.list.col_headcount')}
                        </label>
                        <label className="flex items-center gap-2 py-1 text-sm">
                          <input type="checkbox" checked={visibleCols.profile} onChange={() => toggleCol('profile')} />{' '}
                          {t('app.vacancies.list.col_profile')}
                        </label>
                        <label className="flex items-center gap-2 py-1 text-sm">
                          <input type="checkbox" checked={visibleCols.lastActivity} onChange={() => toggleCol('lastActivity')} />{' '}
                          {t('app.vacancies.list.col_last_activity')}
                        </label>
                      </div>
                      <button
                        type="button"
                        className="btn-primary mt-3 w-full"
                        onClick={() => {
                          setActionsMenuOpen(false)
                          saveView()
                        }}
                      >
                        {t('app.vacancies.list.save_view')}
                      </button>
                    </div>
                  )}
                </div>
              </form>
            </Toolbar>
          ),
          activeFilters:
            views.length > 0 ? (
              <div className="mx-4 flex flex-wrap items-center gap-2">
                {views.map((v) => (
                  <div key={v.id} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-2 py-1 text-sm shadow-sm">
                    <button className="hover:underline" onClick={() => applyView(v)}>
                      {v.name || t('app.vacancies.list.untitled')}
                    </button>
                    <button className="text-slate-400 hover:text-rose-700" onClick={() => removeView(v.id)} title={t('app.vacancies.list.delete_view')}>
                      ×
                    </button>
                  </div>
                ))}
              </div>
            ) : undefined,
          table: (
            <EntityListTableFrame
              status={tableStatus}
              loading={<div className="px-4 py-8 text-center text-sm text-slate-500">{t('common.loading')}</div>}
              empty={
                <div className="px-4 py-6">
                  <EmptyStatePanel
                    compact
                    title={t('app.vacancies.list.empty_title', {
                      defaultValue: 'You have no vacancies yet',
                    })}
                    description={t('app.vacancies.list.empty_description', {
                      defaultValue: 'Create your first vacancy in about 30 seconds to start receiving and processing candidates.',
                    })}
                    whyHint={t('app.vacancies.list.empty_why', {
                      defaultValue:
                        'A vacancy is the role you hire for. Leads and candidates attach to it so ownership and documents stay clear.',
                    })}
                    primaryAction={{
                      label: t('app.vacancies.list.empty_cta', {
                        defaultValue: 'Create vacancy',
                      }),
                      to: CRM_APP_PATHS.setupVacancy,
                    }}
                    secondaryAction={{
                      label: t('app.vacancies.list.empty_cta_setup', {
                        defaultValue: 'Open getting started',
                      }),
                      to: CRM_APP_PATHS.setup,
                    }}
                  />
                </div>
              }
              error={errorBanner}
              table={
                <DataTable
                  columns={vacancyColumns}
                  rows={items}
                  rowKey={(v) => v.id}
                  loading={false}
                  onRowClick={(v) => navigate(`${CRM_APP_PATHS.vacancies}/${v.id}`)}
                  selection={{
                    isSelected: (id) => selected.includes(id),
                    onToggle: (id, checked) =>
                      setSelected((prev) => (checked ? Array.from(new Set([...prev, id])) : prev.filter((x) => x !== id))),
                    onToggleAll: (checked) => setSelected(checked ? (data.items || []).map((i) => i.id) : []),
                    allSelected,
                    someSelected: selected.length > 0,
                  }}
                  emptyState={t('app.vacancies.list.not_found')}
                  ariaLabel={t('app.nav.items.vacancies')}
                />
              }
            />
          ),
          bulkBar: (
            <EntityListBulkBar
              selectedCount={selected.length}
              onClearSelection={() => setSelected([])}
              selectedLabel={(count) => t('app.vacancies.list.bulk_selected', { values: { count } })}
              clearLabel={t('app.vacancies.list.bulk_clear_selection')}
              actions={
                <>
                  <div className="flex items-center gap-1">
                    <span className="text-slate-500">{t('app.vacancies.list.bulk_set_status')}</span>
                    <button className={secondaryBtn} onClick={() => bulkSetStatus('open')}>
                      {t('app.vacancies.list.status.open')}
                    </button>
                    <button className={secondaryBtn} onClick={() => bulkSetStatus('on_hold')}>
                      {t('app.vacancies.list.status.on_hold')}
                    </button>
                    <button className={secondaryBtn} onClick={() => bulkSetStatus('closed')}>
                      {t('app.vacancies.list.status.closed')}
                    </button>
                  </div>
                  <button className={secondaryBtn} onClick={bulkArchive}>
                    {t('app.vacancies.list.bulk_archive')}
                  </button>
                </>
              }
            />
          ),
          pagination: (
            <div className="mx-4 flex items-center justify-between gap-3">
              <div className="text-slate-500">{t('app.vacancies.list.total', { values: { total: data.total } })}</div>
              <EntityListPagination
                page={page}
                pageSize={limit}
                total={data.total || 0}
                onPageChange={goPage}
                previousLabel="←"
                nextLabel={NEXT_PAGE_GLYPH}
                pageLabel={(p, tp) => t('app.vacancies.list.page', { values: { page: p, total: tp } })}
              />
            </div>
          ),
        }}
      />
    </PageShell>
  )
}