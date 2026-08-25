import { api } from '../../../api/client'
import type { Application } from '../../../api/types/application'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'

export type NotesListItem = {
  id: string
  text: string
  created_at?: string
  author_name?: string | null
}

export type NotesListItem = NotesListItem

export type NotesListResult = {
  available: boolean
  items: NotesListItem[]
}

/**
 * Notes owner facade. Transport stays here — capability UI, hosts, and pages
 * must not call `/candidates/:id/notes` themselves.
 *
 * Pre-convert recruitment applications use application comments; converted
 * applications and Candidate Entity use candidate notes.
 *
 * Exported as listNotes / addNote (gate names listNotes / addNote).
 */
export function notesSubjectKey(ctx: WorkspaceCapabilityRenderContext): string {
  return resolveCandidateId(ctx) || applicationNotesKey(ctx)
}

function applicationNotesKey(ctx: WorkspaceCapabilityRenderContext): string {
  const applicationId = resolveApplicationId(ctx)
  return applicationId ? `application:${applicationId}` : ''
}

function resolveApplicationId(ctx: WorkspaceCapabilityRenderContext): string {
  const application = ctx.application
  if (application?.module === 'recruitment' && application.id) {
    return String(application.id).trim()
  }
  return ''
}

function resolveCandidateId(ctx: WorkspaceCapabilityRenderContext): string {
  const application = ctx.application
  if (application) {
    const type = String(application.outcome_entity_type || '').trim()
    const id = String(application.outcome_entity_id || '').trim()
    if (id && (type === 'candidate' || !type)) return id
  }
  const entity = ctx.entity
  if (entity) {
    const type = String(entity.resourceType || '').trim()
    const id = String(entity.resourceId || '').trim()
    if (type === 'candidate') return id
  }
  return ''
}

function mapApplicationComments(raw: unknown): NotesListItem[] {
  if (!Array.isArray(raw)) return []
  return raw
    .map((row, index) => {
      if (!row || typeof row !== 'object') return null
      const item = row as Record<string, unknown>
      const text = String(item.text || item.note || '').trim()
      if (!text) return null
      return {
        id: String(item.id || `comment-${index}`),
        text,
        created_at: String(item.created_at || item.at || '') || undefined,
        author_name: item.author_name ? String(item.author_name) : item.author ? String(item.author) : null,
      } satisfies NotesListItem
    })
    .filter((row): row is NotesListItem => row !== null)
}

async function listApplicationComments(applicationId: string): Promise<NotesListItem[]> {
  const { data } = await api.get<Application>(`/recruitment/applications/${encodeURIComponent(applicationId)}`)
  return mapApplicationComments(data?.extensions?.application_comments_v1)
}

export async function listNotes(ctx: WorkspaceCapabilityRenderContext): Promise<NotesListResult> {
  const candidateId = resolveCandidateId(ctx)
  const applicationId = resolveApplicationId(ctx)
  if (!candidateId && !applicationId) {
    return { available: false, items: [] }
  }
  const items: NotesListItem[] = []
  if (applicationId) {
    items.push(...(await listApplicationComments(applicationId)))
  }
  if (candidateId) {
    const { data } = await api.get<NotesListItem[]>(`/candidates/${encodeURIComponent(candidateId)}/notes`)
    items.push(...(Array.isArray(data) ? data : []))
  }
  return { available: true, items }
}

export async function addNote(ctx: WorkspaceCapabilityRenderContext, text: string): Promise<void> {
  const body = text.trim()
  if (!body) return
  const candidateId = resolveCandidateId(ctx)
  if (candidateId) {
    await api.post(`/candidates/${encodeURIComponent(candidateId)}/notes`, { text: body, visibility: 'internal' })
    return
  }
  const applicationId = resolveApplicationId(ctx)
  if (!applicationId) return
  await api.post(`/recruitment/applications/${encodeURIComponent(applicationId)}/comments`, { note: body })
}
