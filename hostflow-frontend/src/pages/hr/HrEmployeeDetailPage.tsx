import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useI18n } from '../../i18n'
import {
  createWorkforceAbsence,
  createWorkforceEmployment,
  createWorkforceLeaveRequest,
  candDocRecordsToEmployeeDocumentRows,
  getWorkforceEmployeeOperationalProfile,
  getWorkforceHrReview,
  type HrReviewPanel,
  patchWorkforceAbsence,
  patchWorkforceComplianceState,
  patchWorkforceEmployee,
  patchWorkforceEmployment,
  patchWorkforceInsuranceProfile,
  patchWorkforceLeaveRequest,
  patchWorkforceOnboardingTask,
  patchWorkforcePayrollProfile,
  patchWorkforceTaxProfile,
  patchWorkforceWorkEligibility,
  patchWorkforceWorkEligibilityPaymentRequirement,
  patchWorkforceZusProfile,
  type WorkforceComplianceState,
  type WorkforceEmployee,
  type WorkforceEmployeeOperationalProfile,
  type WorkforceHrBundle,
  type WorkforceInsuranceProfile,
  type WorkforceTaxProfile,
  type WorkforceWorkEligibilityPaymentRequirement,
} from '../../api/workforce'
import { usePermissions } from '../../hooks/usePermissions'
import { useToast } from '../../components/Toast'
import { PageBreadcrumb } from '../../components/nav/PageBreadcrumb'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { HrEmployeeDocumentsSection } from './HrEmployeeDocumentsSection'
import WorkEligibilityJourneyWorkspace from '../../components/hr/WorkEligibilityJourneyWorkspace'
import HrRecruitmentTransferSummary from '../../components/hr/HrRecruitmentTransferSummary'
import HrLegalDocumentChecklist from '../../components/hr/HrLegalDocumentChecklist'
import { HrEmployeeRightColumn } from '../../components/hr/HrEmployeeRightColumn'
import HrReviewPanelCard from '../../components/hr/HrReviewPanel'
import HrReviewCaseHero from '../../components/hr/HrReviewCaseHero'
import HrNextActionRail from '../../components/hr/HrNextActionRail'
import HrDataVerificationWorkspace from '../../components/hr/HrDataVerificationWorkspace'
import HrContractPreviewPanel from '../../components/hr/HrContractPreviewPanel'
import HrWorkEligibilityCompact from '../../components/hr/HrWorkEligibilityCompact'
import { HrCurrentTaskPanelFromReview } from '../../components/hr/HrCurrentTaskPanel'
import { formatShortDateIso } from '../../components/hr/hrEmployeeUiFormat'
import { isEmploymentCaseWorkspace, isEmployeeOperationalProfile } from '../../utils/hrEmploymentCaseMode'

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

/** Legal insurance profile row (not ZUS registration workflow). */
const INSURANCE_LEGAL_STATUSES = ['draft', 'registered', 'suspended', 'deregistered'] as const

