import { describe, expect, it } from 'vitest'

import {
  readLatestSubmission,
  readSubmissionAnswerValues,
  salesQuestionnaireToQualifiedValues,
  submissionHasDisplayableAnswers,
} from '../salesQuestionnaireSubmission'
import {
  buildSubmissionAnswerRows,
  formatSubmissionFieldValue,
} from '../salesQuestionnaireSubmissionDisplay'
import type { PresentationFieldWithRules } from '../presentationRules'

const t = (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key

describe('salesQuestionnaireSubmission', () => {
  it('reads latest submission only', () => {
    const lead = {
      normalized: {
        submissions_v1: [
          { submission_id: 'a', normalized_values: { 'service_sales.targeted_advertising.need_type': 'old' } },
          {
            submission_id: 'b',
            normalized_values: {
              'service_sales.targeted_advertising.recruitment_other_role': 'Warehouse pickers',
            },
          },
        ],
      },
    }
    expect(readLatestSubmission(lead)?.submission_id).toBe('b')
    expect(readSubmissionAnswerValues(lead as never, readLatestSubmission(lead), 'service_sales.targeted_advertising')).toEqual({
      'service_sales.targeted_advertising.recruitment_other_role': 'Warehouse pickers',
    })
  })

  it('falls back to sales_questionnaire when submissions_v1 is missing', () => {
    const lead = {
      normalized: {
        sales_questionnaire: {
          need_type: 'recruitment',
          recruitment_other_role: 'Warehouse pickers',
        },
      },
    }
    expect(submissionHasDisplayableAnswers(lead as never)).toBe(true)
    expect(salesQuestionnaireToQualifiedValues(lead, 'service_sales.targeted_advertising')).toEqual({
      'service_sales.targeted_advertising.need_type': 'recruitment',
      'service_sales.targeted_advertising.recruitment_other_role': 'Warehouse pickers',
    })
  })
})

describe('salesQuestionnaireSubmissionDisplay', () => {
  const fields: PresentationFieldWithRules[] = [
    {
      qualified_code: 'service_sales.targeted_advertising.need_type',
      sort_order: 10,
      intake_level: 'required',
      label: 'Czego dotyczy Państwa potrzeba?',
      field_type: 'single_select',
      widget_hint: 'single_select',
    },
    {
      qualified_code: 'service_sales.targeted_advertising.primary_outcome',
      sort_order: 20,
      intake_level: 'required',
      label: 'Jaki wynik jest dla Państwa najważniejszy?',
      field_type: 'single_select',
      widget_hint: 'single_select',
    },
    {
      qualified_code: 'service_sales.targeted_advertising.recruitment_other_role',
      sort_order: 40,
      intake_level: 'optional',
      label: 'Jakie stanowisko?',
      field_type: 'text',
      widget_hint: 'text',
    },
    {
      qualified_code: 'service_sales.targeted_advertising.marketing_materials',
      sort_order: 270,
      intake_level: 'optional',
      label: 'Materiały',
      field_type: 'multi_select',
      widget_hint: 'multi_select',
    },
    {
      qualified_code: 'service_sales.targeted_advertising.hidden_note',
      sort_order: 999,
      intake_level: 'hidden',
      label: 'Hidden',
      field_type: 'text',
    },
  ]

  it('humanizes single_select values instead of showing raw codes', () => {
    expect(
      formatSubmissionFieldValue('fill_roles', fields[1], { t, locale: 'en' }),
    ).toBe('Fill Roles')
  })

  it('builds ordered rows for submitted values only', () => {
    const rows = buildSubmissionAnswerRows({
      values: {
        'service_sales.targeted_advertising.primary_outcome': 'fill_roles',
        'service_sales.targeted_advertising.recruitment_other_role': 'Warehouse pickers',
        'service_sales.targeted_advertising.hidden_note': 'secret',
        'service_sales.targeted_advertising.marketing_materials': ['photos', 'logo'],
      },
      presentationFields: fields,
      t,
      locale: 'en',
    })

    expect(rows.map((row) => row.label)).toEqual([
      'Jaki wynik jest dla Państwa najważniejszy?',
      'Jakie stanowisko?',
      'Materiały',
    ])
    expect(rows[0].value).toBe('Fill Roles')
    expect(rows[1].value).toBe('Warehouse pickers')
    expect(rows[2].value).toBe('Photos, Logo')
  })

  it('shows answers removed from current presentation with fallback labels', () => {
    const currentPresentation: PresentationFieldWithRules[] = [
      {
        qualified_code: 'service_sales.targeted_advertising.recruitment_other_role',
        sort_order: 40,
        intake_level: 'optional',
        label: 'Jakie stanowisko?',
        field_type: 'text',
        widget_hint: 'text',
      },
    ]

    const rows = buildSubmissionAnswerRows({
      values: {
        'service_sales.targeted_advertising.recruitment_other_role': 'Warehouse pickers',
        'service_sales.targeted_advertising.legacy_budget_band': '2000_5000',
      },
      presentationFields: currentPresentation,
      t,
      locale: 'en',
    })

    expect(rows).toHaveLength(2)
    expect(rows[0]).toMatchObject({
      label: 'Jakie stanowisko?',
      value: 'Warehouse pickers',
    })
    expect(rows[1]).toMatchObject({
      qualifiedCode: 'service_sales.targeted_advertising.legacy_budget_band',
      label: 'Legacy Budget Band',
      value: '2000_5000',
    })
  })
})
