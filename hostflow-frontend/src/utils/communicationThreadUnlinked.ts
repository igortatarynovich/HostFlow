import type { CommunicationThread } from '../api/communications'

/** Service order UUID stored under thread_meta.uos (UOS context rail). */
export function uosLinkedServiceOrderId(threadMeta: Record<string, any> | undefined | null): string {
  const u = threadMeta?.uos
  if (!u || typeof u !== 'object') return ''
  return String((u as Record<string, unknown>).linked_service_order_id || '').trim()
}

/** Thread has no candidate, client company, or linked service order — first-class "link later" queue. */
export function isCommunicationThreadUnlinked(th: CommunicationThread): boolean {
  if (String(th.linked_candidate_id || '').trim()) return false
  if (String(th.linked_company_id || '').trim()) return false
  if (uosLinkedServiceOrderId(th.thread_meta)) return false
  return true
}
