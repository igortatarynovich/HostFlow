import { useState } from 'react'

import { INTAKE_REJECT_REASON_CODES } from '../../utils/intakeResolution'
import { useI18n } from '../../i18n'

type RejectProps = {
  open: boolean
  busy: boolean
  onClose: () => void
  onConfirm: (reasonCode: string, note: string) => void | Promise<void>
}

export function LeadQueueQuickRejectModal({ open, busy, onClose, onConfirm }: RejectProps) {
  const { t } = useI18n()
  const [reason, setReason] = useState('')
  const [note, setNote] = useState('')

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
      data-leads-queue-modal
      role="presentation"
      onClick={() => !busy && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl ring-1 ring-slate-900/[0.08]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-slate-900">{t('app.leads.detail.intake_resolution.intake_actions.reject_title')}</h2>
        <label className="mt-4 block text-xs text-slate-700">
          <span className="mb-1 block font-medium">{t('app.leads.detail.intake_resolution.intake_actions.reject_reason')}</span>
          <select className="input h-10 w-full rounded-lg border-slate-300 bg-white text-sm" value={reason} disabled={busy} onChange={(e) => setReason(e.target.value)}>
            <option value="">{t('app.leads.detail.intake_resolution.intake_actions.reject_reason_placeholder')}</option>
            {INTAKE_REJECT_REASON_CODES.map((code) => (
              <option key={code} value={code}>
                {t(`app.leads.detail.intake_resolution.reject_reasons.${code}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="mt-3 block text-xs text-slate-700">
          <span className="mb-1 block font-medium">{t('app.leads.detail.intake_resolution.intake_actions.note_optional')}</span>
          <textarea
            className="input min-h-[3rem] w-full rounded-lg border-slate-300 bg-white px-2 py-1.5 text-sm"
            value={note}
            disabled={busy}
            placeholder={t('app.leads.detail.intake_resolution.intake_actions.note_placeholder')}
            onChange={(e) => setNote(e.target.value)}
          />
        </label>
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={busy} onClick={onClose}>
            {t('common.actions.cancel')}
          </button>
          <button
            type="button"
            className="rounded-lg bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
            disabled={busy || !reason.trim()}
            onClick={() => void onConfirm(reason.trim(), note.trim())}
          >
            {busy ? t('common.loading') : t('app.leads.detail.intake_resolution.intake_actions.reject_submit')}
          </button>
        </div>
      </div>
    </div>
  )
}

type InfoProps = {
  open: boolean
  busy: boolean
  onClose: () => void
  onConfirm: (note: string) => void | Promise<void>
}

export function LeadQueueQuickRequestInfoModal({ open, busy, onClose, onConfirm }: InfoProps) {
  const { t } = useI18n()
  const [note, setNote] = useState('')

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
      data-leads-queue-modal
      role="presentation"
      onClick={() => !busy && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl ring-1 ring-slate-900/[0.08]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-slate-900">{t('app.leads.detail.intake_resolution.intake_actions.request_info')}</h2>
        <p className="mt-1 text-xs text-slate-600">{t('app.leads.queue_keyboard.request_info_hint')}</p>
        <label className="mt-4 block text-xs text-slate-700">
          <span className="mb-1 block font-medium">{t('app.leads.detail.intake_resolution.intake_actions.request_info_label')}</span>
          <textarea
            className="input min-h-[5rem] w-full rounded-lg border-slate-300 bg-white px-2 py-1.5 text-sm"
            value={note}
            disabled={busy}
            placeholder={t('app.leads.detail.intake_resolution.intake_actions.note_placeholder')}
            onChange={(e) => setNote(e.target.value)}
          />
        </label>
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="btn-secondary rounded-lg px-3 py-2 text-sm" disabled={busy} onClick={onClose}>
            {t('common.actions.cancel')}
          </button>
          <button
            type="button"
            className="btn-primary rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50"
            disabled={busy}
            onClick={() => void onConfirm(note.trim())}
          >
            {busy ? t('common.loading') : t('app.leads.detail.intake_resolution.intake_actions.request_info')}
          </button>
        </div>
      </div>
    </div>
  )
}
