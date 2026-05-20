import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import {
  postHrDocumentOpened,
  postHrDocumentReject,
  postHrDocumentRequestCorrection,
  postHrDocumentVerify,
} from '../../api/workforce'
import HrEmploymentIdentityCompact from './HrEmploymentIdentityCompact'
import { openHrDocumentInNewTab } from '../../utils/hrDocumentOpen'
import {
  buildConfirmedReviewedPayload,
  buildInitialFieldEdits,
  countVerifiedDocuments,
  documentsFromPanel,
  firstPendingDocumentIndex,
  isDocumentVerified,
  recommendedPlanDocuments,
  recruiterDisplayForField,
  requiredPlanDocuments,
  sequentialDocumentQueue,
  type DocumentFieldEdit,
} from './hrDocumentVerificationFields'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'

type Props = {
  panel: HrReviewPanel
  employeeId?: string
  handoffId?: string
  manage?: boolean
  onPanelUpdated?: (panel: HrReviewPanel) => void
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'verified':
      return 'border-emerald-200 bg-emerald-50 text-emerald-900'
    case 'rejected':
      return 'border-rose-200 bg-rose-50 text-rose-900'
    case 'needs_correction':
      return 'border-amber-200 bg-amber-50 text-amber-900'
    case 'opened':
      return 'border-sky-200 bg-sky-50 text-sky-900'
    default:
      return 'border-slate-200 bg-slate-50 text-slate-700'
  }
}

