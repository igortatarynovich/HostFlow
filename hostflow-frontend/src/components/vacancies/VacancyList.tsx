import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../../store/useAuth'
import { patchUserMe } from '../../api/users'
import type { UserSavedView } from '../../api/types'
import { resolveApiBase, settings as clientSettings, DEFAULT_TENANT } from '../../api/client'
import EntityListBulkBar from '../surfaces/EntityListBulkBar'
import EntityListPagination from '../surfaces/EntityListPagination'
import EntityListShell from '../surfaces/EntityListShell'
import EntityListTableFrame from '../surfaces/EntityListTableFrame'

// Unify button styles with Candidates page
const primaryBtn = 'btn-primary'
const secondaryBtn = "inline-flex items-center gap-2 px-3 py-2 rounded-md border border-gray-300 text-gray-800 bg-white hover:bg-gray-100 active:bg-gray-200 transition-colors cursor-pointer";

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

const STATUSES = [
  { value: '', label: 'Все' },
  { value: 'open', label: 'Открыта' },
  { value: 'on_hold', label: 'На паузе' },
  { value: 'closed', label: 'Закрыта' },
  { value: 'archived', label: 'В архиве' },
]

const STATUS_LABELS: Record<string, string> = {
  open: 'Открыта',
  on_hold: 'На паузе',
  closed: 'Закрыта',
  archived: 'В архиве',
}

