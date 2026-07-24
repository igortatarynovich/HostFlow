/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { humanizeMetaPlaceholder } from '../sourceCardPresentation'

describe('source card terminology helpers', () => {
  it('detects technical Meta form placeholders', () => {
    expect(humanizeMetaPlaceholder('Meta form 1917672235588961', '1917672235588961')).toBeNull()
    expect(humanizeMetaPlaceholder('Drivers PL', '1917672235588961')).toBe('Drivers PL')
  })
})
