import { describe, expect, it } from 'vitest'

import type { Lead } from '../../api/types'
import { leadIntakeFormAnswerRows } from '../leadIntakeFormAnswers'

function metaLead(overrides: Partial<Lead> & Record<string, unknown> = {}): Lead {
  return {
    id: '00000000-0000-4000-8000-000000000011',
    tenant_id: '00000000-0000-4000-8000-000000000022',
    source: 'meta',
    status: 'needs_routing',
    payload: {},
    created_at: '2026-01-01T00:00:00.000Z',
    ...overrides,
  } as Lead
}

describe('leadIntakeFormAnswerRows', () => {
  it('returns named values and skips utm / ids', () => {
    const rows = leadIntakeFormAnswerRows(
      metaLead({
        normalized: {
          field_answers: [
            { name: 'full_name', values: ['Jan Kowalski'] },
            { name: 'Do you have Code95?', values: ['Yes'] },
            { name: 'utm_source', values: ['fb'] },
            { name: 'leadgen_id', values: ['123'] },
            { name: 'empty', values: [''] },
          ],
        },
      }),
    )
    expect(rows.map((r) => r.label)).toEqual(['Full name', 'Do you have Code95?'])
    expect(rows[1]?.value).toBe('Yes')
  })

  it('returns empty when field_answers missing', () => {
    expect(leadIntakeFormAnswerRows(metaLead({ normalized: {} }))).toEqual([])
  })

  it('prefers stored question labels over field codes', () => {
    const rows = leadIntakeFormAnswerRows(
      metaLead({
        normalized: {
          field_answers: [{ name: 'jaka_masz_kategorie', values: ['C+E'], label: 'Jaką masz kategorię?' }],
        },
      }),
    )
    expect(rows[0]?.label).toBe('Jaką masz kategorię?')
  })
})
