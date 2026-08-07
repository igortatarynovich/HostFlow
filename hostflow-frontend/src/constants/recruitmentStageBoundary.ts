/**
 * Mirrors backend `RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES` (stages after recruitment / handoff boundary).
 * Used to keep agency funnel strips and recruitment list filters aligned with the recruitment zone.
 */
export const RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES: ReadonlySet<string> = new Set([
  'hired',
  'employed',
  'ready_for_hr',
  'processing_by_hr',
  'ready_for_fleet',
  'processing_by_client',
  'docs_submitted_permit',
  'employment_pending',
  'on_trip',
  'probation_ok',
  'permit_ordered',
  'permit_received',
  'visa',
  'red_paper',
  'trip_plan',
  'at_client',
])

const RECRUITMENT_TERMINAL_STAGE_CODES = new Set(['rejected', 'declined'])

export function isRecruitmentTerminalStageCode(code: string | null | undefined): boolean {
  const c = String(code || '').trim().toLowerCase()
  return Boolean(c) && RECRUITMENT_TERMINAL_STAGE_CODES.has(c)
}

export function isPostRecruitmentStageCode(code: string | null | undefined): boolean {
  const c = String(code || '').trim().toLowerCase()
  return Boolean(c) && RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES.has(c)
}
