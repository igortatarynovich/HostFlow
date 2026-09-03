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

  it('translates cargo types and later-section answers into Polish', () => {
    const cargo = fieldOptionsForCode(`${DRIVER_HIRING_QUESTIONNAIRE_PREFIX}cargo_types`, t, 'pl')
    expect(cargo.find((row) => row.value === 'distribution')?.label).toBe('Dystrybucja')
    expect(cargo.find((row) => row.value === 'containers')?.label).toBe('Kontenery')
    expect(cargo.find((row) => row.value === 'car_transporter')?.label).toBe('Autowóz')
    expect(cargo.find((row) => row.value === 'other')?.label).toBe('Inne')

    const housing = fieldOptionsForCode(`${DRIVER_HIRING_QUESTIONNAIRE_PREFIX}housing_between_trips`, t, 'pl')
    expect(housing.map((row) => row.label)).toEqual(['Tak', 'Nie', 'Nie dotyczy'])

    const parking = fieldOptionsForCode(`${DRIVER_HIRING_QUESTIONNAIRE_PREFIX}personal_car_parking`, t, 'pl')
    expect(parking.map((row) => row.label)).toEqual(['Tak', 'Nie'])

    const feedback = fieldOptionsForCode(`${DRIVER_HIRING_QUESTIONNAIRE_PREFIX}feedback_time`, t, 'pl')
    expect(feedback.find((row) => row.value === 'same_day')?.label).toBe('Tego samego dnia')

    const problems = fieldOptionsForCode(`${DRIVER_HIRING_QUESTIONNAIRE_PREFIX}hiring_problems`, t, 'pl')
    expect(problems.find((row) => row.value === 'not_enough_candidates')?.label).toBe('Za mało kandydatów')

    const refusal = fieldOptionsForCode(`${DRIVER_HIRING_QUESTIONNAIRE_PREFIX}refusal_reasons`, t, 'pl')
    expect(refusal.find((row) => row.value === 'pay')?.label).toBe('Wynagrodzenie')
    expect(refusal.find((row) => row.value === 'other')?.label).toBe('Inne')
  })
})
