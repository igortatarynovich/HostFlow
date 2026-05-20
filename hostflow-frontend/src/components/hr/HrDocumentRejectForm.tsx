import { useState } from 'react'
import { useI18n } from '../../i18n'

type Props = {
  busy: boolean
  onCancel: () => void
  onSubmit: (reason: string) => void
}

export default function HrDocumentRejectForm({ busy, onCancel, onSubmit }: Props) {
  const { t } = useI18n()
  const [reason, setReason] = useState('')

  return (
    <div className="mb-3 rounded-lg border border-rose-300 bg-rose-50 p-4">
      <p className="text-sm font-semibold text-rose-950">
        {t('app.hr.decisions.reject_title', { defaultValue: 'Reject candidate' })}
      </p>
      <p className="mt-1 text-xs text-rose-900/90">
        {t('app.hr.decisions.reject_subtitle', {
          defaultValue: 'The candidate cannot be hired. This ends HR review for this case.',
        })}
      </p>
      <label className="mt-3 block text-xs font-medium text-slate-700">
        {t('app.hr.decisions.reject_prompt', { defaultValue: 'Reason for rejection' })}
      </label>
      <textarea
        className="mt-1 w-full rounded-lg border border-rose-200 bg-white px-3 py-2 text-sm"
        rows={3}
        value={reason}
        disabled={busy}
        placeholder={t('app.hr.decisions.reject_placeholder', {
          defaultValue: 'Why is this candidate not suitable for employment?',
        })}
        onChange={(e) => setReason(e.target.value)}
      />
      <div className="mt-3 flex flex-wrap justify-end gap-2">
        <button type="button" className="btn-secondary btn-sm" disabled={busy} onClick={onCancel}>
          {t('common.cancel', { defaultValue: 'Cancel' })}
        </button>
        <button
          type="button"
          className="rounded-lg border border-rose-600 bg-rose-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50"
          disabled={busy || !reason.trim()}
          onClick={() => onSubmit(reason.trim())}
        >
          {t('app.hr.decisions.reject_submit', { defaultValue: 'Reject candidate' })}
        </button>
      </div>
    </div>
  )
}
