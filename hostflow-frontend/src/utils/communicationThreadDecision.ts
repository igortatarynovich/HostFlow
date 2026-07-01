import type { CommunicationThread } from '../api/communications'
import {
  noReplyNeededFromThread,
  slaMutedFromThread,
  slaSnoozedUntilFromThread,
} from './communicationsOpsMode'
function parseMs(iso?: string | null): number {
  if (!iso) return 0
  const t = Date.parse(String(iso))
  return Number.isFinite(t) ? t : 0
}

function isSnoozeActive(th: CommunicationThread): boolean {
  const raw = slaSnoozedUntilFromThread(th)
  if (!raw) return false
  return parseMs(raw) > Date.now()
}

/** SLA clock is in the past; not muted, not no-reply, not actively snoozed. */
export function threadSlaOverdue(th: CommunicationThread): boolean {
  if (noReplyNeededFromThread(th)) return false
  if (slaMutedFromThread(th)) return false
  if (isSnoozeActive(th)) return false
  const due = th.sla_due_at
  if (!due) return false
  const t = parseMs(due)
  return t > 0 && t < Date.now()
}

/**
 * Thread likely needs an outbound reply: unread, or last inbound is newer than last outbound
 * (and SLA policy does not suppress attention).
 */
export function threadNeedsOutboundReply(th: CommunicationThread): boolean {
  if (noReplyNeededFromThread(th)) return false
  if (slaMutedFromThread(th)) return false
  if (isSnoozeActive(th)) return false
  if (Number(th.unread_count || 0) > 0) return true
  const inb = parseMs(th.last_inbound_at)
  const out = parseMs(th.last_outbound_at)
  if (inb <= 0) return false
  if (out <= 0) return true
  return inb > out
}

export type ThreadDecisionTier = 'sla_overdue' | 'needs_reply' | 'normal'

export function threadDecisionTier(th: CommunicationThread): ThreadDecisionTier {
  if (threadSlaOverdue(th)) return 'sla_overdue'
  if (threadNeedsOutboundReply(th)) return 'needs_reply'
  return 'normal'
}

/** Whole hours since last inbound when waiting for reply; null if not applicable. */
export function threadHoursWaitingForReply(th: CommunicationThread): number | null {
  if (!threadNeedsOutboundReply(th)) return null
  const base = th.last_inbound_at || th.last_message_at
  const ms = parseMs(base)
  if (ms <= 0) return null
  const hours = Math.floor((Date.now() - ms) / 3_600_000)
  return hours >= 0 ? hours : null
}
