import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'

import type { RecruitmentOverviewResponse } from '../../../../api/analytics'
import { I18nProvider, useI18n } from '../../../../i18n'
import { RecruitmentOverviewPanel } from '../RecruitmentOverviewPanel'

function overview(partial: Partial<RecruitmentOverviewResponse> = {}): RecruitmentOverviewResponse {
  const base: RecruitmentOverviewResponse = {
    period: { from: '2026-10-01', to: '2026-10-31' },
    acquisition: {
      time_basis: 'lead.created_at',
      new_returning_rule: 'candidate_created_at_strictly_before_lead_created_at_is_returning',
      leads_received: 0,
      unique_candidates_linked: 0,
      new_candidates: 0,
      returning_candidates: 0,
      leads_with_application: 0,
      leads_duplicated: 0,
      leads_in_duplicate_review: 0,
      by_source: [],
      by_vacancy: [],
    },
    recruitment: {
      time_basis: 'recruitment_application.applied_at',
      applications_started: 0,
      by_current_status: [],
      by_vacancy: [],
      by_recruiter: [],
    },
    people: { time_basis: 'candidate.created_at', new_candidates: 0 },
    historical_gap: { linked_recruitment_leads_without_application: 0 },
    limitations: ['application_status_is_current_snapshot_of_started_cohort'],
  }
  return {
    ...base,
    ...partial,
    acquisition: { ...base.acquisition, ...partial.acquisition },
    recruitment: { ...base.recruitment, ...partial.recruitment },
    people: { ...base.people, ...partial.people },
    historical_gap: { ...base.historical_gap, ...partial.historical_gap },
  }
}

function PanelBridge({ data }: { data: RecruitmentOverviewResponse }) {
  const { t } = useI18n()
  const formatNumber = (value?: number) => new Intl.NumberFormat('ru-RU').format(value ?? 0)
  return <RecruitmentOverviewPanel t={t} formatNumber={formatNumber} overview={data} loading={false} />
}

function renderPanel(data: RecruitmentOverviewResponse) {
  return render(
    <I18nProvider initialLocale="ru">
      <PanelBridge data={data} />
    </I18nProvider>,
  )
}

describe('Recruitment overview grains', () => {
  it('places lead, candidate, and application counts in separate sections', () => {
    renderPanel(
      overview({
        acquisition: {
          leads_received: 2,
          unique_candidates_linked: 1,
          new_candidates: 1,
          returning_candidates: 1,
          leads_with_application: 2,
          leads_duplicated: 1,
          by_source: [
            { source: 'facebook', leads: 1, unique_candidates_linked: 1, leads_with_application: 1 },
            { source: 'website', leads: 1, unique_candidates_linked: 1, leads_with_application: 1 },
          ],
          by_vacancy: [
            { vacancy_id: 'a', vacancy_name: 'Vacancy A', leads: 1, unique_candidates_linked: 1, leads_with_application: 1 },
            { vacancy_id: 'b', vacancy_name: 'Vacancy B', leads: 1, unique_candidates_linked: 1, leads_with_application: 1 },
          ],
        },
        people: { time_basis: 'candidate.created_at', new_candidates: 1 },
        recruitment: {
          applications_started: 2,
          by_current_status: [{ status: 'hired', count: 1 }],
          by_vacancy: [
            { vacancy_id: 'a', vacancy_name: 'Vacancy A', applications: 1 },
            { vacancy_id: 'b', vacancy_name: 'Vacancy B', applications: 1 },
            { vacancy_id: null, vacancy_name: null, applications: 0 },
          ],
          by_recruiter: [{ recruiter_id: null, recruiter_name: null, applications: 2 }],
        },
      }),
    )

    const leads = screen.getByTestId('overview-acquisition')
    const people = screen.getByTestId('overview-people')
    const recruitment = screen.getByTestId('overview-recruitment')

    expect(within(leads).getByTestId('kpi-leads-received')).toHaveTextContent('2')
    expect(within(leads).getByTestId('kpi-unique-candidates')).toHaveTextContent('1')
    expect(within(leads).getByTestId('kpi-acquisition-new')).toHaveTextContent('Отклики новых кандидатов')
    expect(within(leads).getByTestId('kpi-acquisition-new')).toHaveTextContent('1')
    expect(within(leads).getByTestId('kpi-acquisition-returning')).toHaveTextContent('1')
    expect(within(leads).queryByText('Новые кандидаты')).not.toBeInTheDocument()

    expect(within(people).getByText('Новые кандидаты')).toBeInTheDocument()
    expect(within(people).getByTestId('kpi-people-new')).toHaveTextContent('1')

    expect(within(recruitment).getByText('Заявки в подборе')).toBeInTheDocument()
    expect(within(recruitment).getByTestId('kpi-applications-started')).toHaveTextContent('2')
    expect(within(recruitment).queryByText('Отклики')).not.toBeInTheDocument()

    expect(within(leads).getByTestId('acquisition-sources')).toHaveTextContent('facebook')
    expect(within(leads).getByTestId('acquisition-sources')).toHaveTextContent('website')
    expect(within(leads).getByTestId('acquisition-vacancies')).toHaveTextContent('Vacancy A')
    expect(within(leads).getByTestId('acquisition-vacancies')).toHaveTextContent('Vacancy B')
    expect(within(recruitment).getByTestId('recruitment-vacancies')).toHaveTextContent('Vacancy A')
    expect(within(recruitment).getByTestId('recruitment-vacancies')).toHaveTextContent('Vacancy B')

    expect(within(recruitment).getByTestId('current-status')).toHaveTextContent('Текущий статус заявок в подборе')
    expect(within(recruitment).getByTestId('current-status')).toHaveTextContent('Нанят')
    expect(screen.queryByText('Нанято за период')).not.toBeInTheDocument()
    expect(screen.queryByText('application_status_is_current_snapshot_of_started_cohort')).not.toBeInTheDocument()

    expect(within(recruitment).getByTestId('recruitment-vacancies')).toHaveTextContent('Без вакансии')
    expect(within(recruitment).getByTestId('recruitment-recruiters')).toHaveTextContent('Не назначен')
  })

  it('hides the historical gap at zero and shows a neutral line when it is positive', () => {
    const { rerender } = renderPanel(overview())
    expect(screen.queryByTestId('historical-gap')).not.toBeInTheDocument()

    rerender(
      <I18nProvider initialLocale="ru">
        <PanelBridge
          data={overview({
            historical_gap: { linked_recruitment_leads_without_application: 3 },
            acquisition: { leads_received: 3 },
          })}
        />
      </I18nProvider>,
    )
    const gap = screen.getByTestId('historical-gap')
    expect(gap).toHaveTextContent('Исторические отклики без записи участия: 3')
    expect(gap.textContent ?? '').not.toMatch(/ошибка|потерян/i)
    expect(gap.getAttribute('title')).toMatch(/не восстановленные/i)
  })

  it('keeps people and recruitment visible when there are no leads', () => {
    renderPanel(
      overview({
        people: { time_basis: 'candidate.created_at', new_candidates: 3 },
        recruitment: {
          applications_started: 2,
          by_current_status: [{ status: 'applied', count: 2 }],
        },
      }),
    )

    expect(screen.getByTestId('overview-acquisition')).toHaveTextContent('Нет откликов за выбранный период.')
    expect(screen.getByTestId('overview-people')).toHaveTextContent('3')
    expect(screen.getByTestId('overview-recruitment')).toHaveTextContent('2')
  })
})
