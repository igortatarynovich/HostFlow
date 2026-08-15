/**
 * Entity Workspace D2 — composition slot catalog.
 *
 * Distinct from Shell `EntityWorkspaceSectionId` (adapter navigation).
 * Do not collapse the two. Do not enable `documents` until Phase E.
 * Do not invent new slot kinds without amending the D2 brief.
 */

export const ENTITY_WORKSPACE_SLOT_CATALOG = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'documents',
  'context-rail',
] as const

export type EntityWorkspaceSlotId = (typeof ENTITY_WORKSPACE_SLOT_CATALOG)[number]

export const ENTITY_WORKSPACE_RESERVED_SLOT_IDS = ['documents'] as const

export type EntityWorkspaceReservedSlotId =
  (typeof ENTITY_WORKSPACE_RESERVED_SLOT_IDS)[number]

export const ENTITY_WORKSPACE_ENABLED_SLOT_IDS = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'context-rail',
] as const

export type EntityWorkspaceEnabledSlotId =
  (typeof ENTITY_WORKSPACE_ENABLED_SLOT_IDS)[number]

export const ENTITY_WORKSPACE_SLOT_KIND = {
  overview: 'content',
  timeline: 'content',
  communication: 'platform',
  forms: 'platform',
  documents: 'platform-reserved',
  'context-rail': 'chrome',
} as const satisfies Record<EntityWorkspaceSlotId, string>

export function isEntityWorkspaceSlotEnabled(id: EntityWorkspaceSlotId): boolean {
  return (ENTITY_WORKSPACE_ENABLED_SLOT_IDS as readonly string[]).includes(id)
}
