import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { TransferReadinessReport as TransferReadinessReportData } from '../../../api/candidates'
import { I18nProvider } from '../../../i18n'
import TransferReadinessReport from '../TransferReadinessReport'

const blockedReport: TransferReadinessReportData = {
  candidate_id: 'cand-1',
  policy_version: 'transfer_policy_v1',
  transfer_allowed: false,
  handoff_create_allowed: false,
  destinations_allowed: [],
  required_documents: ['passport', 'work_permit'],
  missing_documents: ['work_permit'],
  pending_verification_documents: ['driver_license'],
  missing_data_fields: [{ field_code: 'phone', label: 'Phone' }],
  required_confirmations: [{ block_key: 'Passport / ID', confirmed_by_role: 'employee' }],
  approved_overrides: ['visa'],
  source_layers: ['document_packs', 'recruitment_package', 'recruiter_confirmation'],
  blocking_reasons: [
    {
      code: 'missing_required_document',
      message: "Required document 'work_permit' is missing.",
      source_layer: 'document_packs',
    },
    {
      code: 'pending_document_verification',
      message: "Required document 'driver_license' is not verified yet.",
      source_layer: 'document_packs',
    },
    {
      code: 'missing_data_field',
      message: 'Missing required data: Phone',
      source_layer: 'recruitment_package',
    },
    {
      code: 'unconfirmed_block',
      message: 'Recruiter must confirm reviewed block: Passport / ID',
      source_layer: 'recruiter_confirmation',
      block_key: 'Passport / ID',
    },
  ],
}

describe('TransferReadinessReport', () => {
  it('renders grouped blocking reasons by source_layer from API report only', () => {
    render(
      <I18nProvider>
        <TransferReadinessReport report={blockedReport} />
      </I18nProvider>,
    )

    expect(screen.getByText('Transfer readiness')).toBeInTheDocument()
    expect(screen.getByText('Stage → ready_for_handoff: ✗')).toBeInTheDocument()
    expect(screen.getByText('Create handoff: ✗')).toBeInTheDocument()

    expect(screen.getByText("Required document 'work_permit' is missing.")).toBeInTheDocument()
    expect(screen.getByText("Required document 'driver_license' is not verified yet.")).toBeInTheDocument()
    expect(screen.getByText('Missing required data: Phone')).toBeInTheDocument()
    expect(screen.getByText('Recruiter must confirm reviewed block: Passport / ID')).toBeInTheDocument()

    expect(screen.getByText('document packs')).toBeInTheDocument()
    expect(screen.getByText('recruitment package')).toBeInTheDocument()
    expect(screen.getByText('recruiter confirmation')).toBeInTheDocument()

    expect(screen.getByText('work_permit')).toBeInTheDocument()
    expect(screen.getByText('driver_license')).toBeInTheDocument()
    expect(screen.getByText('Phone')).toBeInTheDocument()
    expect(screen.getByText('Passport / ID')).toBeInTheDocument()
    expect(screen.getByText('visa')).toBeInTheDocument()
  })

  it('calls onConfirmBlock with block_key from required_confirmations', async () => {
    const onConfirmBlock = vi.fn()
    render(
      <I18nProvider>
        <TransferReadinessReport report={blockedReport} canConfirm onConfirmBlock={onConfirmBlock} />
      </I18nProvider>,
    )

    screen.getByRole('button', { name: /Confirm reviewed/i }).click()
    expect(onConfirmBlock).toHaveBeenCalledWith('Passport / ID')
  })
})
