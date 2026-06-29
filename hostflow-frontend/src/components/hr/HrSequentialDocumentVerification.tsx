import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import { returnHandoff } from '../../api/handoffs'
import { fetchHandoffHrReview } from '../../api/hrWorkspace'
import {
  postHrAdditionalDocumentRequest,
  postHrDocumentOpened,
  postHrDocumentRequestCorrection,
  postHrDocumentVerify,
  postHrDocumentWaiveRequirement,
  rejectWorkforceHrReview,
  returnWorkforceHrReviewToRecruitment,
} from '../../api/workforce'
import HrDocumentDecisionFooter from './HrDocumentDecisionFooter'
import HrVerificationExceptionsPanel from './HrVerificationExceptionsPanel'
import HrEmploymentIdentityCompact from './HrEmploymentIdentityCompact'
import HrVerificationStepShell from './HrVerificationStepShell'
import HrVerificationDocumentFileActions from './HrVerificationDocumentFileActions'
import { humanVerificationBlockingMessages } from './hrVerificationBlockingHuman'
import BlockerPanel from '../surfaces/BlockerPanel'
import DocumentRow from '../surfaces/DocumentRow'
import DocumentStatus from '../surfaces/DocumentStatus'
import { mapHrVerificationDocumentRow } from '../surfaces/mapHrVerificationDocument'
import { isVerificationPlanReady } from './hrVerificationReadySummary'
import { openHrDocumentInNewTab } from '../../utils/hrDocumentOpen'
import {
  buildConfirmedReviewedPayload,
  buildInitialFieldEdits,
  canConfirmHrVerificationDocument,
  countMissingFieldsOnDocument,
  countUnfilledFieldEdits,
  countVerifiedDocuments,
  documentsFromPanel,
  findQueueIndexForDocumentFocus,
  firstPendingDocumentIndex,
  isDocumentVerified,
  requiredPlanDocuments,
  sequentialDocumentQueue,
  type DocumentFieldEdit,
} from './hrDocumentVerificationFields'
import { formatRecruiterValueForField } from './hrVerificationFieldMeta'
import HrVerificationFieldInput from './HrVerificationFieldInput'
import { dossierBlockKind, dossierShowFileActions } from './dossierBlockKind'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'

const REVIEW_FROZEN_STATUSES = new Set([
  'returned_to_recruitment',
  'rejected_by_hr',
  'approved_for_employment',
])

type Props = {
  panel: HrReviewPanel
  employeeId?: string
  handoffId?: string
  candidateId?: string | null
  manage?: boolean
  onPanelUpdated?: (panel: HrReviewPanel) => void
  onDocumentConfirmed?: (documentLabel: string) => void
  verificationFocus?: { documentKey?: string | null; packCode?: string | null } | null
}

