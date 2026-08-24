import { describe, expect, it } from 'vitest'
import { roleMayLoadFullCommunicationsSettings } from './communicationsSettingsAccess'

describe('roleMayLoadFullCommunicationsSettings', () => {
  it('allows administrator and supervisor', () => {
    expect(roleMayLoadFullCommunicationsSettings('administrator')).toBe(true)
    expect(roleMayLoadFullCommunicationsSettings('supervisor')).toBe(true)
  })

  it('allows employee team_lead without treating every employee as admin', () => {
    expect(roleMayLoadFullCommunicationsSettings('employee', { presetId: 'team_lead' })).toBe(true)
    expect(roleMayLoadFullCommunicationsSettings('employee', { presetId: 'recruiter' })).toBe(false)
    expect(roleMayLoadFullCommunicationsSettings('recruiter')).toBe(false)
    expect(roleMayLoadFullCommunicationsSettings('employee')).toBe(false)
  })
})
