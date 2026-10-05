import { describe, expect, it } from 'vitest'
import {
  coverageKeysForStoredDocType,
  documentTypeMatchesRequiredSet,
  normalizeDocTypeCode,
  persistRecruitmentDocType,
  prefersCombinedLicenseUpload,
} from '../documentUtils'

describe('combined EU license document type', () => {
  it('does not collapse combined license to plain driver_license', () => {
    expect(normalizeDocTypeCode('driver_license_code95')).toBe('driver_license_code95')
    expect(normalizeDocTypeCode('driver_license_with_code95')).toBe('driver_license_code95')
    expect(persistRecruitmentDocType('eu_license_code95')).toBe('driver_license_code95')
  })

  it('lets one combined file cover license and Code 95 slots', () => {
    const keys = coverageKeysForStoredDocType('driver_license_code95')
    expect(keys).toEqual(expect.arrayContaining(['driver_license', 'code95', 'driver_qualification_card']))
    expect(prefersCombinedLicenseUpload(['driver_license', 'code95'])).toBe(true)
    expect(prefersCombinedLicenseUpload(['passport'])).toBe(false)
  })

  it('keeps a slot only when the projected required set names it', () => {
    expect(documentTypeMatchesRequiredSet('visa', ['passport'])).toBe(false)
    expect(documentTypeMatchesRequiredSet('residence_permit', ['passport', 'driver_license_code95'])).toBe(false)
    expect(documentTypeMatchesRequiredSet('driver_license_code95', ['passport', 'driver_license_code95'])).toBe(true)
    expect(documentTypeMatchesRequiredSet('work_permit', [])).toBe(false)
  })
})
