import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  applyEmploymentAcceptPolicy,
  type EmploymentAcceptPolicyResult,
} from '../../api/handoffs'
import {
  fetchHandoffHrReview,
  fetchHrHandoffInboxRow,
  type HrHandoffInboxItem,
} from '../../api/hrWorkspace'
import HrReviewPanelCard from '../../components/hr/HrReviewPanel'
import HrReviewCaseHero from '../../components/hr/HrReviewCaseHero'
import HrNextActionRail from '../../components/hr/HrNextActionRail'
import HrDataVerificationWorkspace from '../../components/hr/HrDataVerificationWorkspace'
import HrContractPreviewPanel from '../../components/hr/HrContractPreviewPanel'
import HrWorkEligibilityCompact from '../../components/hr/HrWorkEligibilityCompact'
import HrHandoffContextSummary from '../../components/hr/HrHandoffContextSummary'
import HrCurrentTaskPanel from '../../components/hr/HrCurrentTaskPanel'
import HrStartAllowedPanel from '../../components/hr/HrStartAllowedPanel'
import { isEmployeeOperationalProfile } from '../../utils/hrEmploymentCaseMode'
import { useI18n } from '../../i18n'
import { PageHeader } from '../../components/nav/PageHeader'
import { useToast } from '../../components/Toast'
import type { HrReviewPanel } from '../../api/workforce'

