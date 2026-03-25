/**
 * Operational “suggested next step” hints by canonical pipeline stage.
 * Used when there is no active reminder — complements document-based next action.
 * Canonical keys align with `canonicalStageKey` / `candidateStageDocPolicy`.
 */
import { isPipelineCompletedCanonicalStage } from './candidatePipelineCompleted'
import { canonicalStageKey } from './stageLabels'

export type StageOperationalHintKind =
  | 'call_candidate'
  | 'assign_vacancy'
  | 'request_documents'
  | 'verify_documents'
  | 'handoff_prep'
  | 'advance_pipeline'

export type StageOperationalHint = {
  kind: StageOperationalHintKind
}

/**
 * Resolve hint from raw or canonical stage code.
 */
export function operationalHintForStage(stageCode: string | null | undefined): StageOperationalHint | null {
  const raw = String(stageCode || '').trim()
  if (!raw) return null
  const c = canonicalStageKey(raw, null) || raw.toLowerCase()

  if (isPipelineCompletedCanonicalStage(c)) return null

  if (c === 'new' || c === 'no_answer') return { kind: 'call_candidate' }
  if (c === 'contacted' || c === 'questionnaire_submitted') return { kind: 'assign_vacancy' }
  if (c === 'docs_wait') return { kind: 'request_documents' }
  if (c === 'docs_got') return { kind: 'verify_documents' }
  if (c === 'ready_for_handoff') return { kind: 'handoff_prep' }

  // Post-docs pipeline: nudge forward without over-specifying
  const latePipeline = new Set([
    'permit_ordered',
    'permit_received',
    'visa',
    'red_paper',
    'trip_plan',
    'at_client',
    'on_trip',
    'processing_by_client',
    'docs_submitted_permit',
    'handoff_returned',
  ])
  if (latePipeline.has(c)) return { kind: 'advance_pipeline' }

  return null
}

export type OperationalHintGateState = {
  /** `false` = contact gate satisfied → do not keep “call candidate” as the headline hint. Omit = unknown (keep stage-default hint). */
  contactAttemptPipelineBlocking?: boolean
  /** `false` = vacancy linked → do not keep “assign vacancy” as the headline hint. Omit = unknown. */
  vacancyPipelineBlocking?: boolean
}

/**
 * Same as {@link operationalHintForStage}, but skips milestones that are already satisfied
 * (uses the next journey stage hint, or `advance_pipeline`).
 */
export function operationalHintForStageResolved(
  stageCode: string | null | undefined,
  nextStageCode: string | null | undefined,
  gates?: OperationalHintGateState | null,
): StageOperationalHint | null {
  let hint = operationalHintForStage(stageCode)
  if (!hint) return null

  const contactBlocking = gates?.contactAttemptPipelineBlocking
  if (hint.kind === 'call_candidate' && contactBlocking === false) {
    const forward = nextStageCode ? operationalHintForStage(nextStageCode) : null
    if (forward && forward.kind !== 'call_candidate') {
      hint = forward
    } else {
      hint = { kind: 'advance_pipeline' }
    }
  }

  const vacancyBlocking = gates?.vacancyPipelineBlocking
  if (hint.kind === 'assign_vacancy' && vacancyBlocking === false) {
    const forward = nextStageCode ? operationalHintForStage(nextStageCode) : null
    if (forward && forward.kind !== 'assign_vacancy') {
      hint = forward
    } else {
      hint = { kind: 'advance_pipeline' }
    }
  }

  return hint
}
