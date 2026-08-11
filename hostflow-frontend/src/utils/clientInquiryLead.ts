import type { Lead } from '../api/types'
import { detectStoredLocale, lookupScopedTranslation, type LocaleCode } from '../i18n'
import type { SearchRole } from './launchSearchRoleDefaults'
import { metaLeadServiceInquiryCode } from './metaLeadB2b'

export type SalesInquiryTab = 'all' | 'new' | 'in_progress' | 'waiting' | 'completed'

const SERVICE_CODES = ['targeting_ads', 'recruitment', 'outsourcing', 'legalization', 'fleet'] as const
const SERVICE_FALLBACKS: Record<(typeof SERVICE_CODES)[number], string> = {
  targeting_ads: 'Targeting ads',
  recruitment: 'Staff recruitment',
  outsourcing: 'Outsourcing',
  legalization: 'Legalization',
  fleet: 'Fleet',
}

function scoped(
  basePath: string,
  leaf: string,
  fallback: string,
  values?: Record<string, string | number>,
  locale: LocaleCode = detectStoredLocale(),
): string {
  let template = lookupScopedTranslation(locale, basePath, leaf) || fallback
  if (values) {
    for (const [key, value] of Object.entries(values)) {
      template = template.split(`{${key}}`).join(String(value))
    }
  }
  return template
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

export function leadSourceProfileId(lead: Lead): string | null {
  const normalized = record(lead.normalized)
  const meta = record(normalized.meta)
  const sourceProfile = record(meta.source_profile)
  const id = text(sourceProfile.id)
  return id || null
}

export function inquiryCompanyName(lead: Lead): string {
  const normalized = record(lead.normalized)
  const company = record(normalized.company_profile)
  const payload = record(lead.payload)
  const payloadCompany = record(payload.company)
  return (
    text(company.name) ||
    text(normalized.company_name) ||
    text(normalized.company_name_hint) ||
    text(payloadCompany.name) ||
    text(lead.company_name) ||
    scoped('app.client_inquiry', 'company_fallback', 'Company')
  )
}

export function inquiryNeedSummary(lead: Lead): string {
  const normalized = record(lead.normalized)
  const need = record(normalized.need)
  const payload = record(lead.payload)
  const payloadNeed = record(payload.need)
  const summary = text(need.summary)
  if (summary) return summary
  const parts = [
    text(need.people_count) || text(payloadNeed.people_count),
    text(need.what_needed) || text(payloadNeed.what_needed),
  ].filter(Boolean)
  return parts.join(' ') || scoped('app.client_inquiry', 'need_fallback', 'Recruitment request')
}

export function inquiryContactPhone(lead: Lead): string | null {
  const normalized = record(lead.normalized)
  const contact = record(normalized.contact_person)
  const payload = record(lead.payload)
  const payloadContact = record(payload.contact)
  // Meta inquiries store the contact flat on `normalized` (phone/email/full_name),
  // not under `contact_person`. Fall back so the phone is never lost.
  const phone = text(contact.phone) || text(payloadContact.phone) || text(normalized.phone) || text(payload.phone)
  return phone || null
}

export function inquiryContactEmail(lead: Lead): string | null {
  const normalized = record(lead.normalized)
  const contact = record(normalized.contact_person)
  const payload = record(lead.payload)
  const payloadContact = record(payload.contact)
  const email = text(contact.email) || text(payloadContact.email) || text(normalized.email) || text(payload.email)
  return email || null
}

export function inquiryContactName(lead: Lead): string | null {
  const normalized = record(lead.normalized)
  const contact = record(normalized.contact_person)
  const payload = record(lead.payload)
  const payloadContact = record(payload.contact)
  const flatName =
    text(normalized.full_name) ||
    [text(normalized.first_name), text(normalized.last_name)].filter(Boolean).join(' ')
  const name = text(contact.full_name) || text(payloadContact.full_name) || flatName
  return name || null
}

export function formatInquiryTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  const locale = detectStoredLocale()
  return date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })
}

/** Relative time for inquiry lists. */
export function formatInquiryRelativeTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  const locale = detectStoredLocale()
  const diffMs = Date.now() - date.getTime()
  const mins = Math.floor(diffMs / 60_000)
  if (mins < 1) {
    return scoped('app.application_workspace.relative_time', 'just_now', 'just now', undefined, locale)
  }
  if (mins < 60) {
    return scoped(
      'app.application_workspace.relative_time',
      'minutes_ago',
      '{n} min ago',
      { n: mins },
      locale,
    )
  }
  const hours = Math.floor(mins / 60)
  if (hours < 24) {
    return scoped(
      'app.application_workspace.relative_time',
      'hours_ago',
      '{n} h ago',
      { n: hours },
      locale,
    )
  }
  const days = Math.floor(hours / 24)
  if (days === 1) {
    return scoped('app.application_workspace.relative_time', 'yesterday', 'yesterday', undefined, locale)
  }
  if (days < 7) {
    return scoped(
      'app.application_workspace.relative_time',
      'days_ago',
      '{n} d ago',
      { n: days },
      locale,
    )
  }
  return date.toLocaleDateString(locale, { day: 'numeric', month: 'short' })
}

