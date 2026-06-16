import type { TransferBlockingReason } from '../../api/candidates'

/** Display-only grouping of API blocking reasons — no gate logic. */
export function groupBlockingReasonsByLayer(
  reasons: TransferBlockingReason[] | null | undefined,
): Array<{ layer: string; items: TransferBlockingReason[] }> {
  const map = new Map<string, TransferBlockingReason[]>()
  for (const reason of reasons || []) {
    const layer = String(reason.source_layer || 'unknown').trim() || 'unknown'
    const bucket = map.get(layer)
    if (bucket) bucket.push(reason)
    else map.set(layer, [reason])
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([layer, items]) => ({ layer, items }))
}

export function formatTransferList(items: string[] | null | undefined): string {
  const list = (items || []).map((x) => String(x || '').trim()).filter(Boolean)
  return list.length ? list.join(', ') : '—'
}
