// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { normalizeDocumentPackProjection } from '../normalize'

describe('normalizeDocumentPackProjection', () => {
  it('normalizes backend pack payload with expiry gaps', () => {
    const pack = normalizeDocumentPackProjection({
      code: 'legal_stay_pack',
      label: 'Legal Stay Pack',
      status: 'gaps',
      skeleton: false,
      applies: true,
      ref_pack_codes: ['pl_non_eu_worker'],
      required: ['passport'],
      present: ['passport'],
      missing: [],
      expired: ['passport'],
      expiring_soon: [],
      missing_expiry: [],
      gaps: ['passport'],
      blockers: ['passport'],
      warnings: [],
      expiry: {
        all_documents_valid: false,
        has_expiring_documents: false,
        has_expired_documents: true,
        has_missing_expiry: false,
      },
    })

    expect(pack).not.toBeNull()
    expect(pack?.status).toBe('gaps')
    expect(pack?.expired).toEqual(['passport'])
    expect(pack?.expiry?.has_expired_documents).toBe(true)
  })

  it('returns null for invalid payload', () => {
    expect(normalizeDocumentPackProjection(null)).toBeNull()
    expect(normalizeDocumentPackProjection({})).toBeNull()
  })

  it('defaults missing arrays for partial payloads', () => {
    const pack = normalizeDocumentPackProjection({
      code: 'driver_pack',
      label: 'Driver Pack',
      status: 'gaps',
    })
    expect(pack?.missing).toEqual([])
    expect(pack?.expired).toEqual([])
    expect(pack?.expiring_soon).toEqual([])
    expect(pack?.gaps).toEqual([])
  })
})
