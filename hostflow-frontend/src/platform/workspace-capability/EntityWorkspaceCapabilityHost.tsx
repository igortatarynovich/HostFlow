import type { WorkspaceContributionDefinition } from './contribution'
import { WORKSPACE_HOST_REGION_IDS } from './hosts'
import { groupContributionsByRegion, renderWorkspaceContribution } from './placement'
import type { WorkspaceCapabilityRenderContext, WorkspaceEntityRef } from './renderContext'

type Props = {
  contributions: readonly WorkspaceContributionDefinition[]
  entity: WorkspaceEntityRef
  patching?: boolean
  onClose: () => void
  onRefresh: () => void
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
}: Props) {
  const ctx: WorkspaceCapabilityRenderContext = {
    host: 'entity_workspace',
    entity,
    patching,
    onClose,
    onRefresh,
  }
  const byRegion = groupContributionsByRegion(contributions)

  return (
    <div className="flex min-h-0 flex-col" data-workspace-capability-host="entity_workspace">
      {WORKSPACE_HOST_REGION_IDS.map((region) => {
        const rows = byRegion[region]
        if (!rows.length) return null
        return (
          <div key={region} data-host-region={region}>
            {rows.map((row) => renderWorkspaceContribution(row, ctx))}
          </div>
        )
      })}
    </div>
  )
}
