import type { ReactNode } from 'react'
import type { WorkspaceContributionDefinition } from './contribution'
import { WORKSPACE_HOST_REGION_IDS, type WorkspaceHostRegionId } from './hosts'
import { groupContributionsByRegion, renderWorkspaceContribution } from './placement'
import type { WorkspaceCapabilityRenderContext, WorkspaceEntityRef } from './renderContext'

export type EntityWorkspacePlacedRegions = Record<WorkspaceHostRegionId, ReactNode>

type Props = {
  contributions: readonly WorkspaceContributionDefinition[]
  entity: WorkspaceEntityRef
  patching?: boolean
  onClose: () => void
  onRefresh: () => void
  /**
   * Chrome adapter. Entity Shell / D1 zones render here.
   * Shared and platform capabilities must come from `placed`, not from the
   * adapter composing them itself.
   */
  children?: (placed: EntityWorkspacePlacedRegions) => ReactNode
}

/**
 * Entity Workspace host placer. Same Capability Host Contract as
 * ApplicationWorkspaceCapabilityHost: regions + contribution protocol only.
 * Not a proof-screen. Not G4. Must not import Notes/Consent/Recruitment/HR.
 */
export function EntityWorkspaceCapabilityHost({
  contributions,
  entity,
  patching = false,
  onClose,
  onRefresh,
  children,
}: Props) {
  const ctx: WorkspaceCapabilityRenderContext = {
    host: 'entity_workspace',
    entity,
    patching,
    onClose,
    onRefresh,
  }
  const byRegion = groupContributionsByRegion(contributions)
  const placed = {} as EntityWorkspacePlacedRegions
  for (const region of WORKSPACE_HOST_REGION_IDS) {
    placed[region] = byRegion[region].map((row) => renderWorkspaceContribution(row, ctx))
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col" data-workspace-capability-host="entity_workspace">
      {children
        ? children(placed)
        : WORKSPACE_HOST_REGION_IDS.map((region) => {
            const rows = byRegion[region]
            if (!rows.length) return null
            return (
              <div key={region} data-host-region={region}>
                {placed[region]}
              </div>
            )
          })}
    </div>
  )
}
