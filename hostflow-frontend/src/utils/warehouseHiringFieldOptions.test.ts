import { describe, expect, it } from 'vitest'
import { fieldOptionsForCode } from './intakePresentationFieldOptions'
import { WAREHOUSE_HIRING_QUESTIONNAIRE_PREFIX } from './warehouseHiringFieldOptions'

const t = (key: string, options?: { defaultValue?: string }) => options?.defaultValue || key

describe('warehouse hiring company questionnaire options', () => {
  it('exposes warehouse / laborer roles from the operator table', () => {
    const options = fieldOptionsForCode(
      `${WAREHOUSE_HIRING_QUESTIONNAIRE_PREFIX}worker_roles`,
      t,
      'ru',
    )
    expect(options.map((row) => row.value)).toEqual([
      'warehouse',
      'picker',
      'packer',
      'sorter',
      'loader',
      'production',
      'laborer',
      'forklift_operator',
      'other',
    ])
  })

  it('exposes pay units as PLN or EUR per hour or month', () => {
    const options = fieldOptionsForCode(
      `${WAREHOUSE_HIRING_QUESTIONNAIRE_PREFIX}pay_netto_unit`,
      t,
      'en',
    )
    expect(options.map((row) => row.value)).toEqual(['pln_hour', 'pln_month', 'eur_hour', 'eur_month'])
  })
})
