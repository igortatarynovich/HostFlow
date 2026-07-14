import clsx from 'clsx'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { listCandidateDocuments } from '../../api/documents'
import type { Document } from '../../api/types'
import type {
  AcceptedEvidenceVariant,
  RequirementChecklistItem,
  RequirementsChecklistResponse,
} from '../../api/candidateRequirements'
import { useI18n } from '../../i18n'
import { useCandidateRequirementsChecklist } from '../../hooks/useCandidateRequirementsChecklist'
import { useToast } from '../Toast'
import {
  mapRequirementsChecklistToBlockers,
} from '../../utils/requirementsPipelineBlockers'
import {
  documentMatchesVariantTypes,
  evidenceStatusLabelKey,
  normDocType,
  requirementStatusBadgeClass,
  resolveRequirementRowStatus,
  variantDocumentTypeCodes,
} from './requirementsChecklistPresentation'

type Props = {
  candidateId: string
  refreshTrigger?: number
  canEdit?: boolean
  onOpenDocs?: (docType?: string) => void
  onUpload?: () => void
  primaryStepHighlight?: boolean
  className?: string
  onChecklistLoaded?: (checklist: RequirementsChecklistResponse | null) => void
  onChanged?: () => void
  onPipelineBlockersChange?: (blockers: import('../../utils/candidateStageDocPolicy').DocBlockersPayload, loading: boolean) => void
}

function requirementTitle(
  t: ReturnType<typeof useI18n>['t'],
  item: RequirementChecklistItem,
): string {
  const code = item.requirement_code
  const fromApi = String(item.public_name || '').trim()
  if (fromApi) return fromApi
  return t(`app.candidate_card.requirements_checklist.requirements.${code}`, {
    defaultValue: code.replace(/_/g, ' '),
  })
}

function variantLabel(
  t: ReturnType<typeof useI18n>['t'],
  variant: AcceptedEvidenceVariant,
  labelForType: (code: string) => string,
): string {
  const code = variant.evidence_variant_code
  const fromKey = t(`app.candidate_card.requirements_checklist.variants.${code}`, { defaultValue: '' }).trim()
  if (fromKey) return fromKey
  const types = variantDocumentTypeCodes(variant)
  if (types.length === 1) return labelForType(types[0])
  if (variant.all_of?.length) {
    return types.map(labelForType).join(' + ')
  }
  return types.map(labelForType).join(' / ')
}

