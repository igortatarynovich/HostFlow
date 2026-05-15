import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  fetchHrDocumentsExpiring,
  fetchHrDocumentsMissing,
  type HrAssigneeScope,
  type HrDocumentQueueItem,
} from '../../api/hrWorkspace'
import { useI18n } from '../../i18n'
import { humanizeToken } from '../../components/hr/hrEmployeeUiFormat'

type HubView = 'all' | 'missing' | 'expiring' | 'verification'

const VERIFIED_LIKE = new Set([
  'verified',
  'approved',
  'completed',
  'issued',
  'active',
  'registered',
  'not_required',
])

function viewFromPath(pathname: string): HubView {
  if (pathname.includes('/documents/missing')) return 'missing'
  if (pathname.includes('/documents/expiring')) return 'expiring'
  if (pathname.includes('/documents/verification')) return 'verification'
  return 'all'
}

function candidateLabel(row: HrDocumentQueueItem): string {
  const s = row.candidate_snapshot_summary || {}
  const fn = typeof s.first_name === 'string' ? s.first_name : ''
  const ln = typeof s.last_name === 'string' ? s.last_name : ''
  const name = [fn, ln].filter(Boolean).join(' ').trim()
  return name || '—'
}

function formatShort(iso: string | null | undefined): string {
  if (!iso) return '—'
  const ms = Date.parse(iso)
  if (!Number.isFinite(ms)) return iso
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'short' }).format(ms)
  } catch {
    return iso
  }
}

type UnifiedRow = HrDocumentQueueItem & { queue: 'missing' | 'expiring' }

const hubTabClass = ({ isActive }: { isActive: boolean }) => clsx('tab', isActive && 'tab-active')

