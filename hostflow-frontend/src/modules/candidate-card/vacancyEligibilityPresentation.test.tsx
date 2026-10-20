import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { I18nProvider } from '../../i18n'
import { CandidateVacancyEligibility, VacancyEligibilityBlock } from './CandidateVacancyEligibility'
import { presentVacancyEligibility, type EligibilityProjection } from './vacancyEligibilityPresentation'

function projection(status: string, requirements: EligibilityProjection['requirements']): EligibilityProjection {
  return {
    candidate_id: 'cand',
    vacancy_id: 'vac',
    shadow_eligibility: status,
    requirements,
  }
}

describe('vacancy eligibility presentation', () => {
  it('turns evaluator rows into recruiter language and hides system codes', () => {
    const view = presentVacancyEligibility(projection('needs_info', [
      {
        qualified_code: 'capability:driving_category:CE',
        strength: 'mandatory',
        affects_eligibility: true,
        expected: { domain: 'capability', code: 'CE' },
        evidence: { categories: ['CE'] },
        result: 'match',
        reason: 'capability_present',
        provenance: [{ source: 'capabilities' }],
      },
      {
        qualified_code: 'experience:total',
        strength: 'mandatory',
        affects_eligibility: true,
        expected: { domain: 'experience', mode: 'minimum', code: 'total', minimum_days: 730 },
        evidence: { days: 1005, years: '2.7534' },
        result: 'match',
        reason: 'calculated_meets_minimum',
        provenance: [{ source: 'experience.aggregates.total_tenure', employment_ids: ['job-1'] }],
      },
      {
        qualified_code: 'experience:trailer_hiring:curtain',
        strength: 'mandatory',
        affects_eligibility: true,
        expected: { domain: 'experience', code: 'curtain' },
        evidence: null,
        result: 'needs_info',
        reason: 'experience_not_recorded',
        provenance: [{ source: 'experience.practical_experience.trailers' }],
      },
      {
        qualified_code: 'experience:international',
        strength: 'preferred',
        affects_eligibility: false,
        result: 'match',
        reason: 'experience_present',
      },
    ]), 'ru')

    expect(view?.statusLabel).toBe('Недостаточно данных')
    expect(view?.countLabel).toBe('2/3 требований подтверждено')
    expect(view?.rows.map((row) => row.requirement)).toEqual([
      'Категория CE',
      'Опыт ≥ 2 года',
      'Штора',
    ])
    expect(view?.rows[0].evidence).toBe('Кандидат: CE')
    expect(view?.rows[0].source).toBe('Источник: квалификация')
    expect(view?.rows[1].evidence).toBe('Рассчитано: 2 года 9 мес.')
    expect(view?.rows[1].source).toBe('Источник: история работы')
    expect(view?.rows[2].evidence).toBe('В подтверждённой истории опыт не найден')
    expect(JSON.stringify(view)).not.toContain('qualified_code')
    expect(JSON.stringify(view)).not.toContain('job-1')
    expect(JSON.stringify(view)).not.toContain('capability_present')
  })

  it('does not call a missing vacancy an eligibility status', () => {
    expect(presentVacancyEligibility({ candidate_id: 'cand', vacancy_id: 'vac', unavailable: 'unknown_profile' }, 'ru')).toBeNull()
  })

  it('labels no_match as a mismatch and keeps the explanation closed until asked', () => {
    const view = presentVacancyEligibility(projection('no_match', [
      {
        qualified_code: 'capability:driving_category:CE',
        strength: 'mandatory',
        affects_eligibility: true,
        expected: { code: 'CE' },
        evidence: { categories: ['C'] },
        result: 'no_match',
        reason: 'capability_absent',
        provenance: [{ source: 'capabilities' }],
      },
    ]), 'ru')
    expect(view?.statusLabel).toBe('Не соответствует')
    expect(view?.statusLabel).not.toBe('Отклонён')
    render(
      <I18nProvider initialLocale="ru">
        <VacancyEligibilityBlock view={view!} />
      </I18nProvider>,
    )
    expect(screen.getByText('Не соответствует')).toBeTruthy()
    expect(screen.queryByText('Отклонён')).toBeNull()
    expect(screen.queryByText('Категория CE')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Подробнее' }))
    expect(screen.getByText('Категория CE')).toBeTruthy()
    expect(screen.getAllByRole('button')).toHaveLength(1)
  })
})

describe('vacancy eligibility on the card', () => {
  it('renders nothing when the card has no vacancy', () => {
    const { container } = render(
      <I18nProvider initialLocale="ru">
        <CandidateVacancyEligibility candidateId="cand" vacancyId={null} />
      </I18nProvider>,
    )
    expect(container).toBeEmptyDOMElement()
  })
})
