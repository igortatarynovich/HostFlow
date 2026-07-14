import { describe, expect, it } from 'vitest'

import {
  SERVICE_SALES_QUESTIONNAIRE_PREFIX,
  fieldOptionsForCode,
  resolveFieldWidget,
} from '../intakePresentationFieldOptions'
import {
  evaluatePresentationFields,
  pruneHiddenPresentationValues,
  type PresentationFieldWithRules,
} from '../presentationRules'

const t = (key: string, options?: { defaultValue?: string }) => options?.defaultValue || key

function salesField(
  suffix: string,
  rules?: PresentationFieldWithRules['presentation_rules'],
): PresentationFieldWithRules {
  return {
    qualified_code: `${SERVICE_SALES_QUESTIONNAIRE_PREFIX}${suffix}`,
    sort_order: 10,
    intake_level: 'optional',
    label: suffix,
    field_type: suffix.includes('materials') || suffix === 'recruitment_roles' ? 'multi_select' : 'single_select',
    widget_hint: suffix.includes('materials') || suffix === 'recruitment_roles' ? 'multi_select' : 'single_select',
    presentation_rules: rules,
  }
}

const NEED_TYPE = `${SERVICE_SALES_QUESTIONNAIRE_PREFIX}need_type`
const GEO_SCOPE = `${SERVICE_SALES_QUESTIONNAIRE_PREFIX}client_geo_scope`

const BASE_FIELDS: PresentationFieldWithRules[] = [
  { ...salesField('need_type'), intake_level: 'required', field_type: 'single_select' },
  { ...salesField('primary_outcome'), intake_level: 'required', field_type: 'single_select' },
  {
    ...salesField('promotion_subject'),
    presentation_rules: {
      show_if: {
        source_field: NEED_TYPE,
        operator: 'in',
        value: ['client_acquisition', 'product_sales', 'service_promotion'],
      },
    },
  },
  {
    ...salesField('client_geo_detail'),
    field_type: 'text',
    widget_hint: 'text',
    presentation_rules: {
      show_if: {
        source_field: GEO_SCOPE,
        operator: 'in',
        value: ['single_city', 'selected_region'],
      },
    },
  },
  {
    ...salesField('recruitment_roles'),
    presentation_rules: {
      show_if: { source_field: NEED_TYPE, operator: 'eq', value: 'employee_recruitment' },
    },
  },
]

describe('sales questionnaire presentation', () => {
  it('exposes Polish option labels for need_type', () => {
    const options = fieldOptionsForCode(`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}need_type`, t, 'pl')
    expect(options.map((item) => item.value)).toContain('client_acquisition')
    expect(options.find((item) => item.value === 'client_acquisition')?.label).toMatch(/klient/i)
  })

  it('renders single_select and multi_select widgets', () => {
    expect(
      resolveFieldWidget({
        qualified_code: `${SERVICE_SALES_QUESTIONNAIRE_PREFIX}need_type`,
        widget_hint: 'single_select',
        field_type: 'single_select',
      }),
    ).toBe('single_select')
    expect(
      resolveFieldWidget({
        qualified_code: `${SERVICE_SALES_QUESTIONNAIRE_PREFIX}marketing_materials`,
        widget_hint: 'multi_select',
        field_type: 'multi_select',
      }),
    ).toBe('multi_select')
  })

  it('shows sales branch fields for client_acquisition', () => {
    const values = {
      [NEED_TYPE]: 'client_acquisition',
    }
    const evaluated = evaluatePresentationFields(BASE_FIELDS, values)
    const visible = evaluated.filter((field) => field.evaluated.visible).map((field) => field.qualified_code)
    expect(visible).toContain(`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}promotion_subject`)
    expect(visible).not.toContain(`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}recruitment_roles`)
  })

  it('shows recruitment branch fields for employee_recruitment', () => {
    const values = {
      [NEED_TYPE]: 'employee_recruitment',
    }
    const evaluated = evaluatePresentationFields(BASE_FIELDS, values)
    const visible = evaluated.filter((field) => field.evaluated.visible).map((field) => field.qualified_code)
    expect(visible).toContain(`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}recruitment_roles`)
    expect(visible).not.toContain(`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}promotion_subject`)
  })

  it('shows client_geo_detail only for city/region scope', () => {
    const hidden = evaluatePresentationFields(BASE_FIELDS, {
      [NEED_TYPE]: 'client_acquisition',
      [GEO_SCOPE]: 'poland',
    })
    expect(
      hidden.find((field) => field.qualified_code.endsWith('client_geo_detail'))?.evaluated.visible,
    ).toBe(false)

    const visible = evaluatePresentationFields(BASE_FIELDS, {
      [NEED_TYPE]: 'client_acquisition',
      [GEO_SCOPE]: 'single_city',
    })
    expect(
      visible.find((field) => field.qualified_code.endsWith('client_geo_detail'))?.evaluated.visible,
    ).toBe(true)
  })

  it('drops hidden branch values before submit', () => {
    const values = {
      [NEED_TYPE]: 'client_acquisition',
      [`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}promotion_subject`]: 'service',
      [`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}recruitment_roles`]: ['driver_ce'],
    }
    const evaluated = evaluatePresentationFields(BASE_FIELDS, values)
    const pruned = pruneHiddenPresentationValues(values, evaluated)
    expect(pruned[`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}promotion_subject`]).toBe('service')
    expect(pruned[`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}recruitment_roles`]).toBeUndefined()
  })

  it('clears recruitment values after switching branch before submit', () => {
    const switched = {
      [NEED_TYPE]: 'employee_recruitment',
      [`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}promotion_subject`]: 'service',
      [`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}recruitment_roles`]: ['driver_ce'],
    }
    const evaluated = evaluatePresentationFields(BASE_FIELDS, switched)
    const pruned = pruneHiddenPresentationValues(switched, evaluated)
    expect(pruned[`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}promotion_subject`]).toBeUndefined()
    expect(pruned[`${SERVICE_SALES_QUESTIONNAIRE_PREFIX}recruitment_roles`]).toEqual(['driver_ce'])
  })
})
