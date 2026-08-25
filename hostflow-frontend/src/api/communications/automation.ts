/** C2.2 Automation Engine client — thin wrapper over `/communications/automation/rules`. */

import api from '../client'

export type CommunicationAutomationTrigger = {
  id?: string
  event_type: string
  event_filter?: Record<string, unknown>
}

export type CommunicationAutomationVersion = {
  id: string
  rule_id: string
  version_number: number
  status: string
  intent_key: string
  preferred_template_key?: string | null
  channel?: string | null
  recipient_strategy: string
  triggers: CommunicationAutomationTrigger[]
  conditions?: Record<string, unknown>
  recipient_config?: Record<string, unknown>
  variables_mapping?: Record<string, unknown>
  meta?: Record<string, unknown>
  published_at?: string | null
  published_by?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type CommunicationAutomationRuleBundle = {
  id: string
  key: string
  name: string
  description?: string | null
  status: string
  enabled: boolean
  priority: number
  created_at?: string | null
  updated_at?: string | null
  draft: CommunicationAutomationVersion | null
  latest_published: CommunicationAutomationVersion | null
  published_version?: CommunicationAutomationVersion
}

export type CommunicationAutomationDecision = {
  id: string
  rule_id: string
  rule_version_id: string
  source_event_id: string
  event_type: string
  outcome: string
  reason_codes: string[]
  intent_key?: string | null
  created_at?: string | null
}

export type CommunicationAutomationDryRunResult = {
  ok: boolean
  outcome: string
  intent_key?: string | null
  reason_codes?: string[]
  template_variables?: Record<string, unknown>
  diagnostics?: Array<{ code?: string; severity?: string; message?: string }>
}

export type CommunicationAutomationRuleCreateInput = {
  key: string
  name: string
  description?: string | null
  enabled?: boolean
  priority?: number
  intent_key: string
  preferred_template_key?: string | null
  channel?: string | null
  recipient_strategy?: string
  recipient_config?: Record<string, unknown>
  conditions?: Record<string, unknown>
  variables_mapping?: Record<string, unknown>
  triggers?: CommunicationAutomationTrigger[]
}

export type CommunicationAutomationDraftPatch = {
  intent_key?: string | null
  preferred_template_key?: string | null
  channel?: string | null
  recipient_strategy?: string | null
  recipient_config?: Record<string, unknown> | null
  conditions?: Record<string, unknown> | null
  variables_mapping?: Record<string, unknown> | null
  meta?: Record<string, unknown> | null
  triggers?: CommunicationAutomationTrigger[] | null
  clear_preferred_template_key?: boolean
  clear_channel?: boolean
}

export async function listCommunicationAutomationRules(params?: {
  includeArchived?: boolean
}): Promise<CommunicationAutomationRuleBundle[]> {
  const res = await api.get('/communications/automation/rules', {
    params: { include_archived: params?.includeArchived ? true : undefined },
  })
  const items = res.data?.items
  return Array.isArray(items) ? items : []
}

export async function getCommunicationAutomationRule(
  ruleId: string,
): Promise<CommunicationAutomationRuleBundle> {
  const res = await api.get(`/communications/automation/rules/${ruleId}`)
  return res.data
}

export async function createCommunicationAutomationRule(
  body: CommunicationAutomationRuleCreateInput,
): Promise<CommunicationAutomationRuleBundle> {
  const res = await api.post('/communications/automation/rules', body)
  return res.data
}

export async function updateCommunicationAutomationDraft(
  ruleId: string,
  body: CommunicationAutomationDraftPatch,
): Promise<CommunicationAutomationRuleBundle> {
  const res = await api.patch(`/communications/automation/rules/${ruleId}/draft`, body)
  return res.data
}

export async function publishCommunicationAutomationRule(
  ruleId: string,
): Promise<CommunicationAutomationRuleBundle> {
  const res = await api.post(`/communications/automation/rules/${ruleId}/publish`)
  return res.data
}

export async function setCommunicationAutomationRuleEnabled(
  ruleId: string,
  enabled: boolean,
): Promise<CommunicationAutomationRuleBundle> {
  const res = await api.post(`/communications/automation/rules/${ruleId}/enabled`, {
    enabled,
  })
  return res.data
}

export async function archiveCommunicationAutomationRule(
  ruleId: string,
): Promise<CommunicationAutomationRuleBundle> {
  const res = await api.post(`/communications/automation/rules/${ruleId}/archive`)
  return res.data
}

export async function listCommunicationAutomationVersions(
  ruleId: string,
): Promise<CommunicationAutomationVersion[]> {
  const res = await api.get(`/communications/automation/rules/${ruleId}/versions`)
  const items = res.data?.items
  return Array.isArray(items) ? items : []
}

export async function dryRunCommunicationAutomationRule(
  ruleId: string,
  body: {
    event_id: string
    event_type: string
    data?: Record<string, unknown>
    correlation_id?: string | null
    version_id?: string | null
  },
): Promise<CommunicationAutomationDryRunResult> {
  const res = await api.post(`/communications/automation/rules/${ruleId}/dry-run`, body)
  return res.data
}

export async function listCommunicationAutomationDecisions(
  ruleId: string,
  limit = 50,
): Promise<CommunicationAutomationDecision[]> {
  const res = await api.get(`/communications/automation/rules/${ruleId}/decisions`, {
    params: { limit },
  })
  const items = res.data?.items
  return Array.isArray(items) ? items : []
}
