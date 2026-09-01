import { describe, expect, it } from 'vitest'
import {
  defaultProfileForPurpose,
  PURPOSE_WIZARD_OPTIONS,
  purposeLabel,
  entityProfileLabel,
} from './intakeFormRoutingSummary'

describe('intakeFormRoutingSummary wizard copy', () => {
  it('puts company request first and candidate application second', () => {
    expect(PURPOSE_WIZARD_OPTIONS[0]?.purpose).toBe('inquiry')
    expect(PURPOSE_WIZARD_OPTIONS[0]?.prominence).toBe('primary')
    expect(PURPOSE_WIZARD_OPTIONS[1]?.purpose).toBe('application')
    expect(PURPOSE_WIZARD_OPTIONS[0]?.hint.toLowerCase()).toContain('not a form for the worker')
    expect(PURPOSE_WIZARD_OPTIONS[1]?.hint.toLowerCase()).toContain('themselves')
  })

  it('defaults company request to driver hiring, not candidate Driver C+E', () => {
    const profiles = [
      { code: 'recruitment.candidate.driver_ce', name: 'Driver C+E' },
      { code: 'service_sales.targeted_advertising', name: 'Targeted advertising' },
      { code: 'service_sales.driver_hiring', name: 'Company driver hiring' },
    ]
    expect(defaultProfileForPurpose(profiles, 'inquiry')).toBe('service_sales.driver_hiring')
    expect(defaultProfileForPurpose(profiles, 'application')).toBe('recruitment.candidate.driver_ce')
  })

  it('falls back to targeted advertising when driver hiring is absent', () => {
    const profiles = [
      { code: 'service_sales.targeted_advertising', name: 'Targeted advertising' },
    ]
    expect(defaultProfileForPurpose(profiles, 'inquiry')).toBe('service_sales.targeted_advertising')
  })

  it('uses operator-facing names instead of advertising jargon', () => {
    expect(purposeLabel('inquiry')).toBe('Company request')
    expect(entityProfileLabel('service_sales.driver_hiring')).toMatch(/hiring drivers/i)
    expect(entityProfileLabel('service_sales.warehouse_hiring')).toMatch(/warehouse/i)
    expect(entityProfileLabel('service_sales.targeted_advertising')).toMatch(/advertising/i)
  })
})
