import { describe, expect, it } from 'vitest'
import {
  durationLines,
  durationReading,
  employmentPeriodError,
  professionalSummary,
  splitConstraints,
  trailerLines,
  type ProfessionalProfileProjection,
  type ProfileCopy,
} from './professionalProfileView'

const copy: ProfileCopy = {
  history: (years) => `${years} лет по истории`,
  declared: (years) => `заявлено ${years}`,
  both: (calculated, declared) => `${calculated} лет по истории / заявлено ${declared}`,
  presence: 'есть опыт',
  insufficient: 'недостаточно истории',
  periodError: 'проверьте историю',
  rowPeriodError: 'Ошибка периода работы',
  hasExperience: 'есть опыт',
  unmapped: (code) => `${code} · не сопоставлено`,
  openEnded: 'по настоящее время',
  noEmployment: 'Нет истории работы',
  noPreferences: 'Нет предпочтений',
  availableFrom: (date) => date,
  present: 'есть',
  absent: 'нет',
  unknown: 'нет данных',
  expired: 'истекло',
  scheduled: 'ещё не действует',
  validityUnknown: 'срок не определён',
}

function aggregate(status: ProfessionalProfileProjection['experience']['aggregates']['ce']['status'], years: string | null = null) {
  return { status, years, days: null, presence: [], raw_presence: [] }
}

function profile(patch: Partial<ProfessionalProfileProjection> = {}): ProfessionalProfileProjection {
  const base: ProfessionalProfileProjection = {
    capabilities: {
      licence: { categories: [], raw_unmapped: [], issuing_country: null, valid_to: null },
      code95: { presence: null, valid_to: null },
      tachograph: { presence: null, issuing_country: null, valid_to: null },
      adr: { presence: null, issuing_country: null, valid_to: null },
    },
    experience: {
      employments: [],
      aggregates: {
        total_tenure: aggregate('no_evidence'),
        ce: aggregate('no_evidence'),
        international: aggregate('no_evidence'),
        eu: aggregate('no_evidence'),
      },
      practical_experience: { trailers: { status: 'no_evidence', years: null, items: [] } },
      geography: { work_areas: [] },
      work_character: { operation_scopes: [], movement_patterns: [], crew_modes: [] },
      declared: {
        ce: { status: 'no_evidence', years: null, origin: null },
        eu: { status: 'no_evidence', years: null },
        non_eu_years: { stored_value: null, interpreted_as: 'no_evidence' },
        legacy_total: { stored_value: null, interpreted_as: 'no_evidence' },
      },
    },
    constraints: [],
    preferences_and_availability: {
      choices: [],
      compensation: null,
      availability: { available_from: null, status: 'no_evidence' },
    },
  }
  return {
    ...base,
    ...patch,
    capabilities: { ...base.capabilities, ...patch.capabilities },
    experience: { ...base.experience, ...patch.experience },
    preferences_and_availability: { ...base.preferences_and_availability, ...patch.preferences_and_availability },
  }
}

