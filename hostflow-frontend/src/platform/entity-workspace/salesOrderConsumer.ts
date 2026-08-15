/**
 * Entity Workspace D6 — Sales Order consumer binding.
 *
 * Slot ids come from compositionSlots.ts. Do not add HR / Vacancy / Services order.
 * Do not enable `documents`. Do not collapse Shell EntityWorkspaceSectionId.
 * This is ADR-032 SalesOrder, not the PX mock order resource.
 */

import {
  ENTITY_WORKSPACE_ENABLED_SLOT_IDS,
  type EntityWorkspaceEnabledSlotId,
} from './compositionSlots'

export const SALES_ORDER_COMPOSITION_CONSUMER_ID = 'sales-order' as const

export const SALES_ORDER_COMPOSITION_SLOTS = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'context-rail',
] as const satisfies readonly EntityWorkspaceEnabledSlotId[]

export type SalesOrderCompositionSlotId = (typeof SALES_ORDER_COMPOSITION_SLOTS)[number]

const ENABLED = new Set<string>(ENTITY_WORKSPACE_ENABLED_SLOT_IDS)

export function assertSalesOrderCompositionSlots(
  slots: readonly string[] = SALES_ORDER_COMPOSITION_SLOTS,
): asserts slots is readonly SalesOrderCompositionSlotId[] {
  for (const id of slots) {
    if (id === 'documents') {
      throw new Error('D6: Sales Order must not enable reserved documents slot')
    }
    if (!ENABLED.has(id)) {
      throw new Error(`D6: Sales Order slot '${id}' is not in the D2 enabled catalog`)
    }
  }
}
