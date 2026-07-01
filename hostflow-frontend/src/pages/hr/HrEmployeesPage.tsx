import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import {
  createWorkforceEmployee,
  listWorkforceEmployeesDirectory,
  type WorkforceEmployeeDirectoryRow,
} from '../../api/workforce'
import { usePermissions } from '../../hooks/usePermissions'
import { useToast } from '../../components/Toast'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { HrVerificationProgressBadge } from '../../components/hr/HrVerificationProgressBadge'

const hrEmployeePath = (id: string, hash?: string) =>
  `${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(id)}${hash ? `#${hash.replace(/^#/, '')}` : ''}`

const STATUS_OPTIONS = [
  '',
  'onboarding',
  'active',
  'on_sick_leave',
  'on_vacation',
  'on_leave',
  'suspended',
  'contract_ending',
  'terminated',
] as const

const COMPLIANCE_OPTIONS = ['', 'compliant', 'missing_docs', 'expiring_docs', 'blocked', 'suspended'] as const

const RISK_OPTIONS = ['', 'none', 'low', 'medium', 'high', 'critical'] as const

function formatShortDate(value: string | null | undefined): string {
  if (value == null || value === '') return ''
  const ms = Date.parse(value)
  if (Number.isNaN(ms)) return value
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'short' }).format(ms)
  } catch {
    return value
  }
}

function isHighRisk(level: string | null | undefined): boolean {
  const k = (level || '').toLowerCase()
  return k === 'high' || k === 'critical'
}

function eligibilityTone(status: string | null | undefined): string {
  const s = String(status || '').toLowerCase()
  if (s.includes('block') || s.includes('suspend')) return 'border-rose-200 bg-rose-50 text-rose-800'
  if (s.includes('missing') || s.includes('expir')) return 'border-amber-200 bg-amber-50 text-amber-900'
  return 'border-emerald-200 bg-emerald-50 text-emerald-800'
}

function statusTone(status: string | null | undefined): string {
  const s = String(status || '').toLowerCase()
  if (s === 'active') return 'border-emerald-200 bg-emerald-50 text-emerald-800'
  if (s.includes('suspend') || s.includes('terminated')) return 'border-rose-200 bg-rose-50 text-rose-800'
  return 'border-slate-200 bg-slate-50 text-slate-800'
}

function deriveNextAction(r: WorkforceEmployeeDirectoryRow): string {
  const review = String(r.hr_review_status || '').toLowerCase()
  if (review && review !== 'approved_for_employment') return 'Complete HR verification'
  if ((r.missing_documents_count || 0) > 0) return 'Upload missing documents'
  if ((r.expiring_documents_count || 0) > 0) return 'Renew expiring documents'
  if (String(r.compliance_status || '').toLowerCase().includes('block')) return 'Resolve compliance blockers'
  if (String(r.status || '').toLowerCase() === 'onboarding') return 'Complete HR review'
  return 'Ready for operational action'
}

