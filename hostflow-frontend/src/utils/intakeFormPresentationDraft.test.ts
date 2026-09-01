import { describe, expect, it } from 'vitest'
import {
  fieldsToPayload,
  mergeCatalogWithPreset,
  publicIntakeUrlForSlug,
  slugifyFieldCodeFromLabel,
} from './intakeFormPresentationDraft'

describe('intakeFormPresentationDraft', () => {
  it('selects preset questions even when the catalog is still empty', () => {
    const rows = mergeCatalogWithPreset(
      [],
      [
        {
          qualified_code: 'service_sales.driver_hiring.contact_company_name',
          intake_level: 'required',
          sort_order: 10,
          label_override: 'fields.service_sales_driver_hiring_contact_company_name',
        },
        {
          qualified_code: 'service_sales.driver_hiring.contact_email',
          intake_level: 'optional',
          sort_order: 20,
        },
      ],
    )
    expect(rows.filter((row) => row.selected)).toHaveLength(2)
    expect(fieldsToPayload(rows).map((field) => field.qualified_code)).toEqual([
      'service_sales.driver_hiring.contact_company_name',
      'service_sales.driver_hiring.contact_email',
    ])
    expect(fieldsToPayload(rows)[0].label_override).toBeUndefined()
  })

  it('keeps preset selection after catalog fields arrive', () => {
    const preset = [
      {
        qualified_code: 'service_sales.driver_hiring.contact_company_name',
        intake_level: 'required' as const,
        sort_order: 10,
      },
    ]
    const first = mergeCatalogWithPreset([], preset)
    const next = mergeCatalogWithPreset(
      [
        {
          qualified_code: 'service_sales.driver_hiring.contact_company_name',
          label: 'Company name',
          intake_level: 'optional',
          field_type: 'text',
          sort_order: 10,
        },
        {
          qualified_code: 'service_sales.driver_hiring.base_location',
          label: 'Base',
          intake_level: 'optional',
          field_type: 'text',
          sort_order: 20,
        },
      ],
      preset,
      first,
    )
    expect(next.find((row) => row.qualified_code.endsWith('contact_company_name'))?.selected).toBe(true)
    expect(next.find((row) => row.qualified_code.endsWith('base_location'))?.selected).toBe(false)
  })

  it('slugifies a typed question name into a field code suffix', () => {
    expect(slugifyFieldCodeFromLabel('Company name')).toBe('company_name')
  })

  it('adds client kind and lang to the public URL', () => {
    const url = publicIntakeUrlForSlug('company-needs-drivers', {
      applicationKind: 'client',
      lang: 'ru',
    })
    expect(url).toContain('lead_form_slug=company-needs-drivers')
    expect(url).toContain('application_kind=client')
    expect(url).toContain('lang=ru')
  })
})
