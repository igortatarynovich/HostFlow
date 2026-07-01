import { useState } from 'react'
import clsx from 'clsx'
import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import { isDocumentWaivable } from './hrDocumentVerificationFields'
import { useI18n } from '../../i18n'

type Mode = 'idle' | 'waive' | 'additional'

type Props = {
  panel: HrReviewPanel
  activeDoc: HrReviewDocumentRow
  canManage: boolean
  busy: boolean
  onWaive: (reason: string) => Promise<void>
  onRequestAdditional: (payload: {
    document_name: string
    note?: string
    urgency?: string
  }) => Promise<void>
}

export default function HrVerificationExceptionsPanel({
  panel,
  activeDoc,
  canManage,
  busy,
  onWaive,
  onRequestAdditional,
}: Props) {
  const { t } = useI18n()
  const [mode, setMode] = useState<Mode>('idle')
  const [waiveReason, setWaiveReason] = useState('')
  const [docName, setDocName] = useState('')
  const [note, setNote] = useState('')
  const [urgency, setUrgency] = useState('')

  const canWaive = isDocumentWaivable(activeDoc)

  if (!canManage) return null

  const close = () => {
    setMode('idle')
    setWaiveReason('')
    setDocName('')
    setNote('')
    setUrgency('')
  }

  if (mode === 'waive') {
    return (
      <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50/80 p-4">
        <p className="text-sm font-semibold text-amber-950">
          {t('app.hr.exceptions.waive_title', { defaultValue: 'Mark requirement as exception' })}
        </p>
        <p className="mt-1 text-xs text-amber-900/90">
          {t('app.hr.exceptions.waive_warning', {
            defaultValue:
              'This requirement will be marked as an exception. Approval can proceed without this document.',
          })}
        </p>
        <p className="mt-2 text-xs text-slate-700">
          {t('app.hr.exceptions.waive_document', {
            defaultValue: 'Document: {document}',
            values: { document: activeDoc.label || activeDoc.document_key },
          })}
        </p>
        <label className="mt-3 block text-xs font-medium text-slate-700">
          {t('app.hr.exceptions.waive_reason', { defaultValue: 'Reason (required)' })}
        </label>
        <textarea
          className="mt-1 w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm"
          rows={3}
          value={waiveReason}
          disabled={busy}
          placeholder={t('app.hr.exceptions.waive_placeholder', {
            defaultValue: 'Why is this requirement waived?',
          })}
          onChange={(e) => setWaiveReason(e.target.value)}
        />
        <div className="mt-3 flex flex-wrap justify-end gap-2">
          <button type="button" className="btn-secondary btn-sm" disabled={busy} onClick={close}>
            {t('common.cancel', { defaultValue: 'Cancel' })}
          </button>
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={busy || !waiveReason.trim()}
            onClick={() => void onWaive(waiveReason.trim()).then(close)}
          >
            {t('app.hr.exceptions.waive_submit', { defaultValue: 'Mark as exception' })}
          </button>
        </div>
      </div>
    )
  }

  if (mode === 'additional') {
    return (
      <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-sm font-semibold text-slate-900">
          {t('app.hr.exceptions.additional_title', { defaultValue: 'Request additional document' })}
        </p>
        <p className="mt-1 text-xs text-slate-600">
          {t('app.hr.exceptions.additional_subtitle', {
            defaultValue:
              'Ask recruitment to provide more information. This blocks final approval until the document is received.',
          })}
        </p>
        <label className="mt-3 block text-xs font-medium text-slate-700">
          {t('app.hr.exceptions.additional_name', { defaultValue: 'Document name' })}
        </label>
        <input
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          value={docName}
          disabled={busy}
          placeholder={t('app.hr.exceptions.additional_name_placeholder', {
            defaultValue: 'e.g. Reference letter from previous employer',
          })}
          onChange={(e) => setDocName(e.target.value)}
        />
        <label className="mt-3 block text-xs font-medium text-slate-700">
          {t('app.hr.exceptions.additional_note', { defaultValue: 'Note for recruitment (optional)' })}
        </label>
        <textarea
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          rows={2}
          value={note}
          disabled={busy}
          onChange={(e) => setNote(e.target.value)}
        />
        <label className="mt-3 block text-xs font-medium text-slate-700">
          {t('app.hr.exceptions.additional_urgency', { defaultValue: 'Urgency (optional)' })}
        </label>
        <select
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          value={urgency}
          disabled={busy}
          onChange={(e) => setUrgency(e.target.value)}
        >
          <option value="">{t('app.hr.exceptions.urgency_none', { defaultValue: 'Not specified' })}</option>
          <option value="normal">{t('app.hr.exceptions.urgency_normal', { defaultValue: 'Normal' })}</option>
          <option value="high">{t('app.hr.exceptions.urgency_high', { defaultValue: 'High' })}</option>
        </select>
        <div className="mt-3 flex flex-wrap justify-end gap-2">
          <button type="button" className="btn-secondary btn-sm" disabled={busy} onClick={close}>
            {t('common.cancel', { defaultValue: 'Cancel' })}
          </button>
          <button
            type="button"
            className="btn-primary btn-sm"
            disabled={busy || !docName.trim()}
            onClick={() =>
              void onRequestAdditional({
                document_name: docName.trim(),
                note: note.trim() || undefined,
                urgency: urgency || undefined,
              }).then(close)
            }
          >
            {t('app.hr.exceptions.additional_submit', { defaultValue: 'Send request' })}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
        {t('app.hr.exceptions.section_title', { defaultValue: 'Exceptions' })}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {canWaive ? (
          <button
            type="button"
            className={clsx('text-xs font-medium text-slate-700 underline-offset-2 hover:underline')}
            disabled={busy}
            onClick={() => setMode('waive')}
          >
            {t('app.hr.exceptions.waive_link', { defaultValue: 'Mark requirement as exception…' })}
          </button>
        ) : null}
        <button
          type="button"
          className="text-xs font-medium text-slate-700 underline-offset-2 hover:underline"
          disabled={busy}
          onClick={() => setMode('additional')}
        >
          {t('app.hr.exceptions.additional_link', { defaultValue: 'Request additional document…' })}
        </button>
      </div>
      {(panel.return_reason || activeDoc.verification_note) && (
        <p className="mt-2 text-xs text-slate-500">
          {activeDoc.verification_note || panel.return_reason}
        </p>
      )}
    </div>
  )
}
