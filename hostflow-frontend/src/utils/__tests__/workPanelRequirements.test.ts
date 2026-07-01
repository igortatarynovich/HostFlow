import { describe, expect, it } from 'vitest'
import {
  blockersFromWorkPanelRequirements,
  parseWorkPanelRequirementsSummary,
} from '../workPanelRequirements'

describe('workPanelRequirements', () => {
  it('maps pipeline_blockers from requirements_summary without visa/karta split', () => {
    const summary = parseWorkPanelRequirementsSummary({
      all_fulfilled: false,
      pipeline_blockers: {
        missing_requirements: ['legal_stay_confirmation', 'identity_document'],
        problematic_requirements: [],
        pending_review_requirements: [],
      },
      items: [
        {
          requirement_code: 'legal_stay_confirmation',
          public_name: 'Legal stay',
          fulfilled: false,
          evaluation_status: 'missing',
        },
      ],
    })
    const blockers = blockersFromWorkPanelRequirements(summary)
    expect(blockers.missing).toEqual(['legal_stay_confirmation', 'identity_document'])
    expect(blockers.missing).not.toContain('visa')
    expect(blockers.missing).not.toContain('karta_pobytu')
  })
})
