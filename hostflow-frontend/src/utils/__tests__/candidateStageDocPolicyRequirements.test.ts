import { describe, expect, it } from 'vitest'
import {
  pipelineRelaxedRequirementsFromOverrides,
  relaxRequirementBlockers,
} from '../candidateStageDocPolicy'

describe('relaxRequirementBlockers', () => {
  it('removes waived requirement codes from blocker lists', () => {
    const relaxed = pipelineRelaxedRequirementsFromOverrides([
      {
        status: 'approved',
        granted_scope: 'pipeline',
        requirement_code: 'driver_license_with_code95',
      },
    ])
    const out = relaxRequirementBlockers(
      {
        missing: ['identity_document', 'driver_license_with_code95'],
        problematic: [],
        inProgress: [],
      },
      relaxed,
    )
    expect(out.missing).toEqual(['identity_document'])
  })
})
