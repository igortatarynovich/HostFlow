import {
  listCommunicationThreads,
  reconcileCommunicationThreadUnread,
  type CommunicationThread,
} from '../api/communications'
import type { InboxChannelScope } from './inboxUrlQuery'

function isEmailChannelThread(th: CommunicationThread): boolean {
  return String(th.channel || '').toLowerCase() === 'email'
}

/** Shared thread pool load for Inbox hub + Communication Center (URL scope parity). */
export async function fetchInboxThreadPool(opts: {
  effectiveChannel: InboxChannelScope
  hasEmail: boolean
  hasMessages: boolean
  q: string
}): Promise<CommunicationThread[]> {
  const qApi = opts.q.trim() || undefined
  if (opts.effectiveChannel === 'email' && opts.hasEmail) {
    try {
      await reconcileCommunicationThreadUnread({ channel: 'email', limit: 5000, includeArchived: true })
    } catch {
      /* ignore */
    }
    const res = await listCommunicationThreads({
      limit: 300,
      channel: 'email',
      includeArchived: true,
      q: qApi,
    })
    return Array.isArray(res.items) ? res.items : []
  }
  try {
    await reconcileCommunicationThreadUnread({ limit: 5000 })
  } catch {
    /* ignore */
  }
  const res = await listCommunicationThreads({ limit: 400, includeArchived: false, q: qApi })
  let items = Array.isArray(res.items) ? res.items : []
  if (opts.effectiveChannel === 'messages' && opts.hasMessages) {
    items = items.filter((th) => !isEmailChannelThread(th))
  }
  return items
}
