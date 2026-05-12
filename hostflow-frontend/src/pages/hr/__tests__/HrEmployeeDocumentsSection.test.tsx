import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { I18nProvider } from '../../../i18n'
import type { Document } from '../../../api/types'
import { HrEmployeeDocumentsSection } from '../HrEmployeeDocumentsSection'

const { mockListDocs, mockGetCtx } = vi.hoisted(() => ({
  mockListDocs: vi.fn(),
  mockGetCtx: vi.fn(),
}))

vi.mock('../../../api/workforce', () => ({
  listWorkforceEmployeeDocuments: (...args: unknown[]) => mockListDocs(...args),
  getHrOperationalContext: (...args: unknown[]) => mockGetCtx(...args),
  recordWorkforceDocumentHrReview: vi.fn(),
}))

vi.mock('../../../api/documents/list', () => ({
  listDocumentChecks: vi.fn(),
}))

vi.mock('../../../store/useAuth', () => ({
  useAuth: () => ({ me: { role: 'recruiter' } }),
}))

vi.mock('../../../components/Toast', () => ({
  useToast: () => ({ notify: vi.fn() }),
}))

const baseDoc: Document = {
  id: 'doc-uuid-1',
  tenant_id: 't1',
  candidate_id: 'c1',
  kind: 'driver',
  doc_type: 'passport',
  type: 'passport',
  type_code: 'passport',
  requested_from: 'driver',
  process_type: 'none',
  status: 'received',
  reminder_days_before: 0,
  files: [],
  meta: {},
  extra: {},
  meta_json: {},
  reminders: [],
  title: 'Passport',
}

function renderSection() {
  return render(
    <I18nProvider>
      <HrEmployeeDocumentsSection employeeId="emp-1" candidateId="cand-1" />
    </I18nProvider>,
  )
}

describe('HrEmployeeDocumentsSection', () => {
  beforeEach(() => {
    mockListDocs.mockResolvedValue([{ document: baseDoc, downloadUrl: null, daysLeft: null }])
    mockGetCtx.mockResolvedValue({
      hr_case: null,
      document_links: [],
      required_document_types: [],
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows file link when row has downloadUrl (workforce documents API)', async () => {
    mockListDocs.mockResolvedValue([
      { document: baseDoc, downloadUrl: 'https://example.com/presigned.pdf', daysLeft: null },
    ])
    renderSection()
    await waitFor(() => {
      const link = screen.getByRole('link')
      expect(link).toHaveAttribute('href', 'https://example.com/presigned.pdf')
      expect(link).toHaveAttribute('target', '_blank')
    })
  })

  it('does not show file link when downloadUrl is absent', async () => {
    mockListDocs.mockResolvedValue([{ document: baseDoc, downloadUrl: null, daysLeft: null }])
    renderSection()
    await waitFor(() => expect(screen.getByText('Passport')).toBeInTheDocument())
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
})
