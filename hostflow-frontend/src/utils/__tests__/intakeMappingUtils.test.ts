import { describe, expect, it } from 'vitest'

import {
  isQualifiedFieldCode,
  legacyTargetFromQualified,
  qualifiedCodeFromLegacyTarget,
  resolveMappingDisplayTarget,
  resolveMappingLegacyTarget,
} from '../intakeMappingUtils'

describe('intakeMappingUtils', () => {
  it('maps qualified phone code to legacy normalized target', () => {
    expect(legacyTargetFromQualified('recruitment.candidate.contacts.phone')).toBe('phone')
    expect(resolveMappingLegacyTarget('', 'recruitment.candidate.contacts.phone')).toBe('phone')
  })

  it('infers qualified code from legacy target', () => {
    expect(qualifiedCodeFromLegacyTarget('email')).toBe('recruitment.candidate.contacts.email')
  })

  it('prefers qualified code for display', () => {
    expect(
      resolveMappingDisplayTarget('phone', 'recruitment.candidate.contacts.phone'),
    ).toBe('recruitment.candidate.contacts.phone')
    expect(resolveMappingDisplayTarget('phone', null)).toBe('recruitment.candidate.contacts.phone')
  })

  it('detects qualified field code strings', () => {
    expect(isQualifiedFieldCode('recruitment.candidate.first_name')).toBe(true)
    expect(isQualifiedFieldCode('phone')).toBe(false)
  })
})