export default function HrEmployeesPage() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const { notify } = useToast()
  const [items, setItems] = useState<WorkforceEmployeeDirectoryRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [nameDraft, setNameDraft] = useState('')

  const [status, setStatus] = useState('')
  const [complianceStatus, setComplianceStatus] = useState('')
  const [riskLevel, setRiskLevel] = useState('')
  const [missingOnly, setMissingOnly] = useState(false)
  const [expiringOnly, setExpiringOnly] = useState(false)
  const [searchInput, setSearchInput] = useState('')
  const [searchDebounced, setSearchDebounced] = useState('')
  const pageSize = 200

  useEffect(() => {
    const tmr = window.setTimeout(() => setSearchDebounced(searchInput.trim()), 350)
    return () => window.clearTimeout(tmr)
  }, [searchInput])

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const page = await listWorkforceEmployeesDirectory({
        status: status || undefined,
        compliance_status: complianceStatus || undefined,
        risk_level: riskLevel || undefined,
        missing_docs: missingOnly || undefined,
        expiring_docs: expiringOnly || undefined,
        search: searchDebounced || undefined,
        limit: pageSize,
        offset: 0,
      })
      setItems(page.items)
      setTotal(page.total)
    } catch (e: unknown) {
      const detail =
        typeof e === 'object' && e !== null && 'response' in e
          ? (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
          : null
      const msg =
        typeof detail === 'string'
          ? detail
          : typeof e === 'object' && e !== null && 'message' in e && typeof (e as Error).message === 'string'
            ? (e as Error).message
            : t('common.errors.request_failed', { defaultValue: 'Request failed' })
      setErr(msg)
      setItems([])
      setTotal(0)
      notify({
        variant: 'error',
        title: t('app.nav.hr.employees.toast_load_error', { defaultValue: 'Could not load employees' }),
      })
    } finally {
      setLoading(false)
    }
  }, [
    complianceStatus,
    expiringOnly,
    missingOnly,
    notify,
    riskLevel,
    searchDebounced,
    status,
    t,
  ])

  useEffect(() => {
    if (can('workforce.view')) void load()
  }, [can, load])

  const onCreate = async () => {
    const display_name = nameDraft.trim()
    if (!display_name) {
      notify({
        variant: 'error',
        title: t('app.nav.hr.employees.name_required', { defaultValue: 'Enter a name' }),
      })
      return
    }
    setCreating(true)
    try {
      await createWorkforceEmployee({ display_name, status: 'onboarding' })
      setNameDraft('')
      notify({
        variant: 'success',
        title: t('app.nav.hr.employees.created', { defaultValue: 'Employee created' }),
      })
      await load()
    } catch {
      notify({
        variant: 'error',
        title: t('app.nav.hr.employees.create_error', { defaultValue: 'Could not create employee' }),
      })
    } finally {
      setCreating(false)
    }
  }

  const dash = t('app.nav.hr.employees.dash', { defaultValue: '—' })

  const rangeLabel = useMemo(() => {
    if (total === 0) return null
    const from = 1
    const to = items.length
    return t('app.nav.hr.employees.directory_total', { from, to, total, defaultValue: '{{from}}–{{to}} of {{total}}' })
  }, [items.length, t, total])

  const stats = useMemo(() => {
    const high = items.filter((r) => isHighRisk(r.risk_level)).length
    const missingSum = items.reduce((a, r) => a + (r.missing_documents_count || 0), 0)
    return { high, missingSum, shown: items.length, total }
  }, [items, total])

  if (!can('workforce.view')) {
    return (
      <div className="p-6 text-sm text-slate-600">
        {t('app.nav.hr.employees.forbidden', { defaultValue: 'You do not have access to the HR workspace.' })}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-900">
            {t('app.nav.hr.employees.heading', { defaultValue: 'Employees' })}
          </h2>
          <p className="mt-1 max-w-4xl text-sm text-slate-600">
            {t('app.nav.hr.employees.subtitle_directory', {
              defaultValue:
                'HR directory from GET /api/v1/workforce/employees/directory (read-model: employment, compliance, risk).',
            })}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.hrDocuments}>
            {t('app.nav.hr.employees.quick_hub', { defaultValue: 'Documents hub' })}
          </Link>
          <button type="button" className="btn-secondary btn-sm shrink-0" onClick={() => void load()}>
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
      </div>

      <div className="sticky top-0 z-20 -mx-1 mb-2 space-y-4 border-b border-slate-200/90 bg-gradient-to-b from-brand-50/95 via-white/95 to-white pb-4 pt-1 backdrop-blur-sm">
        {!loading && !err ? (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="badge border border-slate-200 font-medium tabular-nums">
              {t('app.nav.hr.employees.stat_total', { defaultValue: 'Directory total: {n}', values: { n: stats.total } })}
            </span>
            <span className="badge border border-slate-200 font-medium tabular-nums">
              {t('app.nav.hr.employees.stat_loaded', { defaultValue: 'Loaded: {n}', values: { n: stats.shown } })}
            </span>
            <span className="badge border border-rose-100 bg-rose-50/90 font-medium tabular-nums text-rose-900">
              {t('app.nav.hr.employees.stat_high_risk', { defaultValue: 'High/critical risk: {n}', values: { n: stats.high } })}
            </span>
            <span className="badge border border-amber-100 bg-amber-50/90 font-medium tabular-nums text-amber-950">
              {t('app.nav.hr.employees.stat_missing_sum', { defaultValue: 'Missing doc slots (page): {n}', values: { n: stats.missingSum } })}
            </span>
          </div>
        ) : null}
        {rangeLabel ? <div className="text-xs text-slate-600">{rangeLabel}</div> : null}

        <section className="card p-4 sm:p-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.nav.hr.directory.filters_heading', { defaultValue: 'Filters' })}
          </div>
          <div className="mt-3 flex flex-wrap items-end gap-4">
            <label className="flex min-w-[140px] flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600" htmlFor="dir-status">
                {t('app.nav.hr.directory.filters_status', { defaultValue: 'Status' })}
              </span>
              <select id="dir-status" className="input text-sm" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">{t('app.nav.hr.directory.filters_all', { defaultValue: 'All' })}</option>
                {STATUS_OPTIONS.filter(Boolean).map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex min-w-[160px] flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600" htmlFor="dir-compliance">
                {t('app.nav.hr.directory.filters_compliance', { defaultValue: 'Compliance' })}
              </span>
              <select id="dir-compliance" className="input text-sm" value={complianceStatus} onChange={(e) => setComplianceStatus(e.target.value)}>
                <option value="">{t('app.nav.hr.directory.filters_all', { defaultValue: 'All' })}</option>
                {COMPLIANCE_OPTIONS.filter(Boolean).map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex min-w-[120px] flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600" htmlFor="dir-risk">
                {t('app.nav.hr.directory.filters_risk', { defaultValue: 'Risk' })}
              </span>
              <select id="dir-risk" className="input text-sm" value={riskLevel} onChange={(e) => setRiskLevel(e.target.value)}>
                <option value="">{t('app.nav.hr.directory.filters_all', { defaultValue: 'All' })}</option>
                {RISK_OPTIONS.filter(Boolean).map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex min-w-[min(100%,220px)] flex-1 flex-col gap-1.5 sm:min-w-[240px]">
              <span className="label mb-0 text-xs text-slate-600" htmlFor="dir-search">
                {t('app.nav.hr.directory.filters_search', { defaultValue: 'Search' })}
              </span>
              <input
                id="dir-search"
                className="input text-sm"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder={t('app.nav.hr.directory.filters_search_placeholder', { defaultValue: 'Name…' })}
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={missingOnly} onChange={(e) => setMissingOnly(e.target.checked)} />
              {t('app.nav.hr.directory.filters_missing_only', { defaultValue: 'Only with missing documents' })}
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={expiringOnly} onChange={(e) => setExpiringOnly(e.target.checked)} />
              {t('app.nav.hr.directory.filters_expiring_only', { defaultValue: 'Only with expiring documents' })}
            </label>
          </div>
        </section>
      </div>

      {can('workforce.manage') && (
        <div className="card flex flex-wrap items-end gap-3 p-4">
          <label className="flex flex-col gap-1.5">
            <span className="label mb-0 text-xs text-slate-600" htmlFor="hr-emp-name">
              {t('app.nav.hr.employees.add_manual', { defaultValue: 'Add without candidate link' })}
            </span>
            <input
              id="hr-emp-name"
              className="input min-w-[220px] text-sm"
              value={nameDraft}
              onChange={(e) => setNameDraft(e.target.value)}
              placeholder={t('app.nav.hr.employees.display_name', { defaultValue: 'Full name' })}
            />
          </label>
          <button type="button" className="btn-primary btn-sm" disabled={creating} onClick={() => void onCreate()}>
            {t('app.nav.hr.employees.create', { defaultValue: 'Create' })}
          </button>
        </div>
      )}

      {err && !loading ? (
        <div className="alert-error">
          <p className="font-medium">{t('app.nav.hr.employees.error_title', { defaultValue: 'Could not load employees' })}</p>
          <p className="mt-1">{err}</p>
          <button type="button" className="mt-2 text-sm font-medium underline underline-offset-2" onClick={() => void load()}>
            {t('app.nav.hr.employees.retry', { defaultValue: 'Try again' })}
          </button>
        </div>
      ) : null}

      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-6 text-sm text-slate-600">{t('common.loading', { defaultValue: 'Loading…' })}</div>
        ) : err ? null : items.length === 0 ? (
          <div className="p-6 text-sm text-slate-600">
            {t('app.nav.hr.employees.empty', {
              defaultValue: 'No employees yet. Accept a handoff from Inbox or create one manually (if allowed).',
            })}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table w-full min-w-[1280px] text-left text-sm">
              <thead>
                <tr>
                  <th>{t('app.nav.hr.employees.col_name', { defaultValue: 'Employee' })}</th>
                  <th>{t('app.nav.hr.directory.col_client', { defaultValue: 'Company / Client' })}</th>
                  <th>{t('app.nav.hr.employees.col_status', { defaultValue: 'Status' })}</th>
                  <th>{t('app.nav.hr.directory.col_verification', { defaultValue: 'Verification' })}</th>
                  <th>{t('app.nav.hr.directory.col_compliance', { defaultValue: 'Eligibility' })}</th>
                  <th>{t('app.nav.hr.directory.col_missing', { defaultValue: 'Missing' })}</th>
                  <th>{t('app.nav.hr.directory.col_expiring', { defaultValue: 'Expiring' })}</th>
                  <th>{t('app.hr.review.next_action', { defaultValue: 'Next action' })}</th>
                  <th>{t('app.nav.hr.directory.col_assigned_hr', { defaultValue: 'Assigned HR' })}</th>
                  <th className="w-28">{t('app.nav.hr.employees.col_actions', { defaultValue: 'Actions' })}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.employee_id}>
                    <td>
                      <div className="font-medium text-slate-900">{r.full_name}</div>
                      <div className="mt-0.5 text-[11px] text-slate-500">
                        {r.position || dash}
                        {r.start_date ? ` · ${formatShortDate(r.start_date)}` : ''}
                      </div>
                      <div className="mt-0.5 font-mono text-[10px] text-slate-400">emp:{r.employee_id.slice(0, 8)}…</div>
                    </td>
                    <td className="max-w-[200px]">
                      <div className="truncate text-slate-800" title={r.employer || ''}>{r.employer || dash}</div>
                      <div className="truncate text-xs text-slate-500" title={r.client || ''}>{r.client || dash}</div>
                    </td>
                    <td>
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusTone(r.status)}`}>
                        {r.status || dash}
                      </span>
                    </td>
                    <td>
                      <HrVerificationProgressBadge
                        verified={r.documents_verified_count}
                        total={r.documents_total_count}
                        hrReviewStatus={r.hr_review_status}
                      />
                    </td>
                    <td>
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${eligibilityTone(r.compliance_status)}`}>
                        {r.compliance_status || dash}
                      </span>
                    </td>
                    <td className="tabular-nums text-slate-700">{r.missing_documents_count}</td>
                    <td className="tabular-nums text-slate-700">{r.expiring_documents_count}</td>
                    <td className="max-w-[240px] truncate text-slate-700" title={deriveNextAction(r)}>
                      {deriveNextAction(r)}
                    </td>
                    <td className="max-w-[140px] truncate text-slate-600" title={r.assigned_hr || ''}>
                      {r.assigned_hr || dash}
                    </td>
                    <td>
                      <div className="flex flex-col gap-1">
                        <Link
                          className="text-sm font-medium text-brand-700 hover:underline"
                          to={hrEmployeePath(
                            r.employee_id,
                            r.hr_review_status && r.hr_review_status !== 'approved_for_employment'
                              ? 'hr-verification'
                              : undefined,
                          )}
                        >
                          {r.hr_review_status && r.hr_review_status !== 'approved_for_employment'
                            ? t('app.hr.verify_task.open_verification', { defaultValue: 'Verify documents' })
                            : t('app.nav.hr.employees.open', { defaultValue: 'Open' })}
                        </Link>
                        {r.handoff_id && (!r.hr_review_status || r.hr_review_status === 'approved_for_employment') ? (
                          <Link
                            className="text-xs font-medium text-brand-700 hover:underline"
                            to={`${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(r.handoff_id)}`}
                          >
                            {t('app.nav.hr.employees.open_handoff', { defaultValue: 'Handoff' })}
                          </Link>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
