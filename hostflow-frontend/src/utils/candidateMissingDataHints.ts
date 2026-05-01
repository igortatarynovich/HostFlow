import { isPipelineCompletedCanonicalStage } from './candidatePipelineCompleted'

export type MissingHintKey =
  | 'name'
  | 'contact'
  | 'employer'
  | 'citizenship'
  | 'languages'

type StageBucket = 'early' | 'docs' | 'late' | 'other' | 'terminal'

const LATE_PIPELINE_STAGES = new Set([
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

const STAGE_WEIGHT_RULES: Record<StageBucket, Record<MissingHintKey, number>> = {
  early: {
    contact: 120,
    name: 100,
    employer: 80,
    languages: 75,
    citizenship: 20,
  },
  docs: {
    citizenship: 115,
    employer: 95,
    languages: 85,
    contact: 60,
    name: 50,
  },
  late: {
    employer: 110,
    contact: 70,
    name: 65,
    citizenship: 40,
    languages: 30,
  },
  other: {
    employer: 90,
    contact: 80,
    name: 70,
    citizenship: 30,
    languages: 30,
  },
  terminal: {
    employer: 0,
    contact: 0,
    name: 0,
    citizenship: 0,
    languages: 0,
  },
}

export function resolveMissingDataStageBucket(
  canonicalStageCode: string | null | undefined,
): StageBucket {
  const stage = String(canonicalStageCode || '').trim().toLowerCase()
  if (isPipelineCompletedCanonicalStage(stage)) return 'terminal'
  if (!stage || ['new', 'no_answer', 'contacted', 'questionnaire_submitted'].includes(stage)) {
    return 'early'
  }
  if (['docs_wait', 'docs_got', 'ready_for_handoff'].includes(stage)) {
    return 'docs'
  }
  if (LATE_PIPELINE_STAGES.has(stage)) return 'late'
  return 'other'
}

export function scoreMissingHintForStage(
  hintKey: MissingHintKey,
  canonicalStageCode: string | null | undefined,
): number {
  const bucket = resolveMissingDataStageBucket(canonicalStageCode)
  return STAGE_WEIGHT_RULES[bucket][hintKey] ?? 0
}

