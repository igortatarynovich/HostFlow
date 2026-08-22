/**
 * Entity Workspace D8 — HR employee consumer binding.
 *
 * Slot ids come from compositionSlots.ts. Do not add Services order / handoff.
 * E3 binds `documents` here (first consumer). D3–D7 / D9 stay unbound.
 * Do not collapse Shell EntityWorkspaceSectionId.
 * This is HrEmployeeDetailPage, not Candidate and not HrHandoffDetailPage.
 */

import {
  ENTITY_WORKSPACE_ENABLED_SLOT_IDS,
  type EntityWorkspaceEnabledSlotId,
} from './compositionSlots'

export const HR_EMPLOYEE_COMPOSITION_CONSUMER_ID = 'hr-employee' as const

export const HR_EMPLOYEE_COMPOSITION_SLOTS = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'documents',
  'context-rail',
] as const satisfies readonly EntityWorkspaceEnabledSlotId[]

export type HrEmployeeCompositionSlotId = (typeof HR_EMPLOYEE_COMPOSITION_SLOTS)[number]

const ENABLED = new Set<string>(ENTITY_WORKSPACE_ENABLED_SLOT_IDS)

export function assertHrEmployeeCompositionSlots(
  slots: readonly string[] = HR_EMPLOYEE_COMPOSITION_SLOTS,
): asserts slots is readonly HrEmployeeCompositionSlotId[] {
  for (const id of slots) {
    if (!ENABLED.has(id)) {
      throw new Error(`D8: HR employee slot '${id}' is not in the D2 enabled catalog`)
    }
  }
}
