/**
 * Entity Workspace D7 — Vacancy consumer binding.
 *
 * Slot ids come from compositionSlots.ts. Do not add HR employee / Services order.
 * Do not enable `documents`. Do not collapse Shell EntityWorkspaceSectionId.
 * This is ADR-032 Vacancy, not the PX mock vacancy relation.
 */

import {
  ENTITY_WORKSPACE_ENABLED_SLOT_IDS,
  type EntityWorkspaceEnabledSlotId,
} from './compositionSlots'

export const VACANCY_COMPOSITION_CONSUMER_ID = 'vacancy' as const

export const VACANCY_COMPOSITION_SLOTS = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'context-rail',
] as const satisfies readonly EntityWorkspaceEnabledSlotId[]

export type VacancyCompositionSlotId = (typeof VACANCY_COMPOSITION_SLOTS)[number]

const ENABLED = new Set<string>(ENTITY_WORKSPACE_ENABLED_SLOT_IDS)

export function assertVacancyCompositionSlots(
  slots: readonly string[] = VACANCY_COMPOSITION_SLOTS,
): asserts slots is readonly VacancyCompositionSlotId[] {
  for (const id of slots) {
    if (id === 'documents') {
      throw new Error('D7: Vacancy must not enable reserved documents slot')
    }
    if (!ENABLED.has(id)) {
      throw new Error(`D7: Vacancy slot '${id}' is not in the D2 enabled catalog`)
    }
  }
}
