/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { humanizeMetaPlaceholder, sourceMappingReady } from '../sourceCardPresentation'

describe('source card terminology helpers', () => {
  it('detects technical Meta form placeholders', () => {
    expect(humanizeMetaPlaceholder('Meta form 1917672235588961', '1917672235588961')).toBeNull()
    expect(humanizeMetaPlaceholder('Drivers PL', '1917672235588961')).toBe('Drivers PL')
  })

  it('treats all_set as mapping ready, anything else as a Mapping CTA', () => {
    expect(sourceMappingReady({ mapping_headline: 'all_set' })).toBe(true)
    expect(sourceMappingReady({ mapping_headline: 'needs_check' })).toBe(false)
    expect(sourceMappingReady({})).toBe(false)
  })
})
