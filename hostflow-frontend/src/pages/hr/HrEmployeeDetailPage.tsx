import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useI18n, type TranslateFn } from '../../i18n'
import {
  getWorkforceEmployeeOperationalProfile,
  getWorkforceHrReview,
  patchWorkforceOnboardingTask,
  patchWorkforcePayrollProfile,
  patchWorkforceZusProfile,
  type HrReviewPanel,
  type WorkforceEmployeeOperationalProfile,
  type WorkforceHrBundle,
} from '../../api/workforce'
import { usePermissions } from '../../hooks/usePermissions'
import { useToast } from '../../components/Toast'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell } from '../../components/layout'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import HrReviewPanelCard from '../../components/hr/HrReviewPanel'
import HrNextActionRail from '../../components/hr/HrNextActionRail'
import HrContractPreviewPanel from '../../components/hr/HrContractPreviewPanel'
import HrWorkEligibilityCompact from '../../components/hr/HrWorkEligibilityCompact'
import { EmployeeDossierView } from '../../components/hr/EmployeeDossierView'
import { countVerifiedDocuments, documentsFromPanel } from '../../components/hr/hrDocumentVerificationFields'
import { isEmploymentCaseWorkspace } from '../../utils/hrEmploymentCaseMode'
import { HrEmployeeCommunicationSlot } from './HrEmployeeCommunicationSlot'
import { HrEmployeeFormsSlot } from './HrEmployeeFormsSlot'
import {
  EntityWorkspaceCompositionHost,
  HR_EMPLOYEE_COMPOSITION_CONSUMER_ID,
  HR_EMPLOYEE_COMPOSITION_SLOTS,
  assertHrEmployeeCompositionSlots,
} from '../../platform/entity-workspace'
import { EntityWorkspaceCapabilityHost } from '../../platform/workspace-capability/EntityWorkspaceCapabilityHost'
import { HR_EMPLOYEE_ENTITY_HOST_CONTRIBUTIONS } from '../../platform/workspace-capability/hrEmployeeEntity'

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
  t: TranslateFn,
): Record<string, unknown> | null | undefined {
  const s = raw.trim()
  if (!s) return null
  try {
    const v = JSON.parse(s)
    if (v && typeof v === 'object' && !Array.isArray(v)) return v as Record<string, unknown>
    notify({
      variant: 'error',
      title: t('app.hr.employee_detail.json_must_be_object', { values: { label } }),
    })
    return undefined
  } catch {
    notify({
      variant: 'error',
      title: t('app.hr.employee_detail.invalid_json', { values: { label } }),
    })
    return undefined
  }
}

