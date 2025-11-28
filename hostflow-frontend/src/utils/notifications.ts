import type { NotificationItem, WhoAmI } from '../api/types'

export function isNotificationRelevant(item: NotificationItem, me: WhoAmI | null, opts: { includeUnassigned?: boolean } = {}): boolean {
  if (!me) return false
  const userIds = new Set([
    (me as any)?.user_id,
    me.sub,
    me.email,
    (me as any)?.id,
  ].filter(Boolean).map((value) => String(value)))

  const payload = item.payload ?? {}
  const candidateValues = [
    payload.assignee_id,
    payload.user_id,
    payload.owner_id,
    payload.manager_id,
    payload.candidate_manager_id,
    payload.recipient_id,
  ]
  for (const value of candidateValues) {
    if (value != null && userIds.has(String(value))) return true
  }

  const listCandidates = [payload.user_ids, payload.assignee_ids, payload.manager_ids]
  for (const list of listCandidates) {
    if (Array.isArray(list) && list.some((value) => value != null && userIds.has(String(value)))) {
      return true
    }
  }

  if (opts.includeUnassigned) {
    const managerIds = [payload.manager_id, payload.recruiter_id, payload.assignee_id, payload.owner_id].filter(Boolean)
    if (managerIds.length === 0) {
      return true
    }
  }

  if (payload.email && userIds.has(String(payload.email))) {
    return true
  }
  if (Array.isArray(payload.emails) && payload.emails.some((email: any) => userIds.has(String(email)))) {
    return true
  }

  if (item.entity_type === 'user' && item.entity_id && userIds.has(String(item.entity_id))) {
    return true
  }

  return false
}

export function filterRelevantNotifications(items: NotificationItem[], me: WhoAmI | null, opts: { includeUnassigned?: boolean } = {}) {
  return items.filter((item) => isNotificationRelevant(item, me, opts))
}
