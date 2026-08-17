/**
 * Entity Workspace D9 — Services order consumer binding.
 *
 * Slot ids come from compositionSlots.ts. Do not re-bind Sales Order / HR employee.
 * Do not enable `documents`. Do not collapse Shell EntityWorkspaceSectionId.
 * This is ServicesPage / service_order, not SalesOrderDetailPage.
 */

import {
  ENTITY_WORKSPACE_ENABLED_SLOT_IDS,
  type EntityWorkspaceEnabledSlotId,
} from './compositionSlots'

export const SERVICES_ORDER_COMPOSITION_CONSUMER_ID = 'service-order' as const

export const SERVICES_ORDER_COMPOSITION_SLOTS = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'context-rail',
] as const satisfies readonly EntityWorkspaceEnabledSlotId[]

export type ServicesOrderCompositionSlotId = (typeof SERVICES_ORDER_COMPOSITION_SLOTS)[number]

const ENABLED = new Set<string>(ENTITY_WORKSPACE_ENABLED_SLOT_IDS)

export function assertServicesOrderCompositionSlots(
  slots: readonly string[] = SERVICES_ORDER_COMPOSITION_SLOTS,
): asserts slots is readonly ServicesOrderCompositionSlotId[] {
  for (const id of slots) {
    if (id === 'documents') {
      throw new Error('D9: Services order must not enable reserved documents slot')
    }
    if (!ENABLED.has(id)) {
      throw new Error(`D9: Services order slot '${id}' is not in the D2 enabled catalog`)
    }
  }
}
