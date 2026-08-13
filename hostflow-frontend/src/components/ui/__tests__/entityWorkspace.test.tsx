import { type ReactElement } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '../../../i18n'
import {
  EntityWorkspace,
  EntityWorkspaceHeader,
  EntityWorkspaceRail,
  EntityWorkspaceSummary,
} from '../EntityWorkspace'

function wrap(ui: ReactElement) {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">{ui}</I18nProvider>
    </MemoryRouter>,
  )
}

describe('kit EntityWorkspace', () => {
  it('renders header, summary, tabs, content slot, and rail', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    wrap(
      <EntityWorkspace
        ariaLabel="Inquiry"
        header={<EntityWorkspaceHeader resourceTypeLabel="Inquiry" title="SI-12" backHref="/app/inquiries" />}
        summary={<EntityWorkspaceSummary cards={[{ id: 'status', label: 'Status', value: 'Open' }]} />}
        tabs={{
          items: [
            { id: 'overview', label: 'Overview' },
            { id: 'timeline', label: 'Timeline' },
          ],
          value: 'overview',
          onChange,
        }}
        rail={<EntityWorkspaceRail>Next action</EntityWorkspaceRail>}
      >
        Overview body
      </EntityWorkspace>,
    )
    const root = document.querySelector('[data-entity-workspace="v1"]')
    expect(root).not.toBeNull()
    expect(root?.querySelector('[data-entity-workspace-zone="header"]')).not.toBeNull()
    expect(root?.querySelector('[data-entity-workspace-zone="summary"]')).not.toBeNull()
    expect(root?.querySelector('[data-entity-workspace-zone="navigation"]')).not.toBeNull()
    expect(root?.querySelector('[data-entity-workspace-zone="content"]')).not.toBeNull()
    expect(root?.querySelector('[data-entity-workspace-zone="context-rail"]')).not.toBeNull()
    expect(screen.getByRole('heading', { name: 'SI-12' })).toBeInTheDocument()
    expect(screen.getByText('Overview body')).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Timeline' }))
    expect(onChange).toHaveBeenCalledWith('timeline')
  })

  it('treats timeline as a content slot, not a second product', () => {
    wrap(
      <EntityWorkspace header={<EntityWorkspaceHeader resourceTypeLabel="Entity" title="Row" />}>
        Timeline events
      </EntityWorkspace>,
    )
    expect(screen.getByText('Timeline events')).toBeInTheDocument()
    expect(document.querySelector('[data-entity-workspace-zone="content"]')?.textContent).toContain('Timeline events')
  })
})
