import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../../i18n'
import type { Application } from '../../../api/types/application'
import { ApplicationWorkspaceCapabilityHost } from '../ApplicationWorkspaceCapabilityHost'
import { EntityWorkspaceCapabilityHost } from '../EntityWorkspaceCapabilityHost'
import { CANDIDATE_ENTITY_HOST_CONTRIBUTIONS, ENTITY_EQUIVALENCE_CONSUMER_ID, ENTITY_EQUIVALENCE_HOST_ID } from '../candidateEntity'
import type { WorkspaceContributionDefinition } from '../contribution'

vi.mock('../../../api/communications', () => ({
  listCommunicationThreads: vi.fn(async () => ({ items: [] })),
}))
vi.mock('../../../api/formsPlatform', () => ({
  listFormsPlatformHandlers: vi.fn(async () => []),
}))
vi.mock('../../../api/client', () => ({
  api: { get: vi.fn(async () => ({ data: { items: [] } })) },
}))

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

  it('Candidate Entity bind is host-equivalence, not a second G4 proof', () => {
    expect(ENTITY_EQUIVALENCE_HOST_ID).toBe('entity_workspace')
    expect(ENTITY_EQUIVALENCE_CONSUMER_ID).toBe('candidate')
    expect(CANDIDATE_ENTITY_HOST_CONTRIBUTIONS.map((row) => row.capability_id)).toEqual([
      'communication',
      'forms',
      'documents',
    ])
    for (const row of CANDIDATE_ENTITY_HOST_CONTRIBUTIONS) {
      expect(row.host).toBe('entity_workspace')
      expect(row.consumer).toBe('candidate')
      expect(row.placement.region).toBe('platform_slot')
    }
  })

  it('Entity host chrome adapter still places platform_slot through the contribution contract', () => {
    const { container } = render(
      <MemoryRouter>
        <I18nProvider>
          <EntityWorkspaceCapabilityHost
            entity={{ resourceType: 'candidate', resourceId: 'cand-1' }}
            onClose={() => undefined}
            onRefresh={() => undefined}
            contributions={CANDIDATE_ENTITY_HOST_CONTRIBUTIONS}
          >
            {(placed) => (
              <div data-entity-chrome-adapter="shell">
                <div data-host-region="platform_slot">{placed.platform_slot}</div>
              </div>
            )}
          </EntityWorkspaceCapabilityHost>
        </I18nProvider>
      </MemoryRouter>,
    )
    expect(container.querySelector('[data-workspace-capability-host="entity_workspace"]')).toBeTruthy()
    expect(container.querySelector('[data-proof-consumer]')).toBeNull()
    expect(container.querySelector('[data-entity-chrome-adapter="shell"]')).toBeTruthy()
    expect(container.querySelector('[data-entity-workspace-slot="communication"]')).toBeTruthy()
    expect(container.querySelector('[data-entity-workspace-slot="forms"]')).toBeTruthy()
    expect(container.querySelector('[data-capability-id="communication"]')).toBeTruthy()
    expect(container.querySelector('[data-capability-id="forms"]')).toBeTruthy()
    expect(container.querySelector('[data-capability-id="documents"]')).toBeTruthy()
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
    expect(host?.className).toContain('overflow-hidden')
    expect(host?.className).not.toContain('overflow-y-auto')
    const scroll = container.querySelector('[data-host-region="overview"]')?.parentElement
    expect(scroll?.className).toContain('overflow-y-auto')
    expect(scroll?.className).not.toContain('overscroll-contain')
  })
})
