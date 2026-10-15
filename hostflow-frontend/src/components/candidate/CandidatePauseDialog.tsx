import { useState } from 'react'
import type { CandidateExtra } from '../../api/types'
import { useI18n } from '../../i18n'
import { Button } from '../ui/Button'

export function CandidatePauseDialog({
  extra,
  actorLabel,
  onClose,
  onSave,
}: {
  extra: CandidateExtra
  actorLabel: string
  onClose: () => void
  onSave: (patch: Partial<CandidateExtra>, reminder: { title: string; dueOn: string }) => void
}) {
  const { t } = useI18n()
  const current = extra.candidate_ops?.pause
  const [reason, setReason] = useState(current?.reason || '')
  const [comment, setComment] = useState(current?.comment || '')
  const [resumeOn, setResumeOn] = useState(current?.resume_on || '')

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
      <div className="text-sm font-semibold text-slate-900">
        {t('app.candidate_card.pause.title', { defaultValue: 'Pause' })}
      </div>
      <label className="mt-2 block">
        <div className="label">{t('app.candidate_card.pause.reason', { defaultValue: 'Reason' })}</div>
        <input className="input" value={reason} onChange={(event) => setReason(event.target.value)} />
      </label>
      <label className="mt-2 block">
        <div className="label">{t('app.candidate_card.pause.comment', { defaultValue: 'Comment' })}</div>
        <input className="input" value={comment} onChange={(event) => setComment(event.target.value)} />
      </label>
      <label className="mt-2 block">
        <div className="label">{t('app.candidate_card.pause.resume_on', { defaultValue: 'Resume on' })}</div>
        <input className="input" type="date" value={resumeOn} onChange={(event) => setResumeOn(event.target.value)} />
      </label>
      <div className="mt-3 flex gap-2">
        <Button
          type="button"
          variant="primary"
          size="compact"
          disabled={!reason.trim() || !resumeOn}
          onClick={() => {
            onSave(
              {
                candidate_ops: {
                  ...(extra.candidate_ops || {}),
                  pause: {
                    reason: reason.trim(),
                    comment: comment.trim(),
                    paused_at: new Date().toISOString(),
                    resume_on: resumeOn,
                    paused_by: actorLabel,
                  },
                },
              },
              {
                title: t('app.candidate_card.pause.reminder', { defaultValue: 'Return to candidate' }),
                dueOn: resumeOn,
              },
            )
            onClose()
          }}
        >
          {t('common.actions.save')}
        </Button>
        <Button type="button" variant="secondary" size="compact" onClick={onClose}>
          {t('common.actions.cancel')}
        </Button>
      </div>
    </div>
  )
}
