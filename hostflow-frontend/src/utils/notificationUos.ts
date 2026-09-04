import type { NotificationItem } from '../api/types'

/** UOS notification groups (top bar attention center). */
export type NotificationUosGroup = 'sla' | 'tasks' | 'messages' | 'system'

/**
 * UOS attention tiers for the bell badge (SSOT: CRITICAL = comms SLA breach / unpaid invoice;
 * lead nudges are tasks; HIGH = overdue tasks, handoffs). Message/email unread stay on their own icons.
 */
export type NotificationAttentionTier = 'critical' | 'high' | 'normal'

export function getNotificationUosGroup(item: NotificationItem): NotificationUosGroup {
  const et = String(item.event_type || '').toLowerCase()
  const payload = (item.payload || {}) as Record<string, unknown>
  const source = String(payload.source || '').toLowerCase()

  if (et === 'communications_sla_overdue' || et === 'communications_thread_escalated' || et === 'lead_rodo_delivery_escalated') return 'sla'
  if (et === 'lead_no_next_action' || et === 'lead_stuck_stage') return 'tasks'
  if (et === 'invoice_overdue' || source.includes('invoice_overdue')) return 'sla'
  if (
    source === 'leads_next_action_sla' ||
    source === 'leads_stuck_stage_sla' ||
    source === 'invoice_overdue_sla'
  ) {
    return 'sla'
  }

  if (et === 'reminder_due' || et === 'reminder_overdue') return 'tasks'
  if (source === 'reminders') return 'tasks'

  const threadId = payload.thread_id
  if (threadId != null && String(threadId).trim() !== '') return 'messages'
  if (et.includes('communication')) return 'messages'
  if (et.includes('inbound') && (et.includes('email') || et.includes('message'))) return 'messages'

  return 'system'
}

export function getNotificationAttentionTier(item: NotificationItem): NotificationAttentionTier {
  const p = String(item.priority || '')
    .trim()
    .toLowerCase()
  if (p === 'critical' || p === 'high' || p === 'normal') return p
  if (getNotificationUosGroup(item) === 'sla') return 'critical'
  const et = String(item.event_type || '').toLowerCase()
  if (et === 'reminder_overdue') return 'high'
  if (et === 'handoff_requested') return 'high'
  /** Ops may need to fix routing (default company / vacancy). */
  if (et === 'intake_client_lead_skipped_no_company') return 'high'
  return 'normal'
}
