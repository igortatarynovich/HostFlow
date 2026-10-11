import { memo, useMemo, useState } from 'react'
import { IconNotebook } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { Button } from '../ui/Button'

type CandidateNote = {
  id: string
  text: string
  visibility: 'internal' | 'client' | 'candidate'
  author_id: string
  author_name?: string | null
  created_at: string
}

export default memo(function CandidateNotesRailSection({
  notes,
  notesLoading,
  newNote,
  noteSending,
  onNewNoteChange,
  onAddNote,
  onRefreshNotes,
  readOnly = false,
  variant = 'panel',
}: {
  notes: CandidateNote[]
  notesLoading: boolean
  newNote: string
  noteSending: boolean
  onNewNoteChange: (value: string) => void
  onAddNote: () => void
  onRefreshNotes: () => void
  readOnly?: boolean
  variant?: 'panel' | 'preview'
}) {
  const { t } = useI18n()
  const [composing, setComposing] = useState(false)

  const ordered = useMemo(() => {
    const arr = Array.isArray(notes) ? [...notes] : []
    arr.sort((a, b) => Date.parse(String(b.created_at || 0)) - Date.parse(String(a.created_at || 0)))
    return arr
  }, [notes])

  const latest = ordered[0]

  if (variant === 'preview') {
    return (
      <div>
        {notesLoading && !latest ? (
          <p className="text-xs text-slate-500">{t('common.loading')}</p>
        ) : latest ? (
          <>
            <p className="line-clamp-3 whitespace-pre-wrap text-sm text-slate-800">{latest.text}</p>
            <p className="mt-1 text-[11px] text-slate-500">
              {[latest.author_name, latest.created_at ? new Date(latest.created_at).toLocaleString() : null].filter(Boolean).join(' · ')}
            </p>
          </>
        ) : (
          <p className="text-xs text-slate-500">{t('app.candidate_card.notes.empty')}</p>
        )}
        {readOnly ? null : composing ? (
          <div className="mt-2 space-y-1.5">
            <textarea
              className="input min-h-[64px] w-full"
              placeholder={t('app.candidate_card.notes.placeholder')}
              value={newNote}
              onChange={(e) => onNewNoteChange(e.target.value)}
            />
            <div className="flex gap-1.5">
              <Button
                type="button"
                variant="primary"
                size="compact"
                onClick={() => {
                  onAddNote()
                  setComposing(false)
                }}
                disabled={noteSending || !newNote.trim()}
              >
                {noteSending ? t('app.candidate_card.actions.saving_note') : t('common.actions.add')}
              </Button>
              <Button type="button" variant="secondary" size="compact" onClick={() => setComposing(false)}>
                {t('common.actions.cancel')}
              </Button>
            </div>
          </div>
        ) : (
          <Button type="button" variant="secondary" size="compact" className="mt-2" onClick={() => setComposing(true)}>
            {t('common.actions.add')}
          </Button>
        )}
      </div>
    )
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <IconNotebook size={16} className="text-slate-600" />
          <div>
            <div className="text-xs font-semibold text-slate-800">{t('app.candidate_card.sections.notes.title')}</div>
            <div className="text-[11px] text-slate-500">{t('app.candidate_card.sections.notes.description')}</div>
          </div>
        </div>
        <button
          type="button"
          className="btn-secondary btn-xs"
          onClick={onRefreshNotes}
          disabled={notesLoading}
        >
          {notesLoading ? t('app.candidate_card.actions.refreshing') : t('app.candidate_card.actions.refresh')}
        </button>
      </div>

      {readOnly ? null : (
      <div className="mt-3 space-y-2">
        <textarea
          className="input min-h-[64px] w-full"
          placeholder={t('app.candidate_card.notes.placeholder')}
          value={newNote}
          onChange={(e) => onNewNoteChange(e.target.value)}
        />
        <button
          type="button"
          className="btn-primary w-full"
          onClick={onAddNote}
          disabled={noteSending || !newNote.trim()}
        >
          {noteSending ? t('app.candidate_card.actions.saving_note') : t('common.actions.add')}
        </button>
      </div>
      )}

      <div className="mt-3 max-h-[240px] overflow-y-auto divide-y rounded-lg border border-slate-200 bg-white">
        {ordered.length === 0 ? (
          <div className="p-3 text-xs text-slate-500">{t('app.candidate_card.notes.empty')}</div>
        ) : (
          ordered.slice(0, 20).map((n) => (
            <div key={n.id} className="p-3">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                <span>{new Date(n.created_at).toLocaleString()}</span>
                {n.author_name ? <span className="font-medium text-slate-600">{n.author_name}</span> : null}
                <span className="rounded bg-slate-100 px-2 py-0.5">
                  {t(`app.candidate_card.notes.visibility.${n.visibility}`, { defaultValue: n.visibility })}
                </span>
              </div>
              <div className="whitespace-pre-wrap break-words overflow-wrap-anywhere text-sm text-slate-700">
                {n.text}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
})