export function inquirySourceLabel(lead: Lead): string {
  const src = (lead.source || '').trim().toLowerCase()
  if (src === 'meta') return 'Meta Ads'
  if (src === 'google') return 'Google Ads'
  if (src === 'linkedin') return 'LinkedIn'
  if (src === 'website') {
    return scoped('app.client_inquiry.source', 'website', 'Website')
  }
  if (src === 'referral') {
    return scoped('app.client_inquiry.source', 'referral', 'Referral')
  }
  return lead.source
    ? String(lead.source)
    : scoped('app.client_inquiry.source', 'unknown', 'Unknown')
}

export function inquiryServiceLabel(lead: Lead): string | null {
  const code = metaLeadServiceInquiryCode(lead)
  if (code && (SERVICE_CODES as readonly string[]).includes(code)) {
    return scoped(
      'app.client_inquiry.service',
      code,
      SERVICE_FALLBACKS[code as (typeof SERVICE_CODES)[number]],
    )
  }
  if (code) return code
  const normalized = record(lead.normalized)
  const need = record(normalized.need)
  const raw = text(need.what_needed).toLowerCase()
  // Content matchers for free-text need descriptions (not UI labels).
  if (raw.includes('таргет') || raw.includes('target')) {
    return scoped('app.client_inquiry.service', 'targeting_ads', 'Targeting ads')
  }
  if (raw.includes('подбор') || raw.includes('водител') || raw.includes('driver')) {
    return scoped('app.client_inquiry.service', 'recruitment', 'Staff recruitment')
  }
  if (raw.includes('аутсорс')) {
    return scoped('app.client_inquiry.service', 'outsourcing', 'Outsourcing')
  }
  return null
}

export type SalesInquiryStatusKey = 'new' | 'in_progress' | 'waiting' | 'completed' | 'questionnaire_submitted'

export function inquiryStatusKey(lead: Lead): SalesInquiryStatusKey {
  if (lead.converted_client_id || lead.stage === 'converted' || lead.stage === 'lost') return 'completed'
  const normalized = record(lead.normalized)
  const qStatus = text(normalized.sales_questionnaire_status).toLowerCase()
  const stage = (lead.stage || '').trim().toLowerCase()
  if (stage === 'questionnaire_submitted' || qStatus === 'submitted') return 'questionnaire_submitted'
  if (stage === 'waiting_for_response' || qStatus === 'sent' || qStatus === 'opened' || qStatus === 'in_progress') {
    return 'waiting'
  }
  if (!stage || stage === 'new') return 'new'
  if (stage === 'qualified') return 'waiting'
  return 'in_progress'
}

export function inquiryStatusLabelKey(lead: Lead): SalesInquiryStatusKey {
  return inquiryStatusKey(lead)
}

export function inquiryTabBucket(lead: Lead): SalesInquiryTab {
  return inquiryStatusKey(lead)
}

/** Workflow step index 1–5 for the sales stepper. */
export function salesInquiryWorkflowStep(lead: Lead): number {
  if (lead.converted_client_id) return 4
  const stage = (lead.stage || '').trim().toLowerCase()
  if (stage === 'qualified') return 3
  if (stage === 'waiting_for_response' || stage === 'questionnaire_submitted') return 3
  if (stage === 'contacted') return 2
  return 1
}

export function inquiryRequestTitle(lead: Lead): string {
  const service = inquiryServiceLabel(lead)
  if (service) {
    return scoped('app.client_inquiry', 'request_for', 'Request for {service}', {
      service: service.toLowerCase(),
    })
  }
  return inquiryNeedSummary(lead)
}

export function isOpenClientInquiry(lead: Lead): boolean {
  if (lead.lead_target_type && lead.lead_target_type !== 'client_lead') return false
  if (lead.converted_client_id) return false
  if (lead.stage === 'converted' || lead.stage === 'lost') return false
  return true
}

export function inferSearchRoleFromInquiry(lead: Lead): SearchRole {
  const normalized = record(lead.normalized)
  const need = record(normalized.need)
  const payload = record(lead.payload)
  const payloadNeed = record(payload.need)
  const raw = `${text(need.what_needed)} ${text(payloadNeed.what_needed)}`.toLowerCase()
  // Content matchers for free-text need descriptions (not UI labels).
  if (raw.includes('склад') || raw.includes('warehouse')) return 'warehouse'
  if (raw.includes('офис') || raw.includes('office')) return 'office'
  if (raw.includes('водител') || raw.includes('driver') || raw.includes(' ce')) return 'driver'
  return 'driver'
}

export function isInquiryFromToday(iso: string | null | undefined): boolean {
  if (!iso) return false
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return false
  const now = new Date()
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  )
}
