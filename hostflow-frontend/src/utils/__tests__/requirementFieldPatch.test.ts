import { describe, expect, it } from 'vitest'

import type { Candidate } from '../../api/types'
import {
  buildRequirementFieldPatch,
  formatAddressDisplay,
  readRequirementFieldValue,
  requirementFieldInputKind,
} from '../requirementFieldPatch'

const baseCandidate = {
  id: 'cand-1',
  first_name: 'Jan',
  last_name: 'Kowalski',
  phone: '+48111222333',
  email: 'jan@example.com',
  extra: {
    citizenship: 'PL',
    experience_eu_years: 4,
    address: { city: 'Warsaw', street: 'Marszałkowska', country: 'PL' },
  },
} as Candidate

describe('requirementFieldPatch', () => {
  it('maps known qualified codes to input kinds', () => {
    expect(requirementFieldInputKind('platform.identity.citizenship')).toBe('country')
    expect(requirementFieldInputKind('recruitment.candidate.experience.years_ce')).toBe('number')
    expect(requirementFieldInputKind('platform.identity.address')).toBe('address_line')
  })

  it('reads values from candidate model', () => {
    expect(readRequirementFieldValue(baseCandidate, 'recruitment.candidate.first_name')).toBe('Jan')
    expect(readRequirementFieldValue(baseCandidate, 'platform.identity.citizenship')).toBe('PL')
    expect(readRequirementFieldValue(baseCandidate, 'recruitment.candidate.experience.years_ce')).toBe('4')
    expect(readRequirementFieldValue(baseCandidate, 'platform.identity.address')).toBe(
      'Marszałkowska, Warsaw, PL',
    )
  })

  it('formats address display from string or object', () => {
    expect(formatAddressDisplay('Warsaw, Test 1')).toBe('Warsaw, Test 1')
    expect(formatAddressDisplay({ city: 'Krakow', street: 'Main', country: 'PL' })).toContain('Krakow')
  })

  it('builds PATCH payloads for data fields', () => {
    expect(buildRequirementFieldPatch('recruitment.candidate.first_name', 'Adam', baseCandidate)).toEqual({
      first_name: 'Adam',
    })

    expect(
      buildRequirementFieldPatch('platform.identity.citizenship', 'UA', baseCandidate).extra,
    ).toMatchObject({
      citizenship: 'UA',
    })

    expect(
      buildRequirementFieldPatch('recruitment.candidate.experience.years_ce', '7', baseCandidate).extra,
    ).toMatchObject({
      experience_eu_years: 7,
      years_ce: 7,
    })

    const addressPatch = buildRequirementFieldPatch(
      'platform.identity.address',
      'Warsaw, Test Street 1',
      baseCandidate,
    )
    expect(addressPatch.extra).toMatchObject({ address: 'Warsaw, Test Street 1' })
    expect(addressPatch.personal_data).toMatchObject({ address: 'Warsaw, Test Street 1' })
  })
})
