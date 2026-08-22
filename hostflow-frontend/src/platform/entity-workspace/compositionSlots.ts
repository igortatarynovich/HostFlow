/**
 * Entity Workspace D2 — composition slot catalog.
 *
 * Distinct from Shell `EntityWorkspaceSectionId` (adapter navigation).
 * Do not collapse the two. `documents` is an enabled platform slot (E2);
 * D3–D9 consumers still omit it until a named later E slice.
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

export const ENTITY_WORKSPACE_RESERVED_SLOT_IDS = [] as const

export type EntityWorkspaceReservedSlotId =
  (typeof ENTITY_WORKSPACE_RESERVED_SLOT_IDS)[number]

export const ENTITY_WORKSPACE_ENABLED_SLOT_IDS = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'documents',
  'context-rail',
] as const

export type EntityWorkspaceEnabledSlotId =
  (typeof ENTITY_WORKSPACE_ENABLED_SLOT_IDS)[number]

export const ENTITY_WORKSPACE_SLOT_KIND = {
  overview: 'content',
  timeline: 'content',
  communication: 'platform',
  forms: 'platform',
  documents: 'platform',
  'context-rail': 'chrome',
} as const satisfies Record<EntityWorkspaceSlotId, string>

export function isEntityWorkspaceSlotEnabled(id: EntityWorkspaceSlotId): boolean {
  return (ENTITY_WORKSPACE_ENABLED_SLOT_IDS as readonly string[]).includes(id)
}
