import type { TransferReadinessReport } from '../api/candidates'
import type { RequirementsWorkspaceResponse } from '../api/candidateRequirements'

/** Map workspace bundle transfer_readiness to TransferReadinessReport for shared UI. */
export function workspaceTransferReportFromBundle(
  workspace: RequirementsWorkspaceResponse,
): TransferReadinessReport {
  const tr = workspace.transfer_readiness
  return {
    candidate_id: workspace.candidate_id,
    policy_version: tr.policy_version || 'transfer_policy_v1',
    transfer_allowed: tr.transfer_allowed,
    handoff_create_allowed: tr.handoff_create_allowed,
    destinations_allowed: tr.destinations_allowed || [],
    blocking_reasons: (tr.blocking_reasons || []) as TransferReadinessReport['blocking_reasons'],
    warnings: (tr.warnings || []) as TransferReadinessReport['warnings'],
    required_documents: [],
    missing_documents: [],
    pending_verification_documents: [],
    missing_data_fields: [],
    required_confirmations: [],
    approved_overrides: [],
    source_layers: tr.source_layers || [],
    requirement_gate: tr.requirement_gate,
    requirement_engine: tr.requirement_engine,
  }
}
