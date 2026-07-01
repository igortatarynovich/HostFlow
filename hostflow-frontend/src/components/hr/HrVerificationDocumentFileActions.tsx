import { useRef, useState } from 'react'
import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import { createCandidateDocument, presignUpload, mockUpload } from '../../api/documents'
import { getWorkforceHrReview } from '../../api/workforce'
import { openHrDocumentInNewTab } from '../../utils/hrDocumentOpen'
import { dossierShowFileActions } from './dossierBlockKind'
import { MAX_FILE_MB } from '../../modules/documents/constants'
import { isTooLarge } from '../../modules/documents/documentUtils'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'

type Props = {
  activeDoc: HrReviewDocumentRow
  candidateId?: string | null
  employeeId?: string
  manage: boolean
  busy: boolean
  compact?: boolean
  onOpen: () => void | Promise<void>
  onPanelUpdated?: (panel: HrReviewPanel) => void
}

export default function HrVerificationDocumentFileActions({
  activeDoc,
  candidateId,
  employeeId,
  manage,
  busy,
  compact = false,
  onOpen,
  onPanelUpdated,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const openUrl = activeDoc.open_url || activeDoc.file_url
  const showFileActions = dossierShowFileActions(activeDoc)
  const canOpen = showFileActions && Boolean(openUrl) && activeDoc.actions?.can_open !== false
  const canUpload = showFileActions && manage && Boolean(candidateId?.trim())

  const handlePreview = async () => {
    if (!openUrl) return
    if (canOpen) {
      await onOpen()
      return
    }
    await openHrDocumentInNewTab({ openUrl })
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

    setUploading(true)
    try {
      let docId = activeDoc.document_id?.trim() || ''
      if (!docId) {
        const docType = (activeDoc.document_type || activeDoc.document_key || '').trim()
        if (!docType) {
          throw new Error(
            t('app.hr.verify_shell.upload_missing_type', {
              defaultValue: 'Cannot upload: document type is unknown.',
            }),
          )
        }
        const created = await createCandidateDocument({
          owner_id: cid,
          doc_type: docType,
          kind: 'document',
        })
        docId = created.id
      }

      const presign = await presignUpload(docId)
      const key = presign?.fields?.key || presign?.key || `documents/${docId}/original.bin`
      await mockUpload({ key, file })

      if (employeeId?.trim()) {
        const next = await getWorkforceHrReview(employeeId.trim())
        onPanelUpdated?.(next)
      }

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
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const disabled = busy || uploading

  if (compact) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        {canOpen ? (
          <button type="button" className="btn-primary btn-sm" disabled={disabled} onClick={() => void onOpen()}>
            {t('app.hr.verify_shell.open_file', { defaultValue: 'Open file' })}
          </button>
        ) : null}
        {canUpload ? (
          <>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={disabled}
              onClick={() => inputRef.current?.click()}
            >
              {canOpen
                ? t('app.hr.verify_shell.replace_file', { defaultValue: 'Replace file' })
                : t('app.hr.verify_shell.upload_file', { defaultValue: 'Upload file' })}
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
        {!canOpen && !canUpload ? (
          <span className="text-xs font-medium text-amber-800">
            {t('app.hr.verify_shell.no_file_readonly', { defaultValue: 'No file uploaded yet.' })}
          </span>
        ) : null}
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <p className="text-sm text-slate-600">
        {t('app.hr.verify_shell.open_hint', {
          defaultValue: 'Open the file and compare it with the data on the right.',
        })}
      </p>
      <div className="flex flex-wrap items-center justify-center gap-2">
        {canOpen ? (
          <>
            <button type="button" className="btn-primary" disabled={disabled} onClick={() => void onOpen()}>
              {t('app.hr.verify_shell.open_file', { defaultValue: 'Open file' })}
            </button>
            <button type="button" className="btn-secondary" disabled={disabled} onClick={() => void handlePreview()}>
              {t('app.hr.verify_shell.preview_file', { defaultValue: 'Preview' })}
            </button>
          </>
        ) : null}
        {canUpload ? (
          <>
            <button
              type="button"
              className={canOpen ? 'btn-secondary' : 'btn-primary'}
              disabled={disabled}
              onClick={() => inputRef.current?.click()}
            >
              {canOpen
                ? t('app.hr.verify_shell.replace_file', { defaultValue: 'Replace file' })
                : t('app.hr.verify_shell.upload_file', { defaultValue: 'Upload file' })}
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
      </div>
      {!canOpen && !canUpload ? (
        <p className="text-sm font-medium text-amber-800">
          {t('app.hr.verify_shell.no_file_readonly', {
            defaultValue: 'No file uploaded yet.',
          })}
        </p>
      ) : null}
    </div>
  )
}
