import { describe, expect, it } from 'vitest'

import { sanitizeStagePath, TERMINAL_STAGE_CODES } from '../Pipeline'

describe('Pipeline stage path helpers', () => {
  it('drops intermediate terminal stages when target differs', () => {
    const original = ['permit_received', 'probation_ok', 'rejected']
    const result = sanitizeStagePath(original, 'rejected', TERMINAL_STAGE_CODES)
    expect(result).toEqual(['permit_received', 'rejected'])
  })

  it('keeps terminal stage when it is the target', () => {
    const original = ['permit_received', 'probation_ok']
    const result = sanitizeStagePath(original, 'probation_ok', TERMINAL_STAGE_CODES)
    expect(result).toEqual(original)
  })
})
