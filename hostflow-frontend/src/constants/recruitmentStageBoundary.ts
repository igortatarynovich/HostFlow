/**
 * Mirrors backend `RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES` (stages after recruitment / handoff boundary).
 * Used to keep agency funnel strips and recruitment list filters aligned with the recruitment zone.
 */
export const RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES: ReadonlySet<string> = new Set([
  'hired',
  'employed',
  'processing_by_hr',
  'processing_by_client',
  'docs_submitted_permit',
  'employment_pending',
  'on_trip',
  'probation_ok',
])

export function isPostRecruitmentStageCode(code: string | null | undefined): boolean {
  const c = String(code || '').trim().toLowerCase()
  return Boolean(c) && RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES.has(c)
}
