import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import {
  postHrDocumentReject,
  postHrDocumentRequestCorrection,
  postHrDocumentVerify,
} from '../../api/workforce'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import { buildConfirmedReviewedPayload, buildInitialFieldEdits } from './hrDocumentVerificationFields'

type Props = {
  employeeId: string
  candidateId?: string | null
  reviewDoc: HrReviewDocumentRow
  manage?: boolean
  onPanelUpdated?: (panel: HrReviewPanel) => void
}

export function HrEmployeeDocumentVerifyActions({
  employeeId,
  candidateId,
  reviewDoc,
  manage = false,
  onPanelUpdated,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [busy, setBusy] = useState<string | null>(null)
  const [correctionOpen, setCorrectionOpen] = useState(false)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [correctionNote, setCorrectionNote] = useState('')
  const [rejectReason, setRejectReason] = useState('')

  const documentKey = reviewDoc.document_key
  const scope = { employeeId, documentKey }
  const canAct = manage && Boolean(reviewDoc.document_id) && reviewDoc.actions?.can_verify !== false

  const runAction = async (key: string, fn: () => Promise<HrReviewPanel>) => {
    setBusy(key)
    try {
      const panel = await fn()
      onPanelUpdated?.(panel)
      notify({
        variant: 'success',
        title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }),
      })
      setCorrectionOpen(false)
      setRejectOpen(false)
      setCorrectionNote('')
      setRejectReason('')
    } catch (e: unknown) {
      notify({
        variant: 'error',
        title: e instanceof Error ? e.message : t('common.errors.request_failed'),
      })
    } finally {
      setBusy(null)
    }
  }

  if (!canAct) return null

  const confirmDocument = () => {
    const payload = buildConfirmedReviewedPayload(buildInitialFieldEdits(reviewDoc))
    void runAction('confirm', () => postHrDocumentVerify({ ...scope, reviewed_fields: payload }))
  }

  const submitCorrection = () => {
    const note = correctionNote.trim()
    if (!note) return
    void runAction('correction', () => postHrDocumentRequestCorrection({ ...scope, note }))
  }

  const submitReject = () => {
    const reason = rejectReason.trim()
    if (!reason) return
    void runAction('reject', () => postHrDocumentReject({ ...scope, reason }))
  }

  const uploadNewDefaultNote = t('app.hr.doc_verify.upload_new_note', {
    defaultValue: 'Please upload a new version of this document.',
  })

  return (
    <div className="mt-2 space-y-2">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded border border-emerald-300 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-900 hover:bg-emerald-100 disabled:opacity-50"
          disabled={!!busy}
          onClick={confirmDocument}
        >
          {t('app.hr.verify_shell.confirm', { defaultValue: 'Confirm' })}
        </button>
        <button
          type="button"
          className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100 disabled:opacity-50"
          disabled={!!busy}
          onClick={() => {
            setRejectOpen(false)
            setCorrectionOpen((v) => !v)
            if (!correctionOpen) setCorrectionNote('')
          }}
        >
          {t('app.hr.decisions.request_correction', { defaultValue: 'Request correction' })}
        </button>
        {candidateId ? (
          <Link
            to={`${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}/documents`}
            className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100"
          >
            {t('app.hr.doc_verify.upload_new', { defaultValue: 'Upload new' })}
          </Link>
        ) : (
          <button
            type="button"
            className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100 disabled:opacity-50"
            disabled={!!busy}
            onClick={() => {
              setCorrectionOpen(true)
              setRejectOpen(false)
              setCorrectionNote(uploadNewDefaultNote)
            }}
          >
            {t('app.hr.doc_verify.upload_new', { defaultValue: 'Upload new' })}
          </button>
        )}
        <button
          type="button"
          className="rounded border border-rose-300 px-2 py-1 text-xs text-rose-700 hover:bg-rose-50 disabled:opacity-50"
          disabled={!!busy}
          onClick={() => {
            setCorrectionOpen(false)
            setRejectOpen((v) => !v)
            if (!rejectOpen) setRejectReason('')
          }}
        >
          {t('app.hr.doc_verify.reject_verification', { defaultValue: 'Reject verification' })}
        </button>
      </div>

      {correctionOpen ? (
        <div className="rounded border border-amber-200 bg-amber-50/60 p-2">
          <textarea
            className="w-full rounded border border-slate-200 px-2 py-1 text-xs"
            rows={2}
            value={correctionNote}
            onChange={(e) => setCorrectionNote(e.target.value)}
            placeholder={t('app.hr.doc_verify.correction_placeholder', {
              defaultValue: 'What must be corrected?',
            })}
          />
          <button
            type="button"
            className="mt-1 rounded bg-slate-900 px-2 py-1 text-xs text-white disabled:opacity-50"
            disabled={!correctionNote.trim() || !!busy}
            onClick={submitCorrection}
          >
            {t('common.submit', { defaultValue: 'Submit' })}
          </button>
        </div>
      ) : null}

      {rejectOpen ? (
        <div className="rounded border border-rose-200 bg-rose-50/60 p-2">
          <textarea
            className="w-full rounded border border-slate-200 px-2 py-1 text-xs"
            rows={2}
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder={t('app.hr.doc_verify.reject_placeholder', { defaultValue: 'Rejection reason' })}
          />
          <button
            type="button"
            className="mt-1 rounded bg-rose-700 px-2 py-1 text-xs text-white disabled:opacity-50"
            disabled={!rejectReason.trim() || !!busy}
            onClick={submitReject}
          >
            {t('common.submit', { defaultValue: 'Submit' })}
          </button>
        </div>
      ) : null}
    </div>
  )
}
