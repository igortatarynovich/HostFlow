/** ADR-033 Control Center API — lead lifecycle email policy. */

import { api } from './client'

export type LeadLifecycleOpsPurpose = {
  enabled: boolean
  template_ref?: string | null
}

export type LeadLifecycleEmailPolicy = {
  version: 1
  rodo_send_mode: 'manual' | 'auto_on_lead_created' | 'auto_on_first_action'
  rodo_template_ref?: string | null
  ops_enabled: boolean
  application_received: LeadLifecycleOpsPurpose
  rejection: LeadLifecycleOpsPurpose
  moving_forward: LeadLifecycleOpsPurpose
  channels: string[]
}

export type LeadLifecycleEmailPolicyOut = {
  company_id: string
  policy: LeadLifecycleEmailPolicy
  source: string
}

export type LifecycleEmailPolicyDecision = {
  purpose: string
  send: boolean
  template_ref: string | null
  source_layer: string
  block_code: string | null
  send_mode?: string | null
  enabled: boolean
  reason?: string | null
}

export type VacancyLifecycleOverrideOut = {
  vacancy_id: string
  company_id?: string | null
  override: Record<string, { enabled?: boolean; template_ref?: string | null }>
}

const BASE = '/settings/communications/lead-lifecycle-email'

export async function getLeadLifecycleEmailPolicy(companyId: string): Promise<LeadLifecycleEmailPolicyOut> {
  const { data } = await api.get<LeadLifecycleEmailPolicyOut>(`${BASE}/companies/${encodeURIComponent(companyId)}`)
  return data
}

export async function putLeadLifecycleEmailPolicy(
  companyId: string,
  policy: LeadLifecycleEmailPolicy,
): Promise<LeadLifecycleEmailPolicyOut> {
  const { data } = await api.put<LeadLifecycleEmailPolicyOut>(`${BASE}/companies/${encodeURIComponent(companyId)}`, {
    policy,
  })
  return data
}

export async function resolveLeadLifecycleEmailPreview(params: {
  company_id: string
  purpose: string
  vacancy_id?: string | null
}): Promise<LifecycleEmailPolicyDecision> {
  const { data } = await api.get<LifecycleEmailPolicyDecision>(`${BASE}/resolve-preview`, {
    params: {
      company_id: params.company_id,
      purpose: params.purpose,
      vacancy_id: params.vacancy_id || undefined,
    },
  })
  return data
}

export async function getVacancyLifecycleEmailOverride(vacancyId: string): Promise<VacancyLifecycleOverrideOut> {
  const { data } = await api.get<VacancyLifecycleOverrideOut>(`${BASE}/vacancies/${encodeURIComponent(vacancyId)}`)
  return data
}

export async function putVacancyLifecycleEmailOverride(
  vacancyId: string,
  override: Record<string, { enabled?: boolean; template_ref?: string | null }>,
): Promise<VacancyLifecycleOverrideOut> {
  const { data } = await api.put<VacancyLifecycleOverrideOut>(`${BASE}/vacancies/${encodeURIComponent(vacancyId)}`, {
    override,
  })
  return data
}
