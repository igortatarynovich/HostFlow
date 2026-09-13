import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  applyEmploymentAcceptPolicy,
  fetchHandoffHrReview,
  fetchHrHandoffInboxRow,
  type EmploymentAcceptPolicyOut,
  type HrHandoffInboxItem,
} from '../../api/hrWorkspace'
import HrEmploymentAcceptPanel from '../../components/hr/HrEmploymentAcceptPanel'
import HrHandoffContextSummary from '../../components/hr/HrHandoffContextSummary'
import HrDataVerificationWorkspace from '../../components/hr/HrDataVerificationWorkspace'
import HrReviewPanelCard from '../../components/hr/HrReviewPanel'
import { shouldApplyEmploymentAcceptPolicyOnOpen } from '../../utils/employmentAcceptUi'
import { useI18n } from '../../i18n'
import { PageHeader } from '../../components/nav/PageHeader'
import { useToast } from '../../components/Toast'
import type { HrReviewPanel } from '../../api/workforce'

/**
 * ESO-1 host: existing HR handoff case binds employment_accept_policy.v1.
 * Ritual «Take into HR review» is never shown. Legacy Approve chrome may remain
 * for delayed-HR cases but is not the Employment accept happy path.
 */
export default function HrHandoffDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useI18n()
  const { notify } = useToast()
  const [row, setRow] = useState<HrHandoffInboxItem | null>(null)
  const [policy, setPolicy] = useState<EmploymentAcceptPolicyOut | null>(null)
  const [hrReview, setHrReview] = useState<HrReviewPanel | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [policyError, setPolicyError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)
  const applyOnceRef = useRef<string | null>(null)

  const loadRow = useCallback(async () => {
    if (!id) return null
    const inboxRow = await fetchHrHandoffInboxRow(id)
    setRow(inboxRow)
    return inboxRow
  }, [id])

  const loadHrReviewIfAccepted = useCallback(
    async (inboxRow: HrHandoffInboxItem) => {
      if (!id) return
      if (String(inboxRow.handoff?.status || '').toLowerCase() !== 'accepted') {
        setHrReview(null)
        return
      }
      try {
        setHrReview(await fetchHandoffHrReview(id))
      } catch {
        setHrReview(null)
      }
    },
    [id],
  )

  const runAcceptPolicy = useCallback(async () => {
    if (!id) return
    setApplying(true)
    setPolicyError(null)
    try {
      const result = await applyEmploymentAcceptPolicy(id)
      setPolicy(result)
      if (result.accepted) {
        notify({
          variant: 'success',
          title:
            result.message ||
            t('app.hr.employment_accept.employment_started', { defaultValue: 'Employment started' }),
        })
        const inboxRow = await loadRow()
        if (inboxRow) await loadHrReviewIfAccepted(inboxRow)
      }
    } catch (e: unknown) {
      const ex = e as { response?: { data?: { detail?: unknown } }; message?: string }
      const detail = ex?.response?.data?.detail
      let message = ex?.message || t('common.errors.request_failed')
      if (typeof detail === 'string') message = detail
      else if (detail && typeof detail === 'object') {
        const d = detail as { message?: string; code?: string }
        message = d.message || d.code || message
      }
      setPolicyError(message)
      notify({ variant: 'error', title: message })
    } finally {
      setApplying(false)
    }
  }, [id, loadHrReviewIfAccepted, loadRow, notify, t])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!id) return
      setLoading(true)
      setErr(null)
      try {
        const inboxRow = await loadRow()
        if (cancelled || !inboxRow) return
        const pending = shouldApplyEmploymentAcceptPolicyOnOpen({
          handoffStatus: inboxRow.handoff?.status,
          operationalQueue: String(inboxRow.operational_queue || ''),
        })
        if (pending && applyOnceRef.current !== id) {
          applyOnceRef.current = id
          await runAcceptPolicy()
        } else if (!pending) {
          if (String(inboxRow.handoff?.status || '').toLowerCase() === 'accepted') {
            setPolicy({
              policy_id: 'employment_accept_policy.v1',
              handoff_id: id,
              decision: 'auto_accept',
              ritual_accept_forbidden: true,
              accepted: true,
              employment_started: true,
              blockers: [],
              message: t('app.hr.employment_accept.already_accepted', {
                defaultValue: 'Employment case already accepted',
              }),
            })
            await loadHrReviewIfAccepted(inboxRow)
          }
        }
      } catch (e: unknown) {
        if (cancelled) return
        const ex = e as { response?: { data?: { detail?: string } }; message?: string }
        setErr(ex?.response?.data?.detail || ex?.message || t('common.errors.request_failed'))
        setRow(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, loadHrReviewIfAccepted, loadRow, runAcceptPolicy, t])

  const empId = row?.workforce_employee_id || hrReview?.employee_id || undefined
  const displayName = row?.candidate_display_name || undefined
  const pendingOpen = shouldApplyEmploymentAcceptPolicyOnOpen({
    handoffStatus: row?.handoff?.status,
    operationalQueue: String(row?.operational_queue || ''),
  })
  const accepted =
    Boolean(policy?.accepted) || String(row?.handoff?.status || '').toLowerCase() === 'accepted'

  if (empId) {
    return <Navigate to={`${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(empId)}#hr-verification`} replace />
  }

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
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => {
              void (async () => {
                const inboxRow = await loadRow()
                if (inboxRow) await loadHrReviewIfAccepted(inboxRow)
              })()
            }}
          >
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        }
      />

      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>
      )}

      {row && !loading ? (
        <>
          <HrEmploymentAcceptPanel
            policy={policy}
            applying={applying}
            error={policyError}
            onRetry={pendingOpen ? () => void runAcceptPolicy() : undefined}
          />

          {/* Named negative proof: no ritual Accept control on this host. */}
          <div data-testid="hr-employment-accept-no-ritual" hidden aria-hidden="true" />

          {accepted ? (
            <p className="text-sm text-slate-600" data-testid="hr-employment-accepted-state">
              {t('app.hr.employment_accept.case_open', {
                defaultValue: 'Employment case is open on this HR handoff. ESO-2/3 decision surface is next.',
              })}
            </p>
          ) : null}

          <HrHandoffContextSummary row={row} />

          {accepted && hrReview ? (
            <details className="rounded-lg border border-slate-200 bg-white">
              <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-800">
                {t('app.hr.employment_accept.legacy_review_summary', {
                  defaultValue: 'Legacy document verification (not ESO accept / Formalize)',
                })}
              </summary>
              <div className="space-y-4 border-t border-slate-100 px-4 py-4">
                <HrDataVerificationWorkspace
                  panel={hrReview}
                  handoffId={id}
                  employeeId={empId}
                  manage
                  onPanelUpdated={(next) => {
                    setHrReview(next)
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
                  }}
                />
              </div>
            </details>
          ) : null}
        </>
      ) : null}

      {empId ? (
        <Link
          className="text-sm font-medium text-brand-700 hover:underline"
          to={`${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(empId)}`}
        >
          {t('app.hr.review_case.open_employee_profile', { defaultValue: 'Open employee profile' })}
        </Link>
      ) : null}
    </div>
  )
}
