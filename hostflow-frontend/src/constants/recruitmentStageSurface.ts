/**
 * Recruitment CRM surface: stage lists, filters, and labels.
 * HR / post-handoff codes remain in the domain model but are hidden here.
 *
 * Boundary codes: `recruitmentStageBoundary.ts` (sync with backend `RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES`).
 */
import {
  isPostRecruitmentStageCode,
  RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES,
} from './recruitmentStageBoundary'

export { isPostRecruitmentStageCode, RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES }

/** Default stage order when `/meta/stages` or funnel table is empty (recruitment zone only). */
export const RECRUITMENT_DEFAULT_STAGE_ORDER: readonly string[] = [
  'new',
  'no_answer',
  'contacted',
  'questionnaire_submitted',
  'docs_wait',
  'docs_got',
  'permit_ordered',
  'ready_for_handoff',
  'processing_by_client',
  'docs_submitted_permit',
  'handoff_returned',
  'rejected',
  'declined',
] as const

/** Terminal outcomes — valid as `stage` or `row_status`, not progression steps in funnel pickers. */
export const RECRUITMENT_OUTCOME_STAGE_CODES: ReadonlySet<string> = new Set([
  'rejected',
  'declined',
  'handoff_returned',
])

export function filterRecruitmentVisibleStageCodes(codes: string[]): string[] {
  return codes.filter((code) => {
    const c = String(code || '').trim()
    if (!c) return false
    return !isPostRecruitmentStageCode(c)
  })
}

export function isRecruitmentOutcomeStageCode(code: string | null | undefined): boolean {
  const c = String(code || '').trim().toLowerCase()
  return Boolean(c) && RECRUITMENT_OUTCOME_STAGE_CODES.has(c)
}
