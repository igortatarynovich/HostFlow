import { api } from './client'

export type RequirementPolicyApplicabilityRow = {
  doc_type: string
  applicability: string
}

export type RequirementPolicyEvalBlock = {
  ok?: boolean
  applicability?: RequirementPolicyApplicabilityRow[]
  error?: string
}

export type RequirementPolicyOperatorView = {
  contract_id: string
  write_authority: string
  base: RequirementPolicyEvalBlock
  override: {
    require: string[]
    remove: string[]
    revision: number
    reason: string
  }
  reason: string
  revision: number
  result: RequirementPolicyEvalBlock
  preview_context: Record<string, unknown>
  pack_defaults: {
    requiredTypes?: string[]
    optionalTypes?: string[]
  }
}

export type RequirementPolicyOperatorPut = {
  require: string[]
  remove: string[]
  reason: string
  expected_revision: number
  preview_context?: Record<string, unknown>
}

export async function getRequirementPolicyOperator(params?: {
  residency_status?: string
}): Promise<RequirementPolicyOperatorView> {
  const { data } = await api.get<RequirementPolicyOperatorView>(
    '/platform/requirement-policy-operator',
    { params },
  )
  return data
}

export async function putRequirementPolicyOperator(
  body: RequirementPolicyOperatorPut,
): Promise<RequirementPolicyOperatorView> {
  const { data } = await api.put<RequirementPolicyOperatorView>(
    '/platform/requirement-policy-operator',
    body,
  )
  return data
}
