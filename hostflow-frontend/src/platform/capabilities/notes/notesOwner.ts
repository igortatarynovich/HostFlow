import { api } from '../../../api/client'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'

export type NotesListItem = {
  id: string
  text: string
  created_at?: string
  author_name?: string | null
}

export type NotesListResult = {
  available: boolean
  items: NotesListItem[]
}

/**
 * Notes owner facade. Transport stays here — capability UI, hosts, and pages
 * must not call `/candidates/:id/notes` themselves.
 */
export function notesSubjectKey(ctx: WorkspaceCapabilityRenderContext): string {
  return resolveCandidateId(ctx)
}

function resolveCandidateId(ctx: WorkspaceCapabilityRenderContext): string {
  if (ctx.application?.outcome_entity_type === 'candidate') {
    return String(ctx.application.outcome_entity_id || '').trim()
  }
  if (ctx.entity?.resourceType === 'candidate') {
    return String(ctx.entity.resourceId || '').trim()
  }
  return ''
}

export async function listNotes(ctx: WorkspaceCapabilityRenderContext): Promise<NotesListResult> {
  const candidateId = resolveCandidateId(ctx)
  if (!candidateId) {
    return { available: false, items: [] }
  }
  const { data } = await api.get<NotesListItem[]>(`/candidates/${encodeURIComponent(candidateId)}/notes`)
  return { available: true, items: Array.isArray(data) ? data : [] }
}

export async function addNote(ctx: WorkspaceCapabilityRenderContext, text: string): Promise<void> {
  const candidateId = resolveCandidateId(ctx)
  const body = text.trim()
  if (!candidateId || !body) return
  await api.post(`/candidates/${encodeURIComponent(candidateId)}/notes`, { text: body, visibility: 'internal' })
}
