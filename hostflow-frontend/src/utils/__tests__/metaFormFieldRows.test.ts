import { describe, expect, it } from 'vitest'

import {
  buildMetaFormFieldRows,
  collectFieldEntriesFromMetaPayloadPreview,
  mappingRowCoversSource,
} from '../metaFormFieldRows'

describe('mappingRowCoversSource', () => {
  it('matches comma-separated sources case-insensitively', () => {
    expect(
      mappingRowCoversSource({ sourceText: 'phone_number, mobile', target: 'phone' }, 'Phone_Number'),
    ).toBe(true)
    expect(mappingRowCoversSource({ sourceText: 'email', target: 'email' }, 'phone')).toBe(false)
  })
})

describe('collectFieldEntriesFromMetaPayloadPreview', () => {
  it('extracts first values from field_data', () => {
    const payload = JSON.stringify({
      entry: [
        {
          changes: [
            {
              value: {
                field_data: [
                  { name: 'full_name', values: ['Jan Kowalski'] },
                  { name: 'phone_number', values: ['+48123456789'] },
                ],
              },
            },
          ],
        },
      ],
    })
    expect(collectFieldEntriesFromMetaPayloadPreview(payload)).toEqual({
      full_name: 'Jan Kowalski',
      phone_number: '+48123456789',
    })
  })
})

describe('buildMetaFormFieldRows', () => {
  it('prefers Graph value_preview over incoming payload', () => {
    const payload = JSON.stringify({
      entry: [{ changes: [{ value: { field_data: [{ name: 'country', values: ['Poland'] }] } }] }],
    })
    const rows = buildMetaFormFieldRows({
      graphFields: [{ name: 'country', value_preview: 'Ukraine' }],
      incomingPayloads: [payload],
      incomingNormalized: [],
      mappingRows: [{ sourceText: 'country', target: 'country' }],
    })
    expect(rows).toHaveLength(1)
    expect(rows[0]?.sampleValue).toBe('Ukraine')
    expect(rows[0]?.mapped).toBe(true)
    expect(rows[0]?.target).toBe('country')
  })

  it('includes raw_field_names without sample and marks unmapped', () => {
    const rows = buildMetaFormFieldRows({
      graphFields: [],
      incomingPayloads: [],
      incomingNormalized: [JSON.stringify({ raw_field_names: ['experience_years'] })],
      mappingRows: [],
    })
    expect(rows).toHaveLength(1)
    expect(rows[0]?.name).toBe('experience_years')
    expect(rows[0]?.sampleValue).toBeNull()
    expect(rows[0]?.mapped).toBe(false)
    expect(rows[0]?.target).toBeNull()
  })

  it('deduplicates by field name', () => {
    const rows = buildMetaFormFieldRows({
      graphFields: [
        { name: 'email', value_preview: 'a@b.c' },
        { name: 'email', value_preview: 'ignored' },
      ],
      incomingPayloads: [],
      incomingNormalized: [],
      mappingRows: [],
    })
    expect(rows).toHaveLength(1)
  })
})
