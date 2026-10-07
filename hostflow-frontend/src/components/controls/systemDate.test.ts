import { describe, expect, it } from 'vitest'
import { formatSystemDate, maskSystemDate, parseSystemDate } from './systemDate'

describe('systemDate', () => {
  it('keeps a single digit and accepts only a complete date', () => {
    expect(maskSystemDate('1', 'DD.MM.YYYY')).toBe('1')
    expect(parseSystemDate('1', 'DD.MM.YYYY')).toBeNull()
    expect(maskSystemDate('15012027', 'DD.MM.YYYY')).toBe('15.01.2027')
    expect(parseSystemDate('15.01.2027', 'DD.MM.YYYY')).toBe('2027-01-15')
    expect(parseSystemDate('31.02.2027', 'DD.MM.YYYY')).toBeNull()
  })

  it('uses the profile format both ways', () => {
    expect(formatSystemDate('2027-01-15', 'YYYY-MM-DD')).toBe('2027-01-15')
    expect(parseSystemDate('01/15/2027', 'MM/DD/YYYY')).toBe('2027-01-15')
    expect(formatSystemDate('2027-01-15', 'MM/DD/YYYY')).toBe('01/15/2027')
  })
})