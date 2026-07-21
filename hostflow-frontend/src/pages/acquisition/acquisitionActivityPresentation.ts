import type { AcquisitionActivityEvent } from '../../api/acquisitionActivity'

/** UI label for catalog event_type — display mapping only, not reconstruction. */
export function humanizeEventType(eventType: string): string {
  const raw = String(eventType || '').trim()
  if (!raw) return '—'
  return raw.replace(/([a-z])([A-Z])/g, '$1 $2')
}

/** Text-only JSON for expand panel (never HTML). */
export function formatActivityDetailsJson(event: AcquisitionActivityEvent): string {
  return JSON.stringify(
    {
      id: event.id,
      event_type: event.event_type,
      event_version: event.event_version,
      source_event_id: event.source_event_id,
      recorded_at: event.recorded_at,
      payload: event.payload,
    },
    null,
    2,
  )
}

/** Append page without duplicating ids (Load more safety). */
export function mergeActivityPages(
  prev: AcquisitionActivityEvent[],
  next: AcquisitionActivityEvent[],
): AcquisitionActivityEvent[] {
  if (!next.length) return prev
  if (!prev.length) return [...next]
  const seen = new Set(prev.map((item) => item.id))
  const out = [...prev]
  for (const item of next) {
    if (seen.has(item.id)) continue
    seen.add(item.id)
    out.push(item)
  }
  return out
}
