import { CommunicationCapability } from '../../platform/capabilities/communication/CommunicationCapability'

type Props = {
  candidateId: string
}

/** D4 communication adapter — host places CommunicationCapability; this file stays the Candidate-shaped entry. */
export function CandidateCommunicationSlot({ candidateId }: Props) {
  return (
    <CommunicationCapability
      entity={{ resourceType: 'candidate', resourceId: candidateId }}
      patching={false}
      onClose={() => undefined}
      onRefresh={() => undefined}
    />
  )
}
