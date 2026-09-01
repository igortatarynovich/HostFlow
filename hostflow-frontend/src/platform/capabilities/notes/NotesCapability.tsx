import { useCallback, useEffect, useState } from 'react'
import { Button } from '../../../components/ui/Button'
import { useToast } from '../../../components/Toast'
import { useI18n } from '../../../i18n'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'
import { addNote, listNotes, notesSubjectKey, type NotesListItem } from './notesOwner'

/**
 * Shared Notes widget. Owner = Notes. Host only places this contribution.
 * Storage transport is the Notes owner facade — not candidate-notes API here.
 */
export function NotesCapability(ctx: WorkspaceCapabilityRenderContext) {
  const { t } = useI18n()
  const { notify } = useToast()
  const { onRefresh } = ctx
  const subjectKey = notesSubjectKey(ctx)
  const [notes, setNotes] = useState<NotesListItem[]>([])
  const [available, setAvailable] = useState(Boolean(subjectKey))
  const [loading, setLoading] = useState(Boolean(subjectKey))
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!subjectKey) {
      setNotes([])
      setAvailable(false)
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const result = await listNotes(ctx)
      setAvailable(result.available)
      setNotes(result.items)
    } catch {
      setNotes([])
      setAvailable(false)
    } finally {
      setLoading(false)
    }
    // subjectKey is the owner-resolved transport id; avoid depending on ctx identity.
  }, [subjectKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void load()
  }, [load])

  const save = async () => {
    const text = draft.trim()
    if (!available || !text || saving) return
    setSaving(true)
    try {
      await addNote(ctx, text)
      setDraft('')
      await load()
      onRefresh()
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      notify({
        title: typeof detail === 'string' ? detail : t('app.candidate_card.notes.save_failed'),
        variant: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-3" data-capability-id="notes" data-widget-class="notes">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.candidate_card.notes.title')}
      </p>
      {loading ? <p className="text-sm text-slate-500">{t('common.loading')}</p> : null}
      {!loading && !available ? (
        <p className="text-sm text-slate-500">{t('app.candidate_card.notes.unavailable')}</p>
      ) : null}
      {!loading && available
        ? notes.map((note) => (
            <article key={note.id} className="rounded-none border border-slate-200 bg-white p-3 text-sm text-slate-700">
              <p>{note.text}</p>
              {note.created_at ? <p className="mt-1 text-xs text-slate-400">{new Date(note.created_at).toLocaleString()}</p> : null}
            </article>
          ))
        : null}
      {available ? (
        <div className="space-y-2">
          <textarea
            className="textarea"
            rows={3}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={t('app.candidate_card.notes.placeholder')}
          />
          <Button variant="secondary" size="sm" disabled={saving || !draft.trim()} onClick={() => void save()}>
            {t('common.save')}
          </Button>
        </div>
      ) : null}
    </section>
  )
}
