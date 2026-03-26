import { api } from './client'

export type LeadDistributionTeamMember = {
  user_id: string
  display_name: string
  status: 'available' | 'busy' | 'offline'
  lead_load: number
  languages: string[]
  /** Tenant role; used with pipeline stage `owner_role` when auto-assigning leads (§2.3). */
  role?: string | null
  working_hours_configured?: boolean
  within_working_hours?: boolean
}

export type LeadDistributionNextPreview = {
  user_id: string
  display_name: string
  reason_codes: string[]
  subtitle: string
  detail_lines?: string[]
}

export type LeadDistributionAlert = {
  severity: string
  code: string
  message: string
}

export type LeadDistributionFeatureGate = {
  automatic_allowed: boolean
  advanced_rules_allowed: boolean
  load_balance_pro: boolean
  plan_code: string
}

export type LeadDistributionOut = {
  mode: 'automatic' | 'manual'
  strategy: 'smart' | 'round_robin' | 'manual_rules'
  criteria_order: string[]
  max_leads_per_person: number
  only_active_employees: boolean
  preview_language: string
  language_routing_v1?: Record<string, string[]>
  assignment_detail_lines?: string[]
  rules_summary_lines: string[]
  next_preview: LeadDistributionNextPreview | null
  team: LeadDistributionTeamMember[]
  flow_steps: string[]
  alerts: LeadDistributionAlert[]
  stats: { unassigned_processed_leads: number }
  feature_gate: LeadDistributionFeatureGate
}

export type LeadDistributionPatch = Partial<{
  mode: LeadDistributionOut['mode']
  strategy: LeadDistributionOut['strategy']
  criteria_order: string[]
  max_leads_per_person: number
  only_active_employees: boolean
  preview_language: string
  language_routing_v1: Record<string, string[]>
}>

export async function getLeadDistribution(): Promise<LeadDistributionOut> {
  const { data } = await api.get<LeadDistributionOut>('/leads/distribution')
  return data
}

export async function patchLeadDistribution(payload: LeadDistributionPatch): Promise<LeadDistributionOut> {
  const { data } = await api.patch<LeadDistributionOut>('/leads/distribution', payload)
  return data
}
