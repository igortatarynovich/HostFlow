import { useState } from 'react'

import { addRecruitmentApplicationComment } from '../../api/applications'
import type { Application } from '../../api/types/application'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'
import { applicationComments } from './applicationRail'

type Props = {
  application: Application
  disabled?: boolean
  onUpdated: (application: Application) => void
}

function formatAt(iso: string | null | undefined, locale: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function ApplicationCommentsSection({ application, disabled, onUpdated }: Props) {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const history = applicationComments(application)
  const canSave = Boolean(note.trim()) && !saving && !disabled

  const handleSave = async () => {
    const text = note.trim()
    if (!text || saving || disabled) return
    setSaving(true)
    try {
      const updated = await addRecruitmentApplicationComment(application.id, { note: text })
      setNote('')
      onUpdated(updated)
      notify({
        title: t('app.recruitment_inquiry.comments.saved', { defaultValue: 'Comment saved' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.recruitment_inquiry.comments.save_failed', { defaultValue: 'Could not save comment.' })
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-3" data-testid="recruitment-comments">
      <p className="text-xs text-slate-500">
        {t('app.recruitment_inquiry.comments.subtitle', {
          defaultValue: 'Internal notes on this application — visible to the team.',
        })}
      </p>
      <textarea
        className="textarea mt-0 w-full"
        rows={3}
        maxLength={2000}
        disabled={saving || disabled}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder={t('app.recruitment_inquiry.comments.placeholder', {
          defaultValue: 'Callback tomorrow, asked about rate, considering…',
        })}
        data-testid="recruitment-comment-input"
      />
      <div className="flex justify-end">
        <button
          type="button"
          className="btn-primary rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-60"
          disabled={!canSave}
          onClick={() => void handleSave()}
          data-testid="recruitment-comment-save"
        >
          {saving
            ? t('common.saving', { defaultValue: 'Saving…' })
            : t('app.recruitment_inquiry.comments.save', { defaultValue: 'Save comment' })}
        </button>
      </div>
      {history.length > 0 ? (
        <ul className="space-y-2 border-t border-slate-100 pt-3">
          {history.map((entry, idx) => (
            <li
              key={`${entry.at || 'x'}-${idx}`}
              className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-sm"
            >
              {entry.at ? (
                <p className="text-xs text-slate-500">{formatAt(entry.at, locale)}</p>
              ) : null}
              <p className="mt-1 whitespace-pre-wrap text-slate-800">{entry.note}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-slate-400">
          {t('app.recruitment_inquiry.comments.empty', { defaultValue: 'No comments yet.' })}
        </p>
      )}
    </section>
  )
}
