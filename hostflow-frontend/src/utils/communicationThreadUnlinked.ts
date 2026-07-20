import type { CommunicationThread } from '../api/communications'

/** Service order UUID stored under thread_meta.uos (UOS context rail). */
export function uosLinkedServiceOrderId(threadMeta: Record<string, any> | undefined | null): string {
  const u = threadMeta?.uos
  if (!u || typeof u !== 'object') return ''
  return String((u as Record<string, unknown>).linked_service_order_id || '').trim()
}

function hasEntityLinks(th: CommunicationThread): boolean {
  const links = (th as CommunicationThread & { entity_links?: Array<{ entity_type?: string; entity_id?: string }> })
    .entity_links
  if (!Array.isArray(links) || links.length === 0) return false
  return links.some((link) => String(link?.entity_type || '').trim() && String(link?.entity_id || '').trim())
}

/**
 * Thread has no CRM entity link — «Без привязки» queue (G15).
 * Linked when: candidate/company soft refs, UOS service order, legacy entity_*, or G13 entity_links.
 */
export function isCommunicationThreadUnlinked(th: CommunicationThread): boolean {
  if (String(th.linked_candidate_id || '').trim()) return false
  if (String(th.linked_company_id || '').trim()) return false
  if (uosLinkedServiceOrderId(th.thread_meta)) return false
  if (String(th.entity_type || '').trim() && String(th.entity_id || '').trim()) return false
  if (hasEntityLinks(th)) return false
  return true
}
