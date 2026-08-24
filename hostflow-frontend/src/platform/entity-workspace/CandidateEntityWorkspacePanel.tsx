import {
  CANDIDATE_COMPOSITION_CONSUMER_ID,
  CANDIDATE_COMPOSITION_SLOTS,
  assertCandidateCompositionSlots,
} from './candidateConsumer'
import { EntityWorkspaceShell } from './EntityWorkspaceShell'
import type { EntityWorkspaceShellProps } from './types'
import { CANDIDATE_ENTITY_HOST_CONTRIBUTIONS } from '../workspace-capability/candidateEntity'
import { EntityWorkspaceCapabilityHost } from '../workspace-capability/EntityWorkspaceCapabilityHost'
import { CandidateCompositionBuilder } from './CandidateCompositionBuilder'
import { CandidateInformationLayout } from './CandidateInformationLayout'
import { CandidateQaPanel } from './CandidateQaPanel'

type Props = EntityWorkspaceShellProps & {
  entityId: string
  onClose: () => void
  onRefresh: () => void
}

/**
 * Candidate Entity host-equivalence bind. Not G4.
 * Host places platform surfaces including D2 `documents` (E4 Document Link).
 * Shell is chrome adapter only. Shell `documents` nav ≠ this slot.
 * CL3: overview Information zone places `entity_profile_layout.v1` / `candidate.card`.
 * CL4: composition builder compiles card into that zone; form is a separate artifact.
 * CL5: Q&A zone reads Lead / Application (`entity_profile_qa.v1`); not extra; not a layout widget.
 */
export function CandidateEntityWorkspacePanel({
  entityId,
  onClose,
  onRefresh,
  sectionRenderers,
  ...shellProps
}: Props) {
  assertCandidateCompositionSlots(CANDIDATE_COMPOSITION_SLOTS)

  return (
    <EntityWorkspaceCapabilityHost
      entity={{ resourceType: 'candidate', resourceId: entityId }}
      contributions={CANDIDATE_ENTITY_HOST_CONTRIBUTIONS}
      onClose={onClose}
      onRefresh={onRefresh}
    >
      {(placed) => (
        <EntityWorkspaceShell
          {...shellProps}
          sectionRenderers={{
            ...sectionRenderers,
            overview: () => (
              <div data-entity-workspace-slot="overview" className="space-y-4">
                <CandidateInformationLayout />
                <CandidateCompositionBuilder />
                <CandidateQaPanel />
                {sectionRenderers?.overview?.()}
                <div data-host-region="platform_slot">{placed.platform_slot}</div>
                <div data-host-region="overview">{placed.overview}</div>
              </div>
            ),
            timeline: () => (
              <div data-entity-workspace-slot="timeline">{sectionRenderers?.timeline?.()}</div>
            ),
          }}
        />
      )}
    </EntityWorkspaceCapabilityHost>
  )
}

export { CANDIDATE_COMPOSITION_CONSUMER_ID }
