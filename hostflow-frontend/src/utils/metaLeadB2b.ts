import type { Lead } from '../api/types'
import type { LeadTargetType } from '../api/types/lead'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { detectStoredLocale, lookupScopedTranslation } from '../i18n'

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

function formFallbackLabel(formId: string): string {
  const template =
    lookupScopedTranslation(detectStoredLocale(), 'app.meta', 'form_fallback') || 'form {formId}'
  return template.split('{formId}').join(formId)
}

export function metaLeadNormalized(lead: Lead): Record<string, unknown> {
  return record(lead.normalized)
}

export function metaLeadFormId(lead: Lead): string | null {
  const normalized = metaLeadNormalized(lead)
  const fromNorm = text(normalized.form_id)
  if (fromNorm) return fromNorm
  const route = record(normalized.intake_route_v1)
  const fromRoute = text(route.form_id)
  return fromRoute || null
}

export function metaLeadPageId(lead: Lead): string | null {
  const normalized = metaLeadNormalized(lead)
  const fromNorm = text(normalized.page_id)
  if (fromNorm) return fromNorm
  const route = record(normalized.intake_route_v1)
  return text(route.page_id) || null
}

/** Own company resolved at ingest (needed to persist a form route inline). */
export function metaLeadOwnCompanyId(lead: Lead): string | null {
  const normalized = metaLeadNormalized(lead)
  const routeV1 = record(normalized.intake_route_v1)
  const fromRoute = text(routeV1.own_company_id)
  if (fromRoute) return fromRoute
  const routingV1 = record(normalized.intake_routing_v1)
  return text(routingV1.own_company_id) || null
}

/** Service preselected by a Service Inquiry form route (stamped at ingest). */
export function metaLeadServiceInquiryCode(lead: Lead): string | null {
  const normalized = metaLeadNormalized(lead)
  const block = record(normalized.service_inquiry_v1)
  return text(block.service_code) || null
}

export function metaLeadErrorCode(lead: Lead): string {
  return text(lead.error).split(/\s+/)[0] ?? ''
}

export function isMetaAdNotMappedLead(lead: Lead): boolean {
  const src = text(lead.source).toLowerCase()
  if (src !== 'meta' && src !== 'csv_import') return false
  if (lead.status !== 'needs_routing' && lead.status !== 'failed') return false
  const code = metaLeadErrorCode(lead)
  return code === 'AD_NOT_MAPPED' || code === 'VACANCY_NOT_RESOLVED'
}

export function isMetaB2bCandidateLead(lead: Lead): boolean {
  return lead.lead_type === 'client' && lead.lead_target_type === 'client_lead'
}

export function metaFormSelectionKey(formId: string, pageId?: string | null, source = 'meta'): string {
  return `${source}:${formId}:${pageId ?? ''}`
}

/** Deep-link to Meta field mapping + intake route for a form. */
export function metaIntakeRouteSettingsHref(formId?: string | null, pageId?: string | null): string {
  const base = `${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=field_mapping`
  if (!formId) return base
  const params = new URLSearchParams()
  params.set('tab', 'field_mapping')
  params.set('meta_form_id', formId)
  if (pageId) params.set('meta_page_id', pageId)
  return `${CRM_APP_PATHS.settingsIntegrationsMeta}?${params.toString()}`
}

export function intakeRouteTypeLabel(
  target: LeadTargetType | null | undefined,
  t: (key: string, opts?: { defaultValue?: string }) => string,
): string {
  if (target === 'client_lead') {
    return t('admin.meta_leads.intake_route.route_label.companies', { defaultValue: 'Компании (B2B)' })
  }
  if (target === 'candidate') {
    return t('admin.meta_leads.intake_route.route_label.candidates', { defaultValue: 'Кандидаты' })
  }
  if (target === 'service_order_lead') {
    return t('admin.meta_leads.intake_route.route_label.service', { defaultValue: 'Service order' })
  }
  if (target === 'partner_lead') {
    return t('admin.meta_leads.intake_route.route_label.partner', { defaultValue: 'Partner' })
  }
  return t('admin.meta_leads.intake_route.route_label.unset', { defaultValue: 'Маршрут не задан' })
}

export type InquiryMetaAttribution = {
  line: string
  formLabel: string | null
  campaignLabel: string | null
  adLabel: string | null
}

/** Sales workspace: Meta Lead Ads · form · campaign/ad */
export function inquiryMetaAttribution(lead: Lead): InquiryMetaAttribution | null {
  const normalized = metaLeadNormalized(lead)
  const meta = record(normalized.meta)
  const sourceProfile = record(meta.source_profile)
  const marketing = record(normalized.marketing)
  const utm = record(normalized.utm)
  const payload = record(lead.payload)

  const formId = metaLeadFormId(lead)
  const formName =
    text(sourceProfile.name) ||
    text(marketing.form_name) ||
    text(normalized.form_name) ||
    (formId ? formFallbackLabel(formId) : '')

  const campaignName =
    text(marketing.campaign_name) ||
    text(marketing.campaign) ||
    text(utm.campaign) ||
    text(utm.utm_campaign) ||
    text(payload.campaign_name)

  const adId = lead.ad_id ?? normalized.ad_id
  const adName = text(marketing.ad_name) || text(marketing.ad)
  const adLabel = adName || (adId != null && String(adId).trim() ? `ad ${adId}` : '')

  const src = text(lead.source).toLowerCase()
  const isMeta = src === 'meta' || text(sourceProfile.provider).toLowerCase() === 'meta'
  if (!isMeta && !formName && !campaignName && !adLabel) return null

  const parts = ['Meta Lead Ads']
  if (formName) parts.push(formName)
  if (campaignName) parts.push(campaignName)
  else if (adLabel) parts.push(adLabel)

  return {
    line: parts.join(' · '),
    formLabel: formName || null,
    campaignLabel: campaignName || null,
    adLabel: adLabel || null,
  }
}
