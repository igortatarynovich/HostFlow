import { useEffect, useMemo, useRef, useState } from 'react'
import clsx from 'clsx'
import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import { getWorkforceHrReview, postHrDocumentOpened, postHrDocumentVerify } from '../../api/workforce'
import {
  createCandidateDocument,
  deleteDocument as deleteDocApi,
  mockUpload,
  presignUpload,
} from '../../api/documents'
import DocumentStatus from '../surfaces/DocumentStatus'
import { mapHrVerificationDocumentRow } from '../surfaces/mapHrVerificationDocument'
import {
  buildConfirmedReviewedPayload,
  buildInitialFieldEdits,
  canConfirmHrVerificationDocument,
  countMissingFieldsOnDocument,
  isDocumentVerified,
  type DocumentFieldEdit,
} from './hrDocumentVerificationFields'
import { formatRecruiterValueForField } from './hrVerificationFieldMeta'
import HrVerificationFieldInput from './HrVerificationFieldInput'
import {
  dossierBlockKind,
  dossierDefaultUploadDocType,
  dossierFileRequiredForConfirm,
  dossierShowFileActions,
} from './dossierBlockKind'
import { openHrDocumentInNewTab } from '../../utils/hrDocumentOpen'
import { MAX_FILE_MB } from '../../modules/documents/constants'
import { isTooLarge } from '../../modules/documents/documentUtils'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import { hrDossierBlockAnchorId } from './HrDossierChecklist'

type Props = {
  doc: HrReviewDocumentRow
  employeeId: string
  candidateId?: string | null
  manage: boolean
  previewActive: boolean
  onPreview: () => void
  onPanelUpdated?: (panel: HrReviewPanel) => void
}

