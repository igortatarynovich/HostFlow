// @vitest-environment node
import { describe, expect, it } from 'vitest'
import type { HrDocumentFieldReview } from '../../../api/workforce'
import {
  formatRecruiterValueForField,
  profileValueForField,
  resolveHrFieldInputType,
  stringifyProfileValue,
} from '../hrVerificationFieldMeta'

function field(partial: Partial<HrDocumentFieldReview> & { field_code: string }): HrDocumentFieldReview {
  return {
    label: partial.label ?? partial.field_code,
    ...partial,
  }
}

describe('hrVerificationFieldMeta', () => {
  it('resolves country and date input types', () => {
    expect(resolveHrFieldInputType(field({ field_code: 'address_country' }))).toBe('country')
    expect(resolveHrFieldInputType(field({ field_code: 'birth_date' }))).toBe('date')
    expect(resolveHrFieldInputType(field({ field_code: 'phone' }))).toBe('tel')
  })

  it('stringifies structured address objects', () => {
    expect(
      stringifyProfileValue({
        country: 'PL',
        city: 'Warsaw',
        street: 'Main',
        house: '1',
        zip: '00-001',
      }),
    ).toContain('Warsaw')
  })

  it('prefills field value from flattened profile keys', () => {
    const value = profileValueForField(
      field({
        field_code: 'address_street',
        current_profile_values: { 'snapshot.address_street': 'Marszałkowska' },
      }),
    )
    expect(value).toBe('Marszałkowska')
  })

  it('formats recruiter values for display', () => {
    const text = formatRecruiterValueForField(
      field({
        field_code: 'city',
        current_profile_values: { 'snapshot.city': 'Warsaw' },
      }),
    )
    expect(text).toBe('Warsaw')
  })
})
