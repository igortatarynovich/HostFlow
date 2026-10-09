import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { I18nProvider } from '../../i18n'
import RecruitmentEfficiencyDashboard from '../RecruitmentEfficiencyDashboard'
import type { RecruitmentOverviewResponse } from '../../api/analytics'

const { mockOverview, mockContact, mockDocs, mockApiGet } = vi.hoisted(() => ({
  mockOverview: vi.fn(),
  mockContact: vi.fn(),
  mockDocs: vi.fn(),
  mockApiGet: vi.fn(),
}))

vi.mock('../../api/analytics', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/analytics')>()
  return {
    ...actual,
    getRecruitmentOverview: mockOverview,
    getContactAttemptStats: mockContact,
    getDocumentStats: mockDocs,
  }
})

vi.mock('../../components/nav/PageHeader', () => ({
  PageHeader: ({ secondaryActions }: { secondaryActions?: unknown }) => <div>{secondaryActions as never}</div>,
}))

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  const client = actual.default
  client.get = mockApiGet as typeof client.get
  return { ...actual, default: client }
})

const emptyOverview: RecruitmentOverviewResponse = {
  period: { from: null, to: null },
  acquisition: {
    time_basis: 'lead.created_at',
    new_returning_rule: 'candidate_created_at_strictly_before_lead_created_at_is_returning',
    leads_received: 2,
    unique_candidates_linked: 1,
    new_candidates: 1,
    returning_candidates: 1,
    leads_with_application: 2,
    leads_duplicated: 0,
    leads_in_duplicate_review: 0,
    by_source: [],
    by_vacancy: [],
  },
  recruitment: {
    time_basis: 'recruitment_application.applied_at',
    applications_started: 2,
    by_current_status: [],
    by_vacancy: [],
    by_recruiter: [],
  },
  people: { time_basis: 'candidate.created_at', new_candidates: 1 },
  stages: {
    current: {
      semantics: 'current_candidate_stage_snapshot',
      date_range_applied: false,
      company_basis: 'candidate.company_id',
      vacancy_basis: 'candidate.vacancy_id',
      total_candidates: 0,
      by_stage: [],
    },
    transitions: {
      time_basis: 'candidate_stage_history.at',
      company_attribution: 'not_requested',
      vacancy_attribution: 'not_requested',
      total: 0,
      entered_by_stage: [],
      by_transition: [],
    },
  },
  contacts: {
    time_basis: 'contact_attempt.attempted_at',
    successful_contact_rule: 'result_equals_answered',
    company_attribution: 'not_requested',
    vacancy_attribution: 'not_requested',
    attempts_total: 0,
    candidates_contacted: 0,
    successful_attempts: 0,
    by_result: [],
    by_channel: [],
    by_recruiter: [],
  },
  reasons: {
    semantics: 'current_candidate_status_reason_snapshot',
    date_range_applied: false,
    company_basis: 'candidate.company_id',
    vacancy_basis: 'candidate.vacancy_id',
    rejected: { stage: 'rejected', candidates: 0, candidates_without_reason: 0, by_reason: [] },
    declined: { stage: 'declined', candidates: 0, candidates_without_reason: 0, by_reason: [] },
  },
  historical_gap: { linked_recruitment_leads_without_application: 0 },
  limitations: [],
}

describe('Recruitment overview data source', () => {
  beforeEach(() => {
    mockOverview.mockReset()
    mockContact.mockReset()
    mockDocs.mockReset()
    mockApiGet.mockReset()
    mockOverview.mockResolvedValue(emptyOverview)
    mockApiGet.mockResolvedValue({ data: { items: [] } })
  })

  it('loads recruitment-overview and does not call the legacy cohort endpoints', async () => {
    render(
      <MemoryRouter initialEntries={['/app/overview?module=recruitment']}>
        <I18nProvider initialLocale="ru">
          <RecruitmentEfficiencyDashboard />
        </I18nProvider>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockOverview).toHaveBeenCalled()
    })

    expect(mockContact).not.toHaveBeenCalled()
    expect(mockDocs).not.toHaveBeenCalled()
    const urls = mockApiGet.mock.calls.map((call) => String(call[0]))
    expect(urls.some((url) => url.includes('candidate-slices'))).toBe(false)
    expect(urls.some((url) => url.includes('contact-attempt-stats'))).toBe(false)
    expect(urls.some((url) => url.includes('document-stats'))).toBe(false)
    expect(await screen.findByTestId('kpi-leads-received')).toHaveTextContent('2')
    expect(screen.getByTestId('kpi-people-new')).toHaveTextContent('1')
    expect(screen.getByTestId('kpi-applications-started')).toHaveTextContent('2')
    expect(screen.getByText('Текущие этапы')).toBeInTheDocument()
    expect(screen.getByText('Попытки контакта')).toBeInTheDocument()
    expect(screen.queryByText('Статус документов')).not.toBeInTheDocument()
  })
})
