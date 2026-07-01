import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n'

export const LOST_REASON_CODES = [
  'no_response',
  'not_qualified',
  'duplicate',
  'budget',
  'competitor',
  'no_fit',
  'other',
] as const

type Props = {
  open: boolean
  loading?: boolean
  /** i18n key for body hint under the title (default: modal_hint). */
  hintKey?: string
  onCancel: () => void
  onConfirm: (payload: { lost_reason_code: string; lost_reason_note: string }) => void
}

export default function LostReasonForLostStageModal({
  open,
  loading,
  hintKey = 'app.leads.lost_reason.modal_hint',
  onCancel,
  onConfirm,
}: Props) {
  const { t } = useI18n()
  const [code, setCode] = useState('')
  const [note, setNote] = useState('')

  useEffect(() => {
    if (open) {
      setCode('')
      setNote('')
    }
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="lost-reason-title"
        className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-4 shadow-xl"
      >
        <h2 id="lost-reason-title" className="text-sm font-semibold text-slate-900">
          {t('app.leads.lost_reason.modal_title')}
        </h2>
        <p className="mt-1 text-xs text-slate-600">{t(hintKey)}</p>
        <label className="mt-3 block text-xs font-medium text-slate-700">
          {t('app.leads.lost_reason.code_label')}
          <select
            className="input mt-1 h-9 w-full rounded-lg border-slate-300 text-sm"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          >
            <option value="">{t('app.leads.lost_reason.code_placeholder')}</option>
            {LOST_REASON_CODES.map((c) => (
              <option key={c} value={c}>
                {t(`app.leads.lost_reason.codes.${c}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="mt-2 block text-xs font-medium text-slate-700">
          {t('app.leads.lost_reason.note_label')}
          <textarea
            className="input mt-1 min-h-[4rem] w-full rounded-lg border-slate-300 px-2 py-1.5 text-sm"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={500}
            placeholder={t('app.leads.lost_reason.note_placeholder')}
          />
        </label>
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="btn-secondary h-9 rounded-lg px-3 text-xs" disabled={loading} onClick={onCancel}>
            {t('common.actions.cancel')}
          </button>
          <button
            type="button"
            className="btn-primary h-9 rounded-lg px-3 text-xs"
            disabled={loading || !code.trim()}
            onClick={() => onConfirm({ lost_reason_code: code.trim(), lost_reason_note: note.trim() })}
          >
            {loading ? t('common.loading') : t('app.leads.lost_reason.confirm')}
          </button>
        </div>
      </div>
    </div>
  )
}
