import type { CommunicationThread, CommunicationThreadEntityLink } from '../api/communications'

function uosOrderId(threadMeta: Record<string, any> | undefined | null): string {
  const u = threadMeta?.uos
  if (!u || typeof u !== 'object') return ''
  return String((u as Record<string, unknown>).linked_service_order_id || '').trim()
}

/** Prefer G13 entity_links; fall back to legacy columns / linked_* / UOS meta. */
export function resolveThreadEntityLinks(th: CommunicationThread): CommunicationThreadEntityLink[] {
  const fromG13 = Array.isArray(th.entity_links)
    ? th.entity_links.filter((l) => String(l?.entity_type || '').trim() && String(l?.entity_id || '').trim())
    : []
  if (fromG13.length) return fromG13

  const legacy: CommunicationThreadEntityLink[] = []
  const push = (entity_type: string, entity_id: string) => {
    const et = String(entity_type || '').trim()
    const eid = String(entity_id || '').trim()
    if (!et || !eid) return
    if (legacy.some((l) => l.entity_type === et && l.entity_id === eid)) return
    legacy.push({
      link_id: `legacy:${et}:${eid}`,
      thread_id: String(th.id || ''),
      entity_type: et,
      entity_id: eid,
      is_immutable: false,
    })
  }

  push(String(th.entity_type || ''), String(th.entity_id || ''))
  if (th.linked_candidate_id) push('candidate', String(th.linked_candidate_id))
  if (th.linked_company_id) push('company', String(th.linked_company_id))
  const orderId = uosOrderId(th.thread_meta)
  if (orderId) push('service_order', orderId)
  return legacy
}

export function primaryThreadEntityLabel(th: CommunicationThread): string {
  const links = resolveThreadEntityLinks(th)
  if (!links.length) return '—'
  const primary = links[0]
  return `${primary.entity_type} / ${primary.entity_id}`
}
