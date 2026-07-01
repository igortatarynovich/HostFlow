import clsx from 'clsx'
import { useState } from 'react'
import {
  CORRECTION_SUGGESTION_KEYS,
  correctionSuggestionLabel,
  type CorrectionSuggestionKey,
} from './hrCorrectionSuggestions'
import { useI18n } from '../../i18n'

type Props = {
  documentLabel: string
  busy: boolean
  onCancel: () => void
  onSubmit: (note: string) => void
}

export default function HrDocumentCorrectionForm({ documentLabel, busy, onCancel, onSubmit }: Props) {
  const { t } = useI18n()
  const [note, setNote] = useState('')
  const [picked, setPicked] = useState<CorrectionSuggestionKey | null>(null)

  const applySuggestion = (key: CorrectionSuggestionKey) => {
    setPicked(key)
    const label = correctionSuggestionLabel(key, t)
    setNote((prev) => {
      if (!prev.trim()) return label
      if (prev.includes(label)) return prev
      return `${prev.trim()}\n${label}`
    })
  }

  return (
    <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50/80 p-4">
      <p className="text-sm font-semibold text-amber-950">
        {t('app.hr.decisions.correction_title', { defaultValue: 'Request correction' })}
      </p>
      <p className="mt-1 text-xs text-amber-900/90">
        {t('app.hr.decisions.correction_subtitle', {
          defaultValue: 'Ask recruitment to fix and resubmit. The case returns to the recruiter.',
          values: { document: documentLabel },
        })}
      </p>
      <p className="mt-3 text-xs font-medium text-slate-600">
        {t('app.hr.decisions.correction_prompt', { defaultValue: 'What needs correction?' })}
      </p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {CORRECTION_SUGGESTION_KEYS.map((key) => (
          <button
            key={key}
            type="button"
            className={clsx(
              'rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
              picked === key
                ? 'border-amber-500 bg-amber-100 text-amber-950'
                : 'border-amber-200 bg-white text-amber-900 hover:bg-amber-50',
            )}
            disabled={busy}
            onClick={() => applySuggestion(key)}
          >
            {correctionSuggestionLabel(key, t)}
          </button>
        ))}
      </div>
      <textarea
        className="mt-3 w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm text-slate-900"
        rows={3}
        value={note}
        disabled={busy}
        placeholder={t('app.hr.decisions.correction_placeholder', {
          defaultValue: 'Describe what recruitment should fix…',
        })}
        onChange={(e) => setNote(e.target.value)}
      />
      <div className="mt-3 flex flex-wrap justify-end gap-2">
        <button type="button" className="btn-secondary btn-sm" disabled={busy} onClick={onCancel}>
          {t('common.cancel', { defaultValue: 'Cancel' })}
        </button>
        <button
          type="button"
          className="btn-primary btn-sm"
          disabled={busy || !note.trim()}
          onClick={() => onSubmit(note.trim())}
        >
          {t('app.hr.decisions.correction_submit', { defaultValue: 'Send back to recruitment' })}
        </button>
      </div>
    </div>
  )
}