export function EmployeeDossierDocumentBlock({
  doc,
  employeeId,
  candidateId,
  manage,
  previewActive,
  onPreview,
  onPanelUpdated,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [fieldEdits, setFieldEdits] = useState<Record<string, DocumentFieldEdit>>(() => buildInitialFieldEdits(doc))

  useEffect(() => {
    setFieldEdits(buildInitialFieldEdits(doc))
  }, [doc.document_key, doc.document_id, doc.verification_status])

  const mapped = mapHrVerificationDocumentRow(doc, t)
  const verified = isDocumentVerified(doc)
  const blockKind = dossierBlockKind(doc)
  const showFileActions = dossierShowFileActions(doc)
  const fileRequired = dossierFileRequiredForConfirm(doc)
  const hasFile = Boolean(doc.document_id || doc.open_url || doc.file_url)
  const fields = doc.fields_to_review ?? []
  const missingFieldCount = countMissingFieldsOnDocument(doc)
  const docNeedsCorrection =
    String(doc.verification_status || doc.status || '').toLowerCase() === 'needs_correction'
  const canConfirm = canConfirmHrVerificationDocument(doc, manage, fieldEdits)
  const allFieldsHaveValues =
    fields.length === 0 || fields.every((f) => (fieldEdits[f.field_code]?.value ?? '').trim().length > 0)
  const canUpload = manage && Boolean(candidateId?.trim()) && showFileActions
  const canDelete = manage && Boolean(doc.document_id?.trim()) && !verified && showFileActions

  const scope = useMemo(
    () => ({ employeeId, documentKey: doc.document_key }),
    [employeeId, doc.document_key],
  )

  const refreshPanel = async () => {
    const next = await getWorkforceHrReview(employeeId)
    onPanelUpdated?.(next)
  }

  const handleOpenNewTab = async () => {
    const openUrl = doc.open_url || doc.file_url
    if (!openUrl) return
    setBusy(true)
    try {
      await openHrDocumentInNewTab({ openUrl })
      if (manage && doc.document_key) {
        const next = await postHrDocumentOpened(scope)
        onPanelUpdated?.(next)
      }
    } catch (e: unknown) {
      notify({
        variant: 'error',
        title: e instanceof Error ? e.message : t('common.errors.request_failed'),
      })
    } finally {
      setBusy(false)
    }
  }

  const handleUpload = async (file: File) => {
    const cid = candidateId?.trim()
    if (!cid || !manage) return
    if (isTooLarge(file)) {
      notify({
        variant: 'error',
        title: t('admin.documents.errors.file_too_large', {
          defaultValue: 'File is too large (max {limit} MB)',
          values: { limit: MAX_FILE_MB },
        }),
      })
      return
    }

    setBusy(true)
    try {
      let docId = doc.document_id?.trim() || ''
      if (!docId) {
        const docType = dossierDefaultUploadDocType(doc)
        if (!docType) throw new Error(t('app.hr.verify_shell.upload_missing_type', { defaultValue: 'Cannot upload: document type is unknown.' }))
        const created = await createCandidateDocument({
          owner_id: cid,
          doc_type: docType,
          kind: 'document',
        })
        docId = created.id
      }

      const presignResult = await presignUpload(docId)
      const key = presignResult?.fields?.key || presignResult?.key || `documents/${docId}/original.bin`
      await mockUpload({ key, file })
      await refreshPanel()
      notify({
        variant: 'success',
        title: t('app.hr.verify_shell.upload_done', { defaultValue: 'File uploaded' }),
      })
    } catch (e: unknown) {
      notify({
        variant: 'error',
        title: e instanceof Error ? e.message : t('common.errors.request_failed'),
      })
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const handleDelete = async () => {
    const docId = doc.document_id?.trim()
    if (!docId || !canDelete) return
    const ok = window.confirm(
      t('app.hr.dossier.delete_confirm', {
        defaultValue: 'Delete this document file? You can upload a new one afterward.',
      }),
    )
    if (!ok) return
    setBusy(true)
    try {
      await deleteDocApi(docId)
      await refreshPanel()
      notify({
        variant: 'success',
        title: t('app.hr.dossier.delete_done', { defaultValue: 'Document removed' }),
      })
    } catch (e: unknown) {
      notify({
        variant: 'error',
        title: e instanceof Error ? e.message : t('common.errors.request_failed'),
      })
    } finally {
      setBusy(false)
    }
  }

  const handleConfirm = async () => {
    if (!canConfirm) return
    setBusy(true)
    try {
      const payload = buildConfirmedReviewedPayload(fieldEdits)
      const next = await postHrDocumentVerify({ ...scope, reviewed_fields: payload })
      onPanelUpdated?.(next)
      notify({
        variant: 'success',
        title: t('app.hr.dossier.document_confirmed', { defaultValue: 'Data confirmed' }),
      })
    } catch (e: unknown) {
      notify({
        variant: 'error',
        title: e instanceof Error ? e.message : t('common.errors.request_failed'),
      })
    } finally {
      setBusy(false)
    }
  }

  const disabled = busy

  return (
    <article
      id={hrDossierBlockAnchorId(doc.document_key)}
      className={clsx(
        'rounded-xl border bg-white p-5 shadow-sm',
        verified ? 'border-emerald-200' : previewActive ? 'border-brand-300 ring-2 ring-brand-100' : 'border-slate-200',
      )}
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {blockKind === 'data_only'
              ? t('app.hr.dossier.data_block', { defaultValue: 'Employee data' })
              : t('app.hr.dossier.source_block', { defaultValue: 'Data source' })}
          </p>
          <h3 className="text-lg font-semibold text-slate-900">{doc.label || doc.document_key}</h3>
          {docNeedsCorrection && doc.correction_note ? (
            <p className="mt-1 text-sm text-amber-800">{doc.correction_note}</p>
          ) : null}
        </div>
        <DocumentStatus
          label={mapped.statusLabel}
          displayStatus={mapped.displayStatus}
          severity={mapped.severity}
        />
      </header>

      {showFileActions ? (
        <div className="mt-4 flex flex-wrap gap-2 border-b border-slate-100 pb-4">
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={disabled || !hasFile}
            onClick={() => void handleOpenNewTab()}
          >
            {t('app.hr.verify_shell.open_file', { defaultValue: 'Open' })}
          </button>
          {canUpload ? (
            <>
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={disabled}
                onClick={() => inputRef.current?.click()}
              >
                {hasFile
                  ? t('app.hr.verify_shell.replace_file', { defaultValue: 'Upload' })
                  : t('app.hr.verify_shell.upload_file', { defaultValue: 'Upload' })}
              </button>
              <input
                ref={inputRef}
                type="file"
                className="hidden"
                disabled={disabled}
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) void handleUpload(file)
                }}
              />
            </>
          ) : null}
          <button
            type="button"
            className={clsx('btn-sm', previewActive ? 'btn-primary' : 'btn-secondary')}
            disabled={disabled || !hasFile}
            onClick={onPreview}
          >
            {t('app.hr.verify_shell.preview_file', { defaultValue: 'Preview' })}
          </button>
          {canDelete ? (
            <button
              type="button"
              className="btn-secondary btn-sm text-rose-700"
              disabled={disabled}
              onClick={() => void handleDelete()}
            >
              {t('app.hr.dossier.delete_file', { defaultValue: 'Delete' })}
            </button>
          ) : null}
        </div>
      ) : null}

      {missingFieldCount > 0 ? (
        <p className="mt-4 text-xs font-medium text-amber-800">
          {t('app.hr.verify_shell.missing_count', {
            defaultValue: '{count} field(s) missing — enter from the document',
            values: { count: missingFieldCount },
          })}
        </p>
      ) : null}

      {fields.length > 0 ? (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {fields.map((f) => {
            const ed = fieldEdits[f.field_code] || { value: '', comment: '', confirmed: false }
            const recruiter = formatRecruiterValueForField(f)
            const missing = !(ed.value ?? '').trim()
            return (
              <label
                key={f.field_code}
                className={clsx(
                  'rounded-lg border p-3',
                  missing && !verified ? 'border-amber-200 bg-amber-50/30' : 'border-slate-200 bg-slate-50/40',
                )}
              >
                <span className="block text-sm font-medium text-slate-900">{f.label}</span>
                {recruiter ? (
                  <span className="mt-0.5 block text-xs text-slate-500">
                    {t('app.hr.verify_shell.from_recruitment', { defaultValue: 'From recruitment' })}: {recruiter}
                  </span>
                ) : null}
                {manage && !verified ? (
                  <HrVerificationFieldInput
                    field={f}
                    value={ed.value}
                    disabled={disabled}
                    onChange={(next) =>
                      setFieldEdits((prev) => ({
                        ...prev,
                        [f.field_code]: { ...ed, value: next },
                      }))
                    }
                  />
                ) : (
                  <span className="mt-2 block text-sm text-slate-800">{ed.value || '—'}</span>
                )}
              </label>
            )
          })}
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-600">
          {t('app.hr.verify_shell.no_fields', {
            defaultValue: 'No extra fields — confirm the file is correct.',
          })}
        </p>
      )}

      {manage && !verified ? (
        <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4">
          <button
            type="button"
            className="btn-primary"
            disabled={disabled || !canConfirm || !allFieldsHaveValues}
            onClick={() => void handleConfirm()}
          >
            {t('app.hr.dossier.confirm_data', { defaultValue: 'Confirm data' })}
          </button>
          {fileRequired && !doc.document_id ? (
            <p className="text-sm text-amber-800">
              {t('app.hr.dossier.upload_before_confirm', { defaultValue: 'Upload a file before confirming.' })}
            </p>
          ) : null}
        </div>
      ) : verified ? (
        <p className="mt-4 text-sm font-medium text-emerald-800">
          {t('app.hr.dossier.block_confirmed', { defaultValue: 'Data confirmed' })}
        </p>
      ) : null}
    </article>
  )
}
