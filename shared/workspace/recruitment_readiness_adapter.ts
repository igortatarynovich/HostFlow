/**
 * Recruitment module adapter: requirements workspace runtime → ReadinessContribution.
 * Domain rules stay in Recruitment API; this maps payload shape only.
 */

import type {
  NextActionDeclaration,
  ReadinessBlock,
  ReadinessContribution,
  WorkspaceContextKey,
  WorkspaceStatusSeverity,
} from './workspace_layer_contracts.ts'
import { RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY } from './workspace_layer_contracts.ts'

export type RecruitmentWorkspaceReadinessInput = {
  candidate_id: string
  summary: {
    total_requirements: number
    fulfilled_count: number
    blocking_open_count: number
    pending_review_count: number
    all_fulfilled: boolean
    handoff_ready: boolean
  }
  field_requirements: {
    required_fields: Array<{
      qualified_code: string
      level?: string
      satisfied: boolean
    }>
    missing_count: number
  }
  transfer_readiness: {
    transfer_allowed: boolean
    handoff_create_allowed: boolean
    blocking_reasons: Array<Record<string, unknown>>
    warnings?: Array<Record<string, unknown>>
  }
  pipeline_blockers: {
    unfulfilled_requirements?: Array<{
      requirement_code: string
      public_name?: string | null
      evaluation_status?: string | null
    }>
    pending_review_requirements?: string[]
  }
  operational_requirements: Array<{
    requirement_code: string
    public_name?: string
    status: string
    type?: string
  }>
  checklist: {
    requirements: Array<{
      requirement_code: string
      public_name?: string | null
      level?: string | null
      fulfilled: boolean
      evaluation?: { status?: string }
    }>
  }
}

function resolveSeverity(input: RecruitmentWorkspaceReadinessInput): WorkspaceStatusSeverity {
  if (input.summary.handoff_ready) return 'ready'
  if (input.summary.blocking_open_count > 0 || !input.transfer_readiness.transfer_allowed) {
    return 'blocked'
  }
  if (input.summary.pending_review_count > 0 || (input.transfer_readiness.warnings?.length ?? 0) > 0) {
    return 'warning'
  }
  if (input.summary.all_fulfilled) return 'ready'
  return 'info'
}

function blockerFromRequirement(
  requirement_code: string,
  label: string,
  severity: WorkspaceStatusSeverity = 'blocked',
): ReadinessBlock {
  return {
    block_id: `requirement:${requirement_code}`,
    label_key: label,
    severity,
    capability_key: RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY,
    section_id: 'requirements',
  }
}

export function buildRecruitmentReadinessBlockers(
  input: RecruitmentWorkspaceReadinessInput,
): ReadinessBlock[] {
  const blocks: ReadinessBlock[] = []

  for (const row of input.pipeline_blockers.unfulfilled_requirements ?? []) {
    const label =
      row.public_name?.trim() ||
      row.requirement_code ||
      'workspace.recruitment.blockers.requirement'
    blocks.push(blockerFromRequirement(row.requirement_code, label, 'blocked'))
  }

  for (const code of input.pipeline_blockers.pending_review_requirements ?? []) {
    const item = input.checklist.requirements.find((r) => r.requirement_code === code)
    const label =
      item?.public_name?.trim() ||
      code ||
      'workspace.recruitment.blockers.pending_review'
    blocks.push(blockerFromRequirement(code, label, 'warning'))
  }

  for (const field of input.field_requirements.required_fields) {
    if (field.satisfied) continue
    blocks.push({
      block_id: `field:${field.qualified_code}`,
      label_key: field.qualified_code,
      severity: field.level === 'blocking' ? 'blocked' : 'warning',
      capability_key: RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY,
      section_id: 'requirements',
    })
  }

  for (const reason of input.transfer_readiness.blocking_reasons) {
    const code = String(reason.code ?? reason.reason_code ?? reason.type ?? 'transfer_block')
    const label = String(reason.message ?? reason.label ?? reason.code ?? 'workspace.recruitment.blockers.transfer')
    blocks.push({
      block_id: `transfer:${code}`,
      label_key: label,
      severity: 'blocked',
      capability_key: RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY,
      section_id: 'requirements',
    })
  }

  return blocks
}

export function pickRecruitmentNextAction(
  input: RecruitmentWorkspaceReadinessInput,
  candidateRequirementsPath: string,
): NextActionDeclaration | null {
  if (input.summary.handoff_ready && input.transfer_readiness.handoff_create_allowed) {
    return {
      action_id: 'start_handoff',
      module_key: 'recruitment',
      label_key: 'workspace.recruitment.actions.start_handoff',
      permission: 'candidates.manage',
      priority: 5,
      capability_key: RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY,
      section_id: 'requirements',
      handler_kind: 'navigation',
      handler_ref: `${candidateRequirementsPath}#handoff-readiness`,
    }
  }

  const unfulfilled = input.pipeline_blockers.unfulfilled_requirements ?? []
  if (unfulfilled.length > 0) {
    const first = unfulfilled[0]
    return {
      action_id: `close_requirement:${first.requirement_code}`,
      module_key: 'recruitment',
      label_key:
        first.public_name?.trim() ||
        first.requirement_code ||
        'workspace.recruitment.actions.close_requirement',
      permission: 'candidates.manage',
      priority: 10,
      capability_key: RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY,
      section_id: 'requirements',
      handler_kind: 'navigation',
      handler_ref: `${candidateRequirementsPath}?requirement=${encodeURIComponent(first.requirement_code)}`,
    }
  }

  const openOp = input.operational_requirements.find((row) => row.status !== 'satisfied')
  if (openOp) {
    return {
      action_id: `operational:${openOp.requirement_code}`,
      module_key: 'recruitment',
      label_key:
        openOp.public_name?.trim() ||
        openOp.requirement_code ||
        'workspace.recruitment.actions.complete_activity',
      permission: 'candidates.manage',
      priority: 15,
      capability_key: RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY,
      section_id: 'requirements',
      handler_kind: 'navigation',
      handler_ref: `${candidateRequirementsPath}?requirement=${encodeURIComponent(openOp.requirement_code)}`,
    }
  }

  const missingField = input.field_requirements.required_fields.find((f) => !f.satisfied)
  if (missingField) {
    return {
      action_id: `field:${missingField.qualified_code}`,
      module_key: 'recruitment',
      label_key: missingField.qualified_code,
      permission: 'candidates.manage',
      priority: 20,
      capability_key: RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY,
      section_id: 'requirements',
      handler_kind: 'navigation',
      handler_ref: `${candidateRequirementsPath}#candidate-fields`,
    }
  }

  return null
}

export function recruitmentReadinessFromWorkspace(
  input: RecruitmentWorkspaceReadinessInput,
  options: {
    context?: WorkspaceContextKey
    candidateRequirementsPath: string
  },
): ReadinessContribution {
  const context = options.context ?? 'recruitment'
  const blockers = buildRecruitmentReadinessBlockers(input)

  return {
    module_key: 'recruitment',
    context,
    priority: 10,
    severity: resolveSeverity(input),
    summary_key: 'workspace.recruitment.readiness.summary',
    blockers,
    next_action: pickRecruitmentNextAction(input, options.candidateRequirementsPath),
  }
}
