/**
 * Canonical stages where recruitment is finished (success or loss).
 * Align with backend `PIPELINE_COMPLETED_STAGE_CODES` (`constants/stages.py`).
 */
const PIPELINE_COMPLETED = new Set(['rejected', 'declined', 'employed', 'probation_ok'])

export function isPipelineCompletedCanonicalStage(code: string | null | undefined): boolean {
  if (!code) return false
  return PIPELINE_COMPLETED.has(String(code).trim().toLowerCase())
}
