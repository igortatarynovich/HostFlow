import type { NotificationItem } from '../api/types'
import type { TranslateFn } from '../i18n'

function humanizeEventType(eventType: string): string {
  return eventType
    .trim()
    .toLowerCase()
    .replace(/[._]+/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase())
}

function payloadScalar(payload: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = payload[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
    if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  }
  return ''
}

function payloadPersonName(payload: Record<string, unknown>): string {
  const explicit = payloadScalar(payload, [
    'candidate_name',
    'contact_name',
    'company_name',
    'outcome_entity_name',
  ])
  if (explicit) return explicit
  const first = payloadScalar(payload, ['first_name'])
  const last = payloadScalar(payload, ['last_name'])
  return `${first} ${last}`.trim()
}

function payloadInterpolateValues(payload: Record<string, unknown>): Record<string, string | number> {
  return {
    name: payloadPersonName(payload) || '—',
    source: payloadScalar(payload, ['source']) || '—',
    company: payloadScalar(payload, ['company_name']) || '—',
    filename: payloadScalar(payload, ['filename']) || '—',
    success: payloadScalar(payload, ['success_rows', 'success']) || '—',
    total: payloadScalar(payload, ['total_rows', 'total']) || '—',
    from_stage: payloadScalar(payload, ['from_stage']) || '—',
    to_stage: payloadScalar(payload, ['to_stage', 'stage']) || '—',
    document_name: payloadScalar(payload, ['document_name', 'document_type']) || '—',
    error: payloadScalar(payload, ['error']) || '—',
  }
}

function maybeTranslateKey(
  t: TranslateFn,
  value: string,
  values?: Record<string, string | number>,
): string {
  const v = String(value || '').trim()
  if (!v) return ''
  if (/^(app|common)\./.test(v)) {
    const localized = t(v, { defaultValue: '', values })
    if (localized && localized !== v) return localized
  }
  return v
}

function eventTypeLookupKeys(eventType: string): string[] {
  const trimmed = eventType.trim()
  if (!trimmed) return []
  const lower = trimmed.toLowerCase()
  const underscored = lower.replace(/\./g, '_')
  const keys = [lower, trimmed, underscored]
  return [...new Set(keys.filter(Boolean))]
}

function lookupEventTypeLabel(t: TranslateFn, eventType: string): string {
  if (!eventType) return ''
  for (const variant of eventTypeLookupKeys(eventType)) {
    const typeKey = `app.notifications.event_types.${variant}`
    const fromTypes = t(typeKey, { defaultValue: '' })
    if (fromTypes && fromTypes !== typeKey) return fromTypes
    const eventKey = `app.reminders.events.${variant}`
    const fromEvents = t(eventKey, { defaultValue: '' })
    if (fromEvents && fromEvents !== eventKey) return fromEvents
  }
  return ''
}

function lookupEventTypeDescription(t: TranslateFn, eventType: string): string {
  if (!eventType) return ''
  for (const variant of eventTypeLookupKeys(eventType)) {
    const descKey = `app.notifications.event_types.${variant}_desc`
    const fromTypes = t(descKey, { defaultValue: '' })
    if (fromTypes && fromTypes !== descKey) return fromTypes
  }
  return ''
}

export function notificationEventTypeLabel(eventType: string, t: TranslateFn): string {
  const et = String(eventType || '').trim()
  return (
    lookupEventTypeLabel(t, et.toLowerCase()) ||
    lookupEventTypeLabel(t, et) ||
    t('app.notifications.unknown_event', { defaultValue: humanizeEventType(et || 'notification') })
  )
}

export function notificationDisplayTitle(item: NotificationItem, t: TranslateFn): string {
  const eventType = String(item.event_type || '').trim().toLowerCase()
  const isReminder = eventType === 'reminder_due' || eventType === 'reminder_overdue'
  if (eventType === 'handoff_requested') {
    return t('app.notifications.handoff_requested_title')
  }
  if (eventType === 'handoff_accepted') {
    return t('app.notifications.handoff_accepted_title')
  }
  if (eventType === 'communications_sla_overdue') {
    return t('app.notifications.communications_sla_overdue_title')
  }
  if (eventType === 'communications_thread_escalated') {
    return t('app.notifications.communications_thread_escalated_title')
  }
  if (eventType === 'lead_public_intake_client') {
    return t('app.notifications.lead_public_intake_client_title')
  }
  if (eventType === 'intake_client_lead_skipped_no_company') {
    return t('app.notifications.intake_client_lead_skipped_no_company_title')
  }
  if (eventType === 'intake.questionnaire.submitted') {
    return t('app.notifications.intake_questionnaire_submitted_title', {
      defaultValue: 'Клиент заполнил анкету',
    })
  }
  if (!isReminder) {
    const localized = lookupEventTypeLabel(t, eventType)
    if (localized) return localized
  }
  if (typeof item.payload?.title === 'string' && item.payload.title.trim()) {
    return maybeTranslateKey(t, item.payload.title)
  }
  const localized = lookupEventTypeLabel(t, eventType)
  if (localized) return localized
  return t('app.notifications.unknown_event', {
    defaultValue: humanizeEventType(eventType || 'notification'),
  })
}

export function notificationDisplayDescription(item: NotificationItem, t: TranslateFn): string {
  const payload = (item.payload || {}) as Record<string, unknown>
  const eventType = String(item.event_type || '').trim().toLowerCase()
  const values = payloadInterpolateValues(payload)
  if (eventType === 'candidate_docs_pending_upload') {
    const name = String(payload.candidate_name || '').trim()
    const hasStructured =
      Boolean(name) || payload.ready != null || payload.total != null || payload.missing != null
    if (hasStructured) {
      return t('app.notifications.event_types.candidate_docs_pending_upload_desc', {
        values: {
          name: name || '—',
          ready: (payload.ready as string | number | undefined) ?? (payload.ready_count as string | number | undefined) ?? '—',
          total: (payload.total as string | number | undefined) ?? (payload.total_count as string | number | undefined) ?? '—',
          missing:
            (payload.missing as string | number | undefined) ??
            (payload.missing_count as string | number | undefined) ??
            '—',
        },
      })
    }
  }
  if (eventType === 'lead_public_intake_client') {
    return t('app.notifications.lead_public_intake_client_desc', {
      values: { name: String(payload.candidate_name || '').trim() || '—' },
    })
  }
  if (eventType === 'intake_client_lead_skipped_no_company') {
    return t('app.notifications.intake_client_lead_skipped_no_company_desc', {
      values: { name: String(payload.candidate_name || '').trim() || '—' },
    })
  }
  if (eventType === 'intake.questionnaire.submitted') {
    const line = String(payload.description || payload.body || '').trim()
    if (line && !/^(app|common)\./.test(line)) return line
    const contact = String(payload.contact_name || '').trim() || '—'
    const company = String(payload.company_name || '').trim() || '—'
    return t('app.notifications.intake_questionnaire_submitted_desc', {
      defaultValue: '{contact} — {company}',
      values: { contact, company },
    })
  }
  const templated = lookupEventTypeDescription(t, eventType)
  if (templated) {
    const name = payloadPersonName(payload)
    if (templated.includes('{name}') && !name) {
      return ''
    }
    return t(`app.notifications.event_types.${eventType}_desc`, {
      defaultValue: templated,
      values,
    })
  }
  const raw = String(payload.description || payload.body || '').trim()
  if (!raw) return ''
  return maybeTranslateKey(t, raw, values)
}
