import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { I18nProvider } from '../../../i18n'
import { DocumentPackCards } from '../DocumentPackCards'
import type { DocumentPackProjection } from '../../../api/types'

const samplePacks: DocumentPackProjection[] = [
  {
    code: 'driver_pack',
    label: 'Driver Pack',
    status: 'gaps',
    skeleton: false,
    applies: true,
    ref_pack_codes: ['pl_transport_driver'],
    required: ['driver_license', 'code_95'],
    present: ['code_95'],
    missing: ['driver_license'],
    expired: [],
    expiring_soon: [],
    missing_expiry: [],
    gaps: ['driver_license'],
    blockers: ['driver_license'],
    warnings: [],
    expiry: {
      all_documents_valid: false,
      has_expiring_documents: false,
      has_expired_documents: false,
      has_missing_expiry: false,
    },
  },
  {
    code: 'client_pack',
    label: 'Client Pack',
    status: 'skeleton',
    skeleton: true,
    applies: true,
    ref_pack_codes: ['client_specific_requirements'],
    required: [],
    present: [],
    missing: [],
    expired: [],
    expiring_soon: [],
    missing_expiry: [],
    gaps: [],
    blockers: [],
    warnings: [],
    expiry: {
      all_documents_valid: true,
      has_expiring_documents: false,
      has_expired_documents: false,
      has_missing_expiry: false,
    },
  },
]

describe('DocumentPackCards', () => {
  it('renders pack labels, status, and gap counts', () => {
    render(
      <I18nProvider>
        <DocumentPackCards packs={samplePacks} />
      </I18nProvider>,
    )

    expect(screen.getByText('Driver Pack')).toBeInTheDocument()
    expect(screen.getByText('Client Pack')).toBeInTheDocument()
    expect(screen.getByText('Gaps')).toBeInTheDocument()
    expect(screen.getByText('Skeleton')).toBeInTheDocument()
    expect(screen.getByText('Driver License')).toBeInTheDocument()
  })
})
