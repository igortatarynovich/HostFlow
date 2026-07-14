import { describe, expect, it } from 'vitest'

import type { Lead } from '../../api/types'
import {
  formatQualificationReasonLabel,
  readLeadQualificationPreview,
} from '../leadQualificationPreview'

const t = (key: string, opts?: { values?: Record<string, string | number> }) => {
  const map: Record<string, string> = {
    'app.leads.qualification.reasons.experience_eu_years_below':
      'EU experience: {actual} — min {min}',
    'app.leads.qualification.reasons.missing_experience_eu_years': 'EU years missing',
    'app.leads.qualification.reasons.missing_field': 'Missing: {field}',
    'app.leads.qualification.field_labels.experience_eu_years': 'EU years',
    'common.yes': 'Yes',
    'common.no': 'No',
  }
  let out = map[key] ?? key
  if (opts?.values) {
    for (const [k, v] of Object.entries(opts.values)) {
      out = out.replace(`{${k}}`, String(v))
    }
  }
  return out
}

describe('formatQualificationReasonLabel', () => {
  it('translates structured experience below min with detail suffix', () => {
    expect(formatQualificationReasonLabel('experience_eu_years_below:1:0', t)).toBe(
      'EU experience: {actual} — min {min} (1:0)',
    )
  })

  it('returns unknown legacy experience code unchanged', () => {
    expect(formatQualificationReasonLabel('experience_eu_years<1', t)).toBe('experience_eu_years<1')
  })

  it('returns unknown missing field codes unchanged', () => {
    expect(formatQualificationReasonLabel('missing:experience_eu_years', t)).toBe(
      'missing:experience_eu_years',
    )
  })
})

describe('readLeadQualificationPreview', () => {
  it('reads preview fit reasons from normalized payload', () => {
    const lead = {
      error: 'LEAD_FIT_NO_MATCH',
      normalized: {
        lead_qualification_preview_v1: {
          fit_status: 'no_fit',
          fit_reasons: ['experience_eu_years_below:1:0'],
        },
      },
    } as Lead

    const preview = readLeadQualificationPreview(lead.normalized)
    expect(preview?.fit_status).toBe('no_fit')
    expect(preview?.fit_reasons).toEqual(['experience_eu_years_below:1:0'])
  })
})
