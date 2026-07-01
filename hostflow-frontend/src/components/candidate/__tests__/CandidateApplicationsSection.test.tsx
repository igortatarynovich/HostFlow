import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../../i18n'
import CandidateApplicationsSection from '../CandidateApplicationsSection'
import type { RecruitmentApplicationOut } from '../../../api/candidates'

const { mockList, mockGetVacancy } = vi.hoisted(() => ({
  mockList: vi.fn(),
  mockGetVacancy: vi.fn(),
}))

vi.mock('../../../api/candidates', () => ({
  listCandidateRecruitmentApplications: (...args: unknown[]) => mockList(...args),
}))

vi.mock('../../../api/vacancies', () => ({
  getVacancy: (...args: unknown[]) => mockGetVacancy(...args),
}))

function renderSection(props: {
  candidateId?: string
  locale?: string
  legacyVacancyId?: string | null
}) {
  const {
    candidateId = 'cand-test-1',
    locale = 'en',
    legacyVacancyId = null,
  } = props
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">
        <CandidateApplicationsSection
          candidateId={candidateId}
          locale={locale}
          legacyVacancyId={legacyVacancyId}
        />
      </I18nProvider>
    </MemoryRouter>,
  )
}

const sampleApp: RecruitmentApplicationOut = {
  id: 'app-1',
  candidate_id: 'cand-test-1',
  lead_id: 'lead-1',
  vacancy_id: 'vac-from-api',
  source: 'meta',
  recruiter_id: null,
  applied_at: '2026-03-15T14:30:00.000Z',
  status: 'active',
  application_cycle: null,
  meta: {},
}

describe('CandidateApplicationsSection', () => {
  beforeEach(() => {
    window.localStorage.setItem('hf:ui:lang', 'en')
    mockList.mockResolvedValue([])
    mockGetVacancy.mockImplementation(async (id: string) => ({
      id,
      title: `Title for ${id}`,
    }))
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows a real application row when API returns applications', async () => {
    mockList.mockResolvedValue([sampleApp])
    renderSection({})

    await waitFor(() => {
      expect(screen.getByText('Applications & intent')).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText('meta')).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /Title for vac-from-api/i })).toHaveAttribute(
        'href',
        expect.stringContaining('vac-from-api'),
      )
    })
    expect(screen.queryByText(/Legacy \(dossier\)/i)).not.toBeInTheDocument()
    expect(
      screen.queryByText(
        /No application rows yet — showing the vacancy linked on the candidate dossier \(legacy\)/i,
      ),
    ).not.toBeInTheDocument()
  })

  it('shows legacy dossier row when list is empty but legacyVacancyId is set', async () => {
    mockList.mockResolvedValue([])
    renderSection({ legacyVacancyId: 'vac-legacy-only' })

    await waitFor(() => {
      expect(
        screen.getByText(
          /No application rows yet — showing the vacancy linked on the candidate dossier \(legacy\)/i,
        ),
      ).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText('Legacy (dossier)')).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /Title for vac-legacy-only/i })).toHaveAttribute(
        'href',
        expect.stringContaining('vac-legacy-only'),
      )
    })
  })

  it('does not show legacy fallback when real applications exist (even if legacyVacancyId is passed)', async () => {
    mockList.mockResolvedValue([sampleApp])
    renderSection({ legacyVacancyId: 'vac-legacy-only' })

    await waitFor(() => {
      expect(screen.getByText('meta')).toBeInTheDocument()
    })
    expect(screen.queryByText('Legacy (dossier)')).not.toBeInTheDocument()
    expect(
      screen.queryByText(
        /No application rows yet — showing the vacancy linked on the candidate dossier \(legacy\)/i,
      ),
    ).not.toBeInTheDocument()
  })

  it('shows empty state when no applications and no legacy vacancy', async () => {
    mockList.mockResolvedValue([])
    renderSection({ legacyVacancyId: null })

    await waitFor(() => {
      expect(
        screen.getByText('No application records for this candidate yet.'),
      ).toBeInTheDocument()
    })
    expect(screen.queryByText('Legacy (dossier)')).not.toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})
