/**
 * Capability Host Contract — hosts and regions.
 *
 * Two constitution types implement the same contract. Do not fold
 * Application Workspace into Entity Workspace.
 * Host owns placement only. Registry is not this contract.
 */

export const WORKSPACE_CAPABILITY_HOST_IDS = [
  'entity_workspace',
  'application_workspace',
] as const

export type WorkspaceCapabilityHostId = (typeof WORKSPACE_CAPABILITY_HOST_IDS)[number]

/** Host regions. D2 slot ids are not extra regions — they bind under `platform_slot`. */
export const WORKSPACE_HOST_REGION_IDS = [
  'header',
  'summary',
  'overview',
  'rail',
  'decision',
  'platform_slot',
] as const

export type WorkspaceHostRegionId = (typeof WORKSPACE_HOST_REGION_IDS)[number]

export type WorkspaceHostContract = {
  host: WorkspaceCapabilityHostId
  constitution: '§3.3' | '§3.2'
  regions: readonly WorkspaceHostRegionId[]
}

export const ENTITY_WORKSPACE_HOST = {
  host: 'entity_workspace',
  constitution: '§3.3',
  regions: WORKSPACE_HOST_REGION_IDS,
} as const satisfies WorkspaceHostContract

export const APPLICATION_WORKSPACE_HOST = {
  host: 'application_workspace',
  constitution: '§3.2',
  regions: WORKSPACE_HOST_REGION_IDS,
} as const satisfies WorkspaceHostContract

export const WORKSPACE_CAPABILITY_HOSTS = {
  entity_workspace: ENTITY_WORKSPACE_HOST,
  application_workspace: APPLICATION_WORKSPACE_HOST,
} as const
