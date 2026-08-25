/**
 * Capability Definition — semantic owner + state owner + placement contract.
 *
 * Discriminated by `class`. Not a flat id enum.
 * Host does not own domain meaning. `status` is an owner projection.
 */

import type { WorkspaceCapabilityHostId, WorkspaceHostRegionId } from './hosts'
import type {
  ModuleContributionId,
  PlatformSurfaceId,
  SharedCapabilityId,
  ShellPrimitiveId,
  WorkspaceCapabilityClassId,
} from './catalogs'
import {
  MODULE_CONTRIBUTION_IDS,
  PLATFORM_SURFACE_IDS,
  SHARED_CAPABILITY_IDS,
  SHELL_PRIMITIVE_IDS,
} from './catalogs'

type CapabilityBase<C extends WorkspaceCapabilityClassId, Id extends string> = {
  class: C
  capability_id: Id
  owner: string
  state_owner: string
  allowed_hosts: readonly WorkspaceCapabilityHostId[]
  allowed_regions: readonly WorkspaceHostRegionId[]
}

export type ShellPrimitiveCapability = CapabilityBase<'shell_primitive', ShellPrimitiveId> & {
  projection?: 'owner_status'
}

export type SharedCapabilityDefinition = CapabilityBase<'shared_capability', SharedCapabilityId>

export type PlatformSurfaceCapability = CapabilityBase<'platform_surface', PlatformSurfaceId> & {
  d2_slot: PlatformSurfaceId
  reserved?: boolean
}

export type ModuleCapabilityDefinition = CapabilityBase<
  'module_contribution',
  ModuleContributionId
> & {
  contributor: string
}

export type WorkspaceCapabilityDefinition =
  | ShellPrimitiveCapability
  | SharedCapabilityDefinition
  | PlatformSurfaceCapability
  | ModuleCapabilityDefinition

const BOTH_HOSTS = ['entity_workspace', 'application_workspace'] as const

export const SHELL_PRIMITIVE_CAPABILITIES: {
  readonly [K in ShellPrimitiveId]: ShellPrimitiveCapability & { capability_id: K }
} = {
  identity: {
    class: 'shell_primitive',
    capability_id: 'identity',
    owner: 'entity_or_application_type',
    state_owner: 'entity_or_application_type',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['header'],
  },
  status: {
    class: 'shell_primitive',
    capability_id: 'status',
    owner: 'entity_or_application_type',
    state_owner: 'entity_or_application_type',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['header'],
    projection: 'owner_status',
  },
  ownership: {
    class: 'shell_primitive',
    capability_id: 'ownership',
    owner: 'host_region',
    state_owner: 'entity_or_application_type',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['header', 'rail'],
  },
  actions: {
    class: 'shell_primitive',
    capability_id: 'actions',
    owner: 'action_canon',
    state_owner: 'action_canon',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['header', 'decision'],
  },
  audit: {
    class: 'shell_primitive',
    capability_id: 'audit',
    owner: 'activity',
    state_owner: 'activity',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['rail'],
  },
}

export const SHARED_CAPABILITY_DEFINITIONS: {
  readonly [K in SharedCapabilityId]: SharedCapabilityDefinition & { capability_id: K }
} = {
  contacts: {
    class: 'shared_capability',
    capability_id: 'contacts',
    owner: 'contacts',
    state_owner: 'contacts',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['overview', 'rail'],
  },
  notes: {
    class: 'shared_capability',
    capability_id: 'notes',
    owner: 'notes',
    state_owner: 'notes',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['overview', 'rail'],
  },
  consent: {
    class: 'shared_capability',
    capability_id: 'consent',
    owner: 'compliance',
    state_owner: 'compliance',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['overview', 'rail'],
  },
  tasks: {
    class: 'shared_capability',
    capability_id: 'tasks',
    owner: 'activity',
    state_owner: 'activity',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['rail'],
  },
  relations: {
    class: 'shared_capability',
    capability_id: 'relations',
    owner: 'entity_model',
    state_owner: 'entity_model',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['overview'],
  },
}

export const PLATFORM_SURFACE_CAPABILITIES: {
  readonly [K in PlatformSurfaceId]: PlatformSurfaceCapability & { capability_id: K }
} = {
  timeline: {
    class: 'platform_surface',
    capability_id: 'timeline',
    owner: 'activity',
    state_owner: 'activity',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['platform_slot'],
    d2_slot: 'timeline',
  },
  documents: {
    class: 'platform_surface',
    capability_id: 'documents',
    owner: 'documents',
    state_owner: 'documents',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['platform_slot'],
    d2_slot: 'documents',
  },
  communication: {
    class: 'platform_surface',
    capability_id: 'communication',
    owner: 'communication',
    state_owner: 'communication',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['platform_slot'],
    d2_slot: 'communication',
  },
  forms: {
    class: 'platform_surface',
    capability_id: 'forms',
    owner: 'forms',
    state_owner: 'forms',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['platform_slot'],
    d2_slot: 'forms',
  },
}

export const MODULE_CAPABILITY_DEFINITIONS: {
  readonly [K in ModuleContributionId]: ModuleCapabilityDefinition & { capability_id: K }
} = {
  'recruitment.stage': {
    class: 'module_contribution',
    capability_id: 'recruitment.stage',
    owner: 'recruitment',
    state_owner: 'recruitment',
    contributor: 'recruitment',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['decision', 'rail'],
  },
  'recruitment.vacancy': {
    class: 'module_contribution',
    capability_id: 'recruitment.vacancy',
    owner: 'recruitment',
    state_owner: 'recruitment',
    contributor: 'recruitment',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['rail', 'overview'],
  },
  'recruitment.assignee': {
    class: 'module_contribution',
    capability_id: 'recruitment.assignee',
    owner: 'recruitment',
    state_owner: 'recruitment',
    contributor: 'recruitment',
    allowed_hosts: BOTH_HOSTS,
    allowed_regions: ['rail', 'header'],
  },
  'hr.employment': {
    class: 'module_contribution',
    capability_id: 'hr.employment',
    owner: 'hr',
    state_owner: 'hr',
    contributor: 'hr',
    allowed_hosts: ['entity_workspace'],
    allowed_regions: ['overview', 'rail'],
  },
  'fleet.assignment': {
    class: 'module_contribution',
    capability_id: 'fleet.assignment',
    owner: 'fleet',
    state_owner: 'fleet',
    contributor: 'fleet',
    allowed_hosts: ['entity_workspace'],
    allowed_regions: ['overview', 'rail'],
  },
  'fixture.optional_addon': {
    class: 'module_contribution',
    capability_id: 'fixture.optional_addon',
    owner: 'fixture',
    state_owner: 'fixture',
    contributor: 'fixture',
    allowed_hosts: ['application_workspace'],
    allowed_regions: ['rail'],
  },
}

export const WORKSPACE_CAPABILITY_DEFINITIONS = {
  shell_primitive: SHELL_PRIMITIVE_CAPABILITIES,
  shared_capability: SHARED_CAPABILITY_DEFINITIONS,
  platform_surface: PLATFORM_SURFACE_CAPABILITIES,
  module_contribution: MODULE_CAPABILITY_DEFINITIONS,
} as const

export function assertNoRodoCapabilityId(): void {
  const ids = [
    ...SHELL_PRIMITIVE_IDS,
    ...SHARED_CAPABILITY_IDS,
    ...PLATFORM_SURFACE_IDS,
    ...MODULE_CONTRIBUTION_IDS,
  ]
  if (ids.some((id) => id === 'rodo' || id.endsWith('.rodo'))) {
    throw new Error('capability_id must not be named rodo')
  }
}
