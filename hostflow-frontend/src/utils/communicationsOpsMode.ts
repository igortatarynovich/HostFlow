import type { CommunicationThread } from '../api/communications'
import type { NotificationItem } from '../api/types'

export type CommunicationOpsMode = 'in_work' | 'later' | 'escalated' | 'no_reply_needed'
export type CommunicationIncidentGroup = 'open' | CommunicationOpsMode | 'closed'

export function noReplyNeededFromThread(thread: CommunicationThread): boolean {
  const meta = (thread.thread_meta || {}) as Record<string, any>
  const sla = (meta.sla_policy || {}) as Record<string, any>
  return Boolean(sla.no_reply_needed || meta.no_reply_needed)
}

export function slaMutedFromThread(thread: CommunicationThread): boolean {
  const meta = (thread.thread_meta || {}) as Record<string, any>
  const sla = (meta.sla_policy || {}) as Record<string, any>
  return Boolean(sla.muted || meta.sla_muted)
}

export function slaSnoozedUntilFromThread(thread: CommunicationThread): string | null {
  const meta = (thread.thread_meta || {}) as Record<string, any>
  const sla = (meta.sla_policy || {}) as Record<string, any>
  const raw = String(sla.snoozed_until || '').trim()
  return raw || null
}

export function opsModeFromThread(thread: CommunicationThread): CommunicationOpsMode | null {
  const meta = (thread.thread_meta || {}) as Record<string, any>
  const ops = (meta.ops || {}) as Record<string, any>
  const raw = String(ops.mode || '').trim().toLowerCase()
  if (raw === 'in_work' || raw === 'later' || raw === 'escalated' || raw === 'no_reply_needed') return raw as CommunicationOpsMode
  if (noReplyNeededFromThread(thread)) return 'no_reply_needed'
  if (String(thread.priority || '').trim().toLowerCase() === 'high') return 'escalated'
  return null
}

export function notificationThreadId(item: NotificationItem): string {
  const payload = (item.payload || {}) as Record<string, any>
  return (
    String(payload.thread_id || '').trim() ||
    (String(item.entity_type || '') === 'communication_thread' ? String(item.entity_id || '').trim() : '')
  )
}

export function opsModeFromNotificationPayload(item: NotificationItem): CommunicationOpsMode | null {
  const payload = (item.payload || {}) as Record<string, any>
  const raw = String(payload.ops_mode || payload.operational_mode || payload.mode || '')
    .trim()
    .toLowerCase()
  if (raw === 'in_work' || raw === 'later' || raw === 'escalated' || raw === 'no_reply_needed') return raw as CommunicationOpsMode
  if (payload.no_reply_needed === true) return 'no_reply_needed'
  if (String(payload.priority || '').trim().toLowerCase() === 'high') return 'escalated'
  return null
}

export function incidentGroupOf(item: NotificationItem, modeOverride?: CommunicationOpsMode | null): CommunicationIncidentGroup {
  const mode = modeOverride || opsModeFromNotificationPayload(item)
  if (mode) return mode
  if (item.is_read) return 'closed'
  return 'open'
}