function RequirementRow({
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
}: {
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
}) {
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
  }, [evidence?.evidence_variant_code])

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
  const showEvidenceActions = Boolean(evidence?.evidence_id) && rowStatus !== 'not_applicable'

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

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-slate-900">{requirementTitle(t, item)}</div>
          {purposeHint ? (
            <div className="mt-0.5 text-[11px] text-slate-600">{purposeHint}</div>
          ) : (
            <div className="mt-0.5 text-[11px] text-slate-600">
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
        <div className="mt-2 text-xs text-slate-500">
          {t('app.candidate_card.requirements_checklist.not_applicable_hint', {
            defaultValue: 'Not required for this candidate profile.',
          })}
        </div>
      ) : null}

      {!evidence && canLinkOrSelect ? (
        <div className="mt-3 space-y-2">
          <label className="block text-[11px] font-semibold uppercase tracking-wide text-slate-600">
            {t('app.candidate_card.requirements_checklist.evidence_picker_label', {
              defaultValue: 'Confirm with',
            })}
          </label>
          <div className="flex flex-wrap gap-2">
            <select
              className="input min-w-[12rem] flex-1 text-xs"
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
        <div className="mt-3 space-y-3">
          {activeVariant ? (
            <div className="text-xs text-slate-700">
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
              <ul className="mt-1 space-y-1">
                {evidence.documents.map((doc) => {
                  const typeCode = String(doc.document_type_code || doc.type || '')
                  const docId = String(doc.document_id || doc.id || '')
                  return (
                    <li key={docId || typeCode}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 text-left text-xs hover:bg-slate-100"
                        onClick={() => onOpenDocs?.(typeCode || undefined)}
                      >
                        <span className="font-medium text-slate-900">{labelForType(typeCode)}</span>
                        <span className="text-[11px] text-slate-600">
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
              <div className="mt-1 text-xs text-slate-600">
                {t('app.candidate_card.requirements_checklist.no_linked_documents', {
                  defaultValue: 'No documents linked yet.',
                })}
              </div>
            )}
          </div>

          {canLinkOrSelect && (rowStatus === 'selected' || rowStatus === 'pending_review' || rowStatus === 'rejected') ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-2 space-y-2">
              <div className="text-[11px] font-semibold text-slate-700">
                {t('app.candidate_card.requirements_checklist.link_document', {
                  defaultValue: 'Link document',
                })}
              </div>
              {docsLoading ? (
                <div className="text-xs text-slate-500">{t('common.loading')}</div>
              ) : linkableDocuments.length ? (
                <div className="flex flex-wrap gap-2">
                  <select
                    className="input min-w-[12rem] flex-1 text-xs"
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
                  <div className="text-xs text-slate-600">
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
                        {t('app.candidate_card.docs_panel.open_full', { defaultValue: 'Open full' })}
                      </button>
                    ) : null}
                  </div>
                </div>
              )}
            </div>
          ) : null}

          {canReview || canReplace ? (
            <div className="flex flex-wrap gap-2">
              {canReview ? (
                <>
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={busy}
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
                      className="input text-xs"
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
            <div className="rounded-lg border border-rose-200 bg-rose-50/60 p-2 space-y-2">
              <textarea
                className="input w-full text-xs"
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
            <div className="text-xs text-rose-800">
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

export default function CandidateRequirementsChecklist({
  candidateId,
  refreshTrigger = 0,
  canEdit = true,
  onOpenDocs,
  onUpload,
  primaryStepHighlight = false,
  className,
  onChecklistLoaded,
  onChanged,
  onPipelineBlockersChange,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const {
    checklist,
    loading,
    error,
    actionBusy,
    selectEvidence,
    linkDocument,
    approveEvidence,
    rejectEvidence,
    replaceEvidence,
  } = useCandidateRequirementsChecklist(candidateId, refreshTrigger)

  const [candidateDocuments, setCandidateDocuments] = useState<Document[]>([])
  const [docsLoading, setDocsLoading] = useState(false)

  useEffect(() => {
    onChecklistLoaded?.(checklist)
  }, [checklist, onChecklistLoaded])

  useEffect(() => {
    onPipelineBlockersChange?.(mapRequirementsChecklistToBlockers(checklist), loading)
  }, [checklist, loading, onPipelineBlockersChange])

  const loadDocuments = useCallback(async () => {
    const id = String(candidateId || '').trim()
    if (!id) {
      setCandidateDocuments([])
      return
    }
    setDocsLoading(true)
    try {
      const docs = await listCandidateDocuments(id, { includeLastCheck: true })
      setCandidateDocuments(docs)
    } catch {
      setCandidateDocuments([])
    } finally {
      setDocsLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    void loadDocuments()
  }, [loadDocuments, refreshTrigger])

  const labelForType = useCallback(
    (code: string) => {
      const norm = normDocType(code)
      const fromTypeCodes = t(`admin.documents.type_codes.${norm}`, { defaultValue: '' }).trim()
      if (fromTypeCodes) return fromTypeCodes
      return norm.replace(/_/g, ' ')
    },
    [t],
  )

  const applicableRequirements = useMemo(
    () => (checklist?.requirements || []).filter((item) => resolveRequirementRowStatus(item) !== 'not_applicable'),
    [checklist],
  )
  const fulfilledCount = useMemo(
    () => (checklist?.requirements || []).filter((item) => item.fulfilled).length,
    [checklist],
  )
  const totalCount = checklist?.requirements?.length ?? 0
  const pendingCount = useMemo(
    () =>
      (checklist?.requirements || []).filter((item) => {
        const status = resolveRequirementRowStatus(item)
        return status !== 'approved' && status !== 'not_applicable'
      }).length,
    [checklist],
  )

  const wrapAction = useCallback(
    async (fn: () => Promise<unknown>, successKey: string, defaultSuccess: string) => {
      const result = await fn()
      if (result !== null && result !== undefined) {
        notify({
          variant: 'success',
          title: t(successKey, { defaultValue: defaultSuccess }),
        })
        onChanged?.()
      }
      return result
    },
    [notify, onChanged, t],
  )

  const primary = Boolean(primaryStepHighlight)

  return (
    <section
      className={clsx(
        'rounded-2xl border border-slate-200 bg-white p-3 transition-shadow duration-200',
        primary && 'ring-2 ring-amber-400/95 ring-offset-2 ring-offset-white shadow-sm shadow-amber-500/10',
        className,
      )}
      data-rail-primary-step={primary ? 'true' : undefined}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-xs font-semibold text-slate-800">
              {t('app.candidate_card.requirements_checklist.title', {
                defaultValue: 'Requirements',
              })}
            </div>
            {primary ? (
              <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-950">
                {t('app.candidate_card.rail.primary_step_badge', { defaultValue: 'Next step' })}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-[11px] text-slate-600">
            {t('app.candidate_card.requirements_checklist.subtitle', {
              defaultValue: 'Confirm each requirement — choose evidence, link documents, then approve.',
            })}
          </p>
        </div>
        <span
          className={clsx(
            'rounded-full px-2.5 py-1 text-xs font-semibold',
            checklist?.all_fulfilled
              ? 'bg-emerald-100 text-emerald-900'
              : 'bg-amber-100 text-amber-900',
          )}
        >
          {loading
            ? t('common.loading')
            : checklist?.all_fulfilled
              ? t('app.candidate_card.requirements_checklist.all_confirmed', {
                  defaultValue: 'All confirmed',
                })
              : t('app.candidate_card.requirements_checklist.pending_count', {
                  defaultValue: '{count} open',
                  values: { count: pendingCount },
                })}
        </span>
      </div>

      {!loading && totalCount > 0 ? (
        <div className="mt-1 text-[11px] font-medium text-slate-700">
          {t('app.candidate_card.requirements_checklist.progress', {
            defaultValue: '{fulfilled}/{total} confirmed',
            values: { fulfilled: fulfilledCount, total: totalCount },
          })}
        </div>
      ) : null}

      <div className="mt-3 space-y-2">
        {loading ? (
          <div className="text-xs text-slate-500">{t('common.loading')}</div>
        ) : error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-2 py-2 text-xs text-rose-800">
            {error}
          </div>
        ) : applicableRequirements.length ? (
          applicableRequirements.map((item) => (
            <RequirementRow
              key={item.requirement_code}
              item={item}
              canEdit={canEdit}
              actionBusy={actionBusy}
              labelForType={labelForType}
              candidateDocuments={candidateDocuments}
              docsLoading={docsLoading}
              onSelectVariant={(variantCode) =>
                wrapAction(
                  () => selectEvidence(item.requirement_code, variantCode),
                  'app.candidate_card.requirements_checklist.toast_selected',
                  'Evidence selected',
                )
              }
              onLinkDocument={(evidenceId, documentId) =>
                wrapAction(
                  () => linkDocument(evidenceId, documentId),
                  'app.candidate_card.requirements_checklist.toast_linked',
                  'Document linked',
                )
              }
              onApprove={(evidenceId) =>
                wrapAction(
                  () => approveEvidence(evidenceId),
                  'app.candidate_card.requirements_checklist.toast_approved',
                  'Requirement approved',
                )
              }
              onReject={(evidenceId, reason) =>
                wrapAction(
                  () => rejectEvidence(evidenceId, reason),
                  'app.candidate_card.requirements_checklist.toast_rejected',
                  'Evidence rejected',
                )
              }
              onReplace={(variantCode) =>
                wrapAction(
                  () => replaceEvidence(item.requirement_code, variantCode),
                  'app.candidate_card.requirements_checklist.toast_replaced',
                  'Evidence replaced',
                )
              }
              onOpenDocs={onOpenDocs}
              onUpload={onUpload}
            />
          ))
        ) : (
          <div className="text-xs text-slate-500">
            {t('app.candidate_card.requirements_checklist.empty', {
              defaultValue: 'No requirements for this candidate profile.',
            })}
          </div>
        )}
      </div>
    </section>
  )
}
