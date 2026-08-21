import React, { useEffect, useMemo, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
import { PageShell, PageShellHeader } from '../layout'
import {
  Button,
  EmptyState,
  ListWorkspace,
  StatusBadge,
  listQuerySignature,
  sortApiField,
  useListWorkspace,
  type ListColumnDef,
  type ListDefinition,
  type ListQueryState,
  type ListSavedViewRecord,
  type StatusBadgeSemantic,
} from '../ui'
import { ContextHelp } from '../help/ContextHelp'

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

function vacancyStatusSemantic(value?: string, archived?: boolean): StatusBadgeSemantic {
  if (archived) return 'neutral'
  const v = (value || '').toLowerCase()
  if (v === 'open') return 'success'
  if (v === 'on_hold' || v === 'paused') return 'warning'
  if (v === 'closed') return 'danger'
  if (v === 'filled') return 'info'
  if (v === 'cancelled') return 'neutral'
  return 'neutral'
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

function snapshotToSavedView(view: ListSavedViewRecord): UserSavedView {
  return {
    id: view.id,
    name: view.name,
    filters: view.query,
    is_default: view.isDefault,
  }
}

function savedViewToRecord(view: UserSavedView): ListSavedViewRecord {
  const query: Record<string, string> = {}
  for (const [key, value] of Object.entries(view.filters ?? {})) {
    if (value === undefined || value === null || value === '') continue
    query[key] = String(value)
  }
  return { id: view.id, name: view.name || '', isDefault: view.is_default, query }
}

function vacancyApiParams(query: ListQueryState, definition: ListDefinition<Vacancy>) {
  const status = query.filters.status || ''
  const company = query.filters.company || ''
  const params: Record<string, string | number> = {
    limit: query.pageSize,
    offset: (query.page - 1) * query.pageSize,
    order_by: sortApiField(definition, query.sortColumnId),
    desc: query.sortDirection === 'desc' ? 1 : 0,
  }
  if (query.q) params.q = query.q
  if (status) params.status = status
  if (company) params.company_id = company
  if (status.toLowerCase() === 'archived') params.include_archived = 1
  return params
}

export default function VacancyList() {
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

  const views = useMemo(
    () => (preferences?.saved_views?.vacancies ?? []).map(savedViewToRecord),
    [preferences?.saved_views?.vacancies],
  )
  const candidateViews = useMemo(
    () => preferences?.saved_views?.candidates ?? [],
    [preferences?.saved_views?.candidates],
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
    [t],
  )
  const statusLabel = useCallback(
    (value?: string, archived?: boolean) => {
      const key = archived ? 'archived' : (value || '')
      return statusLabelMap[key as keyof typeof statusLabelMap] || t('common.labels.not_available')
    },
    [statusLabelMap, t],
  )

  const formatLastCandidateActivity = useCallback(
    (iso: string | null | undefined) => {
      if (!iso) return '—'
      try {
        return formatDistanceToNow(new Date(iso), { addSuffix: true, locale: dateFnsLocale })
      } catch {
        return '—'
      }
    },
    [dateFnsLocale],
  )

  const syncVacancyViews = useCallback(
    async (next: UserSavedView[]) => {
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
    },
    [candidateViews, updatePreferences],
  )

  const refresh = () => setRefreshTick((tick) => tick + 1)

  const bulkSetStatus = useCallback(
    async (ids: string[], status: 'open' | 'on_hold' | 'closed' | 'filled' | 'cancelled') => {
      if (ids.length === 0) return
      setData((prev) => ({
        ...prev,
        items: (prev.items || []).map((row) => (ids.includes(row.id) ? { ...row, status, is_archived: false } : row)),
      }))
      try {
        await Promise.allSettled(
          ids.map((id) => {
            const row = (data.items || []).find((item) => item.id === id)
            const tenantForRow = String((row as { tenant_id?: string } | undefined)?.tenant_id || '').trim() || effectiveTenantId
            return patchJSON(`/vacancies/${id}`, { status }, tenantForRow)
          }),
        )
      } catch {
        /* refresh below */
      }
      refresh()
    },
    [data.items, effectiveTenantId],
  )

  const bulkArchive = useCallback(
    async (ids: string[]) => {
      if (ids.length === 0) return
      setData((prev) => ({
        ...prev,
        items: (prev.items || []).map((row) => (ids.includes(row.id) ? { ...row, is_archived: true } : row)),
      }))
      try {
        await Promise.allSettled(
          ids.map((id) => {
            const row = (data.items || []).find((item) => item.id === id)
            const tenantForRow = String((row as { tenant_id?: string } | undefined)?.tenant_id || '').trim() || effectiveTenantId
            return patchJSON(`/vacancies/${id}`, { is_archived: true }, tenantForRow)
          }),
        )
      } catch {
        /* refresh below */
      }
      refresh()
    },
    [data.items, effectiveTenantId],
  )

  const stop = (event: React.MouseEvent) => event.stopPropagation()

  const vacancyColumns: ListColumnDef<Vacancy>[] = useMemo(
    () => [
      {
        id: 'title',
        fieldId: 'title',
        kind: 'text',
        label: t('app.vacancies.list.col_title'),
        sortable: true,
        cellClassName: 'font-medium',
        cell: (row) => (
          <Link className="text-brand-700 hover:underline" to={`${CRM_APP_PATHS.vacancies}/${row.id}`} onClick={stop}>
            {row.title || t('app.vacancies.list.untitled')}
          </Link>
        ),
      },
      {
        id: 'company',
        fieldId: 'company_id',
        kind: 'ref',
        sortField: 'company_name',
        label: t('app.vacancies.list.col_company'),
        sortable: true,
        cell: (row) => row.company_name || '—',
      },
      {
        id: 'status',
        fieldId: 'status',
        kind: 'enum',
        label: t('app.vacancies.list.col_status'),
        sortable: true,
        cell: (row) => (
          <StatusBadge
            label={statusLabel(row.status, row.is_archived)}
            semantic={vacancyStatusSemantic(row.status, row.is_archived)}
          />
        ),
      },
      {
        id: 'candidates',
        fieldId: 'candidate_count',
        kind: 'number',
        label: t('app.vacancies.list.col_candidates'),
        sortable: true,
        defaultSortDirection: 'desc',
        align: 'right',
        tabularNums: true,
        cell: (row) => (
          <Link
            className="font-medium text-brand-700 hover:underline"
            to={`${CRM_APP_PATHS.vacancies}/${row.id}/candidates`}
            onClick={stop}
          >
            {row.candidate_count ?? 0}
          </Link>
        ),
      },
      {
        id: 'headcount',
        fieldId: 'headcount_target',
        kind: 'number',
        label: t('app.vacancies.list.col_headcount'),
        sortable: true,
        defaultSortDirection: 'desc',
        align: 'right',
        tabularNums: true,
        cellClassName: 'text-slate-700',
        cell: (row) =>
          row.headcount_target != null && row.headcount_target > 0 ? (
            <span title={t('app.vacancies.list.headcount_title')}>
              {row.candidate_count ?? 0}/{row.headcount_target}
            </span>
          ) : (
            '—'
          ),
      },
      {
        id: 'profile',
        fieldId: 'candidate_profile_name',
        kind: 'text',
        label: t('app.vacancies.list.col_profile'),
        sortable: true,
        defaultHidden: true,
        cellClassName: 'text-slate-600',
        cell: (row) => row.candidate_profile_name || '—',
      },
      {
        id: 'lastActivity',
        fieldId: 'last_candidate_activity_at',
        kind: 'datetime',
        label: t('app.vacancies.list.col_last_activity'),
        sortable: true,
        defaultSortDirection: 'desc',
        cellClassName: 'text-slate-600',
        cell: (row) => formatLastCandidateActivity(row.last_candidate_activity_at),
      },
      {
        id: 'updated',
        fieldId: 'updated_at',
        kind: 'datetime',
        sortField: 'updated_at',
        label: t('app.vacancies.list.col_updated'),
        sortable: true,
        defaultSortDirection: 'desc',
        cell: (row) =>
          row.updated_at
            ? new Date(row.updated_at).toLocaleDateString()
            : row.created_at
              ? new Date(row.created_at).toLocaleDateString()
              : '—',
      },
    ],
    [formatLastCandidateActivity, statusLabel, t],
  )

  const persistViews = useCallback(
    async (_view: ListSavedViewRecord | string, next: ListSavedViewRecord[]) => {
      await syncVacancyViews(next.map(snapshotToSavedView))
    },
    [syncVacancyViews],
  )

  const definition: ListDefinition<Vacancy> = useMemo(
    () => ({
      resourceId: 'vacancies',
      density: 'comfortable',
      pagination: { mode: 'paged', pageSize: 20 },
      search: { enabled: true, debounceMs: 300 },
      filters: [
        {
          fieldId: 'company',
          kind: 'ref',
          label: t('app.vacancies.list.col_company'),
          urlKey: 'company',
          queryKey: 'company_id',
          widget: 'text',
          placeholder: t('app.vacancies.list.company_placeholder'),
        },
        {
          fieldId: 'status',
          kind: 'enum',
          label: t('app.vacancies.list.col_status'),
          widget: 'chips',
          options: [
            { value: '', label: t('app.vacancies.list.status.all') },
            { value: 'open', label: t('app.vacancies.list.status.open') },
            { value: 'on_hold', label: t('app.vacancies.list.status.on_hold') },
            { value: 'closed', label: t('app.vacancies.list.status.closed') },
            { value: 'filled', label: t('app.vacancies.list.status.filled') },
            { value: 'cancelled', label: t('app.vacancies.list.status.cancelled') },
            { value: 'archived', label: t('app.vacancies.list.status.archived') },
          ],
        },
      ],
      sort: { defaultColumnId: 'updated', defaultDirection: 'desc' },
      selection: { enabled: true },
      columns: vacancyColumns,
      bulkActions: [
        {
          id: 'status-open',
          label: t('app.vacancies.list.status.open'),
          groupId: 'status',
          groupLabel: t('app.vacancies.list.bulk_set_status'),
          onAction: (ids) => void bulkSetStatus(ids, 'open'),
        },
        {
          id: 'status-on-hold',
          label: t('app.vacancies.list.status.on_hold'),
          groupId: 'status',
          groupLabel: t('app.vacancies.list.bulk_set_status'),
          onAction: (ids) => void bulkSetStatus(ids, 'on_hold'),
        },
        {
          id: 'status-closed',
          label: t('app.vacancies.list.status.closed'),
          groupId: 'status',
          groupLabel: t('app.vacancies.list.bulk_set_status'),
          onAction: (ids) => void bulkSetStatus(ids, 'closed'),
        },
        {
          id: 'archive',
          label: t('app.vacancies.list.bulk_archive'),
          onAction: (ids) => void bulkArchive(ids),
        },
      ],
      savedViews: {
        enabled: true,
        views,
        onSave: persistViews,
        onRemove: persistViews,
      },
      representations: ['table'],
      defaultRepresentation: 'table',
      copy: {
        searchPlaceholder: t('app.vacancies.list.search_placeholder'),
        resetLabel: t('common.actions.reset'),
        saveViewLabel: t('app.vacancies.list.save_view'),
        saveViewPrompt: t('app.vacancies.list.view_name_prompt'),
        columnsLabel: t('app.vacancies.list.columns'),
        untitledViewLabel: t('app.vacancies.list.untitled'),
        removeViewLabel: t('app.vacancies.list.delete_view'),
        bulkSelectedLabel: (count) => t('app.vacancies.list.bulk_selected', { values: { count } }),
        bulkClearLabel: t('app.vacancies.list.bulk_clear_selection'),
        previousPageLabel: '←',
        nextPageLabel: NEXT_PAGE_GLYPH,
        pageLabel: (page, totalPages) => t('app.vacancies.list.page', { values: { page, total: totalPages } }),
        paginationSummary: (total) => t('app.vacancies.list.total', { values: { total } }),
      },
    }),
    [bulkArchive, bulkSetStatus, persistViews, t, vacancyColumns, views],
  )

  const role = String(me?.role || '').trim().toLowerCase()
  const initialFilters = useMemo(() => {
    if (role === 'superadmin') return undefined
    const companyId = preferences?.defaults?.company_id
    return companyId ? { company: companyId } : undefined
  }, [preferences?.defaults?.company_id, role])

  const list = useListWorkspace(definition, { initialFilters })

  const querySignature = listQuerySignature(list.query)

  useEffect(() => {
    const params = vacancyApiParams(list.query, definition)
    setLoading(true)
    setError(null)
    getJSON<ListResponse | Vacancy[]>('/vacancies/', params, effectiveTenantId)
      .then((payload) => {
        if (Array.isArray(payload)) {
          setData({ items: payload, total: payload.length, limit: list.query.pageSize, offset: params.offset as number })
        } else {
          setData({
            items: payload.items ?? [],
            total: payload.total ?? 0,
            limit: payload.limit ?? list.query.pageSize,
            offset: payload.offset ?? (params.offset as number),
          })
        }
      })
      .catch((err: { message?: string }) => {
        console.error('[vacancies/list] failed', err)
        const unauthorized =
          err?.message === 'HTTP 401' || /Unauthorized|Missing Authorization/i.test(err?.message || '')
        if (unauthorized) {
          setError({
            title: t('app.vacancies.list.errors.unauthorized'),
            hint: t('app.common.retry_hint'),
          })
        } else if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.vacancies.list.errors.load_failed'))) {
          setError(null)
        } else {
          setError(getFriendlyErrorInfo(err, t('app.vacancies.list.errors.load_failed'), t))
        }
      })
      .finally(() => {
        setLoading(false)
      })
    // Fetch follows platform query signature, not definition object identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveTenantId, planLimitModal, querySignature, refreshTick, t])

  const items = useMemo(() => {
    const rows = [...(data.items || [])]
    const sortKey = sortApiField(definition, list.query.sortColumnId)
    const get = (row: Vacancy, key: string) => {
      if (key === 'title') return (row.title || '').toLowerCase()
      if (key === 'company_name') return (row.company_name || '').toLowerCase()
      if (key === 'status') return row.is_archived ? 'archived' : (row.status || '')
      if (key === 'updated_at' || key === 'created_at') return row[key] || ''
      if (key === 'candidate_count') return Number(row.candidate_count ?? 0)
      if (key === 'headcount_target') return Number(row.headcount_target ?? 0)
      if (key === 'last_candidate_activity_at') return row.last_candidate_activity_at || ''
      if (key === 'candidate_profile_name') return (row.candidate_profile_name || '').toLowerCase()
      return (row as Record<string, unknown>)[key] ?? ''
    }
    rows.sort((left, right) => {
      const av = get(left, sortKey)
      const bv = get(right, sortKey)
      if (av < bv) return list.query.sortDirection === 'asc' ? -1 : 1
      if (av > bv) return list.query.sortDirection === 'asc' ? 1 : -1
      return 0
    })
    return rows
  }, [data.items, definition, list.query.sortColumnId, list.query.sortDirection])

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
    const rows = items.map((row) => ({
      title: row.title || t('app.vacancies.list.untitled'),
      company_name: row.company_name || '',
      status: statusLabel(row.status, row.is_archived),
      candidate_count: String(row.candidate_count ?? 0),
      headcount_target:
        row.headcount_target != null && row.headcount_target > 0 ? String(row.headcount_target) : '',
      candidate_profile_name: row.candidate_profile_name || '',
      last_candidate_activity_at: row.last_candidate_activity_at
        ? new Date(row.last_candidate_activity_at).toLocaleString()
        : '',
      updated_at: row.updated_at ? new Date(row.updated_at).toLocaleString() : '',
      created_at: row.created_at ? new Date(row.created_at).toLocaleString() : '',
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
          title={
            <span className="inline-flex items-center gap-1.5">
              {t('app.nav.items.vacancies', { defaultValue: 'Vacancies' })}
              <ContextHelp term="vacancy" />
            </span>
          }
          primaryAction={
            <Link to={CRM_APP_PATHS.vacancyNew} className="btn-primary btn-sm">
              {t('app.vacancies.list.new_vacancy')}
            </Link>
          }
        />
      </PageShellHeader>

      <ListWorkspace
        className="min-h-0 flex-1"
        controller={list}
        rows={items}
        rowKey={(row) => row.id}
        total={data.total || 0}
        loading={loading}
        error={errorBanner}
        emptyState={
          <EmptyState
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
        }
        toolbarActions={
          <>
            <Button type="button" variant="secondary" size="sm" onClick={refresh} disabled={loading} title={t('app.vacancies.list.refresh_title')}>
              {loading ? t('common.loading') : t('common.actions.refresh')}
            </Button>
            <Button type="button" variant="secondary" size="sm" onClick={exportCSV} title={t('app.vacancies.list.export_csv_title')}>
              {t('app.vacancies.list.export_csv')}
            </Button>
          </>
        }
        onRowClick={(row) => navigate(`${CRM_APP_PATHS.vacancies}/${row.id}`)}
        ariaLabel={t('app.nav.items.vacancies')}
      />
    </PageShell>
  )
}

