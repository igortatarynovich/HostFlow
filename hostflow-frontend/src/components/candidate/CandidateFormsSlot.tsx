import { FormsCapability } from '../../platform/capabilities/forms/FormsCapability'

/** D4 forms adapter — host places FormsCapability; this file stays the Candidate-shaped entry. */
export function CandidateFormsSlot() {
  return (
    <FormsCapability
      patching={false}
      onClose={() => undefined}
      onRefresh={() => undefined}
    />
  )
}
