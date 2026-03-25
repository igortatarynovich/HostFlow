import type { EmailFolderKey } from './emailInboxFolders'
import { parseEmailFolderKey } from './emailInboxFolders'

export type InboxChannelScope = 'all' | 'messages' | 'email'

export function parseInboxChannelScope(raw: string | null | undefined): InboxChannelScope {
  const v = String(raw || '').trim().toLowerCase()
  if (v === 'messages' || v === 'message') return 'messages'
  if (v === 'email' || v === 'mail') return 'email'
  return 'all'
}

export type InboxListQuery = {
  channel: InboxChannelScope
  folder: EmailFolderKey
  q: string
  candidateId: string
  assignedToMe: boolean
  hasAssignee: boolean
  unlinkedOnly: boolean
}

export function readInboxListQuery(searchParams: URLSearchParams): InboxListQuery {
  const u = searchParams.get('unlinked')
  const unlinkedOnly = u === '1' || u === 'true'
  return {
    channel: parseInboxChannelScope(searchParams.get('channel')),
    folder: parseEmailFolderKey(searchParams.get('folder')),
    q: String(searchParams.get('q') || '').trim(),
    candidateId: String(searchParams.get('candidateId') || '').trim(),
    assignedToMe: searchParams.get('assignedToMe') === '1' || searchParams.get('assignedToMe') === 'true',
    hasAssignee: searchParams.get('hasAssignee') === '1' || searchParams.get('hasAssignee') === 'true',
    unlinkedOnly,
  }
}

/** Serialize inbox context for thread/hub links (drops empty / default pieces). */
export function inboxContextSearchParams(q: InboxListQuery): URLSearchParams {
  const p = new URLSearchParams()
  if (q.channel !== 'all') p.set('channel', q.channel)
  if (q.channel === 'email' && q.folder && q.folder !== 'inbox') p.set('folder', q.folder)
  if (q.q) p.set('q', q.q)
  if (q.candidateId) p.set('candidateId', q.candidateId)
  if (q.assignedToMe) p.set('assignedToMe', '1')
  if (q.hasAssignee) p.set('hasAssignee', '1')
  if (q.unlinkedOnly) p.set('unlinked', '1')
  return p
}

export function inboxContextQueryString(q: InboxListQuery): string {
  const p = inboxContextSearchParams(q)
  const s = p.toString()
  return s ? `?${s}` : ''
}