export default function HrSequentialDocumentVerification({
  panel,
  employeeId,
  handoffId,
  manage = false,
  onPanelUpdated,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const docs = useMemo(() => documentsFromPanel(panel), [panel])
  const requiredDocs = useMemo(() => requiredPlanDocuments(docs), [docs])
  const recommendedDocs = useMemo(() => recommendedPlanDocuments(docs), [docs])
  const notRequiredKeys = panel.verification_plan?.not_required_document_keys ?? []
  const queue = useMemo(() => sequentialDocumentQueue(requiredDocs), [requiredDocs])
  const planSteps = panel.verification_plan?.verification_order ?? []
  const progress = useMemo(() => countVerifiedDocuments(docs), [docs])

  const [activeIndex, setActiveIndex] = useState(() => firstPendingDocumentIndex(docs))
  const [busy, setBusy] = useState<string | null>(null)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [correctionOpen, setCorrectionOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [correctionNote, setCorrectionNote] = useState('')
  const [showTechnical, setShowTechnical] = useState(false)

  const activeDoc = queue[activeIndex] ?? null
  const activeStep = activeDoc
    ? planSteps.find((s) => s.document_keys?.includes(activeDoc.document_key))
    : null

  const [fieldEdits, setFieldEdits] = useState<Record<string, DocumentFieldEdit>>({})

  useEffect(() => {
    if (!activeDoc) return
    setFieldEdits(buildInitialFieldEdits(activeDoc))
    setRejectOpen(false)
    setCorrectionOpen(false)
    setRejectReason('')
    setCorrectionNote('')
  }, [activeDoc?.document_key])

  useEffect(() => {
    const next = firstPendingDocumentIndex(docs)
    setActiveIndex((prev) => {
      if (prev >= queue.length) return Math.max(0, queue.length - 1)
      if (queue[prev] && !isDocumentVerified(queue[prev])) return prev
      return next
    })
  }, [docs, queue.length])

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
    async (key: string, fn: () => Promise<HrReviewPanel>) => {
      setBusy(key)
      try {
        const next = await fn()
        onPanelUpdated?.(next)
        notify({ variant: 'success', title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }) })
        return next
      } catch (e: unknown) {
        notify({
          variant: 'error',
          title: e instanceof Error ? e.message : t('common.errors.request_failed'),
        })
        return null
      } finally {
        setBusy(null)
        setRejectOpen(false)
        setCorrectionOpen(false)
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

  const confirmDocument = async () => {
    if (!activeDoc?.document_key || !manage) return
    const payload = buildConfirmedReviewedPayload(fieldEdits)
    const next = await runPanel('confirm', () =>
      postHrDocumentVerify({ ...scope, reviewed_fields: payload }),
    )
    if (!next) return
    const refreshed = sequentialDocumentQueue(next.documents_for_approval ?? [])
    const idx = refreshed.findIndex((d) => !isDocumentVerified(d))
    if (idx >= 0) setActiveIndex(idx)
    else if (activeIndex < refreshed.length - 1) setActiveIndex(activeIndex + 1)
  }

  if (queue.length === 0) return null

  const verificationStatus = String(activeDoc?.verification_status || activeDoc?.status || 'pending')
  const fields = activeDoc?.fields_to_review ?? []
  const canConfirm = manage && activeDoc?.actions?.can_verify && activeDoc.document_id
  const allFieldsHaveValues =
    fields.length === 0 || fields.every((f) => (fieldEdits[f.field_code]?.value ?? '').trim().length > 0)

  return (
    <section id="hr-document-verification" className="scroll-mt-24">
      <div className="sticky top-0 z-10 rounded-xl border border-brand-200 bg-white shadow-md">
        <div className="border-b border-brand-100 bg-brand-50/70 px-4 py-3">
          <h2 className="text-lg font-semibold text-slate-900">
            {activeStep
              ? t('app.hr.doc_flow.step_title', {
                  defaultValue: 'Step {step}: {label}',
                  values: {
                    step: activeStep.step_order,
                    label: activeStep.label,
                  },
                })
              : t('app.hr.doc_flow.title', { defaultValue: 'Document verification' })}
          </h2>
          {activeDoc ? (
            <p className="text-sm font-medium text-slate-700">{activeDoc.label}</p>
          ) : null}
          <p className="mt-1 text-sm text-slate-600">
            {t('app.hr.doc_flow.hint', {
              defaultValue: 'Open each document, check recruiter data, fix if needed, then confirm the document.',
            })}
          </p>
          <p className="mt-2 text-sm font-medium text-slate-800">
            {t('app.hr.doc_flow.progress', {
              defaultValue: '{verified} of {total} documents confirmed',
              values: { verified: progress.verified, total: progress.total },
            })}
            {nextPendingLabel && !isDocumentVerified(activeDoc!) ? (
              <span className="ml-2 font-normal text-slate-600">
                · {t('app.hr.doc_flow.next', { defaultValue: 'Next' })}: {nextPendingLabel}
              </span>
            ) : null}
          </p>
          <div className="mt-2">
            <HrEmploymentIdentityCompact panel={panel} />
          </div>
        </div>

        {activeDoc ? (
          <div className="grid min-h-[28rem] grid-cols-1 lg:grid-cols-2 lg:divide-x lg:divide-slate-100">
            <div className="flex flex-col bg-slate-50/50 p-4 lg:sticky lg:top-[7.5rem] lg:max-h-[calc(100vh-8rem)] lg:self-start">
              <div className="flex flex-1 flex-col rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <h3 className="text-base font-semibold text-slate-900">{activeDoc.label}</h3>
                  <span
                    className={clsx(
                      'inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                      statusBadgeClass(verificationStatus),
                    )}
                  >
                    {verificationStatus.replace(/_/g, ' ')}
                  </span>
                </div>
                {activeDoc.rejection_reason ? (
                  <p className="mt-2 text-xs text-rose-800">{activeDoc.rejection_reason}</p>
                ) : null}
                {activeDoc.correction_note ? (
                  <p className="mt-2 text-xs text-amber-800">{activeDoc.correction_note}</p>
                ) : null}
                <div className="mt-6 flex flex-1 flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-slate-200 bg-slate-50/80 px-4 py-10 text-center">
                  <p className="text-sm text-slate-600">
                    {t('app.hr.doc_flow.viewer_hint', {
                      defaultValue: 'Open the scan or PDF and compare it with the fields on the right.',
                    })}
                  </p>
                  {(activeDoc.open_url || activeDoc.file_url) && activeDoc.actions?.can_open !== false ? (
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={!!busy}
                      onClick={() => void handleOpenDocument()}
                    >
                      {t('app.hr.doc_flow.open_document', { defaultValue: 'Open document' })}
                    </button>
                  ) : (
                    <p className="text-xs font-medium text-amber-800">
                      {t('app.hr.doc_flow.missing_file', {
                        defaultValue: 'Missing file — request from recruiter or candidate',
                      })}
                    </p>
                  )}
                </div>
                {queue.length > 1 ? (
                  <div className="mt-4 flex flex-wrap gap-1">
                    {queue.map((d, i) => {
                      const done = isDocumentVerified(d)
                      const current = i === activeIndex
                      return (
                        <button
                          key={d.document_key}
                          type="button"
                          title={d.label}
                          className={clsx(
                            'h-2 w-6 rounded-full transition-colors',
                            current && 'ring-2 ring-brand-400 ring-offset-1',
                            done ? 'bg-emerald-500' : current ? 'bg-brand-500' : 'bg-slate-200',
                          )}
                          onClick={() => setActiveIndex(i)}
                        />
                      )
                    })}
                  </div>
                ) : null}
              </div>
            </div>

            <div className="flex flex-col p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {t('app.hr.doc_flow.data_to_check', { defaultValue: 'Data to verify' })}
              </p>
              {fields.length > 0 ? (
                <ul className="mt-3 flex-1 space-y-4">
                  {fields.map((f) => {
                    const ed = fieldEdits[f.field_code] || { value: '', comment: '', confirmed: false }
                    const recruiter = recruiterDisplayForField(f)
                    return (
                      <li key={f.field_code} className="rounded-lg border border-slate-200 bg-white p-3">
                        <label className="block text-sm font-medium text-slate-900">{f.label}</label>
                        {recruiter ? (
                          <p className="mt-0.5 text-xs text-slate-500">
                            {t('app.hr.doc_flow.from_recruitment', { defaultValue: 'From recruitment' })}:{' '}
                            <span className="text-slate-700">{recruiter}</span>
                          </p>
                        ) : (
                          <p className="mt-0.5 text-xs font-medium text-amber-800">
                            {t('app.hr.doc_flow.missing_value', { defaultValue: 'Missing — enter from document' })}
                          </p>
                        )}
                        {manage ? (
                          <input
                            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            value={ed.value}
                            onChange={(e) =>
                              setFieldEdits((prev) => ({
                                ...prev,
                                [f.field_code]: { ...ed, value: e.target.value },
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
                  {t('app.hr.doc_flow.no_fields', {
                    defaultValue: 'No separate fields — confirm that the uploaded file is correct.',
                  })}
                </p>
              )}

              {manage && canConfirm ? (
                <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                  <button
                    type="button"
                    className="text-xs text-slate-600 underline-offset-2 hover:underline"
                    onClick={() => setCorrectionOpen((v) => !v)}
                  >
                    {t('app.hr.doc_verify.request_correction', { defaultValue: 'Request correction' })}
                  </button>
                  <button
                    type="button"
                    className="text-xs text-rose-700 underline-offset-2 hover:underline"
                    onClick={() => setRejectOpen((v) => !v)}
                  >
                    {t('app.hr.doc_verify.reject', { defaultValue: 'Reject document' })}
                  </button>
                </div>
              ) : null}

              {correctionOpen && manage ? (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50/50 p-3">
                  <textarea
                    className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                    rows={2}
                    value={correctionNote}
                    onChange={(e) => setCorrectionNote(e.target.value)}
                    placeholder={t('app.hr.doc_verify.correction_placeholder', {
                      defaultValue: 'What must be corrected?',
                    })}
                  />
                  <button
                    type="button"
                    className="btn-secondary btn-sm mt-2"
                    disabled={!correctionNote.trim() || !!busy}
                    onClick={() =>
                      void runPanel('correction', () =>
                        postHrDocumentRequestCorrection({ ...scope, note: correctionNote.trim() }),
                      )
                    }
                  >
                    {t('common.submit', { defaultValue: 'Submit' })}
                  </button>
                </div>
              ) : null}

              {rejectOpen && manage ? (
                <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50/50 p-3">
                  <textarea
                    className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                    rows={2}
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder={t('app.hr.doc_verify.reject_placeholder', { defaultValue: 'Rejection reason' })}
                  />
                  <button
                    type="button"
                    className="btn-secondary btn-sm mt-2"
                    disabled={!rejectReason.trim() || !!busy}
                    onClick={() =>
                      void runPanel('reject', () =>
                        postHrDocumentReject({ ...scope, reason: rejectReason.trim() }),
                      )
                    }
                  >
                    {t('common.submit', { defaultValue: 'Submit' })}
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 bg-slate-50/80 px-4 py-3">
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={activeIndex <= 0 || !!busy}
            onClick={() => setActiveIndex((i) => Math.max(0, i - 1))}
          >
            {t('app.hr.doc_flow.previous', { defaultValue: 'Previous' })}
          </button>
          {canConfirm ? (
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={!!busy || !allFieldsHaveValues}
              onClick={() => void confirmDocument()}
            >
              {isDocumentVerified(activeDoc!)
                ? t('app.hr.doc_flow.reconfirm', { defaultValue: 'Save & next document' })
                : t('app.hr.doc_flow.confirm_continue', {
                    defaultValue: 'Confirm document & continue',
                  })}
            </button>
          ) : (
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={activeIndex >= queue.length - 1 || !!busy}
              onClick={() => setActiveIndex((i) => Math.min(queue.length - 1, i + 1))}
            >
              {t('app.hr.doc_flow.skip_next', { defaultValue: 'Next document' })}
            </button>
          )}
        </div>

        {recommendedDocs.length > 0 ? (
          <details className="border-t border-slate-100 px-4 py-2">
            <summary className="cursor-pointer text-xs font-medium text-slate-600">
              {t('app.hr.doc_flow.recommended_documents', {
                defaultValue: 'Recommended ({count}) — HR may waive',
                values: { count: recommendedDocs.length },
              })}
            </summary>
            <ul className="mt-2 space-y-1 text-sm text-slate-700">
              {recommendedDocs.map((d) => (
                <li key={d.document_key}>
                  {d.label}
                  {isDocumentVerified(d) ? (
                    <span className="ml-2 text-emerald-700">
                      {t('app.hr.doc_flow.verified_short', { defaultValue: 'confirmed' })}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          </details>
        ) : null}

        {notRequiredKeys.length > 0 ? (
          <details className="border-t border-slate-100 px-4 py-2">
            <summary className="cursor-pointer text-xs font-medium text-slate-500">
              {t('app.hr.doc_flow.not_required_system', {
                defaultValue: 'Not required for this case ({count})',
                values: { count: notRequiredKeys.length },
              })}
            </summary>
            <p className="mt-2 text-xs text-slate-500">{notRequiredKeys.join(' · ')}</p>
          </details>
        ) : null}

        {(panel.data_verification_items?.length ?? 0) > 0 ? (
          <details
            className="border-t border-slate-100 px-4 py-2"
            open={showTechnical}
            onToggle={(e) => setShowTechnical((e.target as HTMLDetailsElement).open)}
          >
            <summary className="cursor-pointer text-xs font-medium text-slate-500">
              {t('app.hr.doc_flow.technical_details', { defaultValue: 'Technical details (admin)' })}
            </summary>
            <p className="mt-2 text-xs text-slate-500">
              {t('app.hr.doc_flow.technical_hint', {
                defaultValue:
                  'Checklist, blockers, and field-level status update automatically when you confirm documents.',
              })}
              {panel.data_verification_summary
                ? ` · ${panel.data_verification_summary.verified_count}/${panel.data_verification_summary.total} fields verified`
                : ''}
            </p>
          </details>
        ) : null}
      </div>
    </section>
  )
}
