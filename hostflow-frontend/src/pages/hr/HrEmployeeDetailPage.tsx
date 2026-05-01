import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useI18n } from '../../i18n'
import {
  createWorkforceAbsence,
  createWorkforceEmployment,
  createWorkforceLeaveRequest,
  getWorkforceEmployee,
  getWorkforceHrBundle,
  patchWorkforceAbsence,
  patchWorkforceEmployee,
  patchWorkforceEmployment,
  patchWorkforceLeaveRequest,
  patchWorkforceOnboardingTask,
  patchWorkforcePayrollProfile,
  patchWorkforceZusProfile,
  type WorkforceEmployee,
  type WorkforceHrBundle,
} from '../../api/workforce'
import { usePermissions } from '../../hooks/usePermissions'
import { useToast } from '../../components/Toast'
import { PageBreadcrumb } from '../../components/nav/PageBreadcrumb'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { HrEmployeeDocumentsSection } from './HrEmployeeDocumentsSection'

const EMPLOYEE_STATUSES = [
  'onboarding',
  'active',
  'on_sick_leave',
  'on_vacation',
  'on_leave',
  'suspended',
  'contract_ending',
  'terminated',
] as const

const PAYROLL_STATUSES = [
  'missing_data',
  'ready_for_payroll',
  'sent_to_accounting',
  'settled',
  'correction_needed',
] as const

const PAY_TYPES = ['fixed_salary', 'hourly', 'per_km', 'per_route', 'mixed'] as const

const ZUS_STATUSES = ['not_submitted', 'submitted', 'active', 'correction_required', 'deregistered'] as const

function stringifyJsonField(value: Record<string, unknown> | null | undefined): string {
  if (value == null) return ''
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return ''
  }
}

/** Returns `undefined` on parse error (caller should abort). `null` when empty string (clear). */
function parseOptionalJsonObject(
  raw: string,
  label: string,
  notify: ReturnType<typeof useToast>['notify'],
): Record<string, unknown> | null | undefined {
  const s = raw.trim()
  if (!s) return null
  try {
    const v = JSON.parse(s)
    if (v && typeof v === 'object' && !Array.isArray(v)) return v as Record<string, unknown>
    notify({
      variant: 'error',
      title: `${label}: JSON must be an object`,
    })
    return undefined
  } catch {
    notify({
      variant: 'error',
      title: `${label}: invalid JSON`,
    })
    return undefined
  }
}

function Section({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <details open className="border border-slate-200 rounded-lg bg-white">
      <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-900 border-b border-slate-100">
        {title}
      </summary>
      <div className="p-4">{children}</div>
    </details>
  )
}

