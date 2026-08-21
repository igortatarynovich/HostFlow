import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { I18nProvider } from '../../../i18n'
import type { Application } from '../../../api/types/application'
import { ApplicationWorkspaceCapabilityHost } from '../ApplicationWorkspaceCapabilityHost'
import { EntityWorkspaceCapabilityHost } from '../EntityWorkspaceCapabilityHost'
import type { WorkspaceContributionDefinition } from '../contribution'

const APPLICATION: Application = {
  id: 'app-1',
  module: 'recruitment',
  contact: { name: 'Ada' },
  title: 'Ada',
  status: 'new',
  tab_bucket: 'new',
}

function contribution(
  host: 'entity_workspace' | 'application_workspace',
  region: 'overview' | 'rail',
  ordering: number,
): WorkspaceContributionDefinition {
  return {
    class: 'module_contribution',
    capability_id: 'fixture.optional_addon',
    owner: 'fixture',
    contributor: 'fixture',
    host,
    consumer: host === 'application_workspace' ? 'recruitment_application' : 'entity_workspace',
    component_id: 'workspace.fixture.optional_addon',
    placement: { region },
    ordering,
    visibility: 'entitlement',
    permissions: [],
    state_owner: 'fixture',
    actions: [],
    events: [],
    license: 'optional',
    conflicts: [],
  }
}

describe('host runtime equivalence', () => {
  it('EntityWorkspaceCapabilityHost places contributions by the same region protocol', () => {
    const { container } = render(
      <EntityWorkspaceCapabilityHost
        entity={{ resourceType: 'candidate', resourceId: 'cand-1' }}
        onClose={() => undefined}
        onRefresh={() => undefined}
        contributions={[contribution('entity_workspace', 'overview', 10)]}
      />,
    )
    const host = container.querySelector('[data-workspace-capability-host="entity_workspace"]')
    expect(host).toBeTruthy()
    expect(host?.getAttribute('data-proof-consumer')).toBeNull()
    expect(container.querySelector('[data-host-region="overview"]')).toBeTruthy()
    expect(container.querySelector('[data-capability-id="fixture.optional_addon"]')).toBeTruthy()
    expect(container.querySelector('[data-host-region="header"]')).toBeNull()
    expect(container.querySelector('[data-host-region="decision"]')).toBeNull()
  })

  it('ApplicationWorkspaceCapabilityHost still places G4 chrome and the same regions', () => {
    const { container } = render(
      <I18nProvider>
        <ApplicationWorkspaceCapabilityHost
          application={APPLICATION}
          patching={false}
          onClose={() => undefined}
          onRefresh={() => undefined}
          onStage={() => undefined}
          contributions={[contribution('application_workspace', 'overview', 10)]}
        />
      </I18nProvider>,
    )
    const host = container.querySelector('[data-workspace-capability-host="application_workspace"]')
    expect(host).toBeTruthy()
    expect(host?.getAttribute('data-proof-consumer')).toBe('recruitment_application')
    expect(container.querySelector('[data-host-region="header"]')).toBeTruthy()
    expect(container.querySelector('[data-host-region="decision"]')).toBeTruthy()
    expect(container.querySelector('[data-host-region="overview"]')).toBeTruthy()
    expect(container.querySelector('[data-capability-id="fixture.optional_addon"]')).toBeTruthy()
  })
})
