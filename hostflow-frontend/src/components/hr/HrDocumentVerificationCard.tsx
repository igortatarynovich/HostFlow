import { useMemo, useState } from 'react'
import clsx from 'clsx'
import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import {
  postHrDocumentOpened,
  postHrDocumentReject,
  postHrDocumentRequestCorrection,
  postHrDocumentReviewed,
  postHrDocumentVerify,
} from '../../api/workforce'
import HrDocumentOpenButton from './HrDocumentOpenButton'
import { openHrDocumentInNewTab } from '../../utils/hrDocumentOpen'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'

type Props = {
  doc: HrReviewDocumentRow
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
    case 'missing':
      return 'border-slate-200 bg-slate-100 text-slate-600'
    default:
      return 'border-slate-200 bg-slate-50 text-slate-700'
  }
}

export default function HrDocumentVerificationCard({
  doc,
  employeeId,
  handoffId,
  manage = false,
  onPanelUpdated,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [busy, setBusy] = useState<string | null>(null)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [correctionOpen, setCorrectionOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [correctionNote, setCorrectionNote] = useState('')

  const verificationStatus = doc.verification_status || doc.status
  const fields = doc.fields_to_review || []
  const reviewed = doc.reviewed_fields || {}

  const [fieldEdits, setFieldEdits] = useState<Record<string, { value: string; comment: string; confirmed: boolean }>>(
    () => {
      const init: Record<string, { value: string; comment: string; confirmed: boolean }> = {}
      for (const f of fields) {
        const prev = reviewed[f.field_code]
        const p = prev && typeof prev === 'object' ? (prev as Record<string, unknown>) : {}
        init[f.field_code] = {
          value: String(p.value ?? f.reviewed_value ?? ''),
          comment: String(p.comment ?? f.review_comment ?? ''),
          confirmed: Boolean(p.confirmed ?? f.confirmed),
        }
      }
      return init
    },
  )

  const reviewedPayload = useMemo(() => {
    const out: Record<string, unknown> = {}
    for (const [code, ed] of Object.entries(fieldEdits)) {
      out[code] = { value: ed.value, comment: ed.comment, confirmed: ed.confirmed }
    }
    return out
  }, [fieldEdits])

  const runAction = async (key: string, fn: () => Promise<HrReviewPanel>) => {
    setBusy(key)
    try {
      const panel = await fn()
      onPanelUpdated?.(panel)
      notify({ variant: 'success', title: t('app.hr.employee_detail.saved', { defaultValue: 'Saved' }) })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : t('common.errors.request_failed')
      notify({ variant: 'error', title: msg })
    } finally {
      setBusy(null)
      setRejectOpen(false)
      setCorrectionOpen(false)
    }
  }

  const docKey = doc.document_key
  const scope = { employeeId, handoffId, documentKey: docKey }

  const handleOpen = async () => {
    const openUrl = doc.open_url || doc.file_url
    if (!openUrl) return
    if (!manage) {
      await openHrDocumentInNewTab({ openUrl })
      return
    }
    setBusy('open')
    try {
      await openHrDocumentInNewTab({ openUrl })
      const panel = await postHrDocumentOpened(scope)
      onPanelUpdated?.(panel)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : t('common.errors.request_failed')
      notify({ variant: 'error', title: msg })
    } finally {
      setBusy(null)
    }
  }

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{doc.label}</h3>
          {doc.linked_checklist_item ? (
            <p className="mt-0.5 text-xs text-slate-500">
              {t('app.hr.doc_verify.checklist_item', { defaultValue: 'Checklist' })}:{' '}
              {doc.linked_checklist_item.replace(/_/g, ' ')}
            </p>
          ) : null}
        </div>
        <span
          className={clsx(
            'inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
            statusBadgeClass(String(verificationStatus)),
          )}
        >
          {String(verificationStatus).replace(/_/g, ' ')}
        </span>
      </div>

      {doc.rejection_reason ? (
        <p className="mt-2 text-xs text-rose-800">{doc.rejection_reason}</p>
      ) : null}
      {doc.correction_note ? (
        <p className="mt-2 text-xs text-amber-800">{doc.correction_note}</p>
      ) : null}

      {fields.length > 0 ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="py-1 pr-2">{t('app.hr.doc_verify.col_field', { defaultValue: 'Field' })}</th>
                <th className="py-1 pr-2">{t('app.hr.doc_verify.col_profile', { defaultValue: 'Profile / snapshot' })}</th>
                <th className="py-1 pr-2">{t('app.hr.doc_verify.col_downstream', { defaultValue: 'Used for' })}</th>
                <th className="py-1 pr-2">{t('app.hr.doc_verify.col_confirm', { defaultValue: 'HR confirmation' })}</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((f) => {
                const ed = fieldEdits[f.field_code] || { value: '', comment: '', confirmed: false }
                const profileVals = Object.entries(f.current_profile_values || {})
                return (
                  <tr key={f.field_code} className="border-b border-slate-50 align-top">
                    <td className="py-2 pr-2 font-medium text-slate-800">{f.label}</td>
                    <td className="py-2 pr-2 text-slate-600">
                      {profileVals.length > 0 ? (
                        <ul className="space-y-0.5">
                          {profileVals.map(([k, v]) => (
                            <li key={k}>
                              <span className="text-slate-400">{k.split('.').pop()}: </span>
                              {String(v)}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="italic text-amber-700">
                          {t('app.hr.doc_verify.needs_manual', { defaultValue: 'Needs manual confirmation' })}
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-2 text-slate-500">{(f.downstream_use || []).join(', ')}</td>
                    <td className="py-2 pr-2">
                      {manage ? (
                        <div className="space-y-1 min-w-[12rem]">
                          <input
                            className="w-full border border-slate-200 rounded px-2 py-1 text-xs"
                            placeholder={t('app.hr.doc_verify.confirmed_value', { defaultValue: 'Confirmed value' })}
                            value={ed.value}
                            onChange={(e) =>
                              setFieldEdits((prev) => ({
                                ...prev,
                                [f.field_code]: { ...ed, value: e.target.value },
                              }))
                            }
                          />
                          <input
                            className="w-full border border-slate-200 rounded px-2 py-1 text-xs"
                            placeholder={t('app.hr.doc_verify.comment', { defaultValue: 'Comment' })}
                            value={ed.comment}
                            onChange={(e) =>
                              setFieldEdits((prev) => ({
                                ...prev,
                                [f.field_code]: { ...ed, comment: e.target.value },
                              }))
                            }
                          />
                          <label className="flex items-center gap-1.5 text-xs">
                            <input
                              type="checkbox"
                              checked={ed.confirmed}
                              onChange={(e) =>
                                setFieldEdits((prev) => ({
                                  ...prev,
                                  [f.field_code]: { ...ed, confirmed: e.target.checked },
                                }))
                              }
                            />
                            {t('app.hr.doc_verify.confirmed', { defaultValue: 'Confirmed' })}
                          </label>
                        </div>
                      ) : (
                        <span>{ed.confirmed ? '✓' : '—'}</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        {doc.actions?.can_open !== false && (doc.open_url || doc.file_url) ? (
          <button type="button" className="btn-secondary btn-sm" disabled={!!busy} onClick={() => void handleOpen()}>
            {t('app.hr.review.open_docs', { defaultValue: 'Open document' })}
          </button>
        ) : doc.open_url || doc.file_url ? (
          <HrDocumentOpenButton openUrl={doc.open_url ?? doc.file_url} />
        ) : null}
        {manage && doc.actions?.can_verify && doc.document_id ? (
          <>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={!!busy}
              onClick={() =>
                void runAction('reviewed', () => postHrDocumentReviewed({ ...scope, reviewed_fields: reviewedPayload }))
              }
            >
              {t('app.hr.doc_verify.save_review', { defaultValue: 'Save field review' })}
            </button>
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={!!busy}
              onClick={() =>
                void runAction('verify', () => postHrDocumentVerify({ ...scope, reviewed_fields: reviewedPayload }))
              }
            >
              {t('app.hr.doc_verify.verify', { defaultValue: 'Verify document' })}
            </button>
            <button type="button" className="btn-secondary btn-sm" disabled={!!busy} onClick={() => setCorrectionOpen((v) => !v)}>
              {t('app.hr.doc_verify.request_correction', { defaultValue: 'Request correction' })}
            </button>
            <button type="button" className="btn-secondary btn-sm" disabled={!!busy} onClick={() => setRejectOpen((v) => !v)}>
              {t('app.hr.doc_verify.reject', { defaultValue: 'Reject' })}
            </button>
          </>
        ) : null}
      </div>

      {correctionOpen && manage ? (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50/50 p-3">
          <textarea
            className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
            rows={2}
            value={correctionNote}
            onChange={(e) => setCorrectionNote(e.target.value)}
            placeholder={t('app.hr.doc_verify.correction_placeholder', { defaultValue: 'What must be corrected?' })}
          />
          <button
            type="button"
            className="btn-primary btn-sm mt-2"
            disabled={!correctionNote.trim() || !!busy}
            onClick={() =>
              void runAction('correction', () =>
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
            className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
            rows={2}
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder={t('app.hr.doc_verify.reject_placeholder', { defaultValue: 'Rejection reason' })}
          />
          <button
            type="button"
            className="btn-primary btn-sm mt-2"
            disabled={!rejectReason.trim() || !!busy}
            onClick={() => void runAction('reject', () => postHrDocumentReject({ ...scope, reason: rejectReason.trim() }))}
          >
            {t('common.submit', { defaultValue: 'Submit' })}
          </button>
        </div>
      ) : null}
    </article>
  )
}
