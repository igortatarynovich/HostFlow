import { describe, expect, it } from 'vitest'
import { applyCommercialDefaultsPrefill } from '../../api/clientAccounts'

describe('applyCommercialDefaultsPrefill', () => {
  it('returns empty for missing defaults', () => {
    expect(applyCommercialDefaultsPrefill(null)).toEqual({})
    expect(applyCommercialDefaultsPrefill(undefined)).toEqual({})
  })

  it('maps commercial defaults to form strings', () => {
    expect(
      applyCommercialDefaultsPrefill({
        currency: 'EUR',
        payment_term_days: 21,
        payment_model: 'per_hire',
        vat_rate: 23,
        guarantee_days: 90,
      }),
    ).toEqual({
      currency: 'EUR',
      payment_term_days: '21',
      payment_model: 'per_hire',
      vat_rate: '23',
      guarantee_days: '90',
    })
  })
})
