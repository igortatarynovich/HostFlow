import clsx from 'clsx'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Document } from '../../../api/types'
import type { RequirementChecklistItem } from '../../../api/candidateRequirements'
import { useI18n } from '../../../i18n'
import {
  documentMatchesVariantTypes,
  evaluatedAlternatives,
  evidenceStatusLabelKey,
  formatExtractionValue,
  hasExtractionBlockers,
  normDocType,
  requirementStatusBadgeClass,
  resolveRequirementRowStatus,
  variantDocumentTypeCodes,
} from '../requirementsChecklistPresentation'
import { requirementTitle, variantLabel } from './requirementRowLabels'

export type RequirementDetailPaneProps = {
  item: RequirementChecklistItem
  canEdit: boolean
  actionBusy: boolean
  labelForType: (code: string) => string
  candidateDocuments: Document[]
  docsLoading: boolean
  onSelectVariant: (variantCode: string) => Promise<unknown>
  onLinkDocument: (evidenceId: string, documentId: string) => Promise<unknown>
  onApprove: (evidenceId: string) => Promise<unknown>
  onReject: (evidenceId: string, reason?: string | null) => Promise<unknown>
  onReplace: (variantCode: string) => Promise<unknown>
  onOpenDocs?: (docType?: string) => void
  onUpload?: () => void
  layout?: 'compact' | 'workspace'
  className?: string
}