export default function HrSequentialDocumentVerification({
  panel,
  employeeId,
  handoffId,
  candidateId: candidateIdProp,
  manage: manageProp = false,
  onPanelUpdated,
  onDocumentConfirmed,
  verificationFocus,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const reviewFrozen = REVIEW_FROZEN_STATUSES.has(panel.status)
  const manage = manageProp && !reviewFrozen
  const effectiveEmployeeId = (employeeId || panel.employee_id || '').trim()
  const docs = useMemo(() => documentsFromPanel(panel), [panel])
  const requiredDocs = useMemo(() => requiredPlanDocuments(docs), [docs])
  const queue = useMemo(() => sequentialDocumentQueue(requiredDocs), [requiredDocs])
  const planSteps = panel.verification_plan?.verification_order ?? []
  const progress = useMemo(() => countVerifiedDocuments(docs), [docs])

  const planReady = isVerificationPlanReady(panel)
  const candidateId = candidateIdProp ?? panel.candidate_id ?? null
  const [activeIndex, setActiveIndex] = useState(() => firstPendingDocumentIndex(queue))
  const [busy, setBusy] = useState<string | null>(null)

  const activeDoc = queue[activeIndex] ?? null
  const activeStep = activeDoc
    ? planSteps.find((s) => s.document_keys?.includes(activeDoc.document_key))
    : null

  const [fieldEdits, setFieldEdits] = useState<Record<string, DocumentFieldEdit>>({})

  useEffect(() => {
    if (!activeDoc) return
    setFieldEdits(buildInitialFieldEdits(activeDoc))
  }, [activeDoc?.document_key])

  useEffect(() => {
    const next = firstPendingDocumentIndex(queue)
    setActiveIndex((prev) => {
      if (prev >= queue.length) return Math.max(0, queue.length - 1)
      if (queue[prev] && !isDocumentVerified(queue[prev])) return prev
      return next
    })
  }, [queue])

  useEffect(() => {
    if (!verificationFocus) return
    const idx = findQueueIndexForDocumentFocus(queue, verificationFocus)
    if (idx < 0) return
    setActiveIndex(idx)
  }, [verificationFocus, queue])

  const nextPendingLabel = useMemo(() => {
    const pending = queue.filter((d) => !isDocumentVerified(d))
    const next = pending.find((d) => d.document_key !== activeDoc?.document_key)
    return next?.label ?? null
  }, [queue, activeDoc?.document_key])

  const scope = useMemo(
    () => ({
      employeeId,
      handoffId,
      documentKey: activeDoc?.document_key ?? '',
    }),
    [employeeId, handoffId, activeDoc?.document_key],
  )

  const runPanel = useCallback(
    async (fn: () => Promise<HrReviewPanel>, successTitle?: string) => {
      setBusy('action')
      try {
        const next = await fn()
        onPanelUpdated?.(next)
        notify({
          variant: 'success',
          title: successTitle ?? t('app.hr.verify_shell.saved', { defaultValue: 'Document saved' }),
        })
        return next
      } catch (e: unknown) {
        notify({
          variant: 'error',
          title: e instanceof Error ? e.message : t('common.errors.request_failed'),
        })
        return null
      } finally {
        setBusy(null)
      }
    },
    [notify, onPanelUpdated, t],
  )

  const handleOpenDocument = async () => {
    const openUrl = activeDoc?.open_url || activeDoc?.file_url
    if (!openUrl || !activeDoc) return
    if (!manage || !activeDoc.document_key) {
      await openHrDocumentInNewTab({ openUrl })
      return
    }
    setBusy('open')
    try {
      await openHrDocumentInNewTab({ openUrl })
      const next = await postHrDocumentOpened({
        employeeId,
        handoffId,
        documentKey: activeDoc.document_key,
      })
      onPanelUpdated?.(next)
    } catch (e: unknown) {
      notify({
        variant: 'error',
        title: e instanceof Error ? e.message : t('common.errors.request_failed'),
      })
    } finally {
      setBusy(null)
    }
  }

  const handleRequestCorrection = async (note: string) => {
    if (!activeDoc?.document_key) return
    const caseNote = t('app.hr.decisions.correction_case_note', {
      defaultValue: '{document}: {note}',
      values: { document: activeDoc.label, note },
    })
    await runPanel(async () => {
      let next = await postHrDocumentRequestCorrection({ ...scope, note: caseNote })
      if (effectiveEmployeeId) {
        next = await returnWorkforceHrReviewToRecruitment(effectiveEmployeeId, caseNote)
      } else if (handoffId) {
        await returnHandoff(handoffId, caseNote)
        next = await fetchHandoffHrReview(handoffId)
      }
      return next
    }, t('app.hr.decisions.correction_sent', { defaultValue: 'Sent back to recruitment' }))
  }

  const handleRejectCandidate = async (reason: string) => {
    if (!effectiveEmployeeId) return
    await runPanel(
      () => rejectWorkforceHrReview(effectiveEmployeeId, reason),
      t('app.hr.decisions.reject_done', { defaultValue: 'Candidate rejected' }),
    )
  }

  const handleWaiveRequirement = async (reason: string) => {
    if (!activeDoc?.document_key) return
    await runPanel(
      () => postHrDocumentWaiveRequirement({ ...scope, reason }),
      t('app.hr.exceptions.waive_done', { defaultValue: 'Requirement marked as exception' }),
    )
  }

  const handleAdditionalDocument = async (payload: {
    document_name: string
    note?: string
    urgency?: string
  }) => {
    const caseScope = { employeeId, handoffId }
    await runPanel(
      () => postHrAdditionalDocumentRequest(caseScope, payload),
      t('app.hr.exceptions.additional_done', {
        defaultValue: 'Recruitment will be asked for the document',
      }),
    )
  }

  const confirmDocument = async () => {
    if (!activeDoc?.document_key || !manage) return
    const confirmedLabel = activeDoc.label || activeDoc.document_key
    onDocumentConfirmed?.(confirmedLabel)
    const payload = buildConfirmedReviewedPayload(fieldEdits)
    const next = await runPanel(() =>
      postHrDocumentVerify({ ...scope, reviewed_fields: payload }),
    )
    if (!next) return
    const refreshedDocs = documentsFromPanel(next)
    const refreshedQueue = sequentialDocumentQueue(requiredPlanDocuments(refreshedDocs))
    const idx = refreshedQueue.findIndex((d) => !isDocumentVerified(d))
    if (idx >= 0) setActiveIndex(idx)
    else if (activeIndex < refreshedQueue.length - 1) setActiveIndex(activeIndex + 1)
  }

  const blockingMessages = useMemo(
    () => humanVerificationBlockingMessages(panel, docs, t),
    [panel, docs, t],
  )

  if (queue.length === 0) return null
  if (!activeDoc) return null

  const fields = activeDoc.fields_to_review ?? []
  const blockKind = dossierBlockKind(activeDoc)
  const showFilePanel = dossierShowFileActions(activeDoc)
  const missingFieldCount = manage
    ? countUnfilledFieldEdits(activeDoc, fieldEdits)
    : countMissingFieldsOnDocument(activeDoc)
  const docNeedsCorrection =
    String(activeDoc.verification_status || activeDoc.status || '').toLowerCase() === 'needs_correction'
  const canConfirm = canConfirmHrVerificationDocument(activeDoc, manage, fieldEdits)
  const allFieldsHaveValues =
    fields.length === 0 || countUnfilledFieldEdits(activeDoc, fieldEdits) === 0

  const stepNumber = activeStep?.step_order ?? activeIndex + 1
  const stepLabel = activeStep?.label ?? t('app.hr.verify_shell.default_step', { defaultValue: 'Required documents' })
  const stepHeadline =
    blockKind === 'data_only'
      ? t('app.hr.verify_shell.step_confirm_data', {
          defaultValue: 'Step {step}: Confirm {label}',
          values: { step: stepNumber, label: activeDoc.label },
        })
      : t('app.hr.verify_shell.step_verify', {
          defaultValue: 'Step {step}: Verify {document}',
          values: { step: stepNumber, document: activeDoc.label },
        })
  const activeMapped = mapHrVerificationDocumentRow(activeDoc, t)

  const documentViewer = (
    <div className="flex flex-1 flex-col rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <DocumentRow compact className="border-slate-200 shadow-none" {...activeMapped.row} />
      <div className="mt-5 flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50/80 px-4 py-10 text-center">
        {showFilePanel ? (
          <HrVerificationDocumentFileActions
            activeDoc={activeDoc}
            candidateId={candidateId}
            employeeId={effectiveEmployeeId || employeeId}
            manage={manage}
            busy={!!busy}
            onOpen={handleOpenDocument}
            onPanelUpdated={onPanelUpdated}
          />
        ) : (
          <div className="max-w-sm space-y-2">
            <p className="text-sm font-medium text-slate-800">
              {t('app.hr.dossier.data_block', { defaultValue: 'Employee data' })}
            </p>
            <p className="text-sm text-slate-600">
              {t('app.hr.verify_shell.data_only_hint', {
                defaultValue:
                  'No file for this block — check and complete the fields on the right, then confirm.',
              })}
            </p>
          </div>
        )}
      </div>
      {queue.length > 1 ? (
        <nav
          className="mt-4 space-y-1.5"
          aria-label={t('app.hr.verify_shell.doc_nav', { defaultValue: 'Documents' })}
        >
          {queue.map((d, i) => {
            const mapped = mapHrVerificationDocumentRow(d, t)
            const current = i === activeIndex
            return (
              <button
                key={d.document_key}
                type="button"
                aria-label={d.label}
                aria-current={current ? 'step' : undefined}
                className={clsx(
                  'w-full rounded-lg text-left transition-shadow',
                  current && 'ring-2 ring-brand-400 ring-offset-1',
                )}
                onClick={() => setActiveIndex(i)}
              >
                <DocumentRow compact className="pointer-events-none border-slate-200 shadow-none" {...mapped.row} />
              </button>
            )
          })}
        </nav>
      ) : null}
    </div>
  )

  const dataPanel = (
    <>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.hr.verify_shell.check_data', { defaultValue: 'Check these details' })}
      </p>
      {missingFieldCount > 0 ? (
        <p className="mt-1 text-xs font-medium text-amber-800">
          {blockKind === 'data_only'
            ? t('app.hr.verify_shell.missing_count_data', {
                defaultValue: '{count} field(s) still empty — enter the value',
                values: { count: missingFieldCount },
              })
            : t('app.hr.verify_shell.missing_count', {
                defaultValue: '{count} field(s) missing — enter from the document',
                values: { count: missingFieldCount },
              })}
        </p>
      ) : null}
      {fields.length > 0 ? (
        <ul className="mt-3 flex-1 space-y-3">
          {fields.map((f) => {
            const ed = fieldEdits[f.field_code] || { value: '', comment: '', confirmed: false }
            const recruiter = formatRecruiterValueForField(f)
            return (
              <li key={f.field_code} className="rounded-lg border border-slate-200 bg-white p-3">
                <label className="block text-sm font-medium text-slate-900">{f.label}</label>
                {recruiter ? (
                  <p className="mt-0.5 text-xs text-slate-500">
                    {t('app.hr.verify_shell.from_recruitment', { defaultValue: 'From recruitment' })}:{' '}
                    <span className="text-slate-800">{recruiter}</span>
                  </p>
                ) : (
                  <p className="mt-0.5 text-xs font-medium text-amber-800">
                    {blockKind === 'data_only'
                      ? t('app.hr.verify_shell.missing_field_data', {
                          defaultValue: 'Missing — enter manually',
                        })
                      : t('app.hr.verify_shell.missing_field', {
                          defaultValue: 'Missing — enter from document',
                        })}
                  </p>
                )}
                {manage ? (
                  <HrVerificationFieldInput
                    field={f}
                    value={ed.value}
                    disabled={!!busy}
                    onChange={(next) =>
                      setFieldEdits((prev) => ({
                        ...prev,
                        [f.field_code]: { ...ed, value: next },
                      }))
                    }
                  />
                ) : (
                  <p className="mt-2 text-sm text-slate-800">{ed.value || '—'}</p>
                )}
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-600">
          {t('app.hr.verify_shell.no_fields', {
            defaultValue: 'No extra fields — confirm the file is correct.',
          })}
        </p>
      )}
      <HrVerificationExceptionsPanel
        panel={panel}
        activeDoc={activeDoc}
        canManage={manage}
        busy={!!busy}
        onWaive={handleWaiveRequirement}
        onRequestAdditional={handleAdditionalDocument}
      />
    </>
  )

  const confirmLabel = isDocumentVerified(activeDoc)
    ? t('app.hr.verify_shell.confirm_next', { defaultValue: 'Confirm & next document' })
    : blockKind === 'data_only'
      ? t('app.hr.dossier.confirm_data', { defaultValue: 'Confirm data' })
      : t('app.hr.verify_shell.confirm', { defaultValue: 'Confirm this document' })

  const footer = (
    <HrDocumentDecisionFooter
      activeIndex={activeIndex}
      queueLength={queue.length}
      documentLabel={activeDoc.label}
      busy={!!busy}
      canConfirm={canConfirm}
      confirmLabel={confirmLabel}
      allFieldsHaveValues={allFieldsHaveValues}
      canManage={manage}
      canRejectCase={Boolean(effectiveEmployeeId)}
      onPrevious={() => setActiveIndex((i) => Math.max(0, i - 1))}
      onNext={() => setActiveIndex((i) => Math.min(queue.length - 1, i + 1))}
      onConfirm={() => void confirmDocument()}
      onRequestCorrection={handleRequestCorrection}
      onRejectCandidate={handleRejectCandidate}
    />
  )

  const blockingBanner =
    !planReady && blockingMessages.length > 0 && !reviewFrozen ? (
      <BlockerPanel
        className="mb-3"
        title={t('app.hr.ready.still_needed', { defaultValue: 'Still needed before approval' })}
        severity="blocker"
        items={blockingMessages.map((msg, index) => ({
          id: `${index}-${msg}`,
          label: msg,
          severity: 'blocker' as const,
        }))}
      />
    ) : null

  const frozenBanner = reviewFrozen ? (
    <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
      {panel.status === 'returned_to_recruitment'
        ? t('app.hr.decisions.frozen_returned', {
            defaultValue: 'Case returned to recruitment. Verification is read-only until the package is updated.',
          })
        : panel.status === 'rejected_by_hr'
          ? t('app.hr.decisions.frozen_rejected', {
              defaultValue: 'Candidate rejected. This review is closed.',
            })
          : t('app.hr.decisions.frozen_approved', {
              defaultValue: 'Candidate approved. Document verification is complete.',
            })}
      {panel.return_reason ? (
        <p className="mt-1 text-xs text-slate-600">{panel.return_reason}</p>
      ) : null}
    </div>
  ) : null

  return (
    <HrVerificationStepShell
      stepNumber={stepNumber}
      stepLabel={stepLabel}
      documentLabel={activeDoc.label}
      stepHeadline={stepHeadline}
      statusBadge={
        <DocumentStatus
          label={activeMapped.statusLabel}
          displayStatus={activeMapped.displayStatus}
          severity={activeMapped.severity}
        />
      }
      verifiedCount={progress.verified}
      totalCount={progress.total}
      nextDocumentLabel={nextPendingLabel}
      documentViewer={documentViewer}
      dataPanel={dataPanel}
      footer={
        <>
          {blockingBanner}
          {frozenBanner}
          {footer}
        </>
      }
      identityStrip={<HrEmploymentIdentityCompact panel={panel} />}
    />
  )
}