export default function HrDocumentsHubPage() {
  const { t } = useI18n()
  const location = useLocation()
  const view = viewFromPath(location.pathname)

  const [assigneeScope, setAssigneeScope] = useState<HrAssigneeScope>('team')
  const [horizonDays, setHorizonDays] = useState<7 | 30 | 60 | 90>(30)
  const [expiringStatus, setExpiringStatus] = useState<'all' | 'expired' | 'expiring'>('all')
  const [riskFilter, setRiskFilter] = useState<string>('')
  const [docTypeFilter, setDocTypeFilter] = useState('')
  const [employeeFilter, setEmployeeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [requiredOnly, setRequiredOnly] = useState(false)
  const [groupBy, setGroupBy] = useState<'none' | 'employee' | 'document_type'>('employee')

  const [missing, setMissing] = useState<HrDocumentQueueItem[]>([])
  const [expiring, setExpiring] = useState<HrDocumentQueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const common = { assignee_scope: assigneeScope, limit: 200, offset: 0 }
      const dt = docTypeFilter.trim() || undefined
      const risk = riskFilter.trim() || undefined
      if (view === 'missing') {
        const m = await fetchHrDocumentsMissing({ ...common, document_type: dt })
        setMissing(m.items)
        setExpiring([])
        return
      }
      if (view === 'expiring') {
        const e = await fetchHrDocumentsExpiring({
          ...common,
          horizon_days: horizonDays,
          status: expiringStatus,
          document_type: dt,
          risk,
        })
        setExpiring(e.items)
        setMissing([])
        return
      }
      const e = await fetchHrDocumentsExpiring({
        ...common,
        horizon_days: horizonDays,
        status: 'all',
        document_type: dt,
        risk,
      })
      setExpiring(e.items)
      const m = await fetchHrDocumentsMissing({ ...common, document_type: dt })
      setMissing(m.items)
    } catch (ex: unknown) {
      const e = ex as { response?: { data?: { detail?: string } }; message?: string }
      setErr(e?.response?.data?.detail || e?.message || t('common.errors.request_failed'))
    } finally {
      setLoading(false)
    }
  }, [assigneeScope, docTypeFilter, expiringStatus, horizonDays, riskFilter, t, view])

  useEffect(() => {
    void load()
  }, [load])

  const unified: UnifiedRow[] = useMemo(() => {
    const m = missing.map((r) => ({ ...r, queue: 'missing' as const }))
    const e = expiring.map((r) => ({ ...r, queue: 'expiring' as const }))
    if (view === 'missing') return m
    if (view === 'expiring') return e
    const key = (r: UnifiedRow) => `${r.handoff_id}|${r.document_type}|${r.queue}`
    const seen = new Set<string>()
    const out: UnifiedRow[] = []
    for (const r of [...m, ...e]) {
      const k = key(r)
      if (seen.has(k)) continue
      seen.add(k)
      out.push(r)
    }
    return out
  }, [expiring, missing, view])

  const filtered = useMemo(() => {
    let rows = unified
    if (view === 'verification') {
      rows = rows.filter((r) => !VERIFIED_LIKE.has((r.current_status || '').toLowerCase()))
    }
    if (requiredOnly) rows = rows.filter((r) => r.required)
    const ef = employeeFilter.trim().toLowerCase()
    if (ef) {
      rows = rows.filter((r) => (r.workforce_employee_id || '').toLowerCase().includes(ef))
    }
    const sf = statusFilter.trim().toLowerCase()
    if (sf) {
      rows = rows.filter((r) => (r.current_status || '').toLowerCase().includes(sf))
    }
    return rows
  }, [employeeFilter, requiredOnly, statusFilter, unified, view])

  const grouped = useMemo(() => {
    if (groupBy === 'none') return null as Map<string, UnifiedRow[]> | null
    const m = new Map<string, UnifiedRow[]>()
    for (const r of filtered) {
      const key =
        groupBy === 'employee'
          ? r.workforce_employee_id || t('app.hr.documents_hub.no_employee', { defaultValue: 'No employee link' })
          : r.document_type
      const list = m.get(key) || []
      list.push(r)
      m.set(key, list)
    }
    return m
  }, [filtered, groupBy, t])

  const queueStats = useMemo(() => {
    const missingN = unified.filter((r) => r.queue === 'missing').length
    const expiringN = unified.filter((r) => r.queue === 'expiring').length
    return { missingN, expiringN, shown: filtered.length }
  }, [filtered, unified])

  const p = CRM_APP_PATHS

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-900">
            {t('app.hr.documents_hub.title', { defaultValue: 'HR documents hub' })}
          </h2>
          <p className="mt-1 max-w-4xl text-sm text-slate-600">
            {t('app.hr.documents_hub.subtitle', {
              defaultValue:
                'Operational legal queues over internal HR handoffs — missing requirements, expiries, and verification follow-ups. Not the recruitment documents screen.',
            })}
          </p>
        </div>
        <button type="button" className="btn-secondary btn-sm shrink-0" onClick={() => void load()}>
          {t('common.actions.refresh', { defaultValue: 'Refresh' })}
        </button>
      </div>

      <div className="sticky top-0 z-20 -mx-1 mb-4 space-y-4 border-b border-slate-200/90 bg-gradient-to-b from-brand-50/95 via-white/95 to-white pb-4 pt-1 backdrop-blur-sm">
      <nav
        className="tabs flex-wrap gap-x-1 gap-y-0"
        aria-label={t('app.hr.documents_hub.tabs_aria', { defaultValue: 'Documents hub views' })}
      >
        <NavLink to={p.hrDocuments} end className={hubTabClass}>
          {t('app.hr.documents_hub.tab_all', { defaultValue: 'All' })}
        </NavLink>
        <NavLink to={p.hrDocumentsMissing} className={hubTabClass}>
          {t('app.hr.documents_hub.tab_missing', { defaultValue: 'Missing' })}
        </NavLink>
        <NavLink to={p.hrDocumentsExpiring} className={hubTabClass}>
          {t('app.hr.documents_hub.tab_expiring', { defaultValue: 'Expiring' })}
        </NavLink>
        <NavLink to={p.hrDocumentsVerification} className={hubTabClass}>
          {t('app.hr.documents_hub.tab_verification', { defaultValue: 'Verification' })}
        </NavLink>
      </nav>

      {loading ? <p className="text-sm text-slate-600">{t('common.loading', { defaultValue: 'Loading…' })}</p> : null}
      {err ? <div className="alert-error">{err}</div> : null}

      {!loading && !err ? (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="badge border border-slate-200 font-medium tabular-nums">
            {t('app.hr.documents_hub.stat_shown', { defaultValue: 'Rows: {n}', values: { n: queueStats.shown } })}
          </span>
          <span className="badge border border-amber-100 bg-amber-50/90 font-medium tabular-nums text-amber-950">
            {t('app.hr.documents_hub.stat_missing', { defaultValue: 'Missing queue: {n}', values: { n: queueStats.missingN } })}
          </span>
          <span className="badge border border-brand-100 bg-brand-50/90 font-medium tabular-nums text-brand-900">
            {t('app.hr.documents_hub.stat_expiring', { defaultValue: 'Expiry queue: {n}', values: { n: queueStats.expiringN } })}
          </span>
        </div>
      ) : null}

      <section className="card p-4 sm:p-5">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.hr.documents_hub.filters', { defaultValue: 'Filters' })}
        </div>
        <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="flex flex-col gap-1.5">
            <span className="label mb-0 text-xs text-slate-600">
              {t('app.hr.documents_hub.assignee', { defaultValue: 'Assignee scope' })}
            </span>
            <select
              className="input text-sm"
              value={assigneeScope}
              onChange={(e) => setAssigneeScope(e.target.value as HrAssigneeScope)}
            >
              <option value="team">{t('app.hr.documents_hub.scope_team', { defaultValue: 'Team' })}</option>
              <option value="mine">{t('app.hr.documents_hub.scope_mine', { defaultValue: 'Mine' })}</option>
            </select>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="label mb-0 text-xs text-slate-600">
              {t('app.hr.documents_hub.document_type', { defaultValue: 'Document type' })}
            </span>
            <input
              className="input text-sm"
              value={docTypeFilter}
              onChange={(e) => setDocTypeFilter(e.target.value)}
              placeholder={t('app.hr.documents_hub.document_type_ph', { defaultValue: 'e.g. passport' })}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="label mb-0 text-xs text-slate-600">
              {t('app.hr.documents_hub.employee_id', { defaultValue: 'Employee id contains' })}
            </span>
            <input
              className="input font-mono text-xs"
              value={employeeFilter}
              onChange={(e) => setEmployeeFilter(e.target.value)}
              placeholder="uuid…"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="label mb-0 text-xs text-slate-600">
              {t('app.hr.documents_hub.status_contains', { defaultValue: 'Status contains' })}
            </span>
            <input className="input text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} />
          </label>
          {(view === 'expiring' || view === 'all' || view === 'verification') && (
            <>
              <label className="flex flex-col gap-1.5">
                <span className="label mb-0 text-xs text-slate-600">
                  {t('app.hr.documents_hub.horizon', { defaultValue: 'Expiry horizon (days)' })}
                </span>
                <select
                  className="input text-sm"
                  value={horizonDays}
                  onChange={(e) => setHorizonDays(Number(e.target.value) as 7 | 30 | 60 | 90)}
                >
                  <option value={7}>7</option>
                  <option value={30}>30</option>
                  <option value={60}>60</option>
                  <option value={90}>90</option>
                </select>
              </label>
              {view === 'expiring' ? (
                <label className="flex flex-col gap-1.5">
                  <span className="label mb-0 text-xs text-slate-600">
                    {t('app.hr.documents_hub.expiry_bucket', { defaultValue: 'Expiry bucket' })}
                  </span>
                  <select
                    className="input text-sm"
                    value={expiringStatus}
                    onChange={(e) => setExpiringStatus(e.target.value as 'all' | 'expired' | 'expiring')}
                  >
                    <option value="all">{t('app.hr.documents_hub.bucket_all', { defaultValue: 'All in horizon' })}</option>
                    <option value="expiring">{t('app.hr.documents_hub.bucket_expiring', { defaultValue: 'Expiring' })}</option>
                    <option value="expired">{t('app.hr.documents_hub.bucket_expired', { defaultValue: 'Expired' })}</option>
                  </select>
                </label>
              ) : null}
              <label className="flex flex-col gap-1.5">
                <span className="label mb-0 text-xs text-slate-600">
                  {t('app.hr.documents_hub.risk', { defaultValue: 'Risk' })}
                </span>
                <select className="input text-sm" value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
                  <option value="">{t('app.hr.documents_hub.risk_any', { defaultValue: 'Any' })}</option>
                  <option value="high">{t('app.hr.documents_hub.risk_high', { defaultValue: 'High only' })}</option>
                  <option value="normal">{t('app.hr.documents_hub.risk_normal', { defaultValue: 'Normal' })}</option>
                </select>
              </label>
            </>
          )}
          <label className="flex flex-col gap-1.5 sm:col-span-2">
            <span className="label mb-0 text-xs text-slate-600">
              {t('app.hr.documents_hub.group_by', { defaultValue: 'Group by' })}
            </span>
            <select
              className="input text-sm"
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as 'none' | 'employee' | 'document_type')}
            >
              <option value="employee">{t('app.hr.documents_hub.group_employee', { defaultValue: 'Employee' })}</option>
              <option value="document_type">{t('app.hr.documents_hub.group_doc_type', { defaultValue: 'Document type' })}</option>
              <option value="none">{t('app.hr.documents_hub.group_none', { defaultValue: 'Flat list' })}</option>
            </select>
          </label>
          <label className="flex cursor-pointer items-center gap-2 self-end text-sm text-slate-700 sm:col-span-2">
            <input type="checkbox" checked={requiredOnly} onChange={(e) => setRequiredOnly(e.target.checked)} />
            {t('app.hr.documents_hub.required_only', { defaultValue: 'Required items only' })}
          </label>
        </div>
      </section>
      </div>

      {!loading && !err && filtered.length === 0 ? (
        <p className="text-sm text-slate-600">{t('app.hr.documents_hub.empty', { defaultValue: 'No rows match this view.' })}</p>
      ) : null}

      {!loading && !err && filtered.length > 0
        ? groupBy === 'none' || !grouped
          ? <DocumentQueueTable rows={filtered} t={t} />
          : (
              <div className="space-y-4">
                {[...grouped.entries()].map(([gkey, rows]) => (
                  <section key={gkey} className="card overflow-hidden">
                    <div className="border-b border-slate-200 bg-brand-50/50 px-4 py-3 sm:px-5">
                      <h3 className="text-sm font-semibold text-slate-900">{humanizeToken(gkey)}</h3>
                      <p className="text-xs text-slate-600">
                        {t('app.hr.documents_hub.group_count', { defaultValue: '{n} row(s)', values: { n: rows.length } })}
                      </p>
                    </div>
                    <DocumentQueueTable rows={rows} t={t} embedded />
                  </section>
                ))}
              </div>
            )
        : null}
    </div>
  )
}

