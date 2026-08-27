/** Client-card driver capacity: hired = employed funnel stage, not a manual order field. */

export type BlockingOrderReason = 'schedule' | 'capacity' | 'status' | 'documents'

export type BlockingOrderEntry = {
  key: string
  title: string
  status: string | null
  reasons: BlockingOrderReason[]
  updatedAt: string | null
}

function asNumber(value: unknown): number {
  if (value === null || value === undefined || value === '') return 0
  const num = Number(value)
  return Number.isFinite(num) ? num : 0
}

export function employedCandidatesCount(company: {
  recruitment_candidates_employed?: number | null
} | null | undefined): number {
  return Math.max(0, Math.floor(asNumber(company?.recruitment_candidates_employed)))
}

export function orderRequiredDrivers(order: Record<string, unknown>): number {
  return asNumber(order.required_drivers ?? order.drivers_required ?? order.slots)
}

export function blockingReasonsForOrder(
  order: Record<string, unknown>,
  hiredEmployed: number,
): BlockingOrderReason[] {
  const reasons: BlockingOrderReason[] = []
  const startsAt = order.starts_at ?? order.start ?? order.date_start
  const endsAt = order.ends_at ?? order.end ?? order.date_end
  const required = orderRequiredDrivers(order)
  if (!startsAt || !endsAt) reasons.push('schedule')
  if (required && hiredEmployed < required) reasons.push('capacity')
  if (!order.status || ['draft', 'pending', 'requested'].includes(String(order.status).toLowerCase())) {
    reasons.push('status')
  }
  const docsRequired = asNumber(order.required_documents ?? order.docs_required)
  const docsReady = asNumber(order.attachments_count ?? order.docs_ready ?? order.documents_ready)
  if (docsRequired > docsReady) reasons.push('documents')
  return reasons
}

export function buildBlockingOrders(
  orders: Array<Record<string, unknown>>,
  hiredEmployed: number,
  unnamed: string,
): BlockingOrderEntry[] {
  if (!orders.length) return []
  return orders
    .map((order, index) => {
      const reasons = blockingReasonsForOrder(order, hiredEmployed)
      if (!reasons.length) return null
      const updatedAt = (order.updated_at ?? order.ends_at ?? order.starts_at ?? order.created_at ?? null) as
        | string
        | null
      return {
        key: String(order.id ?? order.code ?? `order-${index}`),
        title: String(order.title ?? order.code ?? unnamed),
        status: order.status != null ? String(order.status) : null,
        reasons,
        updatedAt,
      }
    })
    .filter((entry): entry is BlockingOrderEntry => Boolean(entry))
    .sort((a, b) => {
      const aTime = Date.parse(a.updatedAt ?? '') || 0
      const bTime = Date.parse(b.updatedAt ?? '') || 0
      return bTime - aTime
    })
    .slice(0, 4)
}
