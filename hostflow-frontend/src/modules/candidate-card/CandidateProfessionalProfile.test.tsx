import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { I18nProvider } from '../../i18n'
import { CandidateProfessionalProfile } from './CandidateProfessionalProfile'
import type { ProfessionalProfileProjection } from './professionalProfileView'

function aggregate(
  status: ProfessionalProfileProjection['experience']['aggregates']['ce']['status'],
  years: string | null = null,
) {
  return { status, years, days: null, presence: [], raw_presence: [] }
}

function profile(): ProfessionalProfileProjection {
  return {
    capabilities: {
      licence: { categories: ['CE'], raw_unmapped: [], issuing_country: null, valid_to: null },
      code95: { presence: true, valid_to: null },
      tachograph: { presence: null, issuing_country: null, valid_to: null },
      adr: { presence: true, issuing_country: null, valid_to: null },
    },
    experience: {
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
        work_areas: [{ kind: 'region', code: 'dach' }],
        trailer_types: ['Tautliner'],
      }],
      aggregates: {
        total_tenure: aggregate('calculated', '5.0000'),
        ce: aggregate('ambiguous_history'),
        international: aggregate('presence_only'),
        eu: aggregate('no_evidence'),
      },
      practical_experience: {
        trailers: {
          status: 'presence_only',
          years: null,
          items: [{ code: 'Tautliner', mapping: 'unmapped', target_code: null }],
        },
      },
      geography: { work_areas: [{ kind: 'region', code: 'dach', resolution: 'unmapped' }] },
      work_character: { operation_scopes: [], movement_patterns: [], crew_modes: [] },
      declared: {
        ce: { status: 'declared', years: '7', origin: 'ce_written_as_eu' },
        eu: { status: 'no_evidence', years: '7' },
        non_eu_years: { stored_value: null, interpreted_as: 'no_evidence' },
        legacy_total: { stored_value: null, interpreted_as: 'no_evidence' },
      },
    },
    constraints: [
      {
        id: 'live',
        subject: 'medical',
        code: 'fit',
        effect: 'blocked',
        source: 'operator',
        valid_from: null,
        valid_to: null,
        activity: 'active',
        note: null,
      },
      {
        id: 'old',
        subject: 'medical',
        code: 'fit',
        effect: 'blocked',
        source: 'operator',
        valid_from: null,
        valid_to: '2026-10-17',
        activity: 'expired',
        note: null,
      },
    ],
    preferences_and_availability: {
      choices: [],
      compensation: null,
      availability: { available_from: null, status: 'no_evidence' },
    },
  }
}

describe('CandidateProfessionalProfile', () => {
  it('renders resolver phrases and keeps empty evidence out of the numbers', () => {
    render(
      <I18nProvider initialLocale="ru">
        <CandidateProfessionalProfile profile={profile()} />
      </I18nProvider>,
    )
    expect(screen.getByTestId('professional-summary').textContent).toContain('CE · проверьте историю (заявлено 7)')
    expect(screen.getByTestId('professional-summary').textContent).toContain('Международные · есть опыт')
    expect(screen.getByTestId('professional-summary').textContent).not.toContain('ЕС')
    expect(screen.getByTestId('professional-summary').textContent).not.toMatch(/\b0\b/)
    expect(screen.getByTestId('profile-duration-international').textContent).toContain('есть опыт')
    expect(screen.getByTestId('profile-tenure').textContent).toContain('Рассчитанный стаж')
    expect(screen.getByTestId('profile-experience-character')).toBeTruthy()
    expect(screen.getByText('История работы')).toBeTruthy()
    expect(screen.queryByTestId('profile-duration-eu')).toBeNull()
    expect(screen.getByTestId('profile-duration-total').textContent).toContain('5 лет')
    expect(screen.getByTestId('profile-employment-bad').textContent).toContain('Broken · Driver')
    expect(screen.getByTestId('profile-employment-bad').textContent).toContain('Ошибка периода работы')
    expect(screen.getByTestId('profile-employment-bad').textContent).not.toContain('2024-01-01')
    expect(screen.getByTestId('profile-trailer-Tautliner').textContent).toContain('Tautliner · не сопоставлено')
    expect(screen.getByTestId('profile-area-region-dach').textContent).toContain('dach · не сопоставлено')
    expect(screen.getByTestId('profile-constraint-live').textContent).not.toContain('Истекло')
    fireEvent.click(screen.getByRole('button', { name: /История ограничений/ }))
    expect(screen.getByTestId('profile-constraint-history-old').textContent).toContain('Истекло')
    expect(screen.getByText('Нет предпочтений')).toBeTruthy()
    expect(screen.queryByText('calculated')).toBeNull()
    expect(screen.queryByText('presence_only')).toBeNull()
    expect(screen.queryByText('insufficient_history')).toBeNull()
  })

  it('says there is no employment history when the projection has none', () => {
    const empty = profile()
    empty.experience.employments = []
    empty.experience.aggregates.total_tenure = aggregate('no_evidence')
    empty.experience.aggregates.ce = aggregate('no_evidence')
    empty.experience.declared.ce = { status: 'no_evidence', years: null, origin: null }
    empty.experience.aggregates.international = aggregate('no_evidence')
    empty.experience.practical_experience.trailers.items = []
    empty.experience.geography.work_areas = []
    empty.constraints = []
    render(
      <I18nProvider initialLocale="ru">
        <CandidateProfessionalProfile profile={empty} />
      </I18nProvider>,
    )
    expect(screen.getByText('История работы')).toBeTruthy()
    expect(screen.getByTestId('profile-no-employment').textContent).toContain('Нет истории работы')
    expect(screen.queryByTestId('profile-duration-total')).toBeNull()
    expect(screen.queryByTestId('profile-duration-eu')).toBeNull()
  })

  it('edits availability on the row with save and cancel', () => {
    const row = profile()
    row.preferences_and_availability.availability.available_from = '2026-11-01'
    render(
      <I18nProvider initialLocale="ru">
        <CandidateProfessionalProfile profile={row} candidateId="candidate-1" canEditAvailability />
      </I18nProvider>,
    )
    const availability = screen.getByTestId('profile-available-from')
    expect(availability.textContent).toContain('2026-11-01')
    fireEvent.click(within(availability).getByRole('button', { name: 'Редактировать' }))
    expect(screen.getByTestId('profile-available-from-input')).toBeTruthy()
    expect(within(availability).getByRole('button', { name: 'Сохранить' })).toBeTruthy()
    expect(within(availability).getByRole('button', { name: 'Отмена' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Готово' })).toBeNull()
    fireEvent.click(within(availability).getByRole('button', { name: 'Отмена' }))
    expect(screen.queryByTestId('profile-available-from-input')).toBeNull()
    expect(availability.textContent).toContain('2026-11-01')
  })
})
