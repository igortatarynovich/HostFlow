import type { AcquisitionActivityEvent } from '../../api/acquisitionActivity'
import type { Campaign, CampaignFlight } from '../../api/platformCampaigns'
import type { TranslateFn } from '../../i18n'

export type MarketingFlowKind = 'candidates' | 'clients' | 'service'

export type FlowPreset = {
  kind: MarketingFlowKind
  labelKey: string
  descriptionKey: string
  goal_type: string
  primary_kpi: string
  target_type: string
  route_intent: string
  destinationKey: string
  /** @deprecated use labelKey + t(); kept for setup page fallbacks */
  label: string
  description: string
  destinationLabel: string
}

export const FLOW_PRESETS: FlowPreset[] = [
  {
    kind: 'candidates',
    labelKey: 'app.marketing.flows.candidates.label',
    descriptionKey: 'app.marketing.flows.candidates.description',
    destinationKey: 'app.marketing.flows.candidates.destination',
    label: 'Candidates',
    description: 'Client → vacancy → applications in Recruitment',
    goal_type: 'hiring',
    primary_kpi: 'applications',
    target_type: 'vacancy',
    route_intent: 'candidate_application',
    destinationLabel: 'Vacancy',
  },
  {
    kind: 'clients',
    labelKey: 'app.marketing.flows.clients.label',
    descriptionKey: 'app.marketing.flows.clients.description',
    destinationKey: 'app.marketing.flows.clients.destination',
    label: 'B2B / clients',
    description: 'Client → service (targeting, etc.) → Sales inquiry',
    goal_type: 'sales',
    primary_kpi: 'qualified_leads',
    target_type: 'service',
    route_intent: 'sales_inquiry',
    destinationLabel: 'Service',
  },
  {
    kind: 'service',
    labelKey: 'app.marketing.flows.service.label',
    descriptionKey: 'app.marketing.flows.service.description',
    destinationKey: 'app.marketing.flows.service.destination',
    label: 'Service requests',
    description: 'Client → catalog service → Service flow',
    goal_type: 'sales',
    primary_kpi: 'revenue',
    target_type: 'service',
    route_intent: 'service_request',
    destinationLabel: 'Service',
  },
]

export type MarketingSourceKind = 'public_form' | 'meta'

const STATUS_KEYS: Record<string, string> = {
  draft: 'app.marketing.status.draft',
  active: 'app.marketing.status.active',
  paused: 'app.marketing.status.paused',
  completed: 'app.marketing.status.completed',
  archived: 'app.marketing.status.archived',
  planned: 'app.marketing.status.planned',
  failed: 'app.marketing.status.failed',
}

const STATUS_FALLBACK_EN: Record<string, string> = {
  draft: 'Draft',
  active: 'Active',
  paused: 'Paused',
  completed: 'Completed',
  archived: 'Archived',
  planned: 'Planned',
  failed: 'Failed',
}

export function statusLabel(status: string, t?: TranslateFn): string {
  const s = String(status || '').toLowerCase()
  const key = STATUS_KEYS[s]
  if (key && t) {
    return t(key, { defaultValue: STATUS_FALLBACK_EN[s] || status || '—' })
  }
  return STATUS_FALLBACK_EN[s] || status || '—'
}

export function statusTone(status: string): string {
  const s = String(status || '').toLowerCase()
  if (s === 'active') return 'bg-emerald-50 text-emerald-800 ring-emerald-200'
  if (s === 'paused') return 'bg-amber-50 text-amber-800 ring-amber-200'
  if (s === 'draft' || s === 'planned') return 'bg-slate-100 text-slate-700 ring-slate-200'
  if (s === 'completed') return 'bg-sky-50 text-sky-800 ring-sky-200'
  return 'bg-slate-100 text-slate-600 ring-slate-200'
}

export function formPublicUrl(slug: string | null | undefined): string | null {
  const s = String(slug || '').trim()
  if (!s) return null
  const q = new URLSearchParams({ lead_form_slug: s })
  if (typeof window === 'undefined') return `/public/intake?${q.toString()}`
  return `${window.location.origin}/public/intake?${q.toString()}`
}

export type FlightFunnelCounts = {
  received: number
  routed: number
  routingFailed: number
  duplicates: number
}

