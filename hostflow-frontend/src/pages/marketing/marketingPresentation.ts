import type { AcquisitionActivityEvent } from '../../api/acquisitionActivity'
import type { Campaign, CampaignFlight } from '../../api/platformCampaigns'

export type MarketingFlowKind = 'candidates' | 'clients' | 'service'

export type FlowPreset = {
  kind: MarketingFlowKind
  label: string
  description: string
  goal_type: string
  primary_kpi: string
  target_type: string
  route_intent: string
  destinationLabel: string
}

export const FLOW_PRESETS: FlowPreset[] = [
  {
    kind: 'candidates',
    label: 'Кандидаты',
    description: 'Клиент → вакансия → заявки в Recruitment',
    goal_type: 'hiring',
    primary_kpi: 'applications',
    target_type: 'vacancy',
    route_intent: 'candidate_application',
    destinationLabel: 'Вакансия',
  },
  {
    kind: 'clients',
    label: 'B2B / клиенты',
    description: 'Клиент → услуга (таргетинг и др.) → Sales inquiry',
    goal_type: 'sales',
    primary_kpi: 'qualified_leads',
    target_type: 'service',
    route_intent: 'sales_inquiry',
    destinationLabel: 'Услуга',
  },
  {
    kind: 'service',
    label: 'Заявки на услугу',
    description: 'Клиент → услуга каталога → Service flow',
    goal_type: 'sales',
    primary_kpi: 'revenue',
    target_type: 'service',
    route_intent: 'service_request',
    destinationLabel: 'Услуга',
  },
]

export type MarketingSourceKind = 'public_form' | 'meta'

export function statusLabel(status: string): string {
  const s = String(status || '').toLowerCase()
  const map: Record<string, string> = {
    draft: 'Черновик',
    active: 'Активна',
    paused: 'На паузе',
    completed: 'Завершена',
    archived: 'Архив',
    planned: 'Запланирован',
    failed: 'Ошибка',
  }
  return map[s] || status || '—'
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

export function destinationSummary(campaign: Campaign): string {
  const t = campaign.targets?.[0]
  if (!t) return 'Не задано'
  const labels: Record<string, string> = {
    vacancy: 'Вакансия',
    service: 'Услуга',
    search: 'Поиск',
    client_account: 'Клиент',
  }
  const intentLabels: Record<string, string> = {
    candidate_application: 'кандидаты',
    sales_inquiry: 'sales inquiry',
    service_request: 'услуга',
  }
  const typeLabel = labels[t.target_type] || t.target_type
  const intent = intentLabels[t.route_intent]
  return intent ? `${typeLabel} · ${intent}` : typeLabel
}

export function launchedAt(flight: CampaignFlight | null): string | null {
  return flight?.starts_at || null
}
