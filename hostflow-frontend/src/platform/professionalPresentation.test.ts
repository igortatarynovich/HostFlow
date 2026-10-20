import { describe, expect, it } from 'vitest'
import {
  presentCompensation,
  presentCountry,
  presentDuration,
  presentMonthSpan,
  presentProfessionalCode,
  presentUnmapped,
} from './professionalPresentation'

describe('shared professional presentation', () => {
  it('turns resolver days into years and months', () => {
    expect(presentDuration(1825, '5.0000', 'ru')).toBe('5 лет')
    expect(presentDuration(2006, '5.4959', 'ru')).toBe('5 лет 6 мес.')
    expect(presentDuration(1827, '5.0055', 'ru')).toBe('5 лет')
    expect(presentDuration(null, '5.0000', 'ru')).toBe('5 лет')
  })

  it('labels system catalog codes and leaves unknown codes unlabeled', () => {
    expect(presentProfessionalCode('work_area_region', 'eu', 'ru')).toBe('ЕС')
    expect(presentProfessionalCode('operation_scope', 'domestic', 'ru')).toBe('Внутренние перевозки')
    expect(presentProfessionalCode('movement_pattern', 'long_haul', 'ru')).toBe('Дальние рейсы')
    expect(presentProfessionalCode('work_system', '2_1', 'ru')).toBe('2/1')
    expect(presentProfessionalCode('trailer_hiring', 'curtain', 'ru')).toBe('Штора')
    expect(presentProfessionalCode('work_area_region', 'dach', 'ru')).toBeNull()
    expect(presentUnmapped('Tautliner', 'ru')).toBe('Tautliner · не сопоставлено')
  })

  it('formats pay as an amount per period', () => {
    expect(presentCompensation('4000.00', 'EUR', 'monthly_fixed', 'ru')).toBe('4 000 EUR / месяц')
  })

  it('shows a month span and a country name', () => {
    expect(presentMonthSpan('2020-01-03', '2024-12-31', 'по настоящее время')).toBe('01.2020–12.2024')
    expect(presentCountry('DE', 'ru')).toBe('Германия')
  })
})