export function countFlightFunnel(
  events: AcquisitionActivityEvent[],
  flightId?: string | null,
): FlightFunnelCounts {
  const fid = flightId ? String(flightId) : null
  const scoped = fid ? events.filter((e) => String(e.flight_id || '') === fid) : events
  let received = 0
  let routed = 0
  let routingFailed = 0
  let duplicates = 0
  for (const e of scoped) {
    if (e.event_type === 'SubmissionReceived') received += 1
    else if (e.event_type === 'RoutingCompleted') routed += 1
    else if (e.event_type === 'RoutingFailed') routingFailed += 1
    else if (e.event_type === 'DuplicateDetected') duplicates += 1
  }
  return { received, routed, routingFailed, duplicates }
}

export function recentSubmissionEvents(
  events: AcquisitionActivityEvent[],
  flightId?: string | null,
  limit = 10,
): AcquisitionActivityEvent[] {
  const fid = flightId ? String(flightId) : null
  return events
    .filter((e) => e.event_type === 'SubmissionReceived')
    .filter((e) => !fid || String(e.flight_id || '') === fid)
    .slice(0, limit)
}

export function primaryForm(flight: CampaignFlight | null): CampaignFlight['forms'][number] | null {
  if (!flight?.forms?.length) return null
  return flight.forms.find((f) => f.is_active && f.role === 'primary') || flight.forms[0] || null
}

export function primarySource(
  flight: CampaignFlight | null,
): CampaignFlight['intake_sources'][number] | null {
  if (!flight?.intake_sources?.length) return null
  return (
    flight.intake_sources.find((s) => s.is_active && s.role === 'primary') ||
    flight.intake_sources[0] ||
    null
  )
}

export function activePrimaryForm(
  flight: CampaignFlight | null,
): CampaignFlight['forms'][number] | null {
  if (!flight?.forms?.length) return null
  return flight.forms.find((f) => f.is_active && f.role === 'primary') || null
}

export function activePrimaryIntakeSource(
  flight: CampaignFlight | null,
): CampaignFlight['intake_sources'][number] | null {
  if (!flight?.intake_sources?.length) return null
  return flight.intake_sources.find((s) => s.is_active && s.role === 'primary') || null
}

/** PR1: only offer Connect when a primary slot of that endpoint type is free (no secondary UX). */
export function canConnectSourceKind(
  flight: CampaignFlight | null,
  kind: MarketingSourceKind,
): boolean {
  if (kind === 'public_form') return !activePrimaryForm(flight)
  return !activePrimaryIntakeSource(flight)
}

export function canConnectAnySource(flight: CampaignFlight | null): boolean {
  return canConnectSourceKind(flight, 'public_form') || canConnectSourceKind(flight, 'meta')
}

export function destinationSummary(campaign: Campaign, t?: TranslateFn): string {
  const target = campaign.targets?.[0]
  if (!target) {
    return t
      ? t('app.marketing.destination.unset', { defaultValue: 'Not set' })
      : 'Not set'
  }
  const typeKey =
    target.target_type === 'vacancy'
      ? 'vacancy'
      : target.target_type === 'service'
        ? 'service'
        : target.target_type === 'search'
          ? 'search'
          : target.target_type === 'client_account'
            ? 'client_account'
            : null
  const typeLabel = typeKey
    ? t
      ? t(`app.marketing.destination.${typeKey}`, {
          defaultValue:
            typeKey === 'vacancy'
              ? 'Vacancy'
              : typeKey === 'service'
                ? 'Service'
                : typeKey === 'search'
                  ? 'Search'
                  : 'Client',
        })
      : typeKey === 'vacancy'
        ? 'Vacancy'
        : typeKey === 'service'
          ? 'Service'
          : typeKey === 'search'
            ? 'Search'
            : 'Client'
    : target.target_type

  const intentKey =
    target.route_intent === 'candidate_application'
      ? 'intent_candidates'
      : target.route_intent === 'sales_inquiry'
        ? 'intent_sales_inquiry'
        : target.route_intent === 'service_request'
          ? 'intent_service_request'
          : null
  if (!intentKey) return typeLabel
  const intent = t
    ? t(`app.marketing.destination.${intentKey}`, {
        defaultValue:
          intentKey === 'intent_candidates'
            ? 'candidates'
            : intentKey === 'intent_sales_inquiry'
              ? 'sales inquiry'
              : 'service',
      })
    : intentKey === 'intent_candidates'
      ? 'candidates'
      : intentKey === 'intent_sales_inquiry'
        ? 'sales inquiry'
        : 'service'
  return `${typeLabel} · ${intent}`
}

export function launchedAt(flight: CampaignFlight | null): string | null {
  return flight?.starts_at || null
}
