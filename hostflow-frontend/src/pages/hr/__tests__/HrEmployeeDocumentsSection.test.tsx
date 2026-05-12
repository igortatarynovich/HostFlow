import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from '../../../i18n'
import type { Document } from '../../../api/types'
import { HrEmployeeDocumentsSection } from '../HrEmployeeDocumentsSection'

const { mockListDocs, mockGetCtx, mockDownload } = vi.hoisted(() => ({
  mockListDocs: vi.fn(),
  mockGetCtx: vi.fn(),
  mockDownload: vi.fn(),
}))

vi.mock('../../../api/workforce', () => ({
  listWorkforceEmployeeDocuments: (...args: unknown[]) => mockListDocs(...args),
  getHrOperationalContext: (...args: unknown[]) => mockGetCtx(...args),
  recordWorkforceDocumentHrReview: vi.fn(),
}))

vi.mock('../../../api/documents', () => ({
  downloadDocumentFile: (...args: unknown[]) => mockDownload(...args),
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
    mockListDocs.mockResolvedValue([{ document: baseDoc, daysLeft: null }])
    mockGetCtx.mockResolvedValue({
      hr_case: null,
      document_links: [],
      required_document_types: [],
    })
    mockDownload.mockResolvedValue({ blob: new Blob(['%PDF-1.4'], { type: 'application/pdf' }) })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows Open when document has id (Hub path; workforce list has no recruitment file_url)', async () => {
    renderSection()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Open' })).toBeInTheDocument()
    })
  })

  it('calls downloadDocumentFile(documentId) when Open is clicked', async () => {
    vi.spyOn(window, 'open').mockImplementation(() => null)
    const user = userEvent.setup()
    renderSection()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Open' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Open' }))
    await waitFor(() => {
      expect(mockDownload).toHaveBeenCalledWith('doc-uuid-1')
    })
  })

  it('does not show Open when document id is empty (whitespace)', async () => {
    mockListDocs.mockResolvedValue([{ document: { ...baseDoc, id: '   ' }, daysLeft: null }])
    renderSection()
    await waitFor(() => expect(screen.getByText('Passport')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Open' })).not.toBeInTheDocument()
  })
})
