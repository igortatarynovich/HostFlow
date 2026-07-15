import type { NotificationItem } from '../api/types'
import { communicationsThreadPath, CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from '../app/crmAppPaths'
import { buildInboxThreadPath } from './inboxDeepLinks'
import { getNotificationUosGroup } from './notificationUos'

export function notificationThreadId(item: NotificationItem): string {
  const p = item.payload as Record<string, unknown> | undefined
  const raw = p?.thread_id
  if (typeof raw === 'string') return raw.trim()
  if (raw != null) {
    const s = String(raw).trim()
    return s
  }
  return ''
}

export function notificationThreadChannel(item: NotificationItem): 'messages' | 'email' | undefined {
  const p = item.payload as Record<string, unknown> | undefined
  const c = String(p?.channel || '').trim().toLowerCase()
  if (c === 'email') return 'email'
  if (c === 'messages' || c === 'message') return 'messages'
  return undefined
}

function firstString(...vals: unknown[]): string {
  for (const v of vals) {
    if (typeof v === 'string' && v.trim()) return v.trim()
  }
  return ''
}

/**
 * Target route for a notification row (`null` = hide "Open").
 * Payload text is enough for context; a link is optional when there is no clear target.
 */
export function resolveNotificationOpenPath(
  item: NotificationItem,
  opts: { canInboxDeepLink: boolean },
): string | null {
  const { canInboxDeepLink } = opts
  const eventType = String(item.event_type || '').toLowerCase()
  const uos = getNotificationUosGroup(item)
  const payload = (item.payload || {}) as Record<string, any>
  const threadId = notificationThreadId(item)
  const threadCh = notificationThreadChannel(item)

  const deep = payload.href ?? payload.url ?? payload.deep_link
  if (typeof deep === 'string' && deep.startsWith('/')) return deep

  const entityType = String(item.entity_type || '').toLowerCase()
  const entityId = firstString(item.entity_id)
  /** Payload `thread_id` or DB `entity_id` when row is tied to a communication thread. */
  const effectiveThreadId =
    threadId || (entityType === 'communication_thread' ? entityId : '')

  if (eventType === 'handoff_requested' || eventType === 'handoff_accepted') {
    const cid = firstString(payload.candidate_id, entityType === 'candidate' ? entityId : '')
    if (cid) return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(cid)}`
    return CRM_APP_PATHS.candidates
  }

  if (eventType === 'handoff_rejected' || eventType === 'handoff_returned') {
    const cid = firstString(payload.candidate_id, entityType === 'candidate' ? entityId : '')
    if (cid) return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(cid)}`
    return CRM_APP_PATHS.candidates
  }

  if (eventType === 'lead_stuck_stage') {
    const leadId = firstString(payload.lead_id, entityType === 'lead' ? entityId : '')
    if (leadId) return `${CRM_APP_PATHS.leads}/${encodeURIComponent(leadId)}`
    return CRM_APP_DRILLDOWN_HREFS.leadsProcessedStuck
  }

  if (eventType === 'lead_no_next_action') {
    const leadId = firstString(payload.lead_id, entityType === 'lead' ? entityId : '')
    if (leadId) return `${CRM_APP_PATHS.leads}/${encodeURIComponent(leadId)}`
    return CRM_APP_DRILLDOWN_HREFS.leadsProcessedNoNextAction
  }

  if (eventType === 'invoice_overdue') {
    const iid = firstString(payload.invoice_id, entityType === 'invoice' ? entityId : '')
    if (iid) return `${CRM_APP_PATHS.invoices}/${encodeURIComponent(iid)}`
    return CRM_APP_DRILLDOWN_HREFS.invoicesOverdueUnpaid
  }

  /** Communications SLA / manual escalation — open the thread (entity_id is always set server-side). */
  if (eventType === 'communications_sla_overdue' || eventType === 'communications_thread_escalated') {
    if (effectiveThreadId) {
      if (canInboxDeepLink) {
        return buildInboxThreadPath(effectiveThreadId, threadCh ? { channel: threadCh } : undefined)
      }
      return communicationsThreadPath(effectiveThreadId)
    }
    return CRM_APP_PATHS.slaIncidents
  }

  if (eventType === 'lead.needs_routing') {
    const leadId = firstString(payload.lead_id, entityType === 'lead' ? entityId : '')
    if (leadId) return `${CRM_APP_PATHS.leads}/${encodeURIComponent(leadId)}`
    return CRM_APP_DRILLDOWN_HREFS.leadsNeedsRouting
  }

  if (eventType === 'lead.failed') {
    const leadId = firstString(payload.lead_id, entityType === 'lead' ? entityId : '')
    if (leadId) return `${CRM_APP_PATHS.leads}/${encodeURIComponent(leadId)}`
    return CRM_APP_DRILLDOWN_HREFS.leadsFailed
  }

  if (eventType === 'lead.import.completed' || eventType === 'lead.import.failed') {
    return CRM_APP_PATHS.settingsIntegrationsMeta
  }

  if (
    eventType === 'candidate_docs_pending_upload' ||
    eventType === 'candidate_ready_for_handoff_auto' ||
    eventType === 'candidate.intake_submitted' ||
    eventType === 'candidate.created' ||
    eventType === 'candidate_field_overridden'
  ) {
    const cid = firstString(payload.candidate_id, entityType === 'candidate' ? entityId : '')
    if (cid) return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(cid)}`
    return CRM_APP_PATHS.candidates
  }

  if (eventType === 'document.expiry') {
    const cid = firstString(payload.candidate_id, entityType === 'candidate' ? entityId : '')
    if (cid) return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(cid)}/documents`
    return CRM_APP_PATHS.documents
  }

  if (uos === 'messages') {
    if (effectiveThreadId) {
      if (canInboxDeepLink) {
        return buildInboxThreadPath(effectiveThreadId, threadCh ? { channel: threadCh } : undefined)
      }
      return communicationsThreadPath(effectiveThreadId)
    }
    if (canInboxDeepLink) return CRM_APP_PATHS.inboxMessagesScoped
    return CRM_APP_PATHS.inbox
  }

  if (uos === 'tasks') {
    const reminderId = payload?.reminder_id ?? payload?.task_id
    if (reminderId) return `${CRM_APP_PATHS.tasks}?focus=${encodeURIComponent(String(reminderId))}`
    return CRM_APP_PATHS.tasks
  }

  if (entityType === 'lead' && entityId) {
    return `${CRM_APP_PATHS.leads}/${encodeURIComponent(entityId)}`
  }
  if (entityType === 'candidate' && entityId) {
    return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(entityId)}`
  }
  if (entityType === 'invoice' && entityId) {
    return `${CRM_APP_PATHS.invoices}/${encodeURIComponent(entityId)}`
  }
  if (entityType === 'vacancy' && entityId) {
    return `${CRM_APP_PATHS.vacancies}/${encodeURIComponent(entityId)}`
  }
  if (entityType === 'company' && entityId) {
    return `${CRM_APP_PATHS.agencyClients}/${encodeURIComponent(entityId)}`
  }
  if (entityType === 'communication_thread' && entityId) {
    if (canInboxDeepLink) {
      return buildInboxThreadPath(entityId, threadCh ? { channel: threadCh } : undefined)
    }
    return communicationsThreadPath(entityId)
  }
  if (entityType === 'document' || entityType === 'document_step') {
    return CRM_APP_PATHS.documents
  }

  const leadId = firstString(payload.lead_id)
  if (leadId && eventType.startsWith('lead')) {
    return `${CRM_APP_PATHS.leads}/${encodeURIComponent(leadId)}`
  }

  return null
}
