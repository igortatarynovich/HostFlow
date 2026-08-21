/**
 * Four capability classes — separate catalogs, not one flat enum.
 *
 * Same placement protocol. Different ownership / lifecycle.
 * Do not merge these arrays. Do not name a capability `rodo`.
 */

export const SHELL_PRIMITIVE_IDS = [
  'identity',
  'status',
  'ownership',
  'actions',
  'audit',
] as const

export type ShellPrimitiveId = (typeof SHELL_PRIMITIVE_IDS)[number]

export const SHARED_CAPABILITY_IDS = [
  'contacts',
  'notes',
  'consent',
  'tasks',
  'relations',
] as const

export type SharedCapabilityId = (typeof SHARED_CAPABILITY_IDS)[number]

export const PLATFORM_SURFACE_IDS = [
  'timeline',
  'documents',
  'communication',
  'forms',
] as const

export type PlatformSurfaceId = (typeof PLATFORM_SURFACE_IDS)[number]

export const MODULE_CONTRIBUTION_IDS = [
  'recruitment.stage',
  'recruitment.vacancy',
  'recruitment.assignee',
  'hr.employment',
  'fleet.assignment',
  'fixture.optional_addon',
] as const

export type ModuleContributionId = (typeof MODULE_CONTRIBUTION_IDS)[number]

export const WORKSPACE_CAPABILITY_CLASS_IDS = [
  'shell_primitive',
  'shared_capability',
  'platform_surface',
  'module_contribution',
] as const

export type WorkspaceCapabilityClassId = (typeof WORKSPACE_CAPABILITY_CLASS_IDS)[number]
