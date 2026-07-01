import type {
  RequirementPipelineBlockers,
  RequirementsChecklistResponse,
} from '../api/types/candidateRequirements'
import type { DocBlockersPayload } from './candidateStageDocPolicy'

export function mapRequirementsChecklistToBlockers(
  checklist: RequirementsChecklistResponse | null | undefined,
): DocBlockersPayload {
  if (!checklist) {
    return { missing: [], problematic: [], inProgress: [] }
  }

  const pipeline = checklist.pipeline_blockers
  if (pipeline) {
    return mapRequirementPipelineBlockers(pipeline)
  }

  const missing: string[] = []
  const problematic: string[] = []
  const inProgress: string[] = []

  for (const item of checklist.requirements || []) {
    const evalStatus = String(item.evaluation?.status || '').toLowerCase()
    if (evalStatus === 'not_applicable' || item.fulfilled) continue
    const code = String(item.requirement_code || '').trim()
    if (!code) continue
    const evidenceStatus = String(item.candidate_evidence?.status || '').toLowerCase()
    if (evidenceStatus === 'rejected') {
      problematic.push(code)
    } else if (evalStatus === 'pending_verification' || evidenceStatus === 'pending_review') {
      inProgress.push(code)
    } else {
      missing.push(code)
    }
  }

  return { missing, problematic, inProgress }
}

export function mapRequirementPipelineBlockers(
  pipeline: RequirementPipelineBlockers,
): DocBlockersPayload {
  return {
    missing: [...(pipeline.missing_requirements || [])],
    problematic: [...(pipeline.problematic_requirements || [])],
    inProgress: [...(pipeline.pending_review_requirements || [])],
  }
}

export function requirementBlockerLabelKey(code: string): string {
  return `app.candidate_card.requirements_checklist.requirements.${code}`
}
