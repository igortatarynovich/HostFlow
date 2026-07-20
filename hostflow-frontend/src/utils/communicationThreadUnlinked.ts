import type { CommunicationThread } from '../api/communications'
import { resolveThreadEntityLinks } from './communicationThreadEntityLinks'

/** Service order UUID stored under thread_meta.uos (UOS context rail). */
export function uosLinkedServiceOrderId(threadMeta: Record<string, any> | undefined | null): string {
  const u = threadMeta?.uos
  if (!u || typeof u !== 'object') return ''
  return String((u as Record<string, unknown>).linked_service_order_id || '').trim()
}

/** Thread has no G13/legacy entity binding — first-class "link later" queue. */
export function isCommunicationThreadUnlinked(th: CommunicationThread): boolean {
  if (resolveThreadEntityLinks(th).length) return false
  return true
}
