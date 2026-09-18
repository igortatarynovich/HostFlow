import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../../i18n'
import CandidateMissingPanel from '../CandidateMissingPanel'

function renderPanel(
  missing: {
    code: 'candidate_deleted' | 'candidate_not_found'
    applicationId: string | null
    canRecreate: boolean
  },
  onRecreate?: () => void,
) {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">
        <CandidateMissingPanel missing={missing} onRecreate={onRecreate} />
      </I18nProvider>
    </MemoryRouter>,
  )
}

describe('CandidateMissingPanel', () => {
  it('explains that the candidate does not exist', () => {
    renderPanel({ code: 'candidate_not_found', applicationId: null, canRecreate: false })
    expect(screen.getByText('Candidate does not exist')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /back to candidates/i })).toBeInTheDocument()
  })

  it('offers recreate when a deleted candidate still has an application', async () => {
    const onRecreate = vi.fn()
    renderPanel(
      { code: 'candidate_deleted', applicationId: 'app-1', canRecreate: true },
      onRecreate,
    )
    expect(screen.getByText('Candidate was deleted')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /create again/i }))
    expect(onRecreate).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('link', { name: /open application/i })).toHaveAttribute(
      'href',
      expect.stringContaining('app-1'),
    )
  })
})
