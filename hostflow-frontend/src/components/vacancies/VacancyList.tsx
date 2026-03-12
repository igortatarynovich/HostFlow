import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../../store/useAuth'
import { useI18n } from '../../i18n'
import { patchUserMe } from '../../api/users'
import type { UserSavedView } from '../../api/types'
import { resolveApiBase, settings as clientSettings, DEFAULT_TENANT } from '../../api/client'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'

// Unify button styles with Candidates page
const primaryBtn = 'btn-primary'
const secondaryBtn = 'btn-secondary'

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

function getAuthHeaders() {
  const token =
    (safeStorageGet('access_token') ||
      safeStorageGet('accessToken') ||
      safeStorageGet('token') ||
      '') as string

  const candidates = [
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

async function getJSON<T = any>(path: string, params?: Record<string, any>): Promise<T> {
  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  const url = new URL(cleanPath, API_BASE_URL)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v))
    })
  }
  const res = await fetch(url.toString(), {
    credentials: 'include',
    headers: getAuthHeaders(),
  })
  if (!res.ok) {
    let detail = await res.text()
    try { const j = JSON.parse(detail); detail = j.detail || detail } catch {}
    throw new Error(detail || `HTTP ${res.status}`)
  }
  return res.json()
}

async function patchJSON<T = any>(path: string, body: Record<string, any>): Promise<T> {
  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  const url = new URL(cleanPath, API_BASE_URL).toString()
  const res = await fetch(url, {
    method: 'PATCH',
    credentials: 'include',
    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = await res.text()
    try { const j = JSON.parse(detail); detail = (j as any).detail || detail } catch {}
    throw new Error(detail || `HTTP ${res.status}`)
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
  created_at?: string
  updated_at?: string
  is_archived?: boolean
}

type ListResponse = {
  items: Vacancy[]
  total: number
  limit: number
  offset: number
}

function StatusBadge({ value, archived, label }: { value?: string; archived?: boolean; label: string }) {
  const v = archived ? 'archived' : (value || '')
  const badgeClass = archived
    ? 'badge badge-ghost'
    : v === 'open'
    ? 'badge badge-success'
    : v === 'on_hold'
    ? 'badge badge-warning'
    : v === 'closed'
    ? 'badge badge-error'
    : 'badge'
  return <span className={badgeClass}>{label}</span>
}

// --- small ui helper for sortable headers
function SortHeader({
  children,
  field,
  sort,
  dir,
  onSort,
}: {
  children: React.ReactNode
  field: string
  sort: string
  dir: 'asc' | 'desc'
  onSort: (f: string) => void
}){
  const active = sort === field
  const arrow = !active ? '' : (dir === 'asc' ? '▲' : '▼')
  return (
    <button
      type="button"
      className="w-full px-4 py-3 text-left text-xs font-semibold text-slate-600 transition hover:text-slate-900"
      onClick={() => onSort(field)}
    >
      <span className="inline-flex items-center gap-1.5">{children}{active && <span>{arrow}</span>}</span>
    </button>
  )
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
  const { preferences, updatePreferences } = useAuth()
  const { t } = useI18n()

  const [data, setData] = useState<ListResponse>({ items: [], total: 0, limit: 20, offset: 0 })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refreshTick, setRefreshTick] = useState(0)
  const [selected, setSelected] = useState<string[]>([])
  const statusOptions = useMemo(
    () => [
      { value: '', label: t('app.vacancies.list.status.all') },
      { value: 'open', label: t('app.vacancies.list.status.open') },
      { value: 'on_hold', label: t('app.vacancies.list.status.on_hold') },
      { value: 'closed', label: t('app.vacancies.list.status.closed') },
      { value: 'archived', label: t('app.vacancies.list.status.archived') },
    ],
    [t]
  )
  const statusLabelMap = useMemo(
    () => ({
      open: t('app.vacancies.list.status.open'),
      on_hold: t('app.vacancies.list.status.on_hold'),
      closed: t('app.vacancies.list.status.closed'),
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
  const [visibleCols, setVisibleCols] = useState<{title:boolean; company:boolean; status:boolean; updated:boolean}>({
    title: true, company: true, status: true, updated: true,
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
    const defaultCompanyId = preferences?.defaults?.company_id
    if (defaultCompanyId && !company) {
      const next = new URLSearchParams(search)
      next.set('company', defaultCompanyId)
      next.set('page', '1')
      setSearch(next, { replace: true })
    }
  }, [preferences?.defaults?.company_id, company, search, setSearch])

  // load
  useEffect(() => {
    setLoading(true)
    setError(null)
    getJSON<ListResponse | Vacancy[]>('/vacancies/', params)
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
        setError(
          err?.message === 'HTTP 401' || /Unauthorized|Missing Authorization/i.test(err?.message || '')
            ? t('app.vacancies.list.errors.unauthorized')
            : (err?.message || t('app.vacancies.list.errors.load_failed'))
        )
      })
      .finally(() => {
        setLoading(false)
        setSelected([])
      })
  }, [params, refreshTick, t])


  // client-side сортировка (fallback)
  const items = useMemo(() => {
    const arr = [...(data.items || [])]
    const get = (v: Vacancy, key: string) => {
      if (key === 'title') return (v.title || '').toLowerCase()
      if (key === 'company_name') return (v.company_name || '').toLowerCase()
      if (key === 'status') return (v.is_archived ? 'archived' : (v.status || ''))
      if (key === 'updated_at' || key === 'created_at') return v[key as 'updated_at' | 'created_at'] || ''
      return (v as any)[key] ?? ''
    }
    arr.sort((a,b) => {
      const av = get(a, sort)
      const bv = get(b, sort)
      if (av === bv) return 0
      return (av > bv ? 1 : -1) * (dir === 'asc' ? 1 : -1)
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
      next.set('dir', field === 'created_at' || field === 'updated_at' ? 'desc' : 'asc')
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
      { key: 'updated_at', label: t('app.vacancies.list.col_updated') },
      { key: 'created_at', label: t('app.vacancies.list.col_created') },
    ]
    const rows = items.map(v => ({
      title: v.title || t('app.vacancies.list.untitled'),
      company_name: v.company_name || '',
      status: statusLabel(v.status, v.is_archived),
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

  const bulkSetStatus = async (status: 'open'|'on_hold'|'closed') => {
    if (selected.length === 0) return
    // optimistic UI
    setData(prev => ({...prev, items: (prev.items || []).map(v => selected.includes(v.id) ? {...v, status, is_archived: false} : v)}))
    try{
      await Promise.allSettled(selected.map(id => patchJSON(`/vacancies/${id}`, { status })))
    } catch (_){}
    setSelected([])
    refresh()
  }

  const bulkArchive = async () => {
    if (selected.length === 0) return
    setData(prev => ({...prev, items: (prev.items || []).map(v => selected.includes(v.id) ? {...v, is_archived: true} : v)}))
    try{
      await Promise.allSettled(selected.map(id => patchJSON(`/vacancies/${id}`, { is_archived: true })))
    } catch(_){}
    setSelected([])
    refresh()
  }

  const toggleCol = (k: keyof typeof visibleCols) => setVisibleCols(s => ({ ...s, [k]: !s[k] }))

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
  const visibleColumnCount = (visibleCols.title ? 1 : 0) + (visibleCols.company ? 1 : 0) + (visibleCols.status ? 1 : 0) + (visibleCols.updated ? 1 : 0)
  const tableColSpan = visibleColumnCount + 2

  const vacancyInsights = useMemo(() => {
    const arr = data.items || []
    const open = arr.filter((v) => !v.is_archived && (v.status || '').toLowerCase() === 'open').length
    const closed = arr.filter((v) => !v.is_archived && (v.status || '').toLowerCase() === 'closed').length
    const archived = arr.filter((v) => v.is_archived).length
    return { total: data.total, open, closed, archived }
  }, [data.items, data.total])

  const vacancyHero = (
    <section className="rounded-3xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-6 text-white shadow-card">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <p className="text-2xl font-semibold">{t('app.nav.items.vacancies')}</p>
          <p className="text-sm text-white/80">{t('app.vacancies.list.subtitle')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn-primary bg-white text-brand-700 hover:bg-white/90" onClick={() => navigate('/app/vacancies/new')}>
            {t('app.vacancies.list.new_vacancy')}
          </button>
        </div>
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-white/30 bg-white/10 p-4">
          <div className="text-sm text-white/80">{t('app.vacancies.list.insights.total')}</div>
          <div className="text-3xl font-semibold">{vacancyInsights.total}</div>
        </div>
        <div className="rounded-2xl border border-white/30 bg-white/10 p-4">
          <div className="text-sm text-white/80">{t('app.vacancies.list.insights.open')}</div>
          <div className="text-3xl font-semibold">{vacancyInsights.open}</div>
        </div>
        <div className="rounded-2xl border border-white/30 bg-white/10 p-4">
          <div className="text-sm text-white/80">{t('app.vacancies.list.insights.closed')}</div>
          <div className="text-3xl font-semibold">{vacancyInsights.closed}</div>
        </div>
        <div className="rounded-2xl border border-white/30 bg-white/10 p-4">
          <div className="text-sm text-white/80">{t('app.vacancies.list.insights.archived')}</div>
          <div className="text-3xl font-semibold">{vacancyInsights.archived}</div>
        </div>
      </div>
    </section>
  )

  return (
    <div className="h-full w-full flex flex-col space-y-4">
      {vacancyHero}

      <section className="app-surface space-y-4 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <form onSubmit={onSearch} className="flex flex-1 flex-col gap-3">
            <div className="flex flex-wrap gap-2">
              <input name="q" ref={searchRef} defaultValue={q} placeholder={t('app.vacancies.list.search_placeholder')} className="input w-72 flex-1 min-w-[220px]" />
              <input name="company" defaultValue={company} placeholder={t('app.vacancies.list.company_placeholder')} className="input w-56" />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex flex-wrap items-center gap-2">
                {statusOptions.map((s) => (
                  <button
                    key={s.value || 'all'}
                    type="button"
                    className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${status === s.value ? 'border-brand-600 bg-brand-50 text-brand-800 shadow-sm' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-800'}`}
                    onClick={() => {
                      const next = new URLSearchParams(search)
                      if (!s.value) {
                        next.delete('status')
                      } else {
                        next.set('status', s.value)
                      }
                      next.set('page', '1')
                      setSearch(next, { replace: true })
                    }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <button type="submit" className={secondaryBtn}>{t('common.actions.apply')}</button>
                <button
                  type="button"
                  className={secondaryBtn}
                  onClick={resetFilters}
                  disabled={resetDisabled}
                  title={t('app.vacancies.list.reset_filters_title')}
                >
                  {t('common.actions.reset')}
                </button>
              </div>
            </div>
          </form>
          <div className="flex items-center gap-2">
            <button
              className={secondaryBtn}
              onClick={refresh}
              disabled={loading}
              title={t('app.vacancies.list.refresh_title')}
            >
              {loading ? t('common.loading') : t('common.actions.refresh')}
            </button>
            <button
              className={secondaryBtn}
              onClick={exportCSV}
              title={t('app.vacancies.list.export_csv_title')}
            >{t('app.vacancies.list.export_csv')}</button>
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
                <div className="absolute right-0 z-20 mt-2 w-56 rounded-md border border-slate-200 bg-white p-3 shadow-lg">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t('app.vacancies.list.columns')}</div>
                  <div className="mt-2 space-y-1">
                    <label className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" checked={visibleCols.title} onChange={()=>toggleCol('title')} /> {t('app.vacancies.list.col_title')}</label>
                    <label className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" checked={visibleCols.company} onChange={()=>toggleCol('company')} /> {t('app.vacancies.list.col_company')}</label>
                    <label className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" checked={visibleCols.status} onChange={()=>toggleCol('status')} /> {t('app.vacancies.list.col_status')}</label>
                    <label className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" checked={visibleCols.updated} onChange={()=>toggleCol('updated')} /> {t('app.vacancies.list.col_updated')}</label>
                  </div>
                  <button type="button" className="btn-primary mt-3 w-full" onClick={() => { setActionsMenuOpen(false); saveView() }}>{t('app.vacancies.list.save_view')}</button>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {selected.length > 0 && (
        <div className="app-surface mb-2 flex flex-wrap items-center gap-2 p-3 text-sm">
          <div>{t('app.vacancies.list.bulk_selected', { values: { count: selected.length } })}</div>
          <div className="flex items-center gap-1">
            <span className="text-slate-500">{t('app.vacancies.list.bulk_set_status')}</span>
            <button className={secondaryBtn} onClick={()=>bulkSetStatus('open')}>{t('app.vacancies.list.status.open')}</button>
            <button className={secondaryBtn} onClick={()=>bulkSetStatus('on_hold')}>{t('app.vacancies.list.status.on_hold')}</button>
            <button className={secondaryBtn} onClick={()=>bulkSetStatus('closed')}>{t('app.vacancies.list.status.closed')}</button>
          </div>
          <div className="flex-1" />
          <button className={secondaryBtn} onClick={bulkArchive}>{t('app.vacancies.list.bulk_archive')}</button>
          <button className="btn-secondary" onClick={()=>setSelected([])}>{t('app.vacancies.list.bulk_clear_selection')}</button>
        </div>
      )}

      {/* Saved views row */}
      {views.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-2">
          {views.map((v) => (
            <div key={v.id} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-2 py-1 text-sm shadow-sm">
              <button className="hover:underline" onClick={()=>applyView(v)}>{v.name || t('app.vacancies.list.untitled')}</button>
              <button className="text-slate-400 hover:text-red-500" onClick={()=>removeView(v.id)} title={t('app.vacancies.list.delete_view')}>×</button>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-3">
          <ErrorRecoveryBanner
            info={{
              title: error,
              hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
            }}
            onRetry={() => void load()}
            retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
            compact
          />
        </div>
      )}

      {loading ? (
        <div className="text-sm text-slate-500">{t('app.vacancies.list.loading')}</div>
      ) : (
        <section className="app-surface overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50/90 text-left">
              <tr>
                <th className="w-1 border-b border-r border-slate-200 px-4 py-3">
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} />
                </th>
                {visibleCols.title && (
                  <th className="border-b border-r border-slate-200"><SortHeader field="title" sort={sort} dir={dir} onSort={setSort}>{t('app.vacancies.list.col_title')}</SortHeader></th>
                )}
                {visibleCols.company && (
                  <th className="border-b border-r border-slate-200"><SortHeader field="company_name" sort={sort} dir={dir} onSort={setSort}>{t('app.vacancies.list.col_company')}</SortHeader></th>
                )}
                {visibleCols.status && (
                  <th className="border-b border-r border-slate-200"><SortHeader field="status" sort={sort} dir={dir} onSort={setSort}>{t('app.vacancies.list.col_status')}</SortHeader></th>
                )}
                {visibleCols.updated && (
                  <th className="border-b border-r border-slate-200"><SortHeader field="updated_at" sort={sort} dir={dir} onSort={setSort}>{t('app.vacancies.list.col_updated')}</SortHeader></th>
                )}
                <th className="w-1 border-b border-slate-200 px-4 py-3 text-xs font-semibold text-slate-600">{t('app.vacancies.list.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500" colSpan={tableColSpan}>{t('app.vacancies.list.not_found')}</td>
                </tr>
              )}
              {items.map((v) => (
                <tr key={v.id} className="border-t border-slate-100 hover:bg-slate-50/70 transition">
                  <td className="border-r border-slate-200 px-4 py-3">
                    <input type="checkbox" checked={selected.includes(v.id)} onChange={()=>toggleOne(v.id)} />
                  </td>
                  {visibleCols.title && (
                    <td className="border-r border-slate-200 px-4 py-3 font-medium">
                      <Link className="hover:underline" to={`/app/vacancies/${v.id}`}>
                        {v.title || t('app.vacancies.list.untitled')}
                      </Link>
                    </td>
                  )}
                  {visibleCols.company && (
                    <td className="border-r border-slate-200 px-4 py-3">{v.company_name || '—'}</td>
                  )}
                  {visibleCols.status && (
                    <td className="border-r border-slate-200 px-4 py-3"><StatusBadge value={v.status || ''} archived={v.is_archived} label={statusLabel(v.status, v.is_archived)} /></td>
                  )}
                  {visibleCols.updated && (
                    <td className="border-r border-slate-200 px-4 py-3">{v.updated_at ? new Date(v.updated_at).toLocaleDateString() : (v.created_at ? new Date(v.created_at).toLocaleDateString() : '—')}</td>
                  )}
                  <td className="px-4 py-3">
                    <Link className="btn-secondary btn-sm" to={`/app/vacancies/${v.id}`}>{t('app.vacancies.list.open')}</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <div className="flex items-center justify-between mt-3">
        <div className="text-slate-500">{t('app.vacancies.list.total', { values: { total: data.total } })}</div>
        <div className="flex items-center gap-1">
          <button type="button" onClick={() => goPage(Math.max(1, page - 1))} disabled={page <= 1} className="btn-secondary btn-sm">←</button>
          <span className="px-2 text-sm text-slate-600">{t('app.vacancies.list.page', { values: { page, total: Math.max(1, Math.ceil((data.total || 0) / (data.limit || limit))) } })}</span>
          <button type="button" onClick={() => goPage(Math.min(Math.max(1, Math.ceil((data.total || 0) / (data.limit || limit))), page + 1))} disabled={page >= Math.max(1, Math.ceil((data.total || 0) / (data.limit || limit)))} className="btn-secondary btn-sm">→</button>
        </div>
      </div>
    </div>
  )
}
