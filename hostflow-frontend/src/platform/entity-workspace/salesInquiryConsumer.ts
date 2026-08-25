/**
 * Entity Workspace D3 — first consumer binding (Sales Inquiry).
 *
 * Slot ids come from compositionSlots.ts. Do not add Candidate / HR here.
 * Do not bind `documents` (catalog-enabled in E2; not this consumer).
 * Do not collapse Shell EntityWorkspaceSectionId.
 */

import {
  ENTITY_WORKSPACE_ENABLED_SLOT_IDS,
  type EntityWorkspaceEnabledSlotId,
} from './compositionSlots'

export const SALES_INQUIRY_COMPOSITION_CONSUMER_ID = 'sales-inquiry' as const

export const SALES_INQUIRY_COMPOSITION_SLOTS = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'context-rail',
] as const satisfies readonly EntityWorkspaceEnabledSlotId[]

export type SalesInquiryCompositionSlotId = (typeof SALES_INQUIRY_COMPOSITION_SLOTS)[number]

const ENABLED = new Set<string>(ENTITY_WORKSPACE_ENABLED_SLOT_IDS)

export function assertSalesInquiryCompositionSlots(
  slots: readonly string[] = SALES_INQUIRY_COMPOSITION_SLOTS,
): asserts slots is readonly SalesInquiryCompositionSlotId[] {
  for (const id of slots) {
    if (id === 'documents') {
      throw new Error('D3: Sales Inquiry must not bind documents slot this slice')
    }
    if (!ENABLED.has(id)) {
      throw new Error(`D3: Sales Inquiry slot '${id}' is not in the D2 enabled catalog`)
    }
  }
}