export default function HrEmployeeDetailPage() {
  const { employeeId } = useParams<{ employeeId: string }>()
  const { t } = useI18n()
  const { can } = usePermissions()
  const { notify } = useToast()
  const [employee, setEmployee] = useState<WorkforceEmployee | null>(null)
  const [bundle, setBundle] = useState<WorkforceHrBundle | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)

  const manage = can('workforce.manage')

  const load = useCallback(async () => {
    if (!employeeId) return
    setLoading(true)
    try {
      const [emp, b] = await Promise.all([
        getWorkforceEmployee(employeeId),
        getWorkforceHrBundle(employeeId),
      ])
      setEmployee(emp)
      setBundle(b)
    } catch {
      setEmployee(null)
      setBundle(null)
      notify({
        variant: 'error',
        title: t('app.hr.employee_detail.load_error', { defaultValue: 'Could not load employee' }),
      })
    } finally {
      setLoading(false)
    }
  }, [employeeId, notify, t])

  useEffect(() => {
    if (can('workforce.view') && employeeId) void load()
  }, [can, employeeId, load])

  const snapshotPretty = useMemo(() => {
    if (!employee?.candidate_snapshot) return ''
    try {
      return JSON.stringify(employee.candidate_snapshot, null, 2)
    } catch {
      return ''
    }
  }, [employee?.candidate_snapshot])

  const runSave = async (key: string, fn: () => Promise<void>) => {
    setSaving(key)
    try {
      await fn()
      notify({
        variant: 'success',
        title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }),
      })
      await load()
    } catch {
      notify({
        variant: 'error',
        title: t('app.hr.employee_detail.save_error', { defaultValue: 'Could not save' }),
      })
    } finally {
      setSaving(null)
    }
  }

  if (!can('workforce.view')) {
    return (
      <div className="p-6 text-sm text-slate-600">
        {t('app.hr.employees.forbidden', { defaultValue: 'You do not have access to the HR workspace.' })}
      </div>
    )
  }

  if (!employeeId) {
    return (
      <div className="p-6 text-sm text-slate-600">
        {t('app.hr.employee_detail.missing_id', { defaultValue: 'Missing employee id.' })}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6 text-sm text-slate-500">
        {t('common.loading', { defaultValue: 'Loading…' })}
      </div>
    )
  }

  if (!employee || !bundle) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <p className="text-sm text-slate-600 mb-4">
          {t('app.hr.employee_detail.not_found', { defaultValue: 'Employee not found.' })}
        </p>
        <Link className="text-sm text-brand-600 hover:underline" to={CRM_APP_PATHS.hrEmployees}>
          {t('app.hr.employee_detail.back_list', { defaultValue: '← Back to employees' })}
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6 max-w-5xl mx-auto w-full">
      <PageBreadcrumb
        items={[
          { to: CRM_APP_PATHS.overview, label: t('app.nav.items.overview', { defaultValue: 'Insights' }) },
          { to: CRM_APP_PATHS.hrEmployees, label: t('app.nav.items.hr_employees', { defaultValue: 'HR · Employees' }) },
          { label: employee.display_name },
        ]}
      />

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{employee.display_name}</h1>
          <p className="text-xs text-slate-500 mt-1 font-mono">{employee.id}</p>
        </div>
        <Link
          to={CRM_APP_PATHS.hrEmployees}
          className="text-sm text-slate-600 hover:text-slate-900 underline-offset-2 hover:underline"
        >
          {t('app.hr.employee_detail.back_list', { defaultValue: '← Back to employees' })}
        </Link>
      </div>

      <OverviewSection
        employee={employee}
        manage={manage}
        saving={saving}
        onSave={(payload) =>
          runSave('overview', () => patchWorkforceEmployee(employeeId, payload))
        }
      />

      <HrEmployeeDocumentsSection employeeId={employeeId} candidateId={employee.candidate_id} />

      <PayrollSection
        profile={bundle.payroll_profile}
        manage={manage}
        saving={saving === 'payroll'}
        onSave={(payload) =>
          runSave('payroll', () => patchWorkforcePayrollProfile(employeeId, payload))
        }
      />

      <ZusSection
        profile={bundle.zus_profile}
        manage={manage}
        saving={saving === 'zus'}
        onSave={(payload) => runSave('zus', () => patchWorkforceZusProfile(employeeId, payload))}
      />

      <EmploymentsSection
        employeeId={employeeId}
        rows={bundle.employments}
        manage={manage}
        saving={saving}
        onReload={load}
        notify={notify}
        t={t}
      />

      <OnboardingSection
        tasks={bundle.onboarding_tasks}
        manage={manage}
        saving={saving}
        onMarkDone={(taskId) =>
          runSave(`task-${taskId}`, () => patchWorkforceOnboardingTask(taskId, { status: 'done' }))
        }
      />

      <AbsencesSection
        employeeId={employeeId}
        rows={bundle.absences}
        manage={manage}
        saving={saving}
        onReload={load}
        notify={notify}
        t={t}
      />

      <LeaveSection
        employeeId={employeeId}
        rows={bundle.leave_requests}
        manage={manage}
        saving={saving}
        onReload={load}
        notify={notify}
        t={t}
      />

      {snapshotPretty ? (
        <Section title={t('app.hr.employee_detail.snapshot', { defaultValue: 'Candidate snapshot (hire)' })}>
          <pre className="text-xs bg-slate-50 border border-slate-100 rounded p-3 overflow-x-auto max-h-64 overflow-y-auto">
            {snapshotPretty}
          </pre>
        </Section>
      ) : null}

      {employee.candidate_id ? (
        <div className="text-sm">
          <Link
            className="text-brand-600 hover:underline"
            to={`${CRM_APP_PATHS.candidates}/${encodeURIComponent(employee.candidate_id)}`}
          >
            {t('app.hr.employee_detail.open_candidate', { defaultValue: 'Open linked candidate' })}
          </Link>
        </div>
      ) : null}
    </div>
  )
}

