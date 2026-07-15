import { useState } from 'react'
import { EntityWorkspaceShell } from './EntityWorkspaceShell'
import { ENTITY_WORKSPACE_MOCKS, type EntityWorkspaceMockKey } from './mocks/entityWorkspaceMocks'

/**
 * Manual QA harness — switch mock entity without changing shell layout.
 * Not routed to production; import in dev page or Storybook when added.
 */
export function EntityWorkspaceShellHarness() {
  const [mockKey, setMockKey] = useState<EntityWorkspaceMockKey>('candidate')
  const mock = ENTITY_WORKSPACE_MOCKS[mockKey]

  return (
    <div className="flex h-[720px] min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 shadow-sm">
      <div className="flex shrink-0 items-center gap-2 border-b border-slate-200 bg-slate-100 px-4 py-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Entity Workspace Harness</span>
        {(Object.keys(ENTITY_WORKSPACE_MOCKS) as EntityWorkspaceMockKey[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setMockKey(key)}
            className={`rounded-lg px-3 py-1 text-sm font-medium capitalize ${
              mockKey === key ? 'bg-brand-700 text-white' : 'bg-white text-slate-700 ring-1 ring-slate-200'
            }`}
          >
            {key}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1">
        <EntityWorkspaceShell
          key={mockKey}
          model={mock.model}
          passport={mock.passport}
          resourceTypeLabel={mock.resourceTypeLabel}
          breadcrumbs={[{ label: 'HostFlow' }, { label: mock.resourceTypeLabel }]}
        />
      </div>
    </div>
  )
}