/** `datetime-local` value from an API ISO string (local wall time). */
function isoToDatetimeLocalValue(iso: string | null | undefined): string {
  if (iso == null || iso === '') return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

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
  defaultOpen = true,
  id,
}: {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
  id?: string
}) {
  return (
    <details {...(defaultOpen ? { open: true } : {})} id={id} className="border border-slate-200 rounded-lg bg-white">
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
  const [profile, setProfile] = useState<WorkforceEmployeeOperationalProfile | null>(null)
  const [hrReview, setHrReview] = useState<HrReviewPanel | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)

  const employee = profile?.employee ?? null
  const bundle = profile?.hr_bundle ?? null

  const manage = can('workforce.manage')
  const caseWorkspace = isEmploymentCaseWorkspace(hrReview)

  const scrollToAnchor = (anchor: string) => {
    const sel = anchor.startsWith('#') ? anchor : `#${anchor}`
    document.querySelector(sel)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const load = useCallback(async () => {
    if (!employeeId) return
    setLoading(true)
    try {
      const [p, review] = await Promise.all([
        getWorkforceEmployeeOperationalProfile(employeeId),
        getWorkforceHrReview(employeeId).catch(() => null),
      ])
      setProfile(p)
      setHrReview(review)
    } catch {
      setProfile(null)
      setHrReview(null)
      notify({
        variant: 'error',
        title: t('app.hr.employee_detail.load_error', { defaultValue: 'Could not load employee' }),
      })
    } finally {
      setLoading(false)
    }
  }, [employeeId, notify, t])

  const refreshProfile = useCallback(async () => {
    if (!employeeId) return
    try {
      const p = await getWorkforceEmployeeOperationalProfile(employeeId)
      setProfile(p)
    } catch {
      /* keep current profile; review panel already reflects latest HR review */
    }
  }, [employeeId])

  useEffect(() => {
    if (can('workforce.view') && employeeId) void load()
  }, [can, employeeId, load])

  const prefetchedDocRows = useMemo(() => {
    if (!profile) return undefined
    return candDocRecordsToEmployeeDocumentRows((profile.documents_linked || []) as Array<Record<string, unknown>>)
  }, [profile])

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
        {t('app.nav.hr.employees.forbidden', { defaultValue: 'You do not have access to the HR workspace.' })}
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
        <Link
          className="text-sm text-brand-600 hover:underline"
          to={caseWorkspace ? CRM_APP_PATHS.hrInbox : CRM_APP_PATHS.hrEmployees}
        >
          {caseWorkspace
            ? t('app.hr.review_case.back_to_inbox', { defaultValue: '← Back to HR inbox' })
            : t('app.hr.employee_detail.back_list', { defaultValue: '← Back to employees' })}
        </Link>
      </div>
    )
  }

  return (
    <div className="hr-employee-workspace w-full min-w-0">
      <div className="w-full min-w-0">
        <PageBreadcrumb
          items={[
            { to: CRM_APP_PATHS.overview, label: t('app.nav.items.overview', { defaultValue: 'Insights' }) },
            {
              to: caseWorkspace ? CRM_APP_PATHS.hrInbox : CRM_APP_PATHS.hrEmployees,
              label: caseWorkspace
                ? t('app.nav.items.hr_inbox', { defaultValue: 'HR Inbox' })
                : t('app.nav.items.hr_employees', { defaultValue: 'HR · Employees' }),
            },
            {
              label: caseWorkspace
                ? `${t('app.hr.review_case.badge', { defaultValue: 'HR review case' })} · ${employee.display_name}`
                : employee.display_name,
            },
          ]}
        />

        <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
          {!caseWorkspace ? (
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-slate-900">{employee.display_name}</h1>
              <p className="mt-1 font-mono text-xs text-slate-500">{employee.id}</p>
            </div>
          ) : null}
          <Link
            to={caseWorkspace ? CRM_APP_PATHS.hrInbox : CRM_APP_PATHS.hrEmployees}
            className="text-sm text-slate-600 underline-offset-2 hover:text-slate-900 hover:underline"
          >
            {caseWorkspace
              ? t('app.hr.review_case.back_to_inbox', { defaultValue: '← Back to HR inbox' })
              : t('app.hr.employee_detail.back_list', { defaultValue: '← Back to employees' })}
          </Link>
        </div>

        {hrReview ? <HrReviewCaseHero panel={hrReview} displayName={employee.display_name} /> : null}

        <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_22rem] 2xl:grid-cols-[minmax(0,1fr)_26rem] xl:items-start">
          <div className="min-w-0 space-y-4">
            {caseWorkspace && hrReview ? (
              <HrCurrentTaskPanelFromReview panel={hrReview} onScrollTo={scrollToAnchor} />
            ) : null}
            {hrReview && (caseWorkspace || isEmployeeOperationalProfile(hrReview)) ? (
              <HrDataVerificationWorkspace
                panel={hrReview}
                employeeId={employeeId}
                handoffId={hrReview.handoff_id ?? undefined}
                manage={manage}
                onPanelUpdated={(next) => {
                  setHrReview(next)
                  void refreshProfile()
                }}
              />
            ) : null}
            {hrReview ? (
              <HrReviewPanelCard
                employeeId={employeeId}
                handoffId={hrReview.handoff_id ?? undefined}
                panel={hrReview}
                hideDocuments
                manage={manage}
                onUpdated={(next) => {
                  setHrReview(next)
                  void refreshProfile()
                }}
              />
            ) : null}
            {employeeId && hrReview && (caseWorkspace || isEmployeeOperationalProfile(hrReview)) ? (
              <details className="rounded-lg border border-slate-200 bg-white">
                <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-900">
                  {t('app.hr.contract_preview.section', { defaultValue: 'Contract draft preview' })}
                </summary>
                <div className="border-t border-slate-100 px-2 pb-2">
                  <HrContractPreviewPanel
                    employeeId={employeeId}
                    manage={manage}
                    ownCompanyId={employee?.own_company_id ?? undefined}
                  />
                </div>
              </details>
            ) : null}
            {caseWorkspace ? (
              <HrWorkEligibilityCompact
                panel={hrReview!}
                employeeId={employeeId}
                manage={manage}
                onRefresh={() => void refreshProfile()}
              />
            ) : null}
            {caseWorkspace && profile ? (
              <Section
                title={t('app.hr.employee_operational.section_source', { defaultValue: 'Recruitment handoff' })}
                defaultOpen
              >
                <p className="text-xs text-slate-600 mb-3">
                  {t('app.hr.review_case.handoff_summary_hint', {
                    defaultValue:
                      'Read-only context from recruitment at hire. Verify documents in the approval list above.',
                  })}
                </p>
                <HrRecruitmentTransferSummary profile={profile} linkedDocRows={prefetchedDocRows} compact />
              </Section>
            ) : null}
            {!caseWorkspace ? (
              <>
            <Section title={t('app.hr.employee_operational.section_employment', { defaultValue: 'Employment' })}>
        {profile && profile.employment_operational.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b text-slate-600">
                  <th className="py-2 pr-2">{t('app.hr.employee_operational.col_contract', { defaultValue: 'Contract' })}</th>
                  <th className="py-2 pr-2">{t('app.hr.employee_operational.col_position', { defaultValue: 'Position' })}</th>
                  <th className="py-2 pr-2">{t('app.hr.employee_operational.col_start', { defaultValue: 'Start' })}</th>
                  <th className="py-2 pr-2">{t('app.hr.employee_operational.col_end', { defaultValue: 'End' })}</th>
                  <th className="py-2 pr-2">{t('app.hr.employee_operational.col_probation', { defaultValue: 'Probation' })}</th>
                  <th className="py-2">{t('app.hr.employee_operational.col_active', { defaultValue: 'Active' })}</th>
                </tr>
              </thead>
              <tbody>
                {profile.employment_operational.map((row) => (
                  <tr key={row.id} className="border-b border-slate-50">
                    <td className="py-2 pr-2 font-mono text-xs">{row.contract_type}</td>
                    <td className="py-2 pr-2">{row.position || '—'}</td>
                    <td className="py-2 pr-2">{formatShortDateIso(row.start_date)}</td>
                    <td className="py-2 pr-2">{formatShortDateIso(row.end_date)}</td>
                    <td className="py-2 pr-2">{formatShortDateIso(row.probation_end)}</td>
                    <td className="py-2">{row.is_active ? '✓' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            {t('app.hr.employee_operational.no_employment_rows', { defaultValue: 'No employment rows yet.' })}
          </p>
        )}
      </Section>

      <Section title={t('app.hr.employee_operational.section_compliance', { defaultValue: 'Compliance & risk' })}>
        <p className="mb-3 text-sm text-slate-600 xl:hidden">
          {t('app.hr.employee_operational.alerts_in_rail_hint', {
            defaultValue: 'On wide screens, active alerts and timeline appear in the operational column on the right.',
          })}
        </p>
        {profile && profile.risks.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-slate-600 border-b">
                  <th className="py-1 pr-2">{t('app.hr.employee_operational.risk_code', { defaultValue: 'Code' })}</th>
                  <th className="py-1 pr-2">{t('app.hr.employee_operational.risk_severity', { defaultValue: 'Severity' })}</th>
                  <th className="py-1">{t('app.hr.employee_operational.risk_reason', { defaultValue: 'Reason' })}</th>
                </tr>
              </thead>
              <tbody>
                {profile.risks.slice(0, 20).map((r, i) => (
                  <tr key={i} className="border-b border-slate-50">
                    <td className="py-1 pr-2 font-mono">{String(r.risk_code ?? '—')}</td>
                    <td className="py-1 pr-2">{String(r.severity ?? '—')}</td>
                    <td className="py-1">{String(r.reason ?? r.message ?? '—')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            {t('app.hr.employee_operational.no_risk_rows', { defaultValue: 'No risk rows in the read-model.' })}
          </p>
        )}
      </Section>

      <HrEmployeeDocumentsSection
        employeeId={employeeId}
        candidateId={employee.candidate_id}
        prefetchedRows={prefetchedDocRows}
        missingQueue={profile?.documents_missing}
        expiringQueue={profile?.documents_expiring}
      />

      <Section
        id="hr-employee-work-eligibility"
        defaultOpen
        title={t('app.hr.work_eligibility.section_title', {
          defaultValue: 'Work eligibility & statutory fees',
        })}
      >
        <WorkEligibilityJourneyWorkspace
          employeeId={employeeId}
          profile={bundle.work_eligibility_profile ?? null}
          paymentRequirements={bundle.work_eligibility_payment_requirements ?? []}
          docSummary={
            bundle.hr_document_context_summary ?? {
              total: 0,
              by_context_type: {},
              items: [],
            }
          }
          timeline={profile?.timeline ?? []}
          manage={manage}
          saving={saving}
          onSaveEligibility={(payload) =>
            runSave('work_eligibility', () => patchWorkforceWorkEligibility(employeeId, payload))
          }
          onSavePayment={(rid, payload) =>
            runSave(`wel_pay_${rid}`, () =>
              patchWorkforceWorkEligibilityPaymentRequirement(employeeId, rid, payload),
            )
          }
        />
      </Section>

      <Section title={t('app.hr.employee_operational.section_source', { defaultValue: 'Recruitment handoff' })} defaultOpen>
        <p className="text-xs text-slate-600 mb-3">
          {t('app.hr.employee_operational.source_hint', {
            defaultValue:
              'Read-only context from recruitment at hire. Day-to-day HR work lives in tasks, documents, and workflows above.',
          })}
        </p>
        {profile ? <HrRecruitmentTransferSummary profile={profile} linkedDocRows={prefetchedDocRows} /> : null}
      </Section>

      <OverviewSection
        employee={employee}
        manage={manage}
        saving={saving}
        onSave={(payload) =>
          runSave('overview', () => patchWorkforceEmployee(employeeId, payload))
        }
      />

      <PayrollSection
        profile={bundle.payroll_profile}
        manage={manage}
        saving={saving === 'payroll'}
        defaultOpen={false}
        onSave={(payload) =>
          runSave('payroll', () => patchWorkforcePayrollProfile(employeeId, payload))
        }
      />

      <ZusSection
        profile={bundle.zus_profile}
        manage={manage}
        saving={saving === 'zus'}
        defaultOpen={false}
        onSave={(payload) => runSave('zus', () => patchWorkforceZusProfile(employeeId, payload))}
      />

      <LegalTaxProfileSection
        profile={bundle.tax_profile ?? null}
        manage={manage}
        saving={saving === 'legal_tax'}
        defaultOpen={false}
        onSave={(payload) => runSave('legal_tax', () => patchWorkforceTaxProfile(employeeId, payload))}
      />

      <LegalInsuranceProfileSection
        profile={bundle.insurance_profile ?? null}
        manage={manage}
        saving={saving === 'legal_insurance'}
        defaultOpen={false}
        onSave={(payload) => runSave('legal_insurance', () => patchWorkforceInsuranceProfile(employeeId, payload))}
      />

      <StoredComplianceStateSection
        state={bundle.compliance_state ?? null}
        manage={manage}
        saving={saving === 'legal_compliance'}
        defaultOpen={false}
        onSave={(payload) => runSave('legal_compliance', () => patchWorkforceComplianceState(employeeId, payload))}
        notify={notify}
      />

      <Section
        defaultOpen={false}
        title={t('app.hr.employee_operational.section_legal_documents', { defaultValue: 'Legal document checklist' })}
      >
        <HrLegalDocumentChecklist
          summary={
            bundle.hr_document_context_summary ?? {
              total: 0,
              by_context_type: {},
              items: [],
            }
          }
        />
      </Section>

      <EmploymentsSection
        employeeId={employeeId}
        rows={bundle.employments}
        manage={manage}
        saving={saving}
        onReload={load}
        notify={notify}
        t={t}
        defaultOpen={false}
      />

      <OnboardingSection
        tasks={bundle.onboarding_tasks}
        manage={manage}
        saving={saving}
        overdueCount={profile?.onboarding_overdue_count ?? 0}
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
        defaultOpen={false}
      />

      <LeaveSection
        employeeId={employeeId}
        rows={bundle.leave_requests}
        manage={manage}
        saving={saving}
        onReload={load}
        notify={notify}
        t={t}
        defaultOpen={false}
      />
              </>
            ) : null}
          </div>
          {profile ? (
            <aside className="min-w-0 xl:sticky xl:top-4 xl:self-start">
              {caseWorkspace && hrReview ? (
                <HrNextActionRail
                  panel={hrReview}
                  employeeId={employeeId}
                  profileAlerts={profile.alerts}
                  profileTimeline={profile.timeline}
                  onScrollTo={scrollToAnchor}
                />
              ) : (
                <HrEmployeeRightColumn employeeId={employeeId} profile={profile} bundle={bundle} hrReview={hrReview} />
              )}
            </aside>
          ) : null}
        </div>
      </div>
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
          {t('app.nav.hr.employees.display_name', { defaultValue: 'Full name' })}
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            value={display_name}
            disabled={!manage}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.nav.hr.employees.col_status', { defaultValue: 'Status' })}
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
          {t('app.nav.hr.employees.col_hire', { defaultValue: 'Hire date' })}
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
  defaultOpen = true,
}: {
  profile: WorkforceHrBundle['payroll_profile']
  manage: boolean
  saving: boolean
  onSave: (p: Parameters<typeof patchWorkforcePayrollProfile>[1]) => void
  defaultOpen?: boolean
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
      <Section
        defaultOpen={defaultOpen}
        title={t('app.hr.employee_detail.section_payroll', { defaultValue: 'Payroll profile' })}
      >
        <p className="text-sm text-slate-500">{t('app.hr.employee_detail.no_payroll', { defaultValue: 'No payroll row yet.' })}</p>
      </Section>
    )
  }

  return (
    <Section defaultOpen={defaultOpen} title={t('app.hr.employee_detail.section_payroll', { defaultValue: 'Payroll profile' })}>
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
  defaultOpen = true,
}: {
  profile: WorkforceHrBundle['zus_profile']
  manage: boolean
  saving: boolean
  onSave: (p: Parameters<typeof patchWorkforceZusProfile>[1]) => void
  defaultOpen?: boolean
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
      <Section defaultOpen={defaultOpen} title={t('app.hr.employee_detail.section_zus', { defaultValue: 'ZUS' })}>
        <p className="text-sm text-slate-500">{t('app.hr.employee_detail.no_zus', { defaultValue: 'No ZUS row yet.' })}</p>
      </Section>
    )
  }

  return (
    <Section defaultOpen={defaultOpen} title={t('app.hr.employee_detail.section_zus', { defaultValue: 'ZUS' })}>
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

function WorkEligibilitySection({
  employeeId,
  profile,
  paymentRequirements,
  manage,
  saving,
  onSaveEligibility,
  onSavePayment,
  t,
}: {
  employeeId: string
  profile: WorkforceWorkEligibilityProfile | null
  paymentRequirements: WorkforceWorkEligibilityPaymentRequirement[]
  manage: boolean
  saving: string | null
  onSaveEligibility: (p: Record<string, unknown>) => Promise<void>
  onSavePayment: (rid: string, p: Record<string, unknown>) => Promise<void>
  t: ReturnType<typeof useI18n>['t']
}) {
  const [journey, setJourney] = useState<WorkEligibilityJourney | null>(null)
  const [journeyLoading, setJourneyLoading] = useState(true)

  const paySig = paymentRequirements.map((r) => `${r.id}:${r.payment_status}:${r.updated_at}`).join('|')

  const reloadJourney = useCallback(async () => {
    setJourneyLoading(true)
    try {
      const j = await getWorkEligibilityJourney(employeeId)
      setJourney(j)
    } catch {
      setJourney(null)
    } finally {
      setJourneyLoading(false)
    }
  }, [employeeId])

  useEffect(() => {
    void reloadJourney()
  }, [employeeId, profile?.updated_at, paySig, reloadJourney])

  const [citizenship, setCitizenship] = useState(profile?.citizenship || '')
  const [positionCategory, setPositionCategory] = useState(profile?.position_category || '')
  const [eligibilityStatus, setEligibilityStatus] = useState(profile?.eligibility_status || 'not_evaluated')
  const [requiresPermit, setRequiresPermit] = useState<boolean>(profile?.requires_work_permit !== false)
  const [appStatus, setAppStatus] = useState(profile?.work_permit_application_status || '')
  const [redPaper, setRedPaper] = useState(profile?.red_paper_status || '')

  useEffect(() => {
    if (!profile) return
    setCitizenship(profile.citizenship || '')
    setPositionCategory(profile.position_category || '')
    setEligibilityStatus(profile.eligibility_status || 'not_evaluated')
    setRequiresPermit(profile.requires_work_permit !== false)
    setAppStatus(profile.work_permit_application_status || '')
    setRedPaper(profile.red_paper_status || '')
  }, [profile])

  return (
    <Section
      defaultOpen
      title={t('app.hr.work_eligibility.section_title', {
        defaultValue: 'Work eligibility & statutory fees',
      })}
    >
      <div className="mb-6 rounded-lg border border-slate-200 bg-slate-50/80 p-4">
        <h3 className="text-sm font-semibold text-slate-900 mb-1">
          {t('app.hr.work_eligibility.journey_title', { defaultValue: 'Work eligibility journey' })}
        </h3>
        {journeyLoading ? (
          <p className="text-xs text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
        ) : journey ? (
          <>
            <p className="text-sm text-slate-700 mb-3">{journey.recommended_next_action}</p>
            <ol className="space-y-2">
              {journey.steps.map((step) => (
                <li
                  key={step.step_code}
                  className="flex flex-wrap items-start gap-2 text-sm border border-slate-200 rounded-md bg-white px-3 py-2"
                >
                  <span
                    className={`mt-0.5 inline-flex h-6 min-w-[4.5rem] items-center justify-center rounded text-xs font-medium ${
                      step.status === 'done' || step.status === 'not_required'
                        ? 'bg-slate-200 text-slate-700'
                        : step.status === 'current'
                          ? 'bg-indigo-600 text-white'
                          : step.status === 'blocked'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-amber-100 text-amber-900'
                    }`}
                  >
                    {step.status}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-slate-900">{step.label}</div>
                    <div className="text-xs text-slate-500 font-mono">{step.step_code}</div>
                    {(step.blockers?.length ?? 0) > 0 ? (
                      <div className="text-xs text-rose-700 mt-1">
                        {(step.blockers ?? []).join(' · ')}
                      </div>
                    ) : null}
                    {(step.required_documents?.length ?? 0) > 0 ? (
                      <div className="text-xs text-slate-600 mt-1">
                        Docs: {(step.required_documents ?? []).join(', ')}
                      </div>
                    ) : null}
                    {step.action_label ? (
                      <div className="text-xs text-slate-700 mt-1">{step.action_label}</div>
                    ) : null}
                    {step.external_submission_url ? (
                      <a
                        href={step.external_submission_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-indigo-700 underline mt-1 inline-block"
                      >
                        {t('app.hr.work_eligibility.external_link', { defaultValue: 'External portal' })}
                      </a>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
          </>
        ) : (
          <p className="text-xs text-rose-700">
            {t('app.hr.work_eligibility.journey_error', { defaultValue: 'Could not load journey.' })}
          </p>
        )}
      </div>

      <details className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50">
        <summary className="cursor-pointer select-none px-3 py-2 text-xs font-medium text-slate-600">
          {t('app.hr.work_eligibility.raw_toggle', {
            defaultValue: 'Raw eligibility fields & payment rows (advanced)',
          })}
        </summary>
        <div className="px-3 pb-4 pt-1 border-t border-slate-100">
          {!profile ? (
            <p className="text-sm text-slate-500">
              {t('app.hr.work_eligibility.no_profile', { defaultValue: 'No work eligibility profile yet.' })}
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 max-w-2xl">
              <label className="flex flex-col gap-1 text-xs text-slate-600">
                {t('app.hr.work_eligibility.citizenship', { defaultValue: 'Citizenship (ISO2)' })}
                <input
                  className="border border-slate-200 rounded px-2 py-1.5 text-sm"
                  disabled={!manage}
                  value={citizenship}
                  onChange={(e) => setCitizenship(e.target.value.toUpperCase())}
                  maxLength={8}
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-slate-600">
                {t('app.hr.work_eligibility.position', { defaultValue: 'Position category' })}
                <input
                  className="border border-slate-200 rounded px-2 py-1.5 text-sm"
                  disabled={!manage}
                  value={positionCategory}
                  onChange={(e) => setPositionCategory(e.target.value)}
                  placeholder="driver"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-slate-600">
                {t('app.hr.work_eligibility.status', { defaultValue: 'Eligibility status' })}
                <input
                  className="border border-slate-200 rounded px-2 py-1.5 text-sm"
                  disabled={!manage}
                  value={eligibilityStatus}
                  onChange={(e) => setEligibilityStatus(e.target.value)}
                />
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-600 mt-5">
                <input
                  type="checkbox"
                  disabled={!manage}
                  checked={requiresPermit}
                  onChange={(e) => setRequiresPermit(e.target.checked)}
                />
                {t('app.hr.work_eligibility.requires_permit', { defaultValue: 'Requires work permit' })}
              </label>
              <label className="flex flex-col gap-1 text-xs text-slate-600">
                {t('app.hr.work_eligibility.permit_app', { defaultValue: 'Work permit application status' })}
                <input
                  className="border border-slate-200 rounded px-2 py-1.5 text-sm"
                  disabled={!manage}
                  value={appStatus}
                  onChange={(e) => setAppStatus(e.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-slate-600">
                {t('app.hr.work_eligibility.red_paper', { defaultValue: 'Red paper status' })}
                <input
                  className="border border-slate-200 rounded px-2 py-1.5 text-sm"
                  disabled={!manage}
                  value={redPaper}
                  onChange={(e) => setRedPaper(e.target.value)}
                />
              </label>
              {manage ? (
                <div className="sm:col-span-2">
                  <button
                    type="button"
                    disabled={saving === 'work_eligibility'}
                    className="px-3 py-1.5 rounded text-sm font-medium bg-slate-900 text-white disabled:opacity-50"
                    onClick={() =>
                      void onSaveEligibility({
                        citizenship: citizenship.trim() || null,
                        position_category: positionCategory.trim() || null,
                        eligibility_status: eligibilityStatus.trim() || null,
                        requires_work_permit: requiresPermit,
                        work_permit_application_status: appStatus.trim() || null,
                        red_paper_status: redPaper.trim() || null,
                      }).then(() => {
                        void reloadJourney()
                      })
                    }
                  >
                    {t('app.hr.employee_detail.save', { defaultValue: 'Save' })}
                  </button>
                </div>
              ) : null}
            </div>
          )}

          <div className="mt-6 border-t border-slate-100 pt-4">
            <h3 className="text-sm font-semibold text-slate-900 mb-2">
              {t('app.hr.work_eligibility.payments_title', { defaultValue: 'Work eligibility payments' })}
            </h3>
            {paymentRequirements.length === 0 ? (
              <p className="text-xs text-slate-500">
                {t('app.hr.work_eligibility.payments_empty', {
                  defaultValue: 'No fee rows. They appear for third-country drivers when position is set to driver.',
                })}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm border border-slate-200 rounded">
                  <thead className="bg-slate-50 text-left text-xs text-slate-600">
                    <tr>
                      <th className="px-2 py-2">{t('app.hr.work_eligibility.col_type', { defaultValue: 'Type' })}</th>
                      <th className="px-2 py-2">{t('app.hr.work_eligibility.col_amount', { defaultValue: 'Amount' })}</th>
                      <th className="px-2 py-2">{t('app.hr.work_eligibility.col_status', { defaultValue: 'Status' })}</th>
                      <th className="px-2 py-2">{t('app.hr.work_eligibility.col_blocks', { defaultValue: 'Blocks' })}</th>
                      <th className="px-2 py-2">
                        {t('app.hr.work_eligibility.col_reference', { defaultValue: 'Reference' })}
                      </th>
                      <th className="px-2 py-2">
                        {t('app.hr.work_eligibility.col_receipt', { defaultValue: 'Receipt doc id' })}
                      </th>
                      <th className="px-2 py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {paymentRequirements.map((row) => (
                      <PaymentRequirementRow
                        key={row.id}
                        row={row}
                        manage={manage}
                        saving={saving === `wel_pay_${row.id}`}
                        onMarkWaived={() =>
                          void onSavePayment(row.id, { payment_status: 'waived' }).then(() => {
                            void reloadJourney()
                          })
                        }
                        onSaveDetails={(patch) =>
                          void onSavePayment(row.id, patch).then(() => {
                            void reloadJourney()
                          })
                        }
                        t={t}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </details>
    </Section>
  )
}

function PaymentRequirementRow({
  row,
  manage,
  saving,
  onMarkWaived,
  onSaveDetails,
  t,
}: {
  row: WorkforceWorkEligibilityPaymentRequirement
  manage: boolean
  saving: boolean
  onMarkWaived: () => void
  onSaveDetails: (p: Record<string, unknown>) => void
  t: ReturnType<typeof useI18n>['t']
}) {
  const [reference, setReference] = useState(row.payment_reference || '')
  const [receiptId, setReceiptId] = useState(row.receipt_document_id || '')
  useEffect(() => {
    setReference(row.payment_reference || '')
    setReceiptId(row.receipt_document_id || '')
  }, [row.payment_reference, row.receipt_document_id])

  return (
    <tr className="border-t border-slate-100">
      <td className="px-2 py-2 font-mono text-xs">{row.requirement_type}</td>
      <td className="px-2 py-2">
        {row.amount ?? '—'} {row.currency}
      </td>
      <td className="px-2 py-2">{row.payment_status}</td>
      <td className="px-2 py-2 text-xs text-slate-600">{row.blocks_step ?? '—'}</td>
      <td className="px-2 py-2">
        <input
          className="border border-slate-200 rounded px-1 py-0.5 text-xs w-full max-w-[140px]"
          disabled={!manage}
          value={reference}
          onChange={(e) => setReference(e.target.value)}
        />
      </td>
      <td className="px-2 py-2">
        <input
          className="border border-slate-200 rounded px-1 py-0.5 text-xs w-full max-w-[120px]"
          disabled={!manage}
          value={receiptId}
          onChange={(e) => setReceiptId(e.target.value)}
        />
      </td>
      <td className="px-2 py-2 whitespace-nowrap">
        {manage ? (
          <div className="flex flex-wrap gap-1">
            <button
              type="button"
              disabled={saving}
              className="text-xs px-2 py-0.5 rounded bg-emerald-700 text-white disabled:opacity-50"
              onClick={() => {
                onSaveDetails({
                  payment_reference: reference.trim() || null,
                  receipt_document_id: receiptId.trim() || null,
                  payment_status: 'paid',
                })
              }}
            >
              {t('app.hr.work_eligibility.mark_paid', { defaultValue: 'Mark paid' })}
            </button>
            <button
              type="button"
              disabled={saving}
              className="text-xs px-2 py-0.5 rounded border border-slate-300 disabled:opacity-50"
              onClick={onMarkWaived}
            >
              {t('app.hr.work_eligibility.waive', { defaultValue: 'Waive' })}
            </button>
            <button
              type="button"
              disabled={saving}
              className="text-xs px-2 py-0.5 rounded border border-slate-300 disabled:opacity-50"
              onClick={() =>
                onSaveDetails({
                  payment_reference: reference.trim() || null,
                  receipt_document_id: receiptId.trim() || null,
                })
              }
            >
              {t('app.hr.work_eligibility.save_ref', { defaultValue: 'Save ref' })}
            </button>
          </div>
        ) : null}
      </td>
    </tr>
  )
}

function LegalTaxProfileSection({
  profile,
  manage,
  saving,
  onSave,
  defaultOpen = true,
}: {
  profile: WorkforceTaxProfile | null
  manage: boolean
  saving: boolean
  onSave: (p: Parameters<typeof patchWorkforceTaxProfile>[1]) => void
  defaultOpen?: boolean
}) {
  const { t } = useI18n()
  const [tax_residency_country, setResidency] = useState(profile?.tax_residency_country || '')
  const [tax_office, setOffice] = useState(profile?.tax_office || '')
  const [pit2_submitted, setPit2] = useState(Boolean(profile?.pit2_submitted))
  const [pit2_monthly_amount, setPit2Amt] = useState(
    profile?.pit2_monthly_amount != null ? String(profile.pit2_monthly_amount) : '',
  )
  const [tax_deductible_costs_type, setCosts] = useState(profile?.tax_deductible_costs_type || '')
  const [young_person_relief, setYoung] = useState(Boolean(profile?.young_person_relief))

  useEffect(() => {
    if (!profile) return
    setResidency(profile.tax_residency_country || '')
    setOffice(profile.tax_office || '')
    setPit2(Boolean(profile.pit2_submitted))
    setPit2Amt(profile.pit2_monthly_amount != null ? String(profile.pit2_monthly_amount) : '')
    setCosts(profile.tax_deductible_costs_type || '')
    setYoung(Boolean(profile.young_person_relief))
  }, [profile])

  if (!profile) {
    return (
      <Section
        defaultOpen={defaultOpen}
        title={t('app.hr.employee_legal.section_tax', { defaultValue: 'Tax profile (legal)' })}
      >
        <p className="text-sm text-slate-500">
          {t('app.hr.employee_legal.no_tax_profile', { defaultValue: 'No tax profile row yet.' })}
        </p>
      </Section>
    )
  }

  return (
    <Section
      defaultOpen={defaultOpen}
      title={t('app.hr.employee_legal.section_tax', { defaultValue: 'Tax profile (legal)' })}
    >
      <p className="text-xs text-slate-600 mb-3">
        {t('app.hr.employee_legal.tax_hint', {
          defaultValue: 'PIT-oriented legal fields. This is not payroll calculation.',
        })}
      </p>
      <div className="grid gap-3 sm:grid-cols-2 max-w-2xl">
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.tax_residency', { defaultValue: 'Tax residency (country code)' })}
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm font-mono uppercase"
            disabled={!manage}
            value={tax_residency_country}
            onChange={(e) => setResidency(e.target.value)}
            maxLength={8}
            placeholder="PL"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.tax_office', { defaultValue: 'Tax office' })}
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={tax_office}
            onChange={(e) => setOffice(e.target.value)}
          />
        </label>
        <label className="flex flex-row items-center gap-2 text-xs text-slate-600">
          <input type="checkbox" disabled={!manage} checked={pit2_submitted} onChange={(e) => setPit2(e.target.checked)} />
          {t('app.hr.employee_legal.pit2_submitted', { defaultValue: 'PIT-2 submitted' })}
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.pit2_monthly', { defaultValue: 'PIT-2 monthly amount' })}
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={pit2_monthly_amount}
            onChange={(e) => setPit2Amt(e.target.value)}
            placeholder="0.00"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_legal.deductible_costs', { defaultValue: 'Tax-deductible costs type' })}
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={tax_deductible_costs_type}
            onChange={(e) => setCosts(e.target.value)}
          />
        </label>
        <label className="flex flex-row items-center gap-2 text-xs text-slate-600 sm:col-span-2">
          <input type="checkbox" disabled={!manage} checked={young_person_relief} onChange={(e) => setYoung(e.target.checked)} />
          {t('app.hr.employee_legal.young_relief', { defaultValue: 'Young person relief' })}
        </label>
      </div>
      {manage ? (
        <button
          type="button"
          disabled={saving}
          className="mt-3 px-3 py-1.5 rounded text-sm font-medium bg-slate-900 text-white disabled:opacity-50"
          onClick={() =>
            onSave({
              tax_residency_country: tax_residency_country.trim() || null,
              tax_office: tax_office.trim() || null,
              pit2_submitted,
              pit2_monthly_amount: pit2_monthly_amount.trim() || null,
              tax_deductible_costs_type: tax_deductible_costs_type.trim() || null,
              young_person_relief,
            })
          }
        >
          {t('app.hr.employee_detail.save', { defaultValue: 'Save' })}
        </button>
      ) : null}
    </Section>
  )
}

function LegalInsuranceProfileSection({
  profile,
  manage,
  saving,
  onSave,
  defaultOpen = true,
}: {
  profile: WorkforceInsuranceProfile | null
  manage: boolean
  saving: boolean
  onSave: (p: Parameters<typeof patchWorkforceInsuranceProfile>[1]) => void
  defaultOpen?: boolean
}) {
  const { t } = useI18n()
  const [zus_title_code, setTitle] = useState(profile?.zus_title_code || '')
  const [social_insurance, setSocial] = useState(profile?.social_insurance || '')
  const [health_insurance, setHealth] = useState(profile?.health_insurance || '')
  const [sickness_insurance, setSick] = useState(profile?.sickness_insurance || '')
  const [accident_insurance, setAcc] = useState(profile?.accident_insurance || '')
  const [zus_registration_type, setRegType] = useState(profile?.zus_registration_type || '')
  const [registered_at, setRegAt] = useState(profile?.registered_at || '')
  const [deregistered_at, setDereg] = useState(profile?.deregistered_at || '')
  const [status, setStatus] = useState(profile?.status || 'draft')

  useEffect(() => {
    if (!profile) return
    setTitle(profile.zus_title_code || '')
    setSocial(profile.social_insurance || '')
    setHealth(profile.health_insurance || '')
    setSick(profile.sickness_insurance || '')
    setAcc(profile.accident_insurance || '')
    setRegType(profile.zus_registration_type || '')
    setRegAt(profile.registered_at || '')
    setDereg(profile.deregistered_at || '')
    setStatus(profile.status || 'draft')
  }, [profile])

  if (!profile) {
    return (
      <Section
        defaultOpen={defaultOpen}
        title={t('app.hr.employee_legal.section_insurance', { defaultValue: 'Insurance / ZUS (legal)' })}
      >
        <p className="text-sm text-slate-500">
          {t('app.hr.employee_legal.no_insurance', { defaultValue: 'No insurance profile row yet.' })}
        </p>
      </Section>
    )
  }

  return (
    <Section
      defaultOpen={defaultOpen}
      title={t('app.hr.employee_legal.section_insurance', { defaultValue: 'Insurance / ZUS (legal)' })}
    >
      <p className="text-xs text-slate-600 mb-3">
        {t('app.hr.employee_legal.insurance_hint', {
          defaultValue:
            'Legal insurance materialisation. Distinct from the “ZUS” registration section above (workflow / forms).',
        })}
      </p>
      <div className="grid gap-3 sm:grid-cols-2 max-w-2xl">
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.zus_title_code', { defaultValue: 'ZUS title code' })}
          <input
            className="border border-slate-200 rounded px-2 py-1.5 text-sm font-mono"
            disabled={!manage}
            value={zus_title_code}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.insurance_status', { defaultValue: 'Profile status' })}
          <select
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {INSURANCE_LEGAL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.social', { defaultValue: 'Social insurance' })}
          <input className="border border-slate-200 rounded px-2 py-1.5 text-sm" disabled={!manage} value={social_insurance} onChange={(e) => setSocial(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.health', { defaultValue: 'Health insurance' })}
          <input className="border border-slate-200 rounded px-2 py-1.5 text-sm" disabled={!manage} value={health_insurance} onChange={(e) => setHealth(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.sickness', { defaultValue: 'Sickness insurance' })}
          <input className="border border-slate-200 rounded px-2 py-1.5 text-sm" disabled={!manage} value={sickness_insurance} onChange={(e) => setSick(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.accident', { defaultValue: 'Accident insurance' })}
          <input className="border border-slate-200 rounded px-2 py-1.5 text-sm" disabled={!manage} value={accident_insurance} onChange={(e) => setAcc(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_legal.zus_reg_type', { defaultValue: 'ZUS registration type' })}
          <input className="border border-slate-200 rounded px-2 py-1.5 text-sm" disabled={!manage} value={zus_registration_type} onChange={(e) => setRegType(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.registered_at', { defaultValue: 'Registered at' })}
          <input
            type="date"
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={registered_at ? registered_at.slice(0, 10) : ''}
            onChange={(e) => setRegAt(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.deregistered_at', { defaultValue: 'Deregistered at' })}
          <input
            type="date"
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={deregistered_at ? deregistered_at.slice(0, 10) : ''}
            onChange={(e) => setDereg(e.target.value)}
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
              zus_title_code: zus_title_code.trim() || null,
              social_insurance: social_insurance.trim() || null,
              health_insurance: health_insurance.trim() || null,
              sickness_insurance: sickness_insurance.trim() || null,
              accident_insurance: accident_insurance.trim() || null,
              zus_registration_type: zus_registration_type.trim() || null,
              registered_at: registered_at ? registered_at.slice(0, 10) : null,
              deregistered_at: deregistered_at ? deregistered_at.slice(0, 10) : null,
              status,
            })
          }
        >
          {t('app.hr.employee_detail.save', { defaultValue: 'Save' })}
        </button>
      ) : null}
    </Section>
  )
}

function StoredComplianceStateSection({
  state,
  manage,
  saving,
  onSave,
  notify,
  defaultOpen = true,
}: {
  state: WorkforceComplianceState | null
  manage: boolean
  saving: boolean
  onSave: (p: Parameters<typeof patchWorkforceComplianceState>[1]) => void
  notify: ReturnType<typeof useToast>['notify']
  defaultOpen?: boolean
}) {
  const { t } = useI18n()
  const [status, setStatus] = useState(state?.status || 'not_evaluated')
  const [missing_count, setMissing] = useState(String(state?.missing_count ?? 0))
  const [expired_count, setExpired] = useState(String(state?.expired_count ?? 0))
  const [expiring_soon_count, setExpSoon] = useState(String(state?.expiring_soon_count ?? 0))
  const [high_risk_count, setHigh] = useState(String(state?.high_risk_count ?? 0))
  const [cannot_work, setCannot] = useState(Boolean(state?.cannot_work))
  const [last_evaluated_at, setEvalAt] = useState(() => isoToDatetimeLocalValue(state?.last_evaluated_at))
  const [reasons_json, setReasonsJson] = useState(() => stringifyJsonField((state?.reasons as Record<string, unknown>) ?? undefined))

  useEffect(() => {
    if (!state) return
    setStatus(state.status || 'not_evaluated')
    setMissing(String(state.missing_count ?? 0))
    setExpired(String(state.expired_count ?? 0))
    setExpSoon(String(state.expiring_soon_count ?? 0))
    setHigh(String(state.high_risk_count ?? 0))
    setCannot(Boolean(state.cannot_work))
    setEvalAt(isoToDatetimeLocalValue(state.last_evaluated_at))
    setReasonsJson(stringifyJsonField((state.reasons as Record<string, unknown>) ?? undefined))
  }, [state])

  if (!state) {
    return (
      <Section
        defaultOpen={defaultOpen}
        title={t('app.hr.employee_legal.section_compliance_state', { defaultValue: 'Compliance state (stored)' })}
      >
        <p className="text-sm text-slate-500">
          {t('app.hr.employee_legal.no_compliance', { defaultValue: 'No compliance state row yet.' })}
        </p>
      </Section>
    )
  }

  const parseIntSafe = (raw: string, label: string): number | undefined => {
    const s = raw.trim()
    if (!s) return 0
    const n = Number.parseInt(s, 10)
    if (!Number.isFinite(n) || n < 0) {
      notify({ variant: 'error', title: `${label}: ${t('app.hr.employee_legal.invalid_int', { defaultValue: 'invalid non-negative integer' })}` })
      return undefined
    }
    return n
  }

  return (
    <Section
      defaultOpen={defaultOpen}
      title={t('app.hr.employee_legal.section_compliance_state', { defaultValue: 'Compliance state (stored)' })}
    >
      <p className="text-xs text-slate-600 mb-3">
        {t('app.hr.employee_legal.compliance_hint', {
          defaultValue: 'Persisted snapshot for dashboards and exports. Queues above remain the operational signal.',
        })}
      </p>
      <div className="grid gap-3 sm:grid-cols-2 max-w-2xl">
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.compliance_status', { defaultValue: 'Status' })}
          <input className="border border-slate-200 rounded px-2 py-1.5 text-sm" disabled={!manage} value={status} onChange={(e) => setStatus(e.target.value)} />
        </label>
        <label className="flex flex-row items-center gap-2 text-xs text-slate-600">
          <input type="checkbox" disabled={!manage} checked={cannot_work} onChange={(e) => setCannot(e.target.checked)} />
          {t('app.hr.employee_legal.cannot_work', { defaultValue: 'Cannot work (legal block)' })}
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.missing_count', { defaultValue: 'Missing count' })}
          <input className="border border-slate-200 rounded px-2 py-1.5 text-sm tabular-nums" disabled={!manage} value={missing_count} onChange={(e) => setMissing(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.expired_count', { defaultValue: 'Expired count' })}
          <input className="border border-slate-200 rounded px-2 py-1.5 text-sm tabular-nums" disabled={!manage} value={expired_count} onChange={(e) => setExpired(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.expiring_soon', { defaultValue: 'Expiring soon count' })}
          <input className="border border-slate-200 rounded px-2 py-1.5 text-sm tabular-nums" disabled={!manage} value={expiring_soon_count} onChange={(e) => setExpSoon(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_legal.high_risk', { defaultValue: 'High risk count' })}
          <input className="border border-slate-200 rounded px-2 py-1.5 text-sm tabular-nums" disabled={!manage} value={high_risk_count} onChange={(e) => setHigh(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_legal.last_evaluated', { defaultValue: 'Last evaluated (local)' })}
          <input
            type="datetime-local"
            className="border border-slate-200 rounded px-2 py-1.5 text-sm"
            disabled={!manage}
            value={last_evaluated_at}
            onChange={(e) => setEvalAt(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_legal.reasons_json', { defaultValue: 'Reasons (JSON)' })}
          <textarea
            className="border border-slate-200 rounded px-2 py-1.5 text-sm font-mono min-h-[5rem]"
            disabled={!manage}
            value={reasons_json}
            onChange={(e) => setReasonsJson(e.target.value)}
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
            const mi = parseIntSafe(missing_count, 'missing_count')
            const ex = parseIntSafe(expired_count, 'expired_count')
            const es = parseIntSafe(expiring_soon_count, 'expiring_soon_count')
            const hr = parseIntSafe(high_risk_count, 'high_risk_count')
            if (mi === undefined || ex === undefined || es === undefined || hr === undefined) return
            const reasons = parseOptionalJsonObject(reasons_json, t('app.hr.employee_legal.reasons_json', { defaultValue: 'Reasons (JSON)' }), notify)
            if (reasons === undefined) return
            let lastEv: string | null = null
            if (last_evaluated_at.trim()) {
              const d = new Date(last_evaluated_at)
              if (Number.isNaN(d.getTime())) {
                notify({ variant: 'error', title: t('app.hr.employee_legal.bad_datetime', { defaultValue: 'Invalid last evaluated datetime' }) })
                return
              }
              lastEv = d.toISOString()
            } else {
              lastEv = null
            }
            onSave({
              status: status.trim() || undefined,
              missing_count: mi,
              expired_count: ex,
              expiring_soon_count: es,
              high_risk_count: hr,
              cannot_work,
              last_evaluated_at: lastEv,
              reasons,
            })
          }}
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
  defaultOpen = true,
}: {
  employeeId: string
  rows: WorkforceHrBundle['employments']
  manage: boolean
  saving: string | null
  onReload: () => Promise<void>
  notify: ReturnType<typeof useToast>['notify']
  t: (key: string, opts?: { defaultValue?: string }) => string
  defaultOpen?: boolean
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
    <Section
      id="hr-employee-employments"
      defaultOpen={defaultOpen}
      title={t('app.hr.employee_detail.section_contracts', { defaultValue: 'Contracts (employment)' })}
    >
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
  overdueCount = 0,
  onMarkDone,
}: {
  tasks: WorkforceHrBundle['onboarding_tasks']
  manage: boolean
  saving: string | null
  overdueCount?: number
  onMarkDone: (taskId: string) => void
}) {
  const { t } = useI18n()
  return (
    <Section title={t('app.hr.employee_detail.section_onboarding', { defaultValue: 'Onboarding' })}>
      {overdueCount > 0 ? (
        <p className="mb-3 rounded border border-rose-100 bg-rose-50 px-3 py-2 text-sm text-rose-950">
          {t('app.hr.employee_operational.onboarding_overdue', {
            defaultValue: '{count} task(s) overdue',
            values: { count: overdueCount },
          })}
        </p>
      ) : null}
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
  defaultOpen = true,
}: {
  employeeId: string
  rows: WorkforceHrBundle['absences']
  manage: boolean
  saving: string | null
  onReload: () => Promise<void>
  notify: ReturnType<typeof useToast>['notify']
  t: (key: string, opts?: { defaultValue?: string }) => string
  defaultOpen?: boolean
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
    <Section defaultOpen={defaultOpen} title={t('app.hr.employee_detail.section_absences', { defaultValue: 'Absences' })}>
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
  defaultOpen = true,
}: {
  employeeId: string
  rows: WorkforceHrBundle['leave_requests']
  manage: boolean
  saving: string | null
  onReload: () => Promise<void>
  notify: ReturnType<typeof useToast>['notify']
  t: (key: string, opts?: { defaultValue?: string }) => string
  defaultOpen?: boolean
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
    <Section defaultOpen={defaultOpen} title={t('app.hr.employee_detail.section_leave', { defaultValue: 'Leave requests' })}>
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
