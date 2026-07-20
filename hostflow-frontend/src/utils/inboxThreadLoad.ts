import {
  listCommunicationThreads,
  reconcileCommunicationThreadUnread,
  type CommunicationThread,
  type CommunicationThreadQueue,
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
  /** C1 platform queue — filters Threads server-side when set. */
  queue?: CommunicationThreadQueue | string | null
}): Promise<CommunicationThread[]> {
  const qApi = opts.q.trim() || undefined
  const queue = String(opts.queue || '').trim() || undefined
  const includeArchived = queue === 'closed'
  if (opts.effectiveChannel === 'email' && opts.hasEmail) {
    try {
      await reconcileCommunicationThreadUnread({ channel: 'email', limit: 5000, includeArchived: true })
    } catch {
      /* ignore */
    }
    const res = await listCommunicationThreads({
      limit: 300,
      channel: 'email',
      // Email hub historically loaded archived too; closed queue also needs them.
      includeArchived: true,
      q: qApi,
      queue,
    })
    return Array.isArray(res.items) ? res.items : []
  }
  try {
    await reconcileCommunicationThreadUnread({ limit: 5000 })
  } catch {
    /* ignore */
  }
  const res = await listCommunicationThreads({
    limit: 400,
    includeArchived,
    q: qApi,
    queue,
  })
  let items = Array.isArray(res.items) ? res.items : []
  if (opts.effectiveChannel === 'messages' && opts.hasMessages) {
    items = items.filter((th) => !isEmailChannelThread(th))
  }
  return items
}
