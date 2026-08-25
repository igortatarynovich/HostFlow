/**
 * Contribution Definition — the only legal add-path onto a host.
 *
 * permissions / actions / events / license are references to existing canons.
 * They are not local vocabularies. Discriminated by `class`.
 */

import type { WorkspaceCapabilityHostId, WorkspaceHostRegionId } from './hosts'
import type {
  ModuleContributionId,
  PlatformSurfaceId,
  SharedCapabilityId,
  ShellPrimitiveId,
  WorkspaceCapabilityClassId,
} from './catalogs'

/**
 * D2 slot ids, copied so this contract does not become a D2 consumer.
 * Named gate asserts equality with the D2 slot catalog file.
 */
export const WORKSPACE_PLATFORM_SLOT_IDS = [
  'overview',
  'timeline',
  'communication',
  'forms',
  'documents',
  'context-rail',
] as const

export type WorkspacePlatformSlotId = (typeof WORKSPACE_PLATFORM_SLOT_IDS)[number]

export const WORKSPACE_CONTRIBUTION_FIELD_KEYS = [
  'capability_id',
  'class',
  'owner',
  'contributor',
  'host',
  'consumer',
  'component_id',
  'placement',
  'ordering',
  'visibility',
  'permissions',
  'state_owner',
  'actions',
  'events',
  'license',
  'conflicts',
] as const

export type WorkspaceContributionFieldKey = (typeof WORKSPACE_CONTRIBUTION_FIELD_KEYS)[number]

/** ADR-004 / ADR-019 entitlement view — not a new license SoT. */
export const WORKSPACE_LICENSE_VIEWS = ['default', 'optional', 'paid'] as const
export type WorkspaceLicenseView = (typeof WORKSPACE_LICENSE_VIEWS)[number]

export type WorkspacePlacement =
  | { region: Exclude<WorkspaceHostRegionId, 'platform_slot'> }
  | { region: 'platform_slot'; slot_id: WorkspacePlatformSlotId }

/**
 * Reference fields. Values must already exist on:
 * - permissions → ADR-036 / existing permission keys
 * - actions → Action Canon or already-shipped named actions
 * - events → existing Event Contract Registry types
 * - license → ADR-004 / ADR-019 entitlement
 */
export type WorkspaceContributionReferences = {
  permissions: readonly string[]
  actions: readonly string[]
  events: readonly string[]
  license: WorkspaceLicenseView
}

type ContributionBase<C extends WorkspaceCapabilityClassId, Id extends string> = {
  class: C
  capability_id: Id
  owner: string
  contributor: string
  host: WorkspaceCapabilityHostId
  consumer: string
  component_id: string
  placement: WorkspacePlacement
  ordering: number
  visibility: string
  state_owner: string
  conflicts: readonly string[]
} & WorkspaceContributionReferences

export type ShellPrimitiveContribution = ContributionBase<'shell_primitive', ShellPrimitiveId>
export type SharedCapabilityContribution = ContributionBase<'shared_capability', SharedCapabilityId>
export type PlatformSurfaceContribution = ContributionBase<'platform_surface', PlatformSurfaceId>
export type ModuleCapabilityContribution = ContributionBase<'module_contribution', ModuleContributionId>

export type WorkspaceContributionDefinition =
  | ShellPrimitiveContribution
  | SharedCapabilityContribution
  | PlatformSurfaceContribution
  | ModuleCapabilityContribution

export const REFERENCE_FIELD_CANONS = {
  permissions: 'ADR-036',
  actions: 'Action Canon / already-shipped named actions',
  events: 'backend.app.platform.events.registry',
  license: 'ADR-004 / ADR-019 entitlement',
} as const