export default function RequirementDetailPane({
  item,
  canEdit,
  actionBusy,
  labelForType,
  candidateDocuments,
  docsLoading,
  onSelectVariant,
  onLinkDocument,
  onApprove,
  onReject,
  onReplace,
  onOpenDocs,
  onUpload,
  layout = 'compact',
  className,
}: RequirementDetailPaneProps) {
  const { t } = useI18n()
  const rowStatus = resolveRequirementRowStatus(item)
  const evidence = item.candidate_evidence
  const variants = item.accepted_evidence_variants || []
  const activeVariant =
    variants.find((v) => v.evidence_variant_code === evidence?.evidence_variant_code) || null

  const [selectedVariantCode, setSelectedVariantCode] = useState(
    evidence?.evidence_variant_code || variants[0]?.evidence_variant_code || '',
  )
  const [linkDocumentId, setLinkDocumentId] = useState('')
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [rowBusy, setRowBusy] = useState(false)

  useEffect(() => {
    if (evidence?.evidence_variant_code) {
      setSelectedVariantCode(evidence.evidence_variant_code)
    }
  }, [evidence?.evidence_variant_code, item.requirement_code])

  const allowedTypes = useMemo(
    () => (activeVariant ? variantDocumentTypeCodes(activeVariant) : []),
    [activeVariant],
  )

  const linkableDocuments = useMemo(() => {
    if (!allowedTypes.length) return candidateDocuments
    return candidateDocuments.filter((doc) =>
      documentMatchesVariantTypes(String(doc.doc_type || doc.type || ''), allowedTypes),
    )
  }, [allowedTypes, candidateDocuments])

  useEffect(() => {
    if (!linkDocumentId && linkableDocuments.length) {
      setLinkDocumentId(String(linkableDocuments[0].id))
    }
  }, [linkDocumentId, linkableDocuments])

  const linkedDocIds = useMemo(() => {
    const ids = new Set<string>()
    for (const doc of evidence?.documents || []) {
      const id = String(doc.document_id || doc.id || '').trim()
      if (id) ids.add(id)
    }
    return ids
  }, [evidence?.documents])

  const runRow = useCallback(async (fn: () => Promise<unknown>) => {
    setRowBusy(true)
    try {
      await fn()
    } finally {
      setRowBusy(false)
    }
  }, [])

  const busy = actionBusy || rowBusy
  const editable = canEdit && rowStatus !== 'not_applicable'
  const canLinkOrSelect = editable && rowStatus !== 'approved'
  const canReview = editable && rowStatus === 'pending_review'
  const canReplace =
    canEdit &&
    rowStatus !== 'not_applicable' &&
    Boolean(evidence?.evidence_id) &&
    (rowStatus === 'approved' || rowStatus === 'rejected' || rowStatus === 'pending_review')
  const isWorkspace = layout === 'workspace'
  const showEvidenceActions = Boolean(evidence?.evidence_id) && rowStatus !== 'not_applicable'
  const alternativePaths = useMemo(() => evaluatedAlternatives(item), [item])
  const showAlternativePaths = isWorkspace && alternativePaths.length > 1
  const approveBlocked = hasExtractionBlockers(item)

  const statusLabel = t(evidenceStatusLabelKey(rowStatus), {
    defaultValue:
      rowStatus === 'not_applicable'
        ? 'Not applicable'
        : rowStatus === 'pending_review'
          ? 'Pending review'
          : rowStatus.charAt(0).toUpperCase() + rowStatus.slice(1).replace(/_/g, ' '),
  })

  const purposeHint = item.business_purpose
    ? t(`app.candidate_card.requirements_checklist.purpose.${item.business_purpose}`, {
        defaultValue: '',
      }).trim()
    : ''

  const alternativeStatusLabel = (status: string) =>
    t(`app.candidate_card.requirements_checklist.alternative_status.${status}`, {
      defaultValue:
        status === 'satisfied'
          ? 'Complete'
          : status === 'pending_verification'
            ? 'Partial'
            : status === 'missing'
              ? 'Not started'
              : status.replace(/_/g, ' '),
    })

  return (
    <div
      className={clsx(
        'rounded-xl border border-slate-200 bg-white',
        isWorkspace ? 'p-5' : 'p-3',
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className={clsx('font-semibold text-slate-900', isWorkspace ? 'text-base' : 'text-sm')}>
            {requirementTitle(t, item)}
          </div>
          {purposeHint ? (
            <div className="mt-1 text-xs text-slate-600">{purposeHint}</div>
          ) : (
            <div className="mt-1 text-xs text-slate-600">
              {t('app.candidate_card.requirements_checklist.confirm_hint', {
                defaultValue: 'Choose how you confirm this requirement, then link supporting documents.',
              })}
            </div>
          )}
        </div>
        <span
          className={clsx(
            'shrink-0 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold',
            requirementStatusBadgeClass(rowStatus),
          )}
        >
          {statusLabel}
        </span>
      </div>

      {rowStatus === 'not_applicable' ? (
        <div className="mt-3 text-sm text-slate-500">
          {t('app.candidate_card.requirements_checklist.not_applicable_hint', {
            defaultValue: 'Not required for this candidate profile.',
          })}
        </div>
      ) : null}

      {!evidence && canLinkOrSelect ? (
        <div className="mt-4 space-y-2">
          <label className="block text-[11px] font-semibold uppercase tracking-wide text-slate-600">
            {t('app.candidate_card.requirements_checklist.evidence_picker_label', {
              defaultValue: 'Confirm with',
            })}
          </label>
          <div className="flex flex-wrap gap-2">
            <select
              className="input min-w-[12rem] flex-1 text-sm"
              value={selectedVariantCode}
              onChange={(e) => setSelectedVariantCode(e.target.value)}
              disabled={busy}
            >
              {variants.map((variant) => (
                <option key={variant.evidence_variant_code} value={variant.evidence_variant_code}>
                  {variantLabel(t, variant, labelForType)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={busy || !selectedVariantCode}
              onClick={() => void runRow(() => onSelectVariant(selectedVariantCode))}
            >
              {t('app.candidate_card.requirements_checklist.select_evidence', {
                defaultValue: 'Select evidence',
              })}
            </button>
          </div>
        </div>
      ) : null}

      {showEvidenceActions ? (
        <div className="mt-4 space-y-4">
          {activeVariant ? (
            <div className="text-sm text-slate-700">
              <span className="font-semibold text-slate-800">
                {t('app.candidate_card.requirements_checklist.selected_variant', {
                  defaultValue: 'Evidence',
                })}
                :{' '}
              </span>
              {variantLabel(t, activeVariant, labelForType)}
            </div>
          ) : null}

          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
              {t('app.candidate_card.requirements_checklist.linked_documents', {
                defaultValue: 'Linked documents',
              })}
            </div>
            {evidence?.documents?.length ? (
              <ul className="mt-2 space-y-2">
                {evidence.documents.map((doc) => {
                  const typeCode = String(doc.document_type_code || doc.type || '')
                  const docId = String(doc.document_id || doc.id || '')
                  return (
                    <li key={docId || typeCode}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm hover:bg-slate-100"
                        onClick={() => onOpenDocs?.(typeCode || undefined)}
                      >
                        <span className="font-medium text-slate-900">{labelForType(typeCode)}</span>
                        <span className="text-xs text-slate-600">
                          {doc.has_files === false
                            ? t('app.candidate_card.requirements_checklist.no_files', {
                                defaultValue: 'No files',
                              })
                            : t('app.candidate_card.requirements_checklist.linked', {
                                defaultValue: 'Linked',
                              })}
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            ) : (
              <div className="mt-2 text-sm text-slate-600">
                {t('app.candidate_card.requirements_checklist.no_linked_documents', {
                  defaultValue: 'No documents linked yet.',
                })}
              </div>
            )}
          </div>

          {canLinkOrSelect && (rowStatus === 'selected' || rowStatus === 'pending_review' || rowStatus === 'rejected') ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 space-y-2">
              <div className="text-[11px] font-semibold text-slate-700">
                {t('app.candidate_card.requirements_checklist.link_document', {
                  defaultValue: 'Link document',
                })}
              </div>
              {docsLoading ? (
                <div className="text-sm text-slate-500">{t('common.loading')}</div>
              ) : linkableDocuments.length ? (
                <div className="flex flex-wrap gap-2">
                  <select
                    className="input min-w-[12rem] flex-1 text-sm"
                    value={linkDocumentId}
                    onChange={(e) => setLinkDocumentId(e.target.value)}
                    disabled={busy}
                  >
                    {linkableDocuments.map((doc) => {
                      const id = String(doc.id)
                      const typeCode = String(doc.doc_type || doc.type || '')
                      const already = linkedDocIds.has(id)
                      return (
                        <option key={id} value={id}>
                          {labelForType(typeCode)}
                          {already ? ' ✓' : ''}
                        </option>
                      )
                    })}
                  </select>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={busy || !linkDocumentId || !evidence?.evidence_id}
                    onClick={() =>
                      void runRow(() => onLinkDocument(String(evidence!.evidence_id), linkDocumentId))
                    }
                  >
                    {t('app.candidate_card.requirements_checklist.link_btn', { defaultValue: 'Link' })}
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="text-sm text-slate-600">
                    {t('app.candidate_card.requirements_checklist.upload_first', {
                      defaultValue: 'Upload a matching document first, then link it here.',
                    })}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {onUpload ? (
                      <button type="button" className="btn-primary btn-sm" onClick={onUpload}>
                        {t('app.candidate_card.documents.upload_btn', { defaultValue: 'Upload' })}
                      </button>
                    ) : null}
                    {onOpenDocs ? (
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        onClick={() => onOpenDocs(allowedTypes[0])}
                      >
                        {t('app.candidate_card.docs_panel.open_full', { defaultValue: 'Open documents' })}
                      </button>
                    ) : null}
                  </div>
                </div>
              )}
            </div>
          ) : null}

          {showAlternativePaths ? (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                {t('app.candidate_card.requirements_checklist.evidence_paths', {
                  defaultValue: 'Evidence paths',
                })}
              </div>
              <ul className="mt-2 space-y-2">
                {alternativePaths.map((alt) => {
                  const altCode = String(alt.alternative_code || alt.evidence_variant_code || '')
                  const variant = variants.find((v) => v.evidence_variant_code === altCode)
                  const active = altCode === evidence?.evidence_variant_code
                  return (
                    <li
                      key={altCode}
                      className={clsx(
                        'rounded-lg border px-3 py-2 text-sm',
                        active ? 'border-sky-300 bg-sky-50' : 'border-slate-200 bg-white',
                      )}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium text-slate-900">
                          {variant ? variantLabel(t, variant, labelForType) : altCode}
                        </span>
                        <span className="text-xs font-semibold text-slate-600">
                          {alternativeStatusLabel(String(alt.status || 'missing'))}
                        </span>
                      </div>
                      {alt.document_type_codes?.length ? (
                        <div className="mt-1 text-xs text-slate-600">
                          {alt.document_type_codes.map((code) => labelForType(String(code))).join(' + ')}
                        </div>
                      ) : null}
                    </li>
                  )
                })}
              </ul>
            </div>
          ) : null}

          {evidence?.documents?.some(
            (doc) =>
              (doc.required_extraction_fields?.length || 0) > 0 ||
              (doc.missing_extraction_fields?.length || 0) > 0,
          ) ? (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                {t('app.candidate_card.requirements_checklist.extraction_fields', {
                  defaultValue: 'Document data',
                })}
              </div>
              <div className="mt-2 space-y-3">
                {evidence.documents.map((doc) => {
                  const typeCode = String(doc.document_type_code || doc.type || '')
                  const required = doc.required_extraction_fields || []
                  if (!required.length) return null
                  const extracted = doc.extracted_fields || {}
                  const missing = new Set(doc.missing_extraction_fields || [])
                  return (
                    <div key={String(doc.document_id || doc.id || typeCode)} className="rounded-lg border border-slate-200 p-3">
                      <div className="text-sm font-semibold text-slate-900">{labelForType(typeCode)}</div>
                      <dl className="mt-2 grid gap-2 sm:grid-cols-2">
                        {required.map((fieldCode) => (
                          <div key={fieldCode} className="rounded-md bg-slate-50 px-2 py-1.5">
                            <dt className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                              {t(`app.candidate_card.requirements_checklist.field.${fieldCode}`, {
                                defaultValue: fieldCode.replace(/_/g, ' '),
                              })}
                            </dt>
                            <dd
                              className={clsx(
                                'text-sm',
                                missing.has(fieldCode) ? 'text-amber-800 font-medium' : 'text-slate-900',
                              )}
                            >
                              {missing.has(fieldCode)
                                ? t('app.candidate_card.requirements_checklist.field_missing', {
                                    defaultValue: 'Missing',
                                  })
                                : formatExtractionValue(extracted[fieldCode])}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  )
                })}
              </div>
              {approveBlocked ? (
                <div className="mt-2 text-xs text-amber-800">
                  {t('app.candidate_card.requirements_checklist.approve_blocked_extraction', {
                    defaultValue: 'Fill missing document fields before approving evidence.',
                  })}
                </div>
              ) : null}
            </div>
          ) : null}

          {canReview || canReplace ? (
            <div className="flex flex-wrap gap-2">
              {canReview ? (
                <>
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={busy || approveBlocked}
                    onClick={() => void runRow(() => onApprove(String(evidence!.evidence_id)))}
                  >
                    {t('app.candidate_card.requirements_checklist.approve', { defaultValue: 'Approve' })}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={busy}
                    onClick={() => setRejectOpen((v) => !v)}
                  >
                    {t('app.candidate_card.requirements_checklist.reject', { defaultValue: 'Reject' })}
                  </button>
                </>
              ) : null}

              {canReplace ? (
                <>
                  {variants.length > 1 ? (
                    <select
                      className="input text-sm"
                      value={selectedVariantCode}
                      onChange={(e) => setSelectedVariantCode(e.target.value)}
                      disabled={busy}
                    >
                      {variants.map((variant) => (
                        <option key={variant.evidence_variant_code} value={variant.evidence_variant_code}>
                          {variantLabel(t, variant, labelForType)}
                        </option>
                      ))}
                    </select>
                  ) : null}
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={busy || !selectedVariantCode}
                    onClick={() => void runRow(() => onReplace(selectedVariantCode))}
                  >
                    {t('app.candidate_card.requirements_checklist.replace', {
                      defaultValue: 'Replace evidence',
                    })}
                  </button>
                </>
              ) : null}
            </div>
          ) : null}

          {rejectOpen ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50/60 p-3 space-y-2">
              <textarea
                className="input w-full text-sm"
                rows={2}
                placeholder={t('app.candidate_card.requirements_checklist.reject_reason_placeholder', {
                  defaultValue: 'Reason (optional)',
                })}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  disabled={busy}
                  onClick={() =>
                    void runRow(async () => {
                      await onReject(String(evidence!.evidence_id), rejectReason.trim() || null)
                      setRejectOpen(false)
                      setRejectReason('')
                    })
                  }
                >
                  {t('app.candidate_card.requirements_checklist.confirm_reject', {
                    defaultValue: 'Confirm reject',
                  })}
                </button>
                <button type="button" className="btn-ghost btn-sm" onClick={() => setRejectOpen(false)}>
                  {t('common.actions.cancel', { defaultValue: 'Cancel' })}
                </button>
              </div>
            </div>
          ) : null}

          {evidence?.rejection_reason ? (
            <div className="text-sm text-rose-800">
              {t('app.candidate_card.requirements_checklist.rejection_reason', {
                defaultValue: 'Rejection reason: {reason}',
                values: { reason: evidence.rejection_reason },
              })}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

export function useRequirementLabelForType() {
  const { t } = useI18n()
  return useCallback(
    (code: string) => {
      const norm = normDocType(code)
      const fromTypeCodes = t(`admin.documents.type_codes.${norm}`, { defaultValue: '' }).trim()
      if (fromTypeCodes) return fromTypeCodes
      return norm.replace(/_/g, ' ')
    },
    [t],
  )
}
