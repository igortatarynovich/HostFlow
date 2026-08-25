import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { I18nProvider } from '../../../../i18n'
import RequirementsWorkspaceSummaryBar from '../RequirementsWorkspaceSummaryBar'

describe('RequirementsWorkspaceSummaryBar', () => {
  it('shows intermediate state when requirements closed but handoff_ready is false', () => {
    render(
      <I18nProvider>
        <RequirementsWorkspaceSummaryBar
          summary={{
            total_requirements: 5,
            fulfilled_count: 5,
            blocking_open_count: 0,
            pending_review_count: 0,
            all_fulfilled: true,
            handoff_ready: false,
          }}
          transferReadiness={{
            transfer_allowed: false,
            handoff_create_allowed: false,
            blocking_reasons: [{ code: 'missing_data_field', message: 'Missing phone', source_layer: 'recruitment_package' }],
            requirement_gate: { satisfied: true },
          }}
        />
      </I18nProvider>,
    )

    expect(screen.getByText('Requirements closed — handoff may need extra confirmations')).toBeInTheDocument()
    expect(screen.queryByText('Ready for handoff')).not.toBeInTheDocument()
  })

  it('shows ready for handoff when summary.handoff_ready is true', () => {
    render(
      <I18nProvider>
        <RequirementsWorkspaceSummaryBar
          summary={{
            total_requirements: 5,
            fulfilled_count: 5,
            blocking_open_count: 0,
            pending_review_count: 0,
            all_fulfilled: true,
            handoff_ready: true,
          }}
          transferReadiness={{
            transfer_allowed: true,
            handoff_create_allowed: true,
            blocking_reasons: [],
          }}
        />
      </I18nProvider>,
    )

    expect(screen.getByText('Ready for handoff')).toBeInTheDocument()
  })
})