function DocumentQueueTable({
  rows,
  t,
  embedded,
}: {
  rows: UnifiedRow[]
  t: (key: string, opts?: { defaultValue?: string; values?: Record<string, string | number> }) => string
  embedded?: boolean
}) {
  const wrapClass = embedded ? 'overflow-x-auto' : 'card overflow-hidden'
  return (
    <div className={wrapClass}>
      <div className="overflow-x-auto">
        <table className="table w-full min-w-[1280px] text-left text-sm">
          <thead>
            <tr>
              <th>{t('app.hr.documents_hub.col_candidate', { defaultValue: 'Candidate' })}</th>
              <th>{t('app.hr.documents_hub.col_document', { defaultValue: 'Document' })}</th>
              <th>{t('app.hr.documents_hub.col_queue', { defaultValue: 'Queue' })}</th>
              <th>{t('app.hr.documents_hub.col_required', { defaultValue: 'Req.' })}</th>
              <th>{t('app.hr.documents_hub.col_status', { defaultValue: 'Status' })}</th>
              <th>{t('app.hr.documents_hub.col_expires', { defaultValue: 'Expires' })}</th>
              <th>{t('app.hr.documents_hub.col_risk', { defaultValue: 'Risk' })}</th>
              <th>{t('app.hr.documents_hub.col_actions', { defaultValue: 'Actions' })}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.handoff_id}-${row.document_type}-${row.queue}-${row.expires_at || 'x'}`}>
                <td className="align-top">
                  <div className="font-medium text-slate-900">{candidateLabel(row)}</div>
                  <div className="font-mono text-xs text-slate-500">{row.handoff_id.slice(0, 8)}…</div>
                </td>
                <td className="align-top font-medium text-slate-900">{humanizeToken(row.document_type)}</td>
                <td className="align-top">
                  <span
                    className={clsx(
                      'inline-flex rounded-full border px-2 py-0.5 text-xs font-medium',
                      row.queue === 'missing'
                        ? 'border-amber-200 bg-amber-50 text-amber-950'
                        : 'border-brand-200 bg-brand-50 text-brand-900',
                    )}
                  >
                    {row.queue === 'missing'
                      ? t('app.hr.documents_hub.queue_missing', { defaultValue: 'Missing' })
                      : t('app.hr.documents_hub.queue_expiring', { defaultValue: 'Expiry' })}
                  </span>
                </td>
                <td className="align-top text-slate-700">{row.required ? '✓' : '—'}</td>
                <td className="align-top">
                  <div className="text-slate-900">{humanizeToken(row.current_status)}</div>
                  {row.snapshot_status ? (
                    <div className="text-xs text-slate-500">
                      {t('app.hr.documents_hub.snapshot', {
                        defaultValue: 'At hire: {s}',
                        values: { s: humanizeToken(row.snapshot_status) },
                      })}
                    </div>
                  ) : null}
                </td>
                <td className="align-top tabular-nums text-slate-700">{formatShort(row.expires_at)}</td>
                <td className="align-top">
                  <span
                    className={clsx(
                      'inline-flex rounded-full border px-2 py-0.5 text-xs font-medium',
                      row.risk === 'high' ? 'border-rose-200 bg-rose-50 text-rose-900' : 'badge border border-slate-200',
                    )}
                  >
                    {humanizeToken(row.risk)}
                  </span>
                </td>
                <td className="align-top">
                  <div className="flex flex-col gap-1.5">
                    {row.workforce_employee_id ? (
                      <Link
                        className="text-xs font-medium text-brand-700 hover:text-brand-900 hover:underline"
                        to={`${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(row.workforce_employee_id)}#hr-employee-linked-documents`}
                      >
                        {t('app.hr.documents_hub.open_employee', { defaultValue: 'Open employee' })}
                      </Link>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                    <Link
                      className="text-xs font-medium text-brand-700 hover:text-brand-900 hover:underline"
                      to={`${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(row.handoff_id)}`}
                    >
                      {t('app.hr.documents_hub.open_handoff', { defaultValue: 'Handoff' })}
                    </Link>
                    <button
                      type="button"
                      disabled
                      className="cursor-not-allowed text-left text-xs text-slate-400"
                      title={t('app.hr.documents_hub.planned_verify', {
                        defaultValue: 'Document verification actions will use workforce APIs in a follow-up.',
                      })}
                    >
                      {t('app.hr.documents_hub.mark_verified', { defaultValue: 'Mark verified' })}
                    </button>
                    <button
                      type="button"
                      disabled
                      className="cursor-not-allowed text-left text-xs text-slate-400"
                      title={t('app.hr.documents_hub.planned_correction', {
                        defaultValue: 'Request correction will open a guided task in a follow-up.',
                      })}
                    >
                      {t('app.hr.documents_hub.request_correction', { defaultValue: 'Request correction' })}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
