/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import {
  mappingClosePath,
  mappingClosePathCurrent,
  type MappingClosePathInput,
} from '../mappingClosePath'

function states(mapping: MappingClosePathInput) {
  return mappingClosePath(mapping).map((step) => `${step.id}:${step.state}`)
}

describe('mappingClosePath', () => {
  it('starts on schema when the form has no questions yet', () => {
    expect(states({})).toEqual([
      'schema:current',
      'example:upcoming',
      'map:upcoming',
      'projection:upcoming',
      'applied:upcoming',
    ])
    expect(mappingClosePathCurrent({})).toBe('schema')
  })

  it('asks for an example after schema, even if mapping is already Ready', () => {
    const mapping: MappingClosePathInput = {
      has_schema: true,
      schema_fields: [{ source: 'q1' }],
      summary: { headline: 'all_set' },
    }
    expect(mappingClosePathCurrent(mapping)).toBe('example')
    expect(states(mapping)[0]).toBe('schema:done')
    expect(states(mapping)[2]).toBe('map:done')
  })

  it('asks to map after schema and example exist', () => {
    const mapping: MappingClosePathInput = {
      has_schema: true,
      has_sample: true,
      sample_evidence: { present: true },
    }
    expect(mappingClosePathCurrent(mapping)).toBe('map')
  })

  it('shows projection after Ready, then applied after a real submission', () => {
    const ready: MappingClosePathInput = {
      has_schema: true,
      has_sample: true,
      summary: { headline: 'all_set' },
    }
    expect(mappingClosePathCurrent(ready)).toBe('projection')

    const projected = { ...ready, projection: [{ sentence: 'next writes Wiza' }] }
    expect(mappingClosePathCurrent(projected)).toBe('applied')

    const applied = {
      ...projected,
      applied_evidence: { present: true },
    }
    expect(mappingClosePathCurrent(applied)).toBeNull()
    expect(states(applied).every((row) => row.endsWith(':done'))).toBe(true)
  })
})