function OverviewSection({
  employee,
  manage,
  saving,
  onSave,
}: {
  employee: WorkforceEmployee
  manage: boolean
  saving: string | null
  onSave: (p: Partial<{ display_name: string; status: string; hire_date: string | null }>) => void
}) {
  const { t } = useI18n()
  const [display_name, setDisplayName] = useState(employee.display_name)
  const [status, setStatus] = useState(employee.status)
  const [hire_date, setHireDate] = useState(employee.hire_date || '')

  useEffect(() => {
    setDisplayName(employee.display_name)
    setStatus(employee.status)
    setHireDate(employee.hire_date || '')
  }, [employee.display_name, employee.status, employee.hire_date])

  return (
    <Section title={t('app.hr.employee_detail.section_overview', { defaultValue: 'Overview' })}>
      <div className="grid gap-3 sm:grid-cols-2 max-w-xl">
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employees.display_name', { defaultValue: 'Full name' })}
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            value={display_name}
            disabled={!manage}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employees.col_status', { defaultValue: 'Status' })}
          <select
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            value={status}
            disabled={!manage}
            onChange={(e) => setStatus(e.target.value)}
          >
            {EMPLOYEE_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employees.col_hire', { defaultValue: 'Hire date' })}
          <input
            type="date"
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            value={hire_date}
            disabled={!manage}
            onChange={(e) => setHireDate(e.target.value)}
          />
        </label>
      </div>
      {manage ? (
        <button
          type="button"
          disabled={saving === 'overview'}
          className="mt-3 px-3 py-1.5 rounded text-sm font-medium bg-slate-900 text-white disabled:opacity-50"
          onClick={() =>
            onSave({
              display_name,
              status,
              hire_date: hire_date || null,
            })
          }
        >
          {t('app.hr.employee_detail.save', { defaultValue: 'Save' })}
        </button>
      ) : null}
    </Section>
  )
}

function PayrollSection({
  profile,
  manage,
  saving,
  onSave,
}: {
  profile: WorkforceHrBundle['payroll_profile']
  manage: boolean
  saving: boolean
  onSave: (p: Parameters<typeof patchWorkforcePayrollProfile>[1]) => void
}) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [pay_type, setPayType] = useState(profile?.pay_type || 'mixed')
  const [base_rate, setBaseRate] = useState(profile?.base_rate || '')
  const [currency, setCurrency] = useState(profile?.currency || 'PLN')
  const [payroll_status, setPayrollStatus] = useState(profile?.payroll_status || 'missing_data')
  const [bank_account, setBankAccount] = useState(profile?.bank_account || '')
  const [tax_status, setTaxStatus] = useState(profile?.tax_status || '')
  const [calculation_system, setCalculationSystem] = useState(profile?.calculation_system || '')
  const [pay_day_note, setPayDayNote] = useState(profile?.pay_day_note || '')
  const [pit_json, setPitJson] = useState(() => stringifyJsonField(profile?.pit_declarations ?? undefined))
  const [allowances_json, setAllowancesJson] = useState(() => stringifyJsonField(profile?.allowances ?? undefined))
  const [deductions_json, setDeductionsJson] = useState(() => stringifyJsonField(profile?.deductions ?? undefined))
  const [external_refs_json, setExternalRefsJson] = useState(() =>
    stringifyJsonField(profile?.external_refs ?? undefined),
  )

  useEffect(() => {
    if (!profile) return
    setPayType(profile.pay_type || 'mixed')
    setBaseRate(profile.base_rate || '')
    setCurrency(profile.currency || 'PLN')
    setPayrollStatus(profile.payroll_status || 'missing_data')
    setBankAccount(profile.bank_account || '')
    setTaxStatus(profile.tax_status || '')
    setCalculationSystem(profile.calculation_system || '')
    setPayDayNote(profile.pay_day_note || '')
    setPitJson(stringifyJsonField(profile.pit_declarations ?? undefined))
    setAllowancesJson(stringifyJsonField(profile.allowances ?? undefined))
    setDeductionsJson(stringifyJsonField(profile.deductions ?? undefined))
    setExternalRefsJson(stringifyJsonField(profile.external_refs ?? undefined))
  }, [profile])

  if (!profile) {
    return (
      <Section title={t('app.hr.employee_detail.section_payroll', { defaultValue: 'Payroll profile' })}>
        <p className="text-sm text-slate-500">{t('app.hr.employee_detail.no_payroll', { defaultValue: 'No payroll row yet.' })}</p>
      </Section>
    )
  }

  return (
    <Section title={t('app.hr.employee_detail.section_payroll', { defaultValue: 'Payroll profile' })}>
      <div className="grid gap-3 sm:grid-cols-2 max-w-2xl">
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Pay type
          <select
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={pay_type}
            onChange={(e) => setPayType(e.target.value)}
          >
            {PAY_TYPES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Base rate
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={base_rate}
            onChange={(e) => setBaseRate(e.target.value)}
            placeholder="6500.00"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Currency
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Payroll status
          <select
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={payroll_status}
            onChange={(e) => setPayrollStatus(e.target.value)}
          >
            {PAYROLL_STATUSES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          Bank account
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm font-mono"
            disabled={!manage}
            value={bank_account}
            onChange={(e) => setBankAccount(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          Tax status
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={tax_status}
            onChange={(e) => setTaxStatus(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_calculation_system', { defaultValue: 'Calculation system' })}
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={calculation_system}
            onChange={(e) => setCalculationSystem(e.target.value)}
            placeholder={t('app.hr.employee_detail.payroll_calculation_placeholder', {
              defaultValue: 'e.g. monthly / hourly bundle id',
            })}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_pay_day_note', { defaultValue: 'Pay day note' })}
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={pay_day_note}
            onChange={(e) => setPayDayNote(e.target.value)}
            placeholder={t('app.hr.employee_detail.payroll_pay_day_placeholder', {
              defaultValue: 'e.g. 10th of next month',
            })}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_pit_json', { defaultValue: 'PIT declarations (JSON object)' })}
          <textarea
            className="border border-slate-200 rounded px-2 py-1.5 text-sm font-mono min-h-[5rem]"
            disabled={!manage}
            value={pit_json}
            onChange={(e) => setPitJson(e.target.value)}
            spellCheck={false}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_allowances_json', { defaultValue: 'Allowances (JSON object)' })}
          <textarea
            className="border border-slate-200 rounded px-2 py-1.5 text-sm font-mono min-h-[5rem]"
            disabled={!manage}
            value={allowances_json}
            onChange={(e) => setAllowancesJson(e.target.value)}
            spellCheck={false}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_deductions_json', { defaultValue: 'Deductions (JSON object)' })}
          <textarea
            className="border border-slate-200 rounded px-2 py-1.5 text-sm font-mono min-h-[5rem]"
            disabled={!manage}
            value={deductions_json}
            onChange={(e) => setDeductionsJson(e.target.value)}
            spellCheck={false}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_external_refs_json', { defaultValue: 'External refs (JSON object)' })}
          <textarea
            className="border border-slate-200 rounded px-2 py-1.5 text-sm font-mono min-h-[5rem]"
            disabled={!manage}
            value={external_refs_json}
            onChange={(e) => setExternalRefsJson(e.target.value)}
            spellCheck={false}
          />
        </label>
      </div>
      {manage ? (
        <button
          type="button"
          disabled={saving}
          className="mt-3 px-3 py-1.5 rounded text-sm font-medium bg-slate-900 text-white disabled:opacity-50"
          onClick={() => {
            const pitLabel = t('app.hr.employee_detail.payroll_pit_json', { defaultValue: 'PIT declarations' })
            const pit = parseOptionalJsonObject(pit_json, pitLabel, notify)
            if (pit === undefined) return
            const alwLabel = t('app.hr.employee_detail.payroll_allowances_json', { defaultValue: 'Allowances' })
            const alw = parseOptionalJsonObject(allowances_json, alwLabel, notify)
            if (alw === undefined) return
            const dedLabel = t('app.hr.employee_detail.payroll_deductions_json', { defaultValue: 'Deductions' })
            const ded = parseOptionalJsonObject(deductions_json, dedLabel, notify)
            if (ded === undefined) return
            const extLabel = t('app.hr.employee_detail.payroll_external_refs_json', { defaultValue: 'External refs' })
            const ext = parseOptionalJsonObject(external_refs_json, extLabel, notify)
            if (ext === undefined) return
            onSave({
              pay_type,
              base_rate: base_rate || undefined,
              currency: currency || undefined,
              payroll_status,
              bank_account: bank_account || undefined,
              tax_status: tax_status || undefined,
              calculation_system: calculation_system.trim() || null,
              pay_day_note: pay_day_note.trim() || null,
              pit_declarations: pit,
              allowances: alw,
              deductions: ded,
              external_refs: ext,
            })
          }}
        >
          {t('app.hr.employee_detail.save', { defaultValue: 'Save' })}
        </button>
      ) : null}
    </Section>
  )
}

function ZusSection({
  profile,
  manage,
  saving,
  onSave,
}: {
  profile: WorkforceHrBundle['zus_profile']
  manage: boolean
  saving: boolean
  onSave: (p: Parameters<typeof patchWorkforceZusProfile>[1]) => void
}) {
  const { t } = useI18n()
  const [registration_status, setRegStatus] = useState(profile?.registration_status || 'not_submitted')
  const [employment_basis, setBasis] = useState(profile?.employment_basis || '')
  const [responsible_party, setParty] = useState(profile?.responsible_party || '')
  const [submitted_at, setSubmittedAt] = useState(profile?.submitted_at || '')

  useEffect(() => {
    if (!profile) return
    setRegStatus(profile.registration_status || 'not_submitted')
    setBasis(profile.employment_basis || '')
    setParty(profile.responsible_party || '')
    setSubmittedAt(profile.submitted_at || '')
  }, [profile])

  if (!profile) {
    return (
      <Section title={t('app.hr.employee_detail.section_zus', { defaultValue: 'ZUS' })}>
        <p className="text-sm text-slate-500">{t('app.hr.employee_detail.no_zus', { defaultValue: 'No ZUS row yet.' })}</p>
      </Section>
    )
  }

  return (
    <Section title={t('app.hr.employee_detail.section_zus', { defaultValue: 'ZUS' })}>
      <div className="grid gap-3 sm:grid-cols-2 max-w-2xl">
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Registration status
          <select
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={registration_status}
            onChange={(e) => setRegStatus(e.target.value)}
          >
            {ZUS_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Submitted at
          <input
            type="date"
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={submitted_at ? submitted_at.slice(0, 10) : ''}
            onChange={(e) => setSubmittedAt(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Employment basis
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={employment_basis}
            onChange={(e) => setBasis(e.target.value)}
            placeholder="umowa o pracę / zlecenie / B2B"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Responsible party
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={responsible_party}
            onChange={(e) => setParty(e.target.value)}
            placeholder="hr / accounting / external"
          />
        </label>
      </div>
      {manage ? (
        <button
          type="button"
          disabled={saving}
          className="mt-3 px-3 py-1.5 rounded text-sm font-medium bg-slate-900 text-white disabled:opacity-50"
          onClick={() =>
            onSave({
              registration_status,
              employment_basis: employment_basis || undefined,
              responsible_party: responsible_party || undefined,
              submitted_at: submitted_at ? submitted_at.slice(0, 10) : undefined,
            })
          }
        >
          {t('app.hr.employee_detail.save', { defaultValue: 'Save' })}
        </button>
      ) : null}
    </Section>
  )
}

function EmploymentsSection({
  employeeId,
  rows,
  manage,
  saving,
  onReload,
  notify,
  t,
}: {
  employeeId: string
  rows: WorkforceHrBundle['employments']
  manage: boolean
  saving: string | null
  onReload: () => Promise<void>
  notify: ReturnType<typeof useToast>['notify']
  t: (key: string, opts?: { defaultValue?: string }) => string
}) {
  const [contract_type, setContractType] = useState('umowa_o_prace')
  const [drafts, setDrafts] = useState<
    Record<
      string,
      {
        contract_type: string
        start_date: string
        end_date: string
        rate_model_json: string
        schedule_json: string
        conditions_text: string
      }
    >
  >({})

  useEffect(() => {
    const next: Record<
      string,
      {
        contract_type: string
        start_date: string
        end_date: string
        rate_model_json: string
        schedule_json: string
        conditions_text: string
      }
    > = {}
    for (const r of rows) {
      next[r.id] = {
        contract_type: r.contract_type,
        start_date: r.start_date || '',
        end_date: r.end_date || '',
        rate_model_json: stringifyJsonField(r.rate_model ?? undefined),
        schedule_json: stringifyJsonField(r.schedule ?? undefined),
        conditions_text: r.conditions_text || '',
      }
    }
    setDrafts(next)
  }, [rows])

  const add = async () => {
    try {
      await createWorkforceEmployment(employeeId, { contract_type })
      notify({ variant: 'success', title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }) })
      await onReload()
    } catch {
      notify({
        variant: 'error',
        title: t('app.hr.employee_detail.save_error', { defaultValue: 'Could not save' }),
      })
    }
  }

  const saveRow = async (id: string) => {
    const d = drafts[id]
    if (!d) return
    const rmLabel = t('app.hr.employee_detail.employment_rate_model_json', { defaultValue: 'Rate model' })
    const rate_model = parseOptionalJsonObject(d.rate_model_json, rmLabel, notify)
    if (rate_model === undefined) return
    const schLabel = t('app.hr.employee_detail.employment_schedule_json', { defaultValue: 'Schedule' })
    const schedule = parseOptionalJsonObject(d.schedule_json, schLabel, notify)
    if (schedule === undefined) return
    try {
      await patchWorkforceEmployment(id, {
        contract_type: d.contract_type,
        start_date: d.start_date || undefined,
        end_date: d.end_date || undefined,
        rate_model,
        schedule,
        conditions_text: d.conditions_text.trim() || null,
      })
      notify({ variant: 'success', title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }) })
      await onReload()
    } catch {
      notify({
        variant: 'error',
        title: t('app.hr.employee_detail.save_error', { defaultValue: 'Could not save' }),
      })
    }
  }

  return (
    <Section title={t('app.hr.employee_detail.section_contracts', { defaultValue: 'Contracts (employment)' })}>
      {manage ? (
        <div className="flex flex-wrap items-end gap-2 mb-4 border border-slate-100 rounded p-3 bg-slate-50/80">
          <label className="text-xs text-slate-600 flex flex-col gap-1">
            New contract type
            <input
              className="border border-slate-200 rounded px-2 py-1.5 text-sm"
              value={contract_type}
              onChange={(e) => setContractType(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="px-3 py-1.5 rounded text-sm bg-slate-900 text-white"
            onClick={() => void add()}
          >
            {t('app.hr.employee_detail.add_contract', { defaultValue: 'Add contract' })}
          </button>
        </div>
      ) : null}
      <div className="space-y-4">
        {rows.length === 0 ? (
          <p className="text-sm text-slate-500">{t('app.hr.employee_detail.no_contracts', { defaultValue: 'No contracts yet.' })}</p>
        ) : (
          rows.map((r) => (
            <div key={r.id} className="border border-slate-100 rounded p-3 space-y-2">
              <div className="text-xs font-mono text-slate-500">{r.id}</div>
              <div className="grid gap-2 sm:grid-cols-3">
                <label className="text-xs text-slate-600 flex flex-col gap-1">
                  Type
                  <input
                    className="border border-slate-200 rounded px-2 py-1 text-sm"
                    disabled={!manage}
                    value={drafts[r.id]?.contract_type ?? r.contract_type}
                    onChange={(e) =>
                      setDrafts((prev) => ({
                        ...prev,
                        [r.id]: {
                          ...(prev[r.id] || {
                            contract_type: r.contract_type,
                            start_date: r.start_date || '',
                            end_date: r.end_date || '',
                            rate_model_json: stringifyJsonField(r.rate_model ?? undefined),
                            schedule_json: stringifyJsonField(r.schedule ?? undefined),
                            conditions_text: r.conditions_text || '',
                          }),
                          contract_type: e.target.value,
                        },
                      }))
                    }
                  />
                </label>
                <label className="text-xs text-slate-600 flex flex-col gap-1">
                  Start
                  <input
                    type="date"
                    className="border border-slate-200 rounded px-2 py-1 text-sm"
                    disabled={!manage}
                    value={(drafts[r.id]?.start_date ?? r.start_date)?.slice(0, 10) || ''}
                    onChange={(e) =>
                      setDrafts((prev) => ({
                        ...prev,
                        [r.id]: {
                          contract_type: prev[r.id]?.contract_type ?? r.contract_type,
                          start_date: e.target.value,
                          end_date: prev[r.id]?.end_date ?? (r.end_date || ''),
                          rate_model_json: prev[r.id]?.rate_model_json ?? stringifyJsonField(r.rate_model ?? undefined),
                          schedule_json: prev[r.id]?.schedule_json ?? stringifyJsonField(r.schedule ?? undefined),
                          conditions_text: prev[r.id]?.conditions_text ?? (r.conditions_text || ''),
                        },
                      }))
                    }
                  />
                </label>
                <label className="text-xs text-slate-600 flex flex-col gap-1">
                  End
                  <input
                    type="date"
                    className="border border-slate-200 rounded px-2 py-1 text-sm"
                    disabled={!manage}
                    value={(drafts[r.id]?.end_date ?? r.end_date)?.slice(0, 10) || ''}
                    onChange={(e) =>
                      setDrafts((prev) => ({
                        ...prev,
                        [r.id]: {
                          contract_type: prev[r.id]?.contract_type ?? r.contract_type,
                          start_date: prev[r.id]?.start_date ?? (r.start_date || ''),
                          end_date: e.target.value,
                          rate_model_json: prev[r.id]?.rate_model_json ?? stringifyJsonField(r.rate_model ?? undefined),
                          schedule_json: prev[r.id]?.schedule_json ?? stringifyJsonField(r.schedule ?? undefined),
                          conditions_text: prev[r.id]?.conditions_text ?? (r.conditions_text || ''),
                        },
                      }))
                    }
                  />
                </label>
              </div>
              <label className="text-xs text-slate-600 flex flex-col gap-1">
                {t('app.hr.employee_detail.employment_conditions', { defaultValue: 'Conditions (text)' })}
                <textarea
                  className="border border-slate-200 rounded px-2 py-1 text-sm min-h-[4rem]"
                  disabled={!manage}
                  value={drafts[r.id]?.conditions_text ?? r.conditions_text ?? ''}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [r.id]: {
                        contract_type: prev[r.id]?.contract_type ?? r.contract_type,
                        start_date: prev[r.id]?.start_date ?? (r.start_date || ''),
                        end_date: prev[r.id]?.end_date ?? (r.end_date || ''),
                        rate_model_json: prev[r.id]?.rate_model_json ?? stringifyJsonField(r.rate_model ?? undefined),
                        schedule_json: prev[r.id]?.schedule_json ?? stringifyJsonField(r.schedule ?? undefined),
                        conditions_text: e.target.value,
                      },
                    }))
                  }
                />
              </label>
              <label className="text-xs text-slate-600 flex flex-col gap-1">
                {t('app.hr.employee_detail.employment_rate_model_json', { defaultValue: 'Rate model (JSON object)' })}
                <textarea
                  className="border border-slate-200 rounded px-2 py-1 text-sm font-mono min-h-[5rem]"
                  disabled={!manage}
                  spellCheck={false}
                  value={drafts[r.id]?.rate_model_json ?? stringifyJsonField(r.rate_model ?? undefined)}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [r.id]: {
                        contract_type: prev[r.id]?.contract_type ?? r.contract_type,
                        start_date: prev[r.id]?.start_date ?? (r.start_date || ''),
                        end_date: prev[r.id]?.end_date ?? (r.end_date || ''),
                        rate_model_json: e.target.value,
                        schedule_json: prev[r.id]?.schedule_json ?? stringifyJsonField(r.schedule ?? undefined),
                        conditions_text: prev[r.id]?.conditions_text ?? (r.conditions_text || ''),
                      },
                    }))
                  }
                />
              </label>
              <label className="text-xs text-slate-600 flex flex-col gap-1">
                {t('app.hr.employee_detail.employment_schedule_json', { defaultValue: 'Schedule (JSON object)' })}
                <textarea
                  className="border border-slate-200 rounded px-2 py-1 text-sm font-mono min-h-[5rem]"
                  disabled={!manage}
                  spellCheck={false}
                  value={drafts[r.id]?.schedule_json ?? stringifyJsonField(r.schedule ?? undefined)}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [r.id]: {
                        contract_type: prev[r.id]?.contract_type ?? r.contract_type,
                        start_date: prev[r.id]?.start_date ?? (r.start_date || ''),
                        end_date: prev[r.id]?.end_date ?? (r.end_date || ''),
                        rate_model_json: prev[r.id]?.rate_model_json ?? stringifyJsonField(r.rate_model ?? undefined),
                        schedule_json: e.target.value,
                        conditions_text: prev[r.id]?.conditions_text ?? (r.conditions_text || ''),
                      },
                    }))
                  }
                />
              </label>
              {manage ? (
                <button
                  type="button"
                  disabled={saving === `emp-${r.id}`}
                  className="text-sm px-2 py-1 rounded bg-slate-800 text-white disabled:opacity-50"
                  onClick={() => void saveRow(r.id)}
                >
                  {t('app.hr.employee_detail.save', { defaultValue: 'Save' })}
                </button>
              ) : null}
            </div>
          ))
        )}
      </div>
    </Section>
  )
}

