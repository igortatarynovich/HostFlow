import { api } from './client'

export type AutomationRule = {
  id: string
  tenant_id: string
  enabled: boolean
  trigger: string
  priority?: number
  title: string | null
  conditions: Record<string, any> | null
  actions: Record<string, any> | null
  created_at: string
  updated_at: string
}

export async function listAutomationRules(trigger?: string): Promise<{ items: AutomationRule[] }> {
  const { data } = await api.get('/automation-rules', { params: trigger ? { trigger } : undefined })
  return data
}

export async function createAutomationRule(payload: {
  enabled?: boolean
  trigger: string
  priority?: number
  title?: string
  conditions?: Record<string, any> | null
  actions?: Record<string, any> | null
}): Promise<AutomationRule> {
  const { data } = await api.post('/automation-rules', payload)
  return data
}

export async function patchAutomationRule(
  id: string,
  payload: Partial<Pick<AutomationRule, 'enabled' | 'priority' | 'title' | 'conditions' | 'actions'>>,
) {
  const { data } = await api.patch(`/automation-rules/${id}`, payload)
  return data as AutomationRule
}

export async function deleteAutomationRule(id: string) {
  await api.delete(`/automation-rules/${id}`)
}

