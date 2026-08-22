/**
 * Candidate Entity Workspace — host-equivalence bind + E4 documents.
 *
 * Not G4. G4 stays Recruitment Application on Application Workspace.
 * This is the runtime consumer for `entity_workspace`: the same Capability
 * Host Contract, D2 platform surfaces placed by the host.
 * E4 places `documents` via Document Link. Do not treat this file as G4.
 */

import type { WorkspaceContributionDefinition } from './contribution'

export const ENTITY_EQUIVALENCE_CONSUMER_ID = 'candidate' as const
export const ENTITY_EQUIVALENCE_HOST_ID = 'entity_workspace' as const

export const CANDIDATE_ENTITY_HOST_CONTRIBUTIONS = [
  {
    class: 'platform_surface',
    capability_id: 'communication',
    owner: 'communication',
    contributor: 'communication',
    host: 'entity_workspace',
    consumer: 'candidate',
    component_id: 'workspace.surface.communication',
    placement: { region: 'platform_slot', slot_id: 'communication' },
    ordering: 10,
    visibility: 'always',
    permissions: [],
    state_owner: 'communication',
    actions: [],
    events: [],
    license: 'default',
    conflicts: [],
  },
  {
    class: 'platform_surface',
    capability_id: 'forms',
    owner: 'forms',
    contributor: 'forms',
    host: 'entity_workspace',
    consumer: 'candidate',
    component_id: 'workspace.surface.forms',
    placement: { region: 'platform_slot', slot_id: 'forms' },
    ordering: 20,
    visibility: 'always',
    permissions: [],
    state_owner: 'forms',
    actions: [],
    events: [],
    license: 'default',
    conflicts: [],
  },
  {
    class: 'platform_surface',
    capability_id: 'documents',
    owner: 'documents',
    contributor: 'documents',
    host: 'entity_workspace',
    consumer: 'candidate',
    component_id: 'workspace.surface.documents',
    placement: { region: 'platform_slot', slot_id: 'documents' },
    ordering: 30,
    visibility: 'always',
    permissions: [],
    state_owner: 'documents',
    actions: [],
    events: [],
    license: 'default',
    conflicts: [],
  },
] as const satisfies readonly WorkspaceContributionDefinition[]
