/**
 * Stage-based document / pipeline policy (HostFlow hiring OS).
 *
 * Principle: blockers depend on the current stage — not global "missing docs".
 * Early stages (new / contact / questionnaire) must not be held hostage by the checklist.
 *
 * Tenant overrides: `GET /settings/team/hiring-pipeline-gates` → pass runtime gates into helpers
 * (via `HiringPipelineGatesContext` on the card). When omitted, behavior matches product defaults.
 */

import type { HiringPipelineGatesPublic } from '../api/types'
import { isPipelineCompletedCanonicalStage } from './candidatePipelineCompleted'
import { canonicalStageKey } from './stageLabels'

export type DocBlockersPayload = {
  missing: string[]
  problematic: string[]
  inProgress: string[]
}

/** Resolved gate sets for UI (mirrors backend `HiringPipelineGates`). */
export type HiringPipelineGatesRuntime = {
  stagesWithoutDocPipelineBlock: Set<string>
  stagesVerifyUploadsBlockForward: Set<string>
  stagesRequireVacancyForForward: Set<string>
  contactAttemptGateStages: Set<string>
  stagesDocBlockSoftOnly: Set<string>
}

const _STAGES_WITHOUT = [
  'new',
  'no_answer',
  'contacted',
  'questionnaire_submitted',
] as const

const _STAGES_VERIFY = [
  'docs_got',
  'permit_ordered',
  'ready_for_handoff',
  'processing_by_client',
  'docs_submitted_permit',
  'handoff_returned',
] as const

const _VACANCY_STAGES = ['contacted', 'questionnaire_submitted'] as const

const _CONTACT_ATTEMPT_STAGES = ['new'] as const

/** Product defaults (same as `backend/app/services/hiring_pipeline_gates.py`). */
export const DEFAULT_HIRING_PIPELINE_GATES_RUNTIME: HiringPipelineGatesRuntime = {
  stagesWithoutDocPipelineBlock: new Set(_STAGES_WITHOUT),
  stagesVerifyUploadsBlockForward: new Set(_STAGES_VERIFY),
  stagesRequireVacancyForForward: new Set(_VACANCY_STAGES),
  contactAttemptGateStages: new Set(_CONTACT_ATTEMPT_STAGES),
  stagesDocBlockSoftOnly: new Set(),
}

function _lowerSet(items: string[] | undefined | null): Set<string> {
  const out = new Set<string>()
  for (const x of items || []) {
    const s = String(x || '')
      .trim()
      .toLowerCase()
    if (s) out.add(s)
  }
  return out
}

export function hiringPipelineGatesFromApi(
  g: HiringPipelineGatesPublic | null | undefined,
): HiringPipelineGatesRuntime {
  if (!g) return DEFAULT_HIRING_PIPELINE_GATES_RUNTIME
  return {
    stagesWithoutDocPipelineBlock: _lowerSet(g.stages_without_doc_pipeline_block),
    stagesVerifyUploadsBlockForward: _lowerSet(g.stages_verify_uploads_block_forward),
    stagesRequireVacancyForForward: _lowerSet(g.stages_require_vacancy_for_forward),
    contactAttemptGateStages: _lowerSet(g.contact_attempt_gate_stages),
    stagesDocBlockSoftOnly: _lowerSet(g.stages_doc_block_soft_only),
  }
}

export function docsIssuesPresent(blockers: DocBlockersPayload, loading: boolean): boolean {
  if (loading) return false
  return (
    blockers.missing.length > 0 || blockers.problematic.length > 0 || blockers.inProgress.length > 0
  )
}

/** True when moving forward from this stage should be blocked until a vacancy is assigned. */
export function vacancyPipelineBlocksForward(
  stageCode: string | null | undefined,
  vacancyId: string | null | undefined,
  gates?: HiringPipelineGatesRuntime | null,
): boolean {
  const g = gates ?? DEFAULT_HIRING_PIPELINE_GATES_RUNTIME
  const raw = String(stageCode || '').trim()
  if (!raw) return false
  const c = canonicalStageKey(raw, null) || raw.toLowerCase()
  if (!g.stagesRequireVacancyForForward.has(c)) return false
  return !String(vacancyId || '').trim()
}

/**
 * When contact-attempt policy is on for this candidate, require ≥1 logged attempt before leaving
 * configured gate stages (default: `new`) forward.
 */
export function contactAttemptPipelineBlocksForward(
  stageCode: string | null | undefined,
  contactPolicyEnabled: boolean,
  contactAttemptCount: number,
  gates?: HiringPipelineGatesRuntime | null,
): boolean {
  if (!contactPolicyEnabled) return false
  const g = gates ?? DEFAULT_HIRING_PIPELINE_GATES_RUNTIME
  const raw = String(stageCode || '').trim()
  if (!raw) return false
  const c = canonicalStageKey(raw, null) || raw.toLowerCase()
  if (!g.contactAttemptGateStages.has(c)) return false
  return contactAttemptCount < 1
}

