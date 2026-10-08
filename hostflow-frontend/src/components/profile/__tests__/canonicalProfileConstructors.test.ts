/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { completeFieldBindings } from '../ProfileFieldConstructor'
import { completeDocumentBindings } from '../ProfileDocumentConstructor'

describe('canonical profile binding completion', () => {
  it('round-trips field levels with canonical identity and defaults missing fields to hidden', () => {
    const catalog = [
      { id: 'field-1', qualified_code: 'recruitment.candidate.name' },
      { id: 'field-2', qualified_code: 'recruitment.candidate.phone' },
    ] as any
    expect(completeFieldBindings(catalog, [{
      canonical_field_id: 'field-1', qualified_code: 'recruitment.candidate.name', requirement_level: 'required', sort_order: 10,
    }])).toEqual([
      { canonical_field_id: 'field-1', qualified_code: 'recruitment.candidate.name', requirement_level: 'required', sort_order: 10 },
      { canonical_field_id: 'field-2', qualified_code: 'recruitment.candidate.phone', requirement_level: 'hidden', sort_order: 20 },
    ])
  })

  it('round-trips document levels using immutable version identity', () => {
    const catalog = [
      { document_type_version_id: 'version-1' },
      { document_type_version_id: 'version-2' },
    ] as any
    expect(completeDocumentBindings(catalog, [{
      document_type_version_id: 'version-1', requirement_level: 'preferred', sort_order: 10,
    }])).toEqual([
      { document_type_version_id: 'version-1', requirement_level: 'preferred', sort_order: 10 },
      { document_type_version_id: 'version-2', requirement_level: 'hidden', sort_order: 20 },
    ])
  })
})