function StatusBadge({ value, archived }: { value?: string; archived?: boolean }) {
  const v = archived ? 'archived' : (value || '')
  const label = STATUS_LABELS[v] || '—'
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
    <button type="button" className="px-4 py-3 text-left w-full select-none hover:underline" onClick={()=>onSort(field)}>
      <span className="inline-flex items-center gap-1">{children}{active && <span>{arrow}</span>}</span>
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

  const [data, setData] = useState<ListResponse>({ items: [], total: 0, limit: 20, offset: 0 })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refreshTick, setRefreshTick] = useState(0)
  const [selected, setSelected] = useState<string[]>([])

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
    if (company) p.company = company
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
        setError(err?.message === 'HTTP 401' || /Unauthorized|Missing Authorization/i.test(err?.message || '')
          ? 'Неавторизовано: войдите в систему и повторите.'
          : (err?.message || 'Не удалось загрузить вакансии'))
      })
      .finally(() => {
        setLoading(false)
        setSelected([])
      })
  }, [params, refreshTick])


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
      { key: 'title', label: 'Название' },
      { key: 'company_name', label: 'Компания' },
      { key: 'status', label: 'Статус' },
      { key: 'updated_at', label: 'Обновлена' },
      { key: 'created_at', label: 'Создана' },
    ]
    const rows = items.map(v => ({
      title: v.title || '(без названия)',
      company_name: v.company_name || '',
      status: v.is_archived ? 'В архиве' : (STATUS_LABELS[v.status || ''] || ''),
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
    const name = window.prompt('Название вида:')?.trim()
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

  const tableStatus = loading ? 'loading' : error ? 'error' : items.length === 0 ? 'empty' : 'ready'

  return (
    <EntityListShell
      className="h-full w-full space-y-4"
      resourceLabel="Vacancies"
      selection={{
        selectedCount: selected.length,
        onClearSelection: () => setSelected([]),
      }}
      zones={{
        toolbar: (
          <>
<div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <form onSubmit={onSearch} className="flex flex-1 flex-col gap-3">
            <div className="flex flex-wrap gap-2">
              <input name="q" ref={searchRef} defaultValue={q} placeholder="Поиск… (⌘K)" className="input w-72 flex-1 min-w-[220px]" />
              <input name="company" defaultValue={company} placeholder="Компания…" className="input w-56" />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex flex-wrap items-center gap-2">
                {STATUSES.map((s) => (
                  <button
                    key={s.value || 'all'}
                    type="button"
                    className={`rounded-full border px-3 py-1 text-sm transition ${status === s.value ? 'border-brand-600 bg-brand-50 text-brand-800' : 'border-gray-200 text-gray-600 hover:border-gray-300 hover:text-gray-800'}`}
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
                <button type="submit" className={secondaryBtn}>Применить</button>
                <button
                  type="button"
                  className={secondaryBtn}
                  onClick={resetFilters}
                  disabled={resetDisabled}
                  title="Очистить поля фильтров"
                >
                  Сбросить
                </button>
              </div>
            </div>
          </form>

          <div className="flex items-center gap-2 self-end lg:self-start">
            <button
              className={secondaryBtn}
              onClick={refresh}
              disabled={loading}
              title="Обновить список вакансий"
            >
              {loading ? 'Обновление…' : 'Обновить'}
            </button>
            <button
              className={secondaryBtn}
              onClick={exportCSV}
              title="Выгрузить таблицу в CSV"
            >Экспорт CSV</button>
            <div className="relative" ref={actionsMenuRef}>
              <button
                type="button"
                className={secondaryBtn}
                onClick={() => setActionsMenuOpen((prev) => !prev)}
                title="Дополнительные действия"
              >
                ⋯
              </button>
              {actionsMenuOpen && (
                <div className="absolute right-0 z-20 mt-2 w-56 rounded-md border border-gray-200 bg-white p-3 shadow-lg">
                  <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">Колонки</div>
                  <div className="mt-2 space-y-1">
                    <label className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" checked={visibleCols.title} onChange={()=>toggleCol('title')} /> Название</label>
                    <label className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" checked={visibleCols.company} onChange={()=>toggleCol('company')} /> Компания</label>
                    <label className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" checked={visibleCols.status} onChange={()=>toggleCol('status')} /> Статус</label>
                    <label className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" checked={visibleCols.updated} onChange={()=>toggleCol('updated')} /> Обновлена</label>
                  </div>
                  <button type="button" className="btn-primary mt-3 w-full" onClick={() => { setActionsMenuOpen(false); saveView() }}>Сохранить как вид</button>
                </div>
              )}
            </div>
            <button className={primaryBtn} onClick={()=>navigate('/app/vacancies/new')}>Новая вакансия</button>
          </div>
        </div>
      </div>
{/* Saved views row */}
      {views.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-2">
          {views.map((v) => (
            <div key={v.id} className="inline-flex items-center gap-2 card px-2 py-1 text-sm">
              <button className="hover:underline" onClick={()=>applyView(v)}>{v.name || 'Без названия'}</button>
              <button className="text-gray-400 hover:text-red-500" onClick={()=>removeView(v.id)} title="Удалить">×</button>
            </div>
          ))}
        </div>
      )}
          </>
        ),
        table: (
          <>
{error && (
        <div className="mb-3">
          <div className="alert alert-error"><span>{error}</span></div>
        </div>
      )}
            <EntityListTableFrame
              status={tableStatus}
              loading={<div className="text-sm text-gray-500">Загружаем список вакансий…</div>}
              empty={<p className="px-4 py-8 text-center text-gray-500">Вакансии не найдены</p>}
              error={<div className="alert alert-error"><span>{error}</span></div>}
              table={
<div className="card w-full overflow-auto">
          <table className="min-w-full text-sm table-auto">
            <thead>
              <tr className="bg-gray-50 text-left">
                <th className="px-4 py-3 w-1">
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} />
                </th>
                {visibleCols.title && (
                  <th><SortHeader field="title" sort={sort} dir={dir} onSort={setSort}>Название</SortHeader></th>
                )}
                {visibleCols.company && (
                  <th><SortHeader field="company_name" sort={sort} dir={dir} onSort={setSort}>Компания</SortHeader></th>
                )}
                {visibleCols.status && (
                  <th><SortHeader field="status" sort={sort} dir={dir} onSort={setSort}>Статус</SortHeader></th>
                )}
                {visibleCols.updated && (
                  <th><SortHeader field="updated_at" sort={sort} dir={dir} onSort={setSort}>Обновлена</SortHeader></th>
                )}
                <th className="px-4 py-3 w-1">Действия</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td className="px-4 py-8 text-center text-gray-500" colSpan={6}>Вакансии не найдены</td>
                </tr>
              )}
              {items.map((v) => (
                <tr key={v.id} className="border-t">
                  <td className="px-4 py-3">
                    <input type="checkbox" checked={selected.includes(v.id)} onChange={()=>toggleOne(v.id)} />
                  </td>
                  {visibleCols.title && (
                    <td className="px-4 py-3 font-medium">
                      <Link className="hover:underline" to={`/app/vacancies/${v.id}`}>
                        {v.title || '(без названия)'}
                      </Link>
                    </td>
                  )}
                  {visibleCols.company && (
                    <td className="px-4 py-3">{v.company_name || '—'}</td>
                  )}
                  {visibleCols.status && (
                    <td className="px-4 py-3"><StatusBadge value={v.is_archived ? 'archived' : (v.status || '')} /></td>
                  )}
                  {visibleCols.updated && (
                    <td className="px-4 py-3">{v.updated_at ? new Date(v.updated_at).toLocaleDateString() : (v.created_at ? new Date(v.created_at).toLocaleDateString() : '—')}</td>
                  )}
                  <td className="px-4 py-3">
                    <Link className="btn-ghost btn-sm hover:bg-gray-100 focus:ring-2 focus:ring-blue-200" to={`/app/vacancies/${v.id}`}>Открыть</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
              }
            />
          </>
        ),
        bulkBar: (
          <EntityListBulkBar
            selectedCount={selected.length}
            onClearSelection={() => setSelected([])}
            selectedLabel={(count) => (
              <>
                Выбрано: <span className="font-medium">{count}</span>
              </>
            )}
            clearLabel="Снять выделение"
            actions={
              <>
                <div className="flex items-center gap-1">
                  <span className="text-gray-500">Перевести в статус:</span>
                  <button className={secondaryBtn} onClick={() => bulkSetStatus('open')}>Открыта</button>
                  <button className={secondaryBtn} onClick={() => bulkSetStatus('on_hold')}>На паузе</button>
                  <button className={secondaryBtn} onClick={() => bulkSetStatus('closed')}>Закрыта</button>
                </div>
                <button className={secondaryBtn} onClick={bulkArchive}>В архив</button>
              </>
            }
          />
        ),
        pagination: (
          <div className="flex items-center justify-between gap-3">
            <div className="text-gray-500">Всего: {data.total}</div>
            <EntityListPagination
              page={page}
              pageSize={limit}
              total={data.total || 0}
              onPageChange={goPage}
              previousLabel="←"
              nextLabel="→"
              pageLabel={(p, tp) => `Стр. ${p} / ${tp}`}
            />
          </div>
        ),
      }}
    />
  )
}
