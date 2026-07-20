import type { Lead } from '../api/types'
import type { SearchRole } from './launchSearchRoleDefaults'
import { metaLeadServiceInquiryCode } from './metaLeadB2b'

export type SalesInquiryTab = 'all' | 'new' | 'in_progress' | 'waiting' | 'completed'

const SERVICE_LABELS: Record<string, string> = {
  targeting_ads: 'Таргетинг',
  recruitment: 'Подбор персонала',
  outsourcing: 'Аутсорсинг',
  legalization: 'Легализация',
  fleet: 'Fleet',
}

const SOURCE_LABELS: Record<string, string> = {
  meta: 'Meta Ads',
  google: 'Google Ads',
  website: 'Сайт',
  linkedin: 'LinkedIn',
  referral: 'Рекомендация',
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
    'Компания'
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
  return parts.join(' ') || 'Запрос на подбор'
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
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

/** Relative time for inquiry lists ("10 минут назад", "1 час назад"). */
export function formatInquiryRelativeTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  const diffMs = Date.now() - date.getTime()
  const mins = Math.floor(diffMs / 60_000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин. назад`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} ч. назад`
  const days = Math.floor(hours / 24)
  if (days === 1) return 'вчера'
  if (days < 7) return `${days} дн. назад`
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

export function inquirySourceLabel(lead: Lead): string {
  const src = (lead.source || '').trim().toLowerCase()
  return SOURCE_LABELS[src] || (lead.source ? String(lead.source) : 'Неизвестно')
}

export function inquiryServiceLabel(lead: Lead): string | null {
  const code = metaLeadServiceInquiryCode(lead)
  if (code) return SERVICE_LABELS[code] || code
  const normalized = record(lead.normalized)
  const need = record(normalized.need)
  const raw = text(need.what_needed).toLowerCase()
  if (raw.includes('таргет') || raw.includes('target')) return 'Таргетинг'
  if (raw.includes('подбор') || raw.includes('водител') || raw.includes('driver')) return 'Подбор персонала'
  if (raw.includes('аутсорс')) return 'Аутсорсинг'
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

/** Workflow step index 1–5 for the sales stepper (Связаться → … → Заказ). */
export function salesInquiryWorkflowStep(lead: Lead): number {
  if (lead.converted_client_id) return 4
  const stage = (lead.stage || '').trim().toLowerCase()
  if (stage === 'qualified') return 3
  if (stage === 'questionnaire_submitted') return 1
  if (stage === 'waiting_for_response') return 2
  if (stage === 'contacted') return 2
  return 1
}

export function inquiryRequestTitle(lead: Lead): string {
  const service = inquiryServiceLabel(lead)
  if (service) return `Запрос на ${service.toLowerCase()}`
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
