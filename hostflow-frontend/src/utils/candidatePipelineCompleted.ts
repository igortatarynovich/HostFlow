/**
 * Canonical stages where recruitment is finished (success or loss).
 * Align with backend `PIPELINE_COMPLETED_STAGE_CODES` (`constants/stages.py`).
 */
/** Recruitment-terminal and outcome codes (stage or row_status). HR/post-employment codes excluded from recruitment hints. */
const PIPELINE_COMPLETED = new Set([
  'rejected',
  'declined',
  'handoff_returned',
  'ready_for_handoff',
  'ready_for_hr',
])

export function isPipelineCompletedCanonicalStage(code: string | null | undefined): boolean {
  if (!code) return false
  return PIPELINE_COMPLETED.has(String(code).trim().toLowerCase())
}

/** True when funnel `stage` **or** row-level `row_status` / `status` is a completed pipeline code. */
export function isCandidateOperationallyTerminal(input: {
  stage?: string | null
  row_status?: string | null
  status?: string | null
}): boolean {
  if (isPipelineCompletedCanonicalStage(input.stage)) return true
  const row = String(input.row_status ?? '').trim().toLowerCase()
  if (row && PIPELINE_COMPLETED.has(row)) return true
  const st = String(input.status ?? '').trim().toLowerCase()
  if (st && PIPELINE_COMPLETED.has(st)) return true
  return false
}
