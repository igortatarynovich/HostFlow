/**
 * HR employee Entity Workspace — E3 first consumer bind.
 *
 * Host places D2 `documents`. Documents owns semantics + Document Link SoT.
 * Not G4. Not Candidate. Not HrHandoffDetailPage. Not Shell `documents` nav.
 */

import type { WorkspaceContributionDefinition } from './contribution'

export const HR_EMPLOYEE_ENTITY_CONSUMER_ID = 'hr-employee' as const
export const HR_EMPLOYEE_ENTITY_HOST_ID = 'entity_workspace' as const

export const HR_EMPLOYEE_ENTITY_HOST_CONTRIBUTIONS = [
  {
    class: 'platform_surface',
    capability_id: 'documents',
    owner: 'documents',
    contributor: 'documents',
    host: 'entity_workspace',
    consumer: 'hr-employee',
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