export default function HrHandoffDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useI18n()
  const { notify } = useToast()
  const [row, setRow] = useState<HrHandoffInboxItem | null>(null)
  const [hrReview, setHrReview] = useState<HrReviewPanel | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [policy, setPolicy] = useState<EmploymentAcceptPolicyResult | null>(null)
  const [policyLoading, setPolicyLoading] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setErr(null)
    try {
      const inboxRow = await fetchHrHandoffInboxRow(id)
      setRow(inboxRow)
      if (inboxRow.handoff.status === 'accepted') {
        setPolicy(null)
        try {
          const panel = await fetchHandoffHrReview(id)
          setHrReview(panel)
        } catch {
          setHrReview(null)
        }
      } else {
        setHrReview(null)
      }
    } catch (e: unknown) {
      const ex = e as { response?: { data?: { detail?: string } }; message?: string }
      setErr(ex?.response?.data?.detail || ex?.message || t('common.errors.request_failed'))
      setRow(null)
      setHrReview(null)
    } finally {
      setLoading(false)
    }
  }, [id, t])

  useEffect(() => {
    void load()
  }, [load])

  // RSO-2C: residual pending → Employment policy apply (not ritual Accept button).
  useEffect(() => {
    if (!id || loading || !row) return
    if (row.operational_queue !== 'awaiting_hr_pickup') return
    if (row.handoff.status !== 'pending_review') return
    let cancelled = false
    setPolicyLoading(true)
    void (async () => {
      try {
        const result = await applyEmploymentAcceptPolicy(id)
        if (cancelled) return
        setPolicy(result)
        if (result.accepted) {
          notify({
            variant: 'success',
            title: t('app.nav.hr.handoff.auto_init', {
              defaultValue: 'Employment initialized',
            }),
          })
          await load()
        }
      } catch (e: unknown) {
        if (cancelled) return
        const ex = e as {
          response?: { data?: { detail?: string | { message?: string; code?: string } } }
          message?: string
        }
        const detail = ex?.response?.data?.detail
        const msg =
          typeof detail === 'string'
            ? detail
            : detail && typeof detail === 'object'
              ? detail.message || detail.code
              : ex?.message
        setPolicy({
          policy_id: 'employment_accept_policy.v1',
          handoff_id: id,
          decision: 'review_required',
          blockers: [{ message: msg || t('common.errors.request_failed') }],
          employment_missing: [],
          reuse_violations: [],
          accepted: false,
          employment_started: false,
        })
      } finally {
        if (!cancelled) setPolicyLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, loading, row, load, notify, t])

  const isPickup = row?.operational_queue === 'awaiting_hr_pickup'
  const empId = row?.workforce_employee_id || hrReview?.employee_id || undefined
  const displayName = row?.candidate_display_name || undefined
  const blockers = policy?.blockers ?? []
  const employmentMissing = policy?.employment_missing ?? []

  const scrollTo = (anchor: string) => {
    const sel = anchor.startsWith('#') ? anchor : `#${anchor}`
    document.querySelector(sel)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  // Slice 3: keep /app/hr/handoffs/:id as host when Employee exists (start_allowed binding).
  // Optional deep-link to employee profile remains available below — no auto-redirect workflow.

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbItems={[
          { label: t('app.nav.hr.workspace.title', { defaultValue: 'HR workspace' }), to: CRM_APP_PATHS.hr },
          { label: t('app.nav.hr.inbox.heading', { defaultValue: 'Inbox' }), to: CRM_APP_PATHS.hrInbox },
          { label: displayName || id || '…' },
        ]}
        title={displayName || t('app.nav.hr.handoff.title', { defaultValue: 'Handoff' })}
        kind="browse"
        secondaryActions={
          <button type="button" className="btn-secondary btn-sm" onClick={() => void load()}>
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        }
      />

      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>
      )}

      {row && hrReview && !isPickup ? (
        <>
          <HrReviewCaseHero panel={hrReview} displayName={displayName} />
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_22rem] 2xl:grid-cols-[minmax(0,1fr)_26rem]">
            <div className="min-w-0 space-y-4">
              <HrDataVerificationWorkspace
                panel={hrReview}
                handoffId={id}
                employeeId={empId}
                manage
                onPanelUpdated={(next) => {
                  setHrReview(next)
                  void load()
                }}
              />
              <HrReviewPanelCard
                handoffId={id!}
                employeeId={empId}
                panel={hrReview}
                hideDocuments
                caseDecisionMode
                manage
                onUpdated={(next) => {
                  setHrReview(next)
                  void load()
                }}
              />
              {empId ? (
                <details className="rounded-lg border border-slate-200 bg-white">
                  <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-900">
                    {t('app.hr.contract_preview.section', { defaultValue: 'Contract draft preview' })}
                  </summary>
                  <div className="border-t border-slate-100 px-2 pb-2">
                    <HrContractPreviewPanel employeeId={empId} manage />
                  </div>
                </details>
              ) : null}
              {empId ? (
                <HrStartAllowedPanel
                  handoffId={id!}
                  employeeId={empId}
                  reloadToken={loading ? undefined : `${empId}:${hrReview?.review_id || ''}:${row.handoff.status}`}
                />
              ) : null}
              {empId ? (
                <HrWorkEligibilityCompact panel={hrReview} employeeId={empId} manage onRefresh={() => void load()} />
              ) : null}
              <HrHandoffContextSummary row={row} />
            </div>
            <HrNextActionRail panel={hrReview} employeeId={empId} onScrollTo={scrollTo} />
          </div>
        </>
      ) : null}

      {row && isPickup && !loading ? (
        <>
          <HrReviewCaseHero
            panel={{
              review_id: '',
              status: 'awaiting_hr_pickup',
              checklist: [],
              blockers: [],
              failed_required_items: [],
              can_approve: false,
              documents_for_approval: [],
              handoff_id: id,
              hero: {
                candidate_display_name: displayName,
                handoff_id: id,
                handoff_status: row.handoff.status,
                review_status: 'awaiting_hr_pickup',
                state_message: t('app.nav.hr.handoff.policy_hint', {
                  defaultValue:
                    'Employment accept policy decides whether this case auto-initializes. Ritual Accept is not the happy path.',
                }),
                process_stages: [
                  { code: 'transferred_from_recruitment', label: 'Transferred', state: 'done' },
                  { code: 'hr_pickup', label: 'Employment init', state: 'current' },
                  { code: 'document_verification', label: 'Documents', state: 'pending' },
                  { code: 'legal_eligibility', label: 'Eligibility', state: 'pending' },
                  { code: 'hr_decision', label: 'Decision', state: 'pending' },
                  { code: 'employee_onboarding', label: 'Employee', state: 'pending' },
                ],
              },
            }}
            displayName={displayName}
          />
          <HrCurrentTaskPanel
            task={{
              task_type: 'employment_accept_review',
              title: t('app.hr.review_case.task_policy_title', {
                defaultValue: 'Resolve Employment accept blockers',
              }),
              description: t('app.hr.review_case.task_policy_desc', {
                defaultValue:
                  'When auto-accept cannot proceed, clear the concrete Employment blockers below. Do not re-collect package facts without a conflict reason.',
              }),
              why: t('app.hr.review_case.task_policy_why', {
                defaultValue:
                  'Transfer already emitted ready_for_employment.v1. Employment owns accept/init; ritual Take into HR review is not the default path.',
              }),
              priority: 'critical',
              priority_step: 1,
              priority_total: 8,
              blocks_approval: true,
              primary_action: {
                label: t('app.hr.review_case.view_blockers', { defaultValue: 'View blockers' }),
                anchor: '#hr-employment-blockers',
              },
              secondary_actions: [
                {
                  label: t('app.hr.review_case.view_handoff', { defaultValue: 'View handoff summary' }),
                  anchor: '#hr-handoff-summary',
                },
              ],
              target_anchor: '#hr-employment-blockers',
              completion_condition: t('app.hr.review_case.task_policy_done', {
                defaultValue: 'Policy returns auto_accept and Employment initializes, or blockers are cleared.',
              }),
            }}
            onScrollTo={scrollTo}
          />
          <div id="hr-employment-blockers" className="scroll-mt-24 space-y-2 rounded-lg border border-amber-200 bg-amber-50/80 px-4 py-3">
            <h3 className="text-sm font-semibold text-amber-950">
              {t('app.nav.hr.handoff.blockers_heading', { defaultValue: 'Employment accept blockers' })}
            </h3>
            {policyLoading ? (
              <p className="text-sm text-amber-900">{t('common.loading')}</p>
            ) : blockers.length || employmentMissing.length ? (
              <ul className="list-disc space-y-1 pl-5 text-sm text-amber-950">
                {blockers.map((b, i) => (
                  <li key={`b-${i}`}>{b.message || b.code || 'blocker'}</li>
                ))}
                {employmentMissing.map((m, i) => (
                  <li key={`m-${i}`}>
                    {String(m.field_code || m.code || 'missing')}
                    {m.message ? `: ${String(m.message)}` : ''}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-amber-900">
                {policy?.message ||
                  t('app.nav.hr.handoff.waiting_policy', {
                    defaultValue: 'Waiting for Employment accept policy…',
                  })}
              </p>
            )}
            {policy?.decision ? (
              <p className="font-mono text-[11px] text-amber-800/80">
                decision:{policy.decision}
                {policy.ritual_accept_forbidden ? ' · ritual_accept_forbidden' : ''}
              </p>
            ) : null}
          </div>
          <div id="hr-handoff-summary">
            <HrHandoffContextSummary row={row} />
          </div>
        </>
      ) : null}

      {empId && isEmployeeOperationalProfile(hrReview) ? (
        <Link className="text-sm font-medium text-brand-700 hover:underline" to={`${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(empId)}`}>
          {t('app.hr.review_case.open_employee_profile', { defaultValue: 'Open employee profile' })}
        </Link>
      ) : null}
    </div>
  )
}
