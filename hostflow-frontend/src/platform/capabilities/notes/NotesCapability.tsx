import { useCallback, useEffect, useState } from 'react'
import { api } from '../../../api/client'
import { Button } from '../../../components/ui/Button'
import { useToast } from '../../../components/Toast'
import { useI18n } from '../../../i18n'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'

type NoteRow = {
  id: string
  text: string
  created_at?: string
  author_name?: string | null
}

/**
 * Shared Notes widget. Owner = Notes. Host only places this contribution.
 * Storage: candidate notes when the application has produced a candidate.
 */
export function NotesCapability({ application, onRefresh }: WorkspaceCapabilityRenderContext) {
  const { t } = useI18n()
  const { notify } = useToast()
  const candidateId =
    application.outcome_entity_type === 'candidate' ? String(application.outcome_entity_id || '').trim() : ''
  const [notes, setNotes] = useState<NoteRow[]>([])
  const [loading, setLoading] = useState(Boolean(candidateId))
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!candidateId) {
      setNotes([])
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const { data } = await api.get<NoteRow[]>(`/candidates/${encodeURIComponent(candidateId)}/notes`)
      setNotes(Array.isArray(data) ? data : [])
    } catch {
      setNotes([])
    } finally {
      setLoading(false)
    }
  }, [candidateId])

  useEffect(() => {
    void load()
  }, [load])

  const addNote = async () => {
    const text = draft.trim()
    if (!candidateId || !text || saving) return
    setSaving(true)
    try {
      await api.post(`/candidates/${encodeURIComponent(candidateId)}/notes`, { text, visibility: 'internal' })
      setDraft('')
      await load()
      onRefresh()
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      notify({ title: typeof detail === 'string' ? detail : 'Не удалось сохранить заметку', variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-3" data-capability-id="notes" data-widget-class="notes">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.candidate_card.notes.title', { defaultValue: 'Заметки' })}
      </p>
      {loading ? <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</p> : null}
      {!loading && !candidateId ? (
        <p className="text-sm text-slate-500">
          Заметки появятся после создания кандидата. Shared Notes widget размещён хостом — локальная секция комментариев запрещена.
        </p>
      ) : null}
      {!loading && candidateId
        ? notes.map((note) => (
            <article key={note.id} className="rounded-none border border-slate-200 bg-white p-3 text-sm text-slate-700">
              <p>{note.text}</p>
              {note.created_at ? <p className="mt-1 text-xs text-slate-400">{new Date(note.created_at).toLocaleString()}</p> : null}
            </article>
          ))
        : null}
      {candidateId ? (
        <div className="space-y-2">
          <textarea
            className="textarea"
            rows={3}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={t('app.candidate_card.notes.placeholder', { defaultValue: 'Внутренняя заметка' })}
          />
          <Button variant="secondary" size="sm" disabled={saving || !draft.trim()} onClick={() => void addNote()}>
            {t('common.save', { defaultValue: 'Сохранить' })}
          </Button>
        </div>
      ) : null}
    </section>
  )
}
