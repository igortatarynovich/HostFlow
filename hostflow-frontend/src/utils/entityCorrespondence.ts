/** Resolve Inbox/Threads deep link for a CRM entity (G13-linked threads). */

import { listCommunicationThreads, type CommunicationThread } from '../api/communications'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { buildInboxHubPath, buildInboxThreadPath } from './inboxDeepLinks'

export type EntityCorrespondenceRef = {
  entityType: string
  entityId: string
}

function newestThread(items: CommunicationThread[]): CommunicationThread | null {
  if (!items.length) return null
  return [...items].sort(
    (a, b) =>
      Date.parse(String(b.updated_at || b.last_message_at || 0)) -
      Date.parse(String(a.updated_at || a.last_message_at || 0)),
  )[0]
}

/**
 * Find the newest thread linked to any of the refs (order = preference).
 * Falls back to candidate-scoped inbox hub, then plain Inbox.
 */
export async function resolveEntityCorrespondenceHref(
  refs: EntityCorrespondenceRef[],
  opts?: { candidateId?: string; signal?: AbortSignal },
): Promise<{ href: string; threadId: string | null }> {
  const candidateId = String(opts?.candidateId || '').trim() || undefined

  for (const ref of refs) {
    const entityType = String(ref.entityType || '').trim()
    const entityId = String(ref.entityId || '').trim()
    if (!entityType || !entityId) continue
    try {
      const res = await listCommunicationThreads({
        entityType,
        entityId,
        limit: 10,
        includeArchived: false,
        signal: opts?.signal,
      })
      const thread = newestThread(Array.isArray(res.items) ? res.items : [])
      if (thread?.id) {
        return {
          href: buildInboxThreadPath(thread.id, { candidateId }),
          threadId: thread.id,
        }
      }
    } catch {
      // try next ref
    }
  }

  if (candidateId) {
    return { href: buildInboxHubPath({ candidateId }), threadId: null }
  }
  return { href: CRM_APP_PATHS.inbox, threadId: null }
}