/**
 * Document pipeline resolution: `hard` matches server 409 doc gate; `softWarnOnly` is advisory-only
 * when the stage is listed in `stages_doc_block_soft_only`.
 */
export function docsPipelineBlocksForwardResolved(
  stageCode: string | null | undefined,
  blockers: DocBlockersPayload,
  loading: boolean,
  gates?: HiringPipelineGatesRuntime | null,
): { hard: boolean; softWarnOnly: boolean } {
  if (loading) return { hard: false, softWarnOnly: false }
  const g = gates ?? DEFAULT_HIRING_PIPELINE_GATES_RUNTIME
  const raw = String(stageCode || '').trim()
  if (!raw) return { hard: false, softWarnOnly: false }
  const code = canonicalStageKey(raw, null) || raw.toLowerCase()
  if (!code || isPipelineCompletedCanonicalStage(code)) {
    return { hard: false, softWarnOnly: false }
  }
  if (g.stagesWithoutDocPipelineBlock.has(code)) {
    return { hard: false, softWarnOnly: false }
  }
  let wouldHard = false
  if (blockers.missing.length > 0 || blockers.problematic.length > 0) {
    wouldHard = true
  } else if (g.stagesVerifyUploadsBlockForward.has(code) && blockers.inProgress.length > 0) {
    wouldHard = true
  }
  if (!wouldHard) return { hard: false, softWarnOnly: false }
  if (g.stagesDocBlockSoftOnly.has(code)) {
    return { hard: false, softWarnOnly: true }
  }
  return { hard: true, softWarnOnly: false }
}

/**
 * Whether moving forward in the pipeline should be blocked by document state.
 * Does not replace server-side rules (e.g. ready_for_handoff / handoff) — UI alignment only.
 */
export function docsPipelineBlocksForward(
  stageCode: string | null | undefined,
  blockers: DocBlockersPayload,
  loading: boolean,
  gates?: HiringPipelineGatesRuntime | null,
): boolean {
  return docsPipelineBlocksForwardResolved(stageCode, blockers, loading, gates).hard
}

const normType = (t: string) => String(t || '').trim().toLowerCase()

/** Remove doc types that have an active approved pipeline waiver (pipeline or both). */
export function relaxDocBlockers(blockers: DocBlockersPayload, relaxedTypes: Iterable<string>): DocBlockersPayload {
  const set = new Set<string>()
  for (const raw of relaxedTypes) {
    const c = normType(raw)
    if (c) set.add(c)
  }
  const filt = (xs: string[]) => xs.filter((t) => !set.has(normType(t)))
  return {
    missing: filt(blockers.missing),
    problematic: filt(blockers.problematic),
    inProgress: filt(blockers.inProgress),
  }
}

export function pipelineRelaxedTypesFromOverrides(
  overrides: Array<{ status: string; granted_scope?: string | null; doc_type_code?: string | null }>,
): Set<string> {
  const out = new Set<string>()
  for (const o of overrides) {
    if (String(o.status || '').toLowerCase() !== 'approved') continue
    const g = String(o.granted_scope || '').toLowerCase()
    if (g === 'pipeline' || g === 'both') {
      const c = normType(String(o.doc_type_code || ''))
      if (c) out.add(c)
    }
  }
  return out
}

/** Remove requirement codes that have an active approved pipeline waiver (pipeline or both). */
export function relaxRequirementBlockers(
  blockers: DocBlockersPayload,
  relaxedRequirements: Iterable<string>,
): DocBlockersPayload {
  const set = new Set<string>()
  for (const raw of relaxedRequirements) {
    const c = normType(raw)
    if (c) set.add(c)
  }
  const filt = (xs: string[]) => xs.filter((t) => !set.has(normType(t)))
  return {
    missing: filt(blockers.missing),
    problematic: filt(blockers.problematic),
    inProgress: filt(blockers.inProgress),
  }
}

export function pipelineRelaxedRequirementsFromOverrides(
  overrides: Array<{ status: string; granted_scope?: string | null; requirement_code?: string | null }>,
): Set<string> {
  const out = new Set<string>()
  for (const o of overrides) {
    if (String(o.status || '').toLowerCase() !== 'approved') continue
    const g = String(o.granted_scope || '').toLowerCase()
    if (g === 'pipeline' || g === 'both') {
      const c = normType(String(o.requirement_code || ''))
      if (c) out.add(c)
    }
  }
  return out
}
