import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../i18n'
import WorkspaceStatusRail from './WorkspaceStatusRail'
import type { WorkspaceStatusSnapshot } from '@hostflow/workspace'
import { WORKSPACE_CONTRACTS_SCHEMA_VERSION } from '@hostflow/workspace'

const baseSnapshot: WorkspaceStatusSnapshot = {
  schema_version: WORKSPACE_CONTRACTS_SCHEMA_VERSION,
  session: {
    context: 'recruitment',
    anchor: {
      anchor_kind: 'candidate',
      anchor_id: 'cand-1',
      tenant_id: 'tenant-1',
    },
    enabled_modules: ['recruitment'],
  },
  contributions: [
    {
      module_key: 'recruitment',
      context: 'recruitment',
      priority: 10,
      severity: 'blocked',
      summary_key: 'workspace.recruitment.readiness.summary',
      blockers: [
        {
          block_id: 'requirement:identity_confirmation',
          label_key: 'Identity confirmation',
          severity: 'blocked',
        },
      ],
      next_action: {
        action_id: 'close_requirement:identity_confirmation',
        module_key: 'recruitment',
        label_key: 'Upload passport',
        permission: 'candidates.manage',
        priority: 10,
        handler_kind: 'navigation',
        handler_ref: '/app/candidates/cand-1/requirements?requirement=identity_confirmation',
      },
    },
  ],
  displayed_next_action: {
    action_id: 'close_requirement:identity_confirmation',
    module_key: 'recruitment',
    label_key: 'Upload passport',
    permission: 'candidates.manage',
    priority: 10,
    handler_kind: 'navigation',
    handler_ref: '/app/candidates/cand-1/requirements?requirement=identity_confirmation',
  },
  aggregated_severity: 'blocked',
}

function renderRail(snapshot: WorkspaceStatusSnapshot | null, loading = false) {
  return render(
    <I18nProvider initialLocale="en">
      <MemoryRouter>
        <WorkspaceStatusRail snapshot={snapshot} loading={loading} />
      </MemoryRouter>
    </I18nProvider>,
  )
}

describe('WorkspaceStatusRail', () => {
  it('shows blockers and next action from aggregated snapshot', () => {
    renderRail(baseSnapshot)
    expect(screen.getByTestId('workspace-status-blockers')).toBeTruthy()
    expect(screen.getByText('Identity confirmation')).toBeTruthy()
    expect(screen.getByTestId('workspace-status-next-action')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Upload passport' })).toBeTruthy()
  })

  it('shows loading state', () => {
    renderRail(null, true)
    expect(screen.getByText(/Checking readiness/i)).toBeTruthy()
  })
})
