import { describe, expect, it } from 'vitest'
import { fieldOptionsForCode } from './intakePresentationFieldOptions'
import { DRIVER_HIRING_QUESTIONNAIRE_PREFIX } from './driverHiringFieldOptions'

const t = (key: string, options?: { defaultValue?: string }) => options?.defaultValue || key

describe('driver hiring company questionnaire options', () => {
  it('exposes C / C+E / D categories', () => {
    const options = fieldOptionsForCode(
      `${DRIVER_HIRING_QUESTIONNAIRE_PREFIX}driver_categories`,
      t,
      'ru',
    )
    expect(options.map((row) => row.value)).toEqual(['c', 'ce', 'd', 'other'])
  })

  it('exposes pay system including per-day', () => {
    const options = fieldOptionsForCode(`${DRIVER_HIRING_QUESTIONNAIRE_PREFIX}pay_system`, t, 'en')
    expect(options.some((row) => row.value === 'per_day')).toBe(true)
  })
})
