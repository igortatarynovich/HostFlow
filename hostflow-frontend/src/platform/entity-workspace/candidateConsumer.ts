/**
 * Entity Workspace D4 — Candidate consumer binding.
 *
 * Slot ids come from compositionSlots.ts. Do not add HR / Vacancy / Client / Order.
 * E4 binds `documents` here (Candidate Document Link). D3 / D5–D7 / D9 stay unbound.
 * Do not collapse Shell EntityWorkspaceSectionId.
 */

import {
  ENTITY_WORKSPACE_ENABLED_SLOT_IDS,
  type EntityWorkspaceEnabledSlotId,
} from './compositionSlots'

export const CANDIDATE_COMPOSITION_CONSUMER_ID = 'candidate' as const

export const CANDIDATE_COMPOSITION_SLOTS = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'documents',
  'context-rail',
] as const satisfies readonly EntityWorkspaceEnabledSlotId[]

export type CandidateCompositionSlotId = (typeof CANDIDATE_COMPOSITION_SLOTS)[number]

const ENABLED = new Set<string>(ENTITY_WORKSPACE_ENABLED_SLOT_IDS)

export function assertCandidateCompositionSlots(
  slots: readonly string[] = CANDIDATE_COMPOSITION_SLOTS,
): asserts slots is readonly CandidateCompositionSlotId[] {
  for (const id of slots) {
    if (!ENABLED.has(id)) {
      throw new Error(`D4: Candidate slot '${id}' is not in the D2 enabled catalog`)
    }
  }
}
