import type { WorkspaceContributionDefinition } from './contribution'
import { WORKSPACE_HOST_REGION_IDS, type WorkspaceHostRegionId } from './hosts'
import { WORKSPACE_CAPABILITY_RENDERERS } from './renderers'
import type { WorkspaceCapabilityRenderContext } from './renderContext'

/**
 * Shared contribution protocol for both constitution hosts.
 * Hosts place; they do not own Notes/Consent/Recruitment/HR semantics.
 */
export function groupContributionsByRegion(
  contributions: readonly WorkspaceContributionDefinition[],
): Record<WorkspaceHostRegionId, WorkspaceContributionDefinition[]> {
  const ordered = [...contributions].sort((a, b) => a.ordering - b.ordering)
  const grouped = {} as Record<WorkspaceHostRegionId, WorkspaceContributionDefinition[]>
  for (const region of WORKSPACE_HOST_REGION_IDS) {
    grouped[region] = ordered.filter((row) => row.placement.region === region)
  }
  return grouped
}

export function renderWorkspaceContribution(
  row: WorkspaceContributionDefinition,
  ctx: WorkspaceCapabilityRenderContext,
) {
  const Renderer = WORKSPACE_CAPABILITY_RENDERERS[row.component_id as keyof typeof WORKSPACE_CAPABILITY_RENDERERS]
  if (!Renderer) return null
  return <Renderer key={row.capability_id} {...ctx} />
}
