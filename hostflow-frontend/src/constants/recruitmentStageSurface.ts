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

/**
 * Canonical Process Engine system stages a candidate funnel row may map to.
 * Keep in sync with `pe_system_stages` for module=recruitment (non-alias rows).
 */
export const RECRUITMENT_PE_SYSTEM_STAGE_CODES: readonly string[] = [
  'new',
  'no_answer',
  'contacted',
  'questionnaire_submitted',
  'waiting_documents',
  'documents_received',
  'ready_for_handoff',
  'processing_by_client',
  'processing_by_hr',
  'rejected',
  'declined',
  'employed',
] as const

/** Funnel `code` → PE system stage. Sync with `recruitment_legacy_to_pe_map()`. */
const RECRUITMENT_FUNNEL_CODE_TO_PE: Record<string, string> = {
  new: 'new',
  no_answer: 'no_answer',
  contacted: 'contacted',
  questionnaire_submitted: 'questionnaire_submitted',
  docs_wait: 'waiting_documents',
  waiting_documents: 'waiting_documents',
  docs_got: 'documents_received',
  documents_received: 'documents_received',
  permit_ordered: 'processing_by_client',
  ready_for_handoff: 'ready_for_handoff',
  processing_by_client: 'processing_by_client',
  processing_by_hr: 'processing_by_hr',
  docs_submitted_permit: 'processing_by_client',
  permit_received: 'processing_by_client',
  handoff_returned: 'processing_by_client',
  employment_pending: 'processing_by_client',
  at_client: 'processing_by_client',
  visa: 'processing_by_client',
  red_paper: 'processing_by_client',
  trip_plan: 'processing_by_client',
  ready_for_hr: 'ready_for_handoff',
  on_trip: 'employed',
  employed: 'employed',
  hired: 'employed',
  probation_ok: 'employed',
  rejected: 'rejected',
  declined: 'declined',
}

export const RECRUITMENT_MAPPABLE_FUNNEL_STAGE_CODES: readonly string[] = Object.keys(
  RECRUITMENT_FUNNEL_CODE_TO_PE,
)

export function inferRecruitmentPeSystemStageCode(code: string | null | undefined): string | null {
  const key = String(code || '').trim().toLowerCase()
  return key ? RECRUITMENT_FUNNEL_CODE_TO_PE[key] || null : null
}

export function isRecruitmentMappableFunnelStageCode(code: string | null | undefined): boolean {
  return inferRecruitmentPeSystemStageCode(code) != null
}

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
