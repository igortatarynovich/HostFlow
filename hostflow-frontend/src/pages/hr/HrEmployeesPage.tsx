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

const hrEmployeePath = (id: string) => `${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(id)}`

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

  if (!can('workforce.view')) {
    return (
      <div className="p-6 text-sm text-slate-600">
        {t('app.nav.hr.employees.forbidden', { defaultValue: 'You do not have access to the HR workspace.' })}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            {t('app.nav.hr.employees.heading', { defaultValue: 'Employees' })}
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            {t('app.nav.hr.employees.subtitle_directory', {
              defaultValue:
                'HR directory from GET /api/v1/workforce/employees/directory (read-model: employment, compliance, risk).',
            })}
          </p>
        </div>
        <button
          type="button"
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
          onClick={() => void load()}
        >
          {t('common.actions.refresh', { defaultValue: 'Refresh' })}
        </button>
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-slate-500" htmlFor="dir-status">
            {t('app.nav.hr.directory.filters_status', { defaultValue: 'Status' })}
          </label>
          <select
            id="dir-status"
            className="rounded border border-slate-200 px-2 py-1.5 text-sm min-w-[140px]"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">{t('app.nav.hr.directory.filters_all', { defaultValue: 'All' })}</option>
            {STATUS_OPTIONS.filter(Boolean).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-slate-500" htmlFor="dir-compliance">
            {t('app.nav.hr.directory.filters_compliance', { defaultValue: 'Compliance' })}
          </label>
          <select
            id="dir-compliance"
            className="rounded border border-slate-200 px-2 py-1.5 text-sm min-w-[160px]"
            value={complianceStatus}
            onChange={(e) => setComplianceStatus(e.target.value)}
          >
            <option value="">{t('app.nav.hr.directory.filters_all', { defaultValue: 'All' })}</option>
            {COMPLIANCE_OPTIONS.filter(Boolean).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-slate-500" htmlFor="dir-risk">
            {t('app.nav.hr.directory.filters_risk', { defaultValue: 'Risk' })}
          </label>
          <select
            id="dir-risk"
            className="rounded border border-slate-200 px-2 py-1.5 text-sm min-w-[120px]"
            value={riskLevel}
            onChange={(e) => setRiskLevel(e.target.value)}
          >
            <option value="">{t('app.nav.hr.directory.filters_all', { defaultValue: 'All' })}</option>
            {RISK_OPTIONS.filter(Boolean).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="flex min-w-[200px] flex-1 flex-col gap-1">
          <label className="text-xs font-medium text-slate-500" htmlFor="dir-search">
            {t('app.nav.hr.directory.filters_search', { defaultValue: 'Search' })}
          </label>
          <input
            id="dir-search"
            className="rounded border border-slate-200 px-2 py-1.5 text-sm"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t('app.nav.hr.directory.filters_search_placeholder', { defaultValue: 'Name…' })}
          />
        </div>
        <label className="flex cursor-pointer items-center gap-2 pt-5 text-sm text-slate-700">
          <input type="checkbox" checked={missingOnly} onChange={(e) => setMissingOnly(e.target.checked)} />
          {t('app.nav.hr.directory.filters_missing_only', { defaultValue: 'Only with missing documents' })}
        </label>
        <label className="flex cursor-pointer items-center gap-2 pt-5 text-sm text-slate-700">
          <input type="checkbox" checked={expiringOnly} onChange={(e) => setExpiringOnly(e.target.checked)} />
          {t('app.nav.hr.directory.filters_expiring_only', { defaultValue: 'Only with expiring documents' })}
        </label>
      </div>

      {can('workforce.manage') && (
        <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-slate-50/80 p-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-500" htmlFor="hr-emp-name">
              {t('app.nav.hr.employees.add_manual', { defaultValue: 'Add without candidate link' })}
            </label>
            <input
              id="hr-emp-name"
              className="min-w-[220px] rounded border border-slate-200 px-2 py-1.5 text-sm"
              value={nameDraft}
              onChange={(e) => setNameDraft(e.target.value)}
              placeholder={t('app.nav.hr.employees.display_name', { defaultValue: 'Full name' })}
            />
          </div>
          <button
            type="button"
            className="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            disabled={creating}
            onClick={() => void onCreate()}
          >
            {t('app.nav.hr.employees.create', { defaultValue: 'Create' })}
          </button>
        </div>
      )}

      {rangeLabel ? <div className="text-xs text-slate-500">{rangeLabel}</div> : null}

      {err && !loading ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          <p className="font-medium">{t('app.nav.hr.employees.error_title', { defaultValue: 'Could not load employees' })}</p>
          <p className="mt-1 text-rose-800">{err}</p>
          <button
            type="button"
            className="mt-2 text-sm font-medium text-rose-950 underline underline-offset-2 hover:no-underline"
            onClick={() => void load()}
          >
            {t('app.nav.hr.employees.retry', { defaultValue: 'Try again' })}
          </button>
        </div>
      ) : null}

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        {loading ? (
          <div className="p-6 text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</div>
        ) : err ? null : items.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">
            {t('app.nav.hr.employees.empty', {
              defaultValue: 'No employees yet. Accept a handoff from Inbox or create one manually (if allowed).',
            })}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1100px] text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.employees.col_name', { defaultValue: 'Name' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.employees.col_status', { defaultValue: 'Status' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.directory.col_employer', { defaultValue: 'Employer' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.directory.col_client', { defaultValue: 'Client' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.directory.col_position', { defaultValue: 'Position' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.employees.col_start', { defaultValue: 'Start date' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.directory.col_compliance', { defaultValue: 'Compliance' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.directory.col_missing', { defaultValue: 'Missing' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.directory.col_expiring', { defaultValue: 'Expiring' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.directory.col_assigned_hr', { defaultValue: 'Assigned HR' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.directory.col_risk', { defaultValue: 'Risk' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.directory.col_handoff', { defaultValue: 'Handoff' })}</th>
                  <th className="px-3 py-2 font-medium">{t('app.nav.hr.directory.col_candidate_id', { defaultValue: 'Candidate ID' })}</th>
                  <th className="w-24 px-3 py-2 font-medium">{t('app.nav.hr.employees.col_actions', { defaultValue: 'Actions' })}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.employee_id} className="border-b border-slate-100 last:border-0">
                    <td className="px-3 py-2 font-medium text-slate-900">{r.full_name}</td>
                    <td className="px-3 py-2 text-slate-700">{r.status}</td>
                    <td className="max-w-[140px] truncate px-3 py-2 text-slate-600" title={r.employer || ''}>
                      {r.employer || dash}
                    </td>
                    <td className="max-w-[140px] truncate px-3 py-2 text-slate-600" title={r.client || ''}>
                      {r.client || dash}
                    </td>
                    <td className="max-w-[160px] truncate px-3 py-2 text-slate-600" title={r.position || ''}>
                      {r.position || dash}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-slate-600">
                      {r.start_date ? formatShortDate(r.start_date) : dash}
                    </td>
                    <td className="px-3 py-2 text-slate-700">{r.compliance_status}</td>
                    <td className="px-3 py-2 text-slate-700">{r.missing_documents_count}</td>
                    <td className="px-3 py-2 text-slate-700">{r.expiring_documents_count}</td>
                    <td className="max-w-[140px] truncate px-3 py-2 text-slate-600" title={r.assigned_hr || ''}>
                      {r.assigned_hr || dash}
                    </td>
                    <td className="px-3 py-2 text-slate-700">{r.risk_level}</td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-600">
                      {r.handoff_id ? `${r.handoff_id.slice(0, 8)}…` : dash}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-600">
                      {r.candidate_id ? `${r.candidate_id.slice(0, 8)}…` : dash}
                    </td>
                    <td className="px-3 py-2">
                      <Link className="text-sm text-brand-600 hover:underline" to={hrEmployeePath(r.employee_id)}>
                        {t('app.nav.hr.employees.open', { defaultValue: 'Open' })}
                      </Link>
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
