import { describe, expect, it } from 'vitest'
import { primaryWorkItem } from '../HrStartAllowedPanel'
import type { EmploymentStartAllowedOut } from '../../../api/employmentStartAllowed'

describe('HrStartAllowedPanel primary work', () => {
  it('uses ui_primary_item as the only operator work item', () => {
    const result = {
      policy_id: 'employment_start_allowed.v1',
      decision: 'missing',
      start_allowed: false,
      active_missing: [
        { code: 'written_employment_contract_or_confirmation' },
        { code: 'occupational_medical_fit_for_post' },
        { code: 'introductory_bhp_before_admit' },
      ],
      primary_item: { code: 'written_employment_contract_or_confirmation', message: 'Contract' },
      ui_primary_item: { code: 'written_employment_contract_or_confirmation', message: 'Contract' },
    } as EmploymentStartAllowedOut
    expect(primaryWorkItem(result)?.code).toBe('written_employment_contract_or_confirmation')
    expect(result.active_missing?.length).toBe(3)
  })

  it('prefers ui_primary_item when present', () => {
    const result = {
      policy_id: 'employment_start_allowed.v1',
      decision: 'missing',
      start_allowed: false,
      primary_item: { code: 'a' },
      ui_primary_item: { code: 'b' },
    } as EmploymentStartAllowedOut
    expect(primaryWorkItem(result)?.code).toBe('b')
  })
})
