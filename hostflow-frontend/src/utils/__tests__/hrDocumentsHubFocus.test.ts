// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { resolveFocusedEmployeeId } from '../hrDocumentsHubFocus'

describe('resolveFocusedEmployeeId', () => {
  const rows = [
    { workforce_employee_id: 'emp-aaa-111' },
    { workforce_employee_id: 'emp-bbb-222' },
    { workforce_employee_id: 'emp-aaa-111' },
  ]

  it('returns null when filter is empty', () => {
    expect(resolveFocusedEmployeeId('', rows)).toBeNull()
  })

  it('returns null when zero employees match', () => {
    expect(resolveFocusedEmployeeId('emp-zzz', rows)).toBeNull()
  })

  it('returns null when more than one employee matches', () => {
    expect(resolveFocusedEmployeeId('emp-', rows)).toBeNull()
  })

  it('returns the employee id when exactly one matches', () => {
    expect(resolveFocusedEmployeeId('bbb', rows)).toBe('emp-bbb-222')
  })
})
