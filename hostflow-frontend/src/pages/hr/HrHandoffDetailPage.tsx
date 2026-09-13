import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  applyEmploymentAcceptPolicy,
  confirmEmploymentStarted,
  evaluateEarlyEmployability,
  fetchHandoffHrReview,
  fetchHrHandoffInboxRow,
  formalizeEmployment,
  resolveEmploymentMissing,
  type EarlyEmployabilityOut,
  type EmploymentAcceptPolicyOut,
  type EmploymentFormalizeOut,
  type EmploymentStartedOut,
  type HrHandoffInboxItem,
} from '../../api/hrWorkspace'
import HrEmploymentAcceptPanel from '../../components/hr/HrEmploymentAcceptPanel'
import HrEmploymentDecisionSurface from '../../components/hr/HrEmploymentDecisionSurface'
import HrEmploymentFormalizePanel from '../../components/hr/HrEmploymentFormalizePanel'
import HrEmploymentStartedPanel from '../../components/hr/HrEmploymentStartedPanel'
import HrHandoffContextSummary from '../../components/hr/HrHandoffContextSummary'
import HrDataVerificationWorkspace from '../../components/hr/HrDataVerificationWorkspace'
import HrReviewPanelCard from '../../components/hr/HrReviewPanel'
import { shouldApplyEmploymentAcceptPolicyOnOpen } from '../../utils/employmentAcceptUi'
import { decisionSurfaceMode, employabilityFromResolution } from '../../utils/employmentDecisionUi'
import { shouldEnterFormalizeFromEmployability } from '../../utils/employmentFormalizeUi'
import {
  isStartedTerminal,
  shouldEnterStartedFromFormalize,
  shouldRedirectToEmployeeCardFromHandoffHost,
} from '../../utils/employmentStartedUi'
import { useI18n } from '../../i18n'
import { PageHeader } from '../../components/nav/PageHeader'
import { useToast } from '../../components/Toast'
import type { HrReviewPanel } from '../../api/workforce'

/**
 * HR handoff case host: ESO-1 accept + ESO-2/3 Decision Surface + ESO-4 Formalize + ESO-5 Started.
 * Started entry only when ready_to_create_employee=true. No employee-card redirect on this host.
 * Recruitment untouched.
 */
