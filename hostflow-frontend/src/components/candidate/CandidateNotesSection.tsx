import { memo } from 'react'
import type { RefObject } from 'react'
import { IconNotebook } from '@tabler/icons-react'
import { useI18n } from '../../i18n'

type CandidateNote = {
  id: string
  text: string
  visibility: 'internal' | 'client' | 'candidate'
  author_id: string
  author_name?: string | null
  created_at: string
}

interface CandidateNotesSectionProps {
  notesRef: RefObject<HTMLDivElement>
  notes: CandidateNote[]
  notesLoading: boolean
  newNote: string
  noteSending: boolean
  onNewNoteChange: (value: string) => void
  onAddNote: () => void
  onRefreshNotes: () => void
}

function CandidateNotesSection({
  notesRef,
  notes,
  notesLoading,
  newNote,
  noteSending,
  onNewNoteChange,
  onAddNote,
  onRefreshNotes,
}: CandidateNotesSectionProps) {
  const { t } = useI18n()

  return (
    <aside
      ref={notesRef}
      id="section-notes"
      className="card sticky top-20 w-full space-y-3 p-4"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <IconNotebook size={20} className="text-slate-600" />
          <div>
            <h3 className="text-sm font-medium text-slate-700">{t('app.candidate_card.sections.notes.title')}</h3>
            <p className="text-xs text-slate-500">{t('app.candidate_card.sections.notes.description')}</p>
          </div>
        </div>
        <button
          type="button"
          className="btn-ghost text-xs"
          onClick={onRefreshNotes}
          disabled={notesLoading}
        >
          {notesLoading ? t('app.candidate_card.actions.refreshing') : t('app.candidate_card.actions.refresh')}
        </button>
      </div>
      <div className="space-y-2">
        <textarea
          className="input min-h-[72px] w-full"
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
      <div className="max-h-[400px] overflow-y-auto divide-y rounded-lg border border-brand-100 bg-white/90">
        {notes.length === 0 && <div className="p-3 text-slate-500">{t('app.candidate_card.notes.empty')}</div>}
        {notes.map((n) => (
          <div key={n.id} className="p-3">
            <div className="mb-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
              <span>{new Date(n.created_at).toLocaleString()}</span>
              {n.author_name && (
                <span className="font-medium text-slate-600">{n.author_name}</span>
              )}
              <span className="rounded bg-slate-100 px-2 py-0.5">
                {t(`app.candidate_card.notes.visibility.${n.visibility}`, { defaultValue: n.visibility })}
              </span>
            </div>
            <div className="whitespace-pre-wrap break-words overflow-wrap-anywhere text-slate-700">{n.text}</div>
          </div>
        ))}
      </div>
    </aside>
  )
}

export default memo(CandidateNotesSection)
