import type { Lead } from '../api/types'
import { clientAcquisitionInquiryPath } from '../app/clientAcquisitionPaths'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { settingsLeadFormDetailPath } from '../app/crmAppPaths'
import { leadSourceProfileId } from './clientInquiryLead'
import { readLatestSubmission } from './salesQuestionnaireSubmission'

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

export function inquiryRequiresReview(lead: Lead): boolean {
  const normalized = record(lead.normalized)
  return normalized.intake_review_required === true
}

export function inquiryReviewMessage(lead: Lead): string {
  const normalized = record(lead.normalized)
  return (
    text(normalized.intake_review_message) ||
    'Не удалось однозначно определить существующую заявку. Создана новая заявка, требующая проверки.'
  )
}

export function inquiryWorkPath(lead: Lead): string {
  const channelId = leadSourceProfileId(lead)
  if (channelId) return clientAcquisitionInquiryPath(channelId, lead.id)
  return `${CRM_APP_PATHS.leads}/${lead.id}`
}

export function inquiryQuestionnaireFormId(lead: Lead): string | null {
  const submission = readLatestSubmission(lead)
  const fromSubmission = text(submission?.form_id)
  if (fromSubmission) return fromSubmission
  const normalized = record(lead.normalized)
  const meta = record(normalized.meta)
  return text(meta.questionnaire_form_id) || null
}

export function inquiryQuestionnaireFormPath(lead: Lead): string | null {
  const formId = inquiryQuestionnaireFormId(lead)
  return formId ? settingsLeadFormDetailPath(formId) : null
}

export function clientCompanyPath(clientId: string): string {
  return `${CRM_APP_PATHS.agencyClients}/${encodeURIComponent(clientId)}`
}

export function clientOriginInquiryPath(extra: Record<string, unknown> | null | undefined): string | null {
  const data = record(extra)
  const leadId = text(data.source_lead_id)
  if (!leadId) return null
  const channelId = text(data.source_channel_id)
  if (channelId) return clientAcquisitionInquiryPath(channelId, leadId)
  return `${CRM_APP_PATHS.leads}/${leadId}`
}

export function clientOriginQuestionnaireFormPath(extra: Record<string, unknown> | null | undefined): string | null {
  const data = record(extra)
  const formId = text(data.source_form_id)
  return formId ? settingsLeadFormDetailPath(formId) : null
}