describe('professional profile view', () => {
  it('shows calculated and declared together when they differ', () => {
    const reading = durationReading(aggregate('calculated', '5.0000'), '7')
    const row = profile({
      experience: {
        ...profile().experience,
        aggregates: { ...profile().experience.aggregates, ce: aggregate('calculated', '5.0000') },
        declared: { ...profile().experience.declared, ce: { status: 'declared', years: '7', origin: 'ce_written_as_eu' } },
      },
      capabilities: {
        ...profile().capabilities,
        code95: { presence: true, valid_to: null },
        adr: { presence: true, valid_to: null },
      },
    })
    expect(reading.kind).toBe('both')
    expect(professionalSummary(row, copy, 'ru')).toEqual([
      'CE 5 лет (заявлено 7)',
      'Code 95 ✓',
      'ADR ✓',
    ])
  })

  it('shows both numbers when calculated equals declared', () => {
    const row = profile({
      experience: {
        ...profile().experience,
        aggregates: { ...profile().experience.aggregates, ce: aggregate('calculated', '5.0000') },
        declared: { ...profile().experience.declared, ce: { status: 'declared', years: '5', origin: 'ce_written_as_eu' } },
      },
    })
    expect(professionalSummary(row, copy, 'ru')).toEqual(['CE 5 лет (заявлено 5)'])
  })

  it('shows only declared or only calculated', () => {
    const declaredOnly = profile({
      experience: {
        ...profile().experience,
        declared: { ...profile().experience.declared, ce: { status: 'declared', years: '7', origin: 'ce_written_as_eu' } },
      },
    })
    const calculatedOnly = profile({
      experience: {
        ...profile().experience,
        aggregates: { ...profile().experience.aggregates, international: aggregate('calculated', '5.0000') },
      },
    })
    expect(professionalSummary(declaredOnly, copy, 'ru')).toEqual(['CE · заявлено 7'])
    expect(professionalSummary(calculatedOnly, copy, 'ru')).toEqual(['Международные 5 лет'])
  })

  it('does not turn presence or no evidence into a number', () => {
    const row = profile({
      experience: {
        ...profile().experience,
        aggregates: {
          ...profile().experience.aggregates,
          ce: aggregate('presence_only'),
          eu: aggregate('no_evidence'),
        },
      },
    })
    const summary = professionalSummary(row, copy, 'ru')
    expect(summary).toEqual(['CE · есть опыт'])
    expect(summary.join(' ')).not.toMatch(/0/)
    expect(durationLines(row, copy, 'ru').some((line) => line.id === 'eu')).toBe(false)
  })

  it('names a broken period instead of hiding it as missing history', () => {
    const row = profile({
      experience: {
        ...profile().experience,
        aggregates: { ...profile().experience.aggregates, ce: aggregate('ambiguous_history') },
        employments: [{
          id: 'bad',
          employer_name: 'Broken',
          country: 'DE',
          position: 'Driver',
          start_date: '2024-01-01',
          end_date: '2023-01-01',
          driving_categories: ['CE'],
          operation_scopes: [],
          movement_patterns: [],
          crew_modes: [],
          work_areas: [],
          trailer_types: [],
        }],
      },
    })
    expect(professionalSummary(row, copy, 'ru')).toEqual(['CE · проверьте историю'])
    expect(durationLines(row, copy, 'ru').some((line) => line.id === 'ce')).toBe(false)
    expect(employmentPeriodError('2024-01-01', '2023-01-01')).toBe(true)
  })

  it('keeps an open employment and an unmapped code visible', () => {
    expect(employmentPeriodError('2020-01-01', null)).toBe(false)
    const row = profile({
      experience: {
        ...profile().experience,
        aggregates: { ...profile().experience.aggregates, total_tenure: aggregate('insufficient_history') },
        practical_experience: {
          trailers: {
            status: 'presence_only',
            years: null,
            items: [{ code: 'Tautliner', mapping: 'unmapped', target_code: null }],
          },
        },
        geography: { work_areas: [{ kind: 'region', code: 'dach', resolution: 'unmapped' }] },
      },
    })
    expect(durationLines(row, copy, 'ru').find((line) => line.id === 'total')?.text).toBe('недостаточно истории')
    expect(trailerLines(row, copy, 'ru')).toEqual([{ code: 'Tautliner', unmapped: true, text: 'Tautliner · не сопоставлено' }])
    expect(row.experience.geography.work_areas[0].code).toBe('dach')
  })

  it('separates active constraints from expired ones and empty preferences', () => {
    const row = profile({
      constraints: [
        { id: 'now', subject: 'route', code: 'night', effect: 'limited', source: 'operator_recorded', valid_from: null, valid_to: null, activity: 'active', note: null },
        { id: 'old', subject: 'vehicle', code: 'bus', effect: 'prohibited', source: 'medical', valid_from: null, valid_to: '2020-01-01', activity: 'expired', note: null },
      ],
    })
    expect(splitConstraints(row).current.map((item) => item.id)).toEqual(['now'])
    expect(splitConstraints(row).history.map((item) => item.id)).toEqual(['old'])
    expect(row.preferences_and_availability.choices).toEqual([])
    expect(row.preferences_and_availability.availability.status).toBe('no_evidence')
  })
})