function OnboardingSection({
  tasks,
  manage,
  saving,
  onMarkDone,
}: {
  tasks: WorkforceHrBundle['onboarding_tasks']
  manage: boolean
  saving: string | null
  onMarkDone: (taskId: string) => void
}) {
  const { t } = useI18n()
  return (
    <Section title={t('app.hr.employee_detail.section_onboarding', { defaultValue: 'Onboarding' })}>
      <ul className="space-y-2">
        {tasks.map((task) => (
          <li key={task.id} className="flex flex-wrap items-center justify-between gap-2 border border-slate-100 rounded px-3 py-2">
            <div>
              <div className="text-sm font-medium text-slate-900">{task.title}</div>
              <div className="text-xs text-slate-500">{task.status}</div>
            </div>
            {manage && task.status !== 'done' ? (
              <button
                type="button"
                disabled={saving === `task-${task.id}`}
                className="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-50"
                onClick={() => onMarkDone(task.id)}
              >
                {t('app.hr.employee_detail.mark_done', { defaultValue: 'Mark done' })}
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </Section>
  )
}

function AbsencesSection({
  employeeId,
  rows,
  manage,
  saving,
  onReload,
  notify,
  t,
}: {
  employeeId: string
  rows: WorkforceHrBundle['absences']
  manage: boolean
  saving: string | null
  onReload: () => Promise<void>
  notify: ReturnType<typeof useToast>['notify']
  t: (key: string, opts?: { defaultValue?: string }) => string
}) {
  const [absence_type, setType] = useState('sick_leave')
  const [start_date, setStart] = useState('')
  const [end_date, setEnd] = useState('')

  const create = async () => {
    if (!start_date) {
      notify({ variant: 'error', title: t('app.hr.employee_detail.date_required', { defaultValue: 'Start date is required' }) })
      return
    }
    try {
      await createWorkforceAbsence(employeeId, {
        absence_type,
        start_date,
        end_date: end_date || undefined,
      })
      notify({ variant: 'success', title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }) })
      setStart('')
      setEnd('')
      await onReload()
    } catch {
      notify({
        variant: 'error',
        title: t('app.hr.employee_detail.save_error', { defaultValue: 'Could not save' }),
      })
    }
  }

  return (
    <Section title={t('app.hr.employee_detail.section_absences', { defaultValue: 'Absences' })}>
      {manage ? (
        <div className="flex flex-wrap gap-2 items-end mb-4 p-3 bg-slate-50/80 rounded border border-slate-100">
          <label className="text-xs flex flex-col gap-1">
            Type
            <input className="border rounded px-2 py-1 text-sm" value={absence_type} onChange={(e) => setType(e.target.value)} />
          </label>
          <label className="text-xs flex flex-col gap-1">
            Start
            <input type="date" className="border rounded px-2 py-1 text-sm" value={start_date} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="text-xs flex flex-col gap-1">
            End
            <input type="date" className="border rounded px-2 py-1 text-sm" value={end_date} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <button type="button" className="text-sm px-3 py-1.5 rounded bg-slate-900 text-white" onClick={() => void create()}>
            {t('app.hr.employee_detail.add', { defaultValue: 'Add' })}
          </button>
        </div>
      ) : null}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-600 border-b">
              <th className="py-2 pr-2">Type</th>
              <th className="py-2 pr-2">Start</th>
              <th className="py-2 pr-2">End</th>
              <th className="py-2 pr-2">Status</th>
              {manage ? <th className="py-2"> </th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} className="border-b border-slate-50">
                <td className="py-2 pr-2">{a.absence_type}</td>
                <td className="py-2 pr-2">{a.start_date}</td>
                <td className="py-2 pr-2">{a.end_date || '—'}</td>
                <td className="py-2 pr-2">{a.status}</td>
                {manage ? (
                  <td className="py-2">
                    {a.status !== 'settled' ? (
                      <button
                        type="button"
                        className="text-xs text-brand-600 hover:underline disabled:opacity-50"
                        disabled={saving === `abs-${a.id}`}
                        onClick={async () => {
                          try {
                            await patchWorkforceAbsence(a.id, { status: 'settled' })
                            notify({ variant: 'success', title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }) })
                            await onReload()
                          } catch {
                            notify({
                              variant: 'error',
                              title: t('app.hr.employee_detail.save_error', { defaultValue: 'Could not save' }),
                            })
                          }
                        }}
                      >
                        {t('app.hr.employee_detail.mark_settled', { defaultValue: 'Mark settled' })}
                      </button>
                    ) : null}
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  )
}

function LeaveSection({
  employeeId,
  rows,
  manage,
  saving,
  onReload,
  notify,
  t,
}: {
  employeeId: string
  rows: WorkforceHrBundle['leave_requests']
  manage: boolean
  saving: string | null
  onReload: () => Promise<void>
  notify: ReturnType<typeof useToast>['notify']
  t: (key: string, opts?: { defaultValue?: string }) => string
}) {
  const [leave_type, setLeaveType] = useState('urlop_wypoczynkowy')
  const [start_date, setStart] = useState('')
  const [end_date, setEnd] = useState('')

  const create = async () => {
    if (!start_date || !end_date) {
      notify({
        variant: 'error',
        title: t('app.hr.employee_detail.leave_dates_required', { defaultValue: 'Start and end dates are required' }),
      })
      return
    }
    try {
      await createWorkforceLeaveRequest(employeeId, {
        leave_type,
        start_date,
        end_date,
      })
      notify({ variant: 'success', title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }) })
      setStart('')
      setEnd('')
      await onReload()
    } catch {
      notify({
        variant: 'error',
        title: t('app.hr.employee_detail.save_error', { defaultValue: 'Could not save' }),
      })
    }
  }

  return (
    <Section title={t('app.hr.employee_detail.section_leave', { defaultValue: 'Leave requests' })}>
      {manage ? (
        <div className="flex flex-wrap gap-2 items-end mb-4 p-3 bg-slate-50/80 rounded border border-slate-100">
          <label className="text-xs flex flex-col gap-1">
            Type
            <input className="border rounded px-2 py-1 text-sm" value={leave_type} onChange={(e) => setLeaveType(e.target.value)} />
          </label>
          <label className="text-xs flex flex-col gap-1">
            Start
            <input type="date" className="border rounded px-2 py-1 text-sm" value={start_date} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="text-xs flex flex-col gap-1">
            End
            <input type="date" className="border rounded px-2 py-1 text-sm" value={end_date} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <button type="button" className="text-sm px-3 py-1.5 rounded bg-slate-900 text-white" onClick={() => void create()}>
            {t('app.hr.employee_detail.add', { defaultValue: 'Add' })}
          </button>
        </div>
      ) : null}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-600 border-b">
              <th className="py-2 pr-2">Type</th>
              <th className="py-2 pr-2">Start</th>
              <th className="py-2 pr-2">End</th>
              <th className="py-2 pr-2">Status</th>
              {manage ? <th className="py-2"> </th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((lv) => (
              <tr key={lv.id} className="border-b border-slate-50">
                <td className="py-2 pr-2">{lv.leave_type}</td>
                <td className="py-2 pr-2">{lv.start_date}</td>
                <td className="py-2 pr-2">{lv.end_date}</td>
                <td className="py-2 pr-2">{lv.status}</td>
                {manage ? (
                  <td className="py-2 flex gap-2">
                    {lv.status === 'pending' ? (
                      <>
                        <button
                          type="button"
                          className="text-xs text-green-700 hover:underline disabled:opacity-50"
                          disabled={saving === `lv-${lv.id}`}
                          onClick={async () => {
                            try {
                              await patchWorkforceLeaveRequest(lv.id, { status: 'approved' })
                              notify({ variant: 'success', title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }) })
                              await onReload()
                            } catch {
                              notify({
                                variant: 'error',
                                title: t('app.hr.employee_detail.save_error', { defaultValue: 'Could not save' }),
                              })
                            }
                          }}
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          className="text-xs text-rose-700 hover:underline disabled:opacity-50"
                          disabled={saving === `lv-${lv.id}`}
                          onClick={async () => {
                            try {
                              await patchWorkforceLeaveRequest(lv.id, { status: 'rejected' })
                              notify({ variant: 'success', title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }) })
                              await onReload()
                            } catch {
                              notify({
                                variant: 'error',
                                title: t('app.hr.employee_detail.save_error', { defaultValue: 'Could not save' }),
                              })
                            }
                          }}
                        >
                          Reject
                        </button>
                      </>
                    ) : null}
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  )
}
