import StageTag from '../../../components/StageTag'
import type { AugmentedCandidate } from '../types'

/**
 * Этап в списке — только цветной бейдж; смена этапа — в карточке или массово.
 */
export function CandidatesTableRowStageCell({ candidate }: { candidate: AugmentedCandidate }) {
  return (
    <div className="min-w-0 max-w-[min(220px,100%)]">
      <StageTag code={candidate.stage} size="sm" />
    </div>
  )
}
