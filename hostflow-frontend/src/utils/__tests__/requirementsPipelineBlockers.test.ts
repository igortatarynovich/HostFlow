import { describe, expect, it } from 'vitest'

import {
  mapRequirementPipelineBlockers,
  mapRequirementsChecklistToBlockers,
} from '../requirementsPipelineBlockers'

describe('mapRequirementsChecklistToBlockers', () => {
  it('maps legal stay as a single missing requirement blocker', () => {
    const blockers = mapRequirementsChecklistToBlockers({
      candidate_id: 'c1',
      all_fulfilled: false,
      pipeline_blockers: {
        missing_requirements: ['legal_stay_confirmation'],
        problematic_requirements: [],
        pending_review_requirements: [],
      },
      requirements: [],
    })
    expect(blockers.missing).toEqual(['legal_stay_confirmation'])
    expect(blockers.problematic).toEqual([])
    expect(blockers.inProgress).toEqual([])
  })

  it('does not emit visa and karta pobytu as separate blockers', () => {
    const blockers = mapRequirementPipelineBlockers({
      missing_requirements: ['legal_stay_confirmation'],
    })
    expect(blockers.missing).not.toContain('visa')
    expect(blockers.missing).not.toContain('karta_pobytu')
  })
})