export default function HrHandoffDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useI18n()
  const { notify } = useToast()
  const [row, setRow] = useState<HrHandoffInboxItem | null>(null)
  const [policy, setPolicy] = useState<EmploymentAcceptPolicyOut | null>(null)
  const [employability, setEmployability] = useState<EarlyEmployabilityOut | null>(null)
  const [formalize, setFormalize] = useState<EmploymentFormalizeOut | null>(null)
  const [started, setStarted] = useState<EmploymentStartedOut | null>(null)
  const [hrReview, setHrReview] = useState<HrReviewPanel | null>(null)
  const [legacyOpen, setLegacyOpen] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [policyError, setPolicyError] = useState<string | null>(null)
  const [decisionError, setDecisionError] = useState<string | null>(null)
  const [formalizeError, setFormalizeError] = useState<string | null>(null)
  const [startedError, setStartedError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [resolving, setResolving] = useState(false)
  const [formalizeEvaluating, setFormalizeEvaluating] = useState(false)
  const [formalizeConfirming, setFormalizeConfirming] = useState(false)
  const [startedEvaluating, setStartedEvaluating] = useState(false)
  const [startedConfirming, setStartedConfirming] = useState(false)
  const applyOnceRef = useRef<string | null>(null)
  const evalOnceRef = useRef<string | null>(null)
  const startedOnceRef = useRef<string | null>(null)
  const startedRef = useRef<EmploymentStartedOut | null>(null)
  startedRef.current = started

  const loadRow = useCallback(async () => {
    if (!id) return null
    const inboxRow = await fetchHrHandoffInboxRow(id)
    setRow(inboxRow)
    return inboxRow
  }, [id])

  const parseDetail = useCallback(
    (e: unknown): string => {
      const ex = e as { response?: { data?: { detail?: unknown } }; message?: string }
      const detail = ex?.response?.data?.detail
      let message = ex?.message || t('common.errors.request_failed')
      if (typeof detail === 'string') message = detail
      else if (detail && typeof detail === 'object') {
        const d = detail as { message?: string; code?: string }
        message = d.message || d.code || message
      }
      return message
    },
    [t],
  )

  const runStartedEvaluate = useCallback(async () => {
    if (!id) return
    setStartedEvaluating(true)
    setStartedError(null)
    try {
      // Evaluate only — no start_confirmation (human confirm is explicit).
      const result = await confirmEmploymentStarted(id, {
        require_confirm_when_not_started: false,
        ensure_employee: false,
      })
      setStarted(result)
    } catch (e: unknown) {
      setStartedError(parseDetail(e))
    } finally {
      setStartedEvaluating(false)
    }
  }, [id, parseDetail])

  const enterStartedIfReady = useCallback(
    async (formalizeResult: EmploymentFormalizeOut | null | undefined) => {
      if (!shouldEnterStartedFromFormalize(formalizeResult)) {
        if (!isStartedTerminal(startedRef.current)) {
          setStarted(null)
          startedOnceRef.current = null
        }
        return
      }
      if (startedOnceRef.current === id && startedRef.current) return
      startedOnceRef.current = id || null
      await runStartedEvaluate()
    },
    [id, runStartedEvaluate],
  )

  const runFormalize = useCallback(async () => {
    if (!id) return
    setFormalizeEvaluating(true)
    setFormalizeError(null)
    try {
      const result = await formalizeEmployment(id)
      setFormalize(result)
      await enterStartedIfReady(result)
    } catch (e: unknown) {
      setFormalizeError(parseDetail(e))
    } finally {
      setFormalizeEvaluating(false)
    }
  }, [enterStartedIfReady, id, parseDetail])

  const runEmployability = useCallback(async () => {
    if (!id) return
    setEvaluating(true)
    setDecisionError(null)
    try {
      const result = await evaluateEarlyEmployability(id)
      setEmployability(result)
      if (shouldEnterFormalizeFromEmployability(result)) {
        await runFormalize()
      } else {
        setFormalize(null)
        setStarted(null)
        startedOnceRef.current = null
      }
    } catch (e: unknown) {
      setDecisionError(parseDetail(e))
    } finally {
      setEvaluating(false)
    }
  }, [id, parseDetail, runFormalize])

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
        await loadRow()
        evalOnceRef.current = null
        await runEmployability()
      }
    } catch (e: unknown) {
      const message = parseDetail(e)
      setPolicyError(message)
      notify({ variant: 'error', title: message })
    } finally {
      setApplying(false)
    }
  }, [id, loadRow, notify, parseDetail, runEmployability, t])

  const runResolve = useCallback(
    async (patch: { facts?: Record<string, unknown>; evidence?: Record<string, unknown> }) => {
      if (!id) return
      setResolving(true)
      setDecisionError(null)
      try {
        const result = await resolveEmploymentMissing(id, {
          resolution_patch: patch,
          require_patch_when_not_ready: true,
        })
        const next = employabilityFromResolution(result, employability)
        if (next) setEmployability(next as EarlyEmployabilityOut)
        if (result.rejection_reason) {
          setDecisionError(result.rejection_reason)
        }
        if (shouldEnterFormalizeFromEmployability(next) || result.resolution_decision === 'ready_to_formalize') {
          await runFormalize()
        }
      } catch (e: unknown) {
        const message = parseDetail(e)
        setDecisionError(message)
        notify({ variant: 'error', title: message })
      } finally {
        setResolving(false)
      }
    },
    [employability, id, notify, parseDetail, runFormalize],
  )

  const runFormalizeConfirm = useCallback(
    async (patch: { confirmed_actions: string[] }) => {
      if (!id) return
      setFormalizeConfirming(true)
      setFormalizeError(null)
      try {
        const result = await formalizeEmployment(id, {
          formalize_patch: patch,
          require_patch_when_missing: true,
        })
        setFormalize(result)
        if (result.rejection_reason) {
          setFormalizeError(result.rejection_reason)
        }
        startedOnceRef.current = null
        await enterStartedIfReady(result)
      } catch (e: unknown) {
        const message = parseDetail(e)
        setFormalizeError(message)
        notify({ variant: 'error', title: message })
      } finally {
        setFormalizeConfirming(false)
      }
    },
    [enterStartedIfReady, id, notify, parseDetail],
  )

  const runStartedConfirm = useCallback(
    async (confirmation: { confirmed: true; start_date?: string }) => {
      if (!id) return
      setStartedConfirming(true)
      setStartedError(null)
      try {
        const result = await confirmEmploymentStarted(id, {
          start_confirmation: confirmation,
          require_confirm_when_not_started: true,
          ensure_employee: false,
        })
        setStarted(result)
        if (result.rejection_reason) {
          setStartedError(result.rejection_reason)
        } else if (isStartedTerminal(result)) {
          notify({
            variant: 'success',
            title:
              result.decision === 'already_started'
                ? t('app.hr.employment_started.already_started_title', {
                    defaultValue: 'Already started',
                  })
                : t('app.hr.employment_started.started_title', { defaultValue: 'Started' }),
          })
          // Stay on handoff host — refresh row for employee id display only; never Navigate.
          await loadRow()
        }
      } catch (e: unknown) {
        const message = parseDetail(e)
        setStartedError(message)
        notify({ variant: 'error', title: message })
      } finally {
        setStartedConfirming(false)
      }
    },
    [id, loadRow, notify, parseDetail, t],
  )

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
            if (evalOnceRef.current !== id) {
              evalOnceRef.current = id
              await runEmployability()
            }
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
  }, [id, loadRow, runAcceptPolicy, runEmployability, t])

  const loadLegacyReview = useCallback(async () => {
    if (!id || !row) return
    if (String(row.handoff?.status || '').toLowerCase() !== 'accepted') return
    try {
      setHrReview(await fetchHandoffHrReview(id))
    } catch {
      setHrReview(null)
    }
  }, [id, row])

  const empId = row?.workforce_employee_id || hrReview?.employee_id || started?.employee_id || undefined
  const displayName = row?.candidate_display_name || undefined
  const pendingOpen = shouldApplyEmploymentAcceptPolicyOnOpen({
    handoffStatus: row?.handoff?.status,
    operationalQueue: String(row?.operational_queue || ''),
  })
  const accepted =
    Boolean(policy?.accepted) || String(row?.handoff?.status || '').toLowerCase() === 'accepted'
  const readyForFormalize = decisionSurfaceMode(employability).readyForFormalize
  const showFormalize = accepted && (readyForFormalize || Boolean(formalize) || formalizeEvaluating)
  const showStarted =
    accepted &&
    (shouldEnterStartedFromFormalize(formalize) || Boolean(started) || startedEvaluating)
  const startedTerminal = isStartedTerminal(started)

  // Lock: never redirect to employee card from this HR handoff host.
  if (
    shouldRedirectToEmployeeCardFromHandoffHost({
      workforceEmployeeId: empId,
      formalize,
      started,
      showStartedSurface: showStarted,
    })
  ) {
    return null
  }

  return (
    <div className="space-y-4" data-testid="hr-handoff-detail-host">
      <PageHeader
        breadcrumbItems={[
          { label: t('app.nav.hr.workspace.title', { defaultValue: 'HR workspace' }), to: CRM_APP_PATHS.hr },
          { label: t('app.nav.hr.inbox.heading', { defaultValue: 'Inbox' }), to: CRM_APP_PATHS.hrInbox },
          { label: displayName || id || '…' },
        ]}
        title={displayName || t('app.nav.hr.handoff.title', { defaultValue: 'Handoff' })}
        kind="browse"
        secondaryActions={
          <button type="button" className="btn-secondary btn-sm" onClick={() => void loadRow()}>
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

          <div data-testid="hr-employment-accept-no-ritual" hidden aria-hidden="true" />

          {accepted ? (
            <HrEmploymentDecisionSurface
              employability={employability}
              evaluating={evaluating}
              resolving={resolving}
              error={decisionError}
              formalizeBound={showFormalize}
              onResolve={(patch) => void runResolve(patch)}
            />
          ) : null}

          {showFormalize ? (
            <HrEmploymentFormalizePanel
              formalize={formalize}
              evaluating={formalizeEvaluating}
              confirming={formalizeConfirming}
              error={formalizeError}
              onConfirm={(patch) => void runFormalizeConfirm(patch)}
            />
          ) : null}

          {showStarted ? (
            <HrEmploymentStartedPanel
              started={started}
              evaluating={startedEvaluating}
              confirming={startedConfirming}
              error={startedError}
              onConfirm={(confirmation) => void runStartedConfirm(confirmation)}
            />
          ) : null}

          {startedTerminal ? (
            <div data-testid="hr-employment-started-host-terminal" hidden aria-hidden="true" />
          ) : null}

          <HrHandoffContextSummary row={row} />

          {accepted ? (
            <details
              className="rounded-lg border border-slate-200 bg-white"
              onToggle={(e) => {
                const open = (e.target as HTMLDetailsElement).open
                setLegacyOpen(open)
                if (open && !hrReview) void loadLegacyReview()
              }}
            >
              <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-800">
                {t('app.hr.employment_accept.legacy_review_summary', {
                  defaultValue: 'Legacy document verification (not Employment Formalize)',
                })}
              </summary>
              {legacyOpen && hrReview ? (
                <div className="space-y-4 border-t border-slate-100 px-4 py-4">
                  <HrDataVerificationWorkspace
                    panel={hrReview}
                    handoffId={id}
                    employeeId={empId}
                    manage
                    onPanelUpdated={(next) => setHrReview(next)}
                  />
                  <HrReviewPanelCard
                    handoffId={id!}
                    employeeId={empId}
                    panel={hrReview}
                    hideDocuments
                    caseDecisionMode
                    manage
                    onUpdated={(next) => setHrReview(next)}
                  />
                </div>
              ) : legacyOpen ? (
                <p className="border-t border-slate-100 px-4 py-3 text-sm text-slate-500">{t('common.loading')}</p>
              ) : null}
            </details>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