function Section({
  title,
  children,
  defaultOpen = true,
  open,
  id,
}: {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
  open?: boolean
  id?: string
}) {
  const openProps = open !== undefined ? { open } : defaultOpen ? { open: true as const } : {}
  return (
    <details {...openProps} id={id} className="border border-slate-200 rounded-lg bg-white">
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

  const [employmentDecisionOpen, setEmploymentDecisionOpen] = useState(false)
  const [workEligibilityJourneyOpen, setWorkEligibilityJourneyOpen] = useState(false)

  const scrollToAnchor = (anchor: string) => {
    const sel = anchor.startsWith('#') ? anchor : `#${anchor}`
    if (sel === '#hr-employee-review') setEmploymentDecisionOpen(true)
    if (sel === '#hr-review-eligibility') setWorkEligibilityJourneyOpen(true)
    document.querySelector(sel)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const dossierDocsVerified = useMemo(() => {
    if (!hrReview) return false
    const progress = countVerifiedDocuments(documentsFromPanel(hrReview))
    return progress.total > 0 && progress.verified >= progress.total
  }, [hrReview])

  const showPostVerifySections = Boolean(hrReview && (caseWorkspace || dossierDocsVerified))
  const showEmploymentDecision =
    Boolean(hrReview) &&
    (hrReview.status === 'approved_for_employment' || dossierDocsVerified)

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

  useEffect(() => {
    if (loading || !employee) return
    const hash = window.location.hash
    if (hash) scrollToAnchor(hash)
  }, [loading, employee])

  const handleDossierHrPanelUpdated = useCallback(
    (next: HrReviewPanel) => {
      setHrReview(next)
      void refreshProfile()
    },
    [refreshProfile],
  )

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

  const isCutover = Boolean(employeeId)
  if (isCutover) {
    assertHrEmployeeCompositionSlots(HR_EMPLOYEE_COMPOSITION_SLOTS)
  }

  return (
    <PageShell
      className="hr-employee-workspace w-full min-w-0 overflow-visible"
      data-entity-workspace-consumer={isCutover ? HR_EMPLOYEE_COMPOSITION_CONSUMER_ID : undefined}
    >
      <div className="w-full min-w-0">
        <div data-entity-workspace-slot="context-rail">
        <PageHeader
          breadcrumbItems={[
            { label: t('app.nav.hr.workspace.title', { defaultValue: 'HR workspace' }), to: CRM_APP_PATHS.hr },
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
          title={employee.display_name}
          subtitle={caseWorkspace ? t('app.hr.review_case.badge', { defaultValue: 'HR review case' }) : employee.id}
          kind="browse"
        />
        </div>

        <div
          className={
            caseWorkspace
              ? 'mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_22rem] 2xl:grid-cols-[minmax(0,1fr)_26rem] xl:items-start'
              : 'mt-6'
          }
        >
          <div className="min-w-0 space-y-4">
            <div data-entity-workspace-slot="overview" className="space-y-4">
            <EmployeeDossierView
              employeeId={employeeId!}
              employee={employee}
              profile={profile}
              hrReview={hrReview}
              manage={manage}
              caseMode={caseWorkspace}
              onHrPanelUpdated={handleDossierHrPanelUpdated}
              onScrollTo={scrollToAnchor}
            />
            </div>
            {showEmploymentDecision && hrReview ? (
              <details
                id="hr-employee-review"
                className="rounded-lg border border-slate-200 bg-white"
                open={caseWorkspace || employmentDecisionOpen}
                onToggle={(e) => setEmploymentDecisionOpen((e.target as HTMLDetailsElement).open)}
              >
                <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-900">
                  {t('app.hr.review_case.employment_decision', { defaultValue: 'Employment decision' })}
                </summary>
                <div className="border-t border-slate-100 p-2">
                  <HrReviewPanelCard
                    employeeId={employeeId}
                    handoffId={hrReview.handoff_id ?? undefined}
                    panel={hrReview}
                    workforceEligibility={profile.workforce_eligibility}
                    hideDocuments
                    caseDecisionMode={caseWorkspace}
                    manage={manage}
                    onUpdated={(next) => {
                      setHrReview(next)
                      void refreshProfile()
                    }}
                  />
                </div>
              </details>
            ) : null}
            {showPostVerifySections && employeeId && hrReview ? (
              <HrWorkEligibilityCompact
                panel={hrReview}
                employeeId={employeeId}
                manage={manage}
                onRefresh={refreshProfile}
                journeyExpanded={workEligibilityJourneyOpen}
                onJourneyExpandedChange={setWorkEligibilityJourneyOpen}
              />
            ) : null}
            {caseWorkspace && employeeId && hrReview ? (
              <details className="rounded-lg border border-slate-200 bg-white">
                <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-900">
                  {t('app.hr.contract_preview.section', { defaultValue: 'Contract draft preview' })}
                </summary>
                <div className="border-t border-slate-100 px-2 pb-2">
                  <HrContractPreviewPanel
                    employeeId={employeeId}
                    manage={manage}
                    ownCompanyId={employee?.own_company_id ?? undefined}
                    workforceEligibility={profile.workforce_eligibility}
                  />
                </div>
              </details>
            ) : null}
            {hrReview?.status === 'approved_for_employment' && bundle ? (
              <details id="hr-post-approve" className="rounded-lg border border-slate-200 bg-white">
                <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-900">
                  {t('app.hr.dossier.post_approve', { defaultValue: 'Post-approval workspace' })}
                </summary>
                <div className="space-y-4 border-t border-slate-100 p-2">
                  <OnboardingSection
                    tasks={bundle.onboarding_tasks}
                    manage={manage}
                    saving={saving}
                    overdueCount={profile.onboarding_overdue_count ?? 0}
                    onMarkDone={(taskId) =>
                      void runSave(`task-${taskId}`, () => patchWorkforceOnboardingTask(taskId, { status: 'done' }))
                    }
                  />
                  <PayrollSection
                    profile={bundle.payroll_profile}
                    manage={manage}
                    saving={Boolean(saving)}
                    defaultOpen={false}
                    onSave={(p) => void runSave('payroll', () => patchWorkforcePayrollProfile(employeeId!, p))}
                  />
                  <ZusSection
                    profile={bundle.zus_profile}
                    manage={manage}
                    saving={Boolean(saving)}
                    defaultOpen={false}
                    onSave={(p) => void runSave('zus', () => patchWorkforceZusProfile(employeeId!, p))}
                  />
                </div>
              </details>
            ) : null}
            {isCutover ? (
              <EntityWorkspaceCompositionHost
                consumerId={HR_EMPLOYEE_COMPOSITION_CONSUMER_ID}
                enabledSlots={['communication', 'forms']}
                renderers={{
                  communication: () => (
                    <HrEmployeeCommunicationSlot candidateId={String(employee.candidate_id || '')} />
                  ),
                  forms: () => <HrEmployeeFormsSlot />,
                }}
              />
            ) : null}
            {isCutover ? (
              <EntityWorkspaceCapabilityHost
                entity={{ resourceType: 'workforce_employee', resourceId: employeeId }}
                contributions={HR_EMPLOYEE_ENTITY_HOST_CONTRIBUTIONS}
                onClose={() => undefined}
                onRefresh={() => void refreshProfile()}
              >
                {(placed) => <div data-host-region="platform_slot">{placed.platform_slot}</div>}
              </EntityWorkspaceCapabilityHost>
            ) : null}
            {isCutover ? (
              <div data-entity-workspace-slot="timeline">
                <section className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-sm font-semibold text-slate-900">
                    {t('app.entity_workspace.slot.timeline', { defaultValue: 'Timeline' })}
                  </p>
                  {profile.timeline.length === 0 ? (
                    <p className="text-sm text-slate-600">
                      {t('app.hr.employee_operational.timeline_empty', { defaultValue: 'No timeline events.' })}
                    </p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {profile.timeline.slice(0, 5).map((ev) => (
                        <li key={ev.id} className="text-slate-700">
                          <span className="font-medium text-slate-900">{ev.title}</span>
                          {ev.kind ? <span className="text-slate-500"> · {ev.kind}</span> : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>
            ) : null}
          </div>
          {caseWorkspace && profile ? (
            <aside
              className="min-w-0 xl:sticky xl:top-4 xl:self-start"
              data-entity-workspace-slot="context-rail"
            >
              {caseWorkspace && hrReview ? (
                <HrNextActionRail
                  panel={hrReview}
                  employeeId={employeeId}
                  profileAlerts={profile.alerts}
                  profileTimeline={profile.timeline}
                  workforceEligibility={profile.workforce_eligibility}
                  onScrollTo={scrollToAnchor}
                />
              ) : null}
            </aside>
          ) : null}
        </div>
      </div>
    </PageShell>
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
          {t('app.hr.employee_detail.payroll_pay_type')}
          <select
            className="border border-slate-200 rounded px-2 py-2 text-sm"
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
          {t('app.hr.employee_detail.payroll_base_rate')}
          <input
            className="border border-slate-200 rounded px-2 py-2 text-sm"
            disabled={!manage}
            value={base_rate}
            onChange={(e) => setBaseRate(e.target.value)}
            placeholder="6500.00"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_detail.payroll_currency')}
          <input
            className="border border-slate-200 rounded px-2 py-2 text-sm"
            disabled={!manage}
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_detail.payroll_status')}
          <select
            className="border border-slate-200 rounded px-2 py-2 text-sm"
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
          {t('app.hr.employee_detail.payroll_bank_account')}
          <input
            className="border border-slate-200 rounded px-2 py-2 text-sm font-mono"
            disabled={!manage}
            value={bank_account}
            onChange={(e) => setBankAccount(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_tax_status')}
          <input
            className="border border-slate-200 rounded px-2 py-2 text-sm"
            disabled={!manage}
            value={tax_status}
            onChange={(e) => setTaxStatus(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_calculation_system', { defaultValue: 'Calculation system' })}
          <input
            className="border border-slate-200 rounded px-2 py-2 text-sm"
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
            className="border border-slate-200 rounded px-2 py-2 text-sm"
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
            className="border border-slate-200 rounded px-2 py-2 text-sm font-mono min-h-[5rem]"
            disabled={!manage}
            value={pit_json}
            onChange={(e) => setPitJson(e.target.value)}
            spellCheck={false}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_allowances_json', { defaultValue: 'Allowances (JSON object)' })}
          <textarea
            className="border border-slate-200 rounded px-2 py-2 text-sm font-mono min-h-[5rem]"
            disabled={!manage}
            value={allowances_json}
            onChange={(e) => setAllowancesJson(e.target.value)}
            spellCheck={false}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_deductions_json', { defaultValue: 'Deductions (JSON object)' })}
          <textarea
            className="border border-slate-200 rounded px-2 py-2 text-sm font-mono min-h-[5rem]"
            disabled={!manage}
            value={deductions_json}
            onChange={(e) => setDeductionsJson(e.target.value)}
            spellCheck={false}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600 sm:col-span-2">
          {t('app.hr.employee_detail.payroll_external_refs_json', { defaultValue: 'External refs (JSON object)' })}
          <textarea
            className="border border-slate-200 rounded px-2 py-2 text-sm font-mono min-h-[5rem]"
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
          className="mt-3 px-3 py-2 rounded text-sm font-medium bg-slate-900 text-white disabled:opacity-50"
          onClick={() => {
            const pitLabel = t('app.hr.employee_detail.payroll_pit_json', { defaultValue: 'PIT declarations' })
            const pit = parseOptionalJsonObject(pit_json, pitLabel, notify, t)
            if (pit === undefined) return
            const alwLabel = t('app.hr.employee_detail.payroll_allowances_json', { defaultValue: 'Allowances' })
            const alw = parseOptionalJsonObject(allowances_json, alwLabel, notify, t)
            if (alw === undefined) return
            const dedLabel = t('app.hr.employee_detail.payroll_deductions_json', { defaultValue: 'Deductions' })
            const ded = parseOptionalJsonObject(deductions_json, dedLabel, notify, t)
            if (ded === undefined) return
            const extLabel = t('app.hr.employee_detail.payroll_external_refs_json', { defaultValue: 'External refs' })
            const ext = parseOptionalJsonObject(external_refs_json, extLabel, notify, t)
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
          {t('app.hr.employee_detail.zus_registration_status')}
          <select
            className="border border-slate-200 rounded px-2 py-2 text-sm"
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
          {t('app.hr.employee_detail.zus_submitted_at')}
          <input
            type="date"
            className="border border-slate-200 rounded px-2 py-2 text-sm"
            disabled={!manage}
            value={submitted_at ? submitted_at.slice(0, 10) : ''}
            onChange={(e) => setSubmittedAt(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_detail.zus_employment_basis')}
          <input
            className="border border-slate-200 rounded px-2 py-2 text-sm"
            disabled={!manage}
            value={employment_basis}
            onChange={(e) => setBasis(e.target.value)}
            placeholder={t('app.hr.employee_detail.zus_employment_basis_placeholder')}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('app.hr.employee_detail.zus_responsible_party')}
          <input
            className="border border-slate-200 rounded px-2 py-2 text-sm"
            disabled={!manage}
            value={responsible_party}
            onChange={(e) => setParty(e.target.value)}
            placeholder={t('app.hr.employee_detail.zus_responsible_party_placeholder')}
          />
        </label>
      </div>
      {manage ? (
        <button
          type="button"
          disabled={saving}
          className="mt-3 px-3 py-2 rounded text-sm font-medium bg-slate-900 text-white disabled:opacity-50"
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
