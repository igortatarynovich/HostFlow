/** Deep links into the unified Inbox (Communication Center). */

import { inboxContextQueryString, type InboxListQuery } from './inboxUrlQuery'

function baseListQuery(partial: Partial<InboxListQuery>): InboxListQuery {
  return {
    channel: 'all',
    folder: 'inbox',
    q: '',
    candidateId: '',
    assignedToMe: false,
    hasAssignee: false,
    unlinkedOnly: false,
    ...partial,
  }
}

export function buildInboxThreadPath(
  threadId: string,
  query?: { candidateId?: string; channel?: 'messages' | 'email' },
): string {
  const id = String(threadId || '').trim()
  if (!id) return '/app/inbox'
  const path = `/app/inbox/threads/${encodeURIComponent(id)}`
  const channel: InboxListQuery['channel'] =
    query?.channel === 'email' ? 'email' : query?.channel === 'messages' ? 'messages' : 'all'
  const list = baseListQuery({
    channel,
    candidateId: String(query?.candidateId || '').trim(),
  })
  return `${path}${inboxContextQueryString(list)}`
}

export function buildInboxHubPath(query?: { candidateId?: string; channel?: 'messages' | 'email' | 'all' }): string {
  const list = baseListQuery({
    channel: query?.channel && query.channel !== 'all' ? query.channel : 'all',
    candidateId: String(query?.candidateId || '').trim(),
  })
  return `/app/inbox${inboxContextQueryString(list)}`
}
