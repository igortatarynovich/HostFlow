/**
 * Entity Workspace D5 — Client consumer binding.
 *
 * Slot ids come from compositionSlots.ts. Do not add HR / Vacancy / Order.
 * Do not enable `documents`. Do not collapse Shell EntityWorkspaceSectionId.
 */

import {
  ENTITY_WORKSPACE_ENABLED_SLOT_IDS,
  type EntityWorkspaceEnabledSlotId,
} from './compositionSlots'

export const CLIENT_COMPOSITION_CONSUMER_ID = 'client' as const

export const CLIENT_COMPOSITION_SLOTS = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'context-rail',
] as const satisfies readonly EntityWorkspaceEnabledSlotId[]

export type ClientCompositionSlotId = (typeof CLIENT_COMPOSITION_SLOTS)[number]

const ENABLED = new Set<string>(ENTITY_WORKSPACE_ENABLED_SLOT_IDS)

export function assertClientCompositionSlots(
  slots: readonly string[] = CLIENT_COMPOSITION_SLOTS,
): asserts slots is readonly ClientCompositionSlotId[] {
  for (const id of slots) {
    if (id === 'documents') {
      throw new Error('D5: Client must not enable reserved documents slot')
    }
    if (!ENABLED.has(id)) {
      throw new Error(`D5: Client slot '${id}' is not in the D2 enabled catalog`)
    }
  }
}
