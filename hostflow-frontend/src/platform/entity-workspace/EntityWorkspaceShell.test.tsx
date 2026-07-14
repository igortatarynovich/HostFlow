import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { EntityWorkspaceShell } from './EntityWorkspaceShell'
import { ENTITY_WORKSPACE_MOCKS } from './mocks/entityWorkspaceMocks'

function expectFiveZones(container: HTMLElement) {
  expect(container.querySelector('[data-entity-workspace-zone="header"]')).toBeTruthy()
  expect(container.querySelector('[data-entity-workspace-zone="summary"]')).toBeTruthy()
  expect(container.querySelector('[data-entity-workspace-zone="navigation"]')).toBeTruthy()
  expect(container.querySelector('[data-entity-workspace-zone="content"]')).toBeTruthy()
  expect(container.querySelector('[data-entity-workspace-zone="context-rail"]')).toBeTruthy()
}

describe('EntityWorkspaceShell', () => {
  it('renders five zones for candidate, client, and order mocks with same shell', () => {
    for (const key of ['candidate', 'client', 'order'] as const) {
      const mock = ENTITY_WORKSPACE_MOCKS[key]
      const { container, unmount } = render(
        <div className="h-[640px]">
          <EntityWorkspaceShell model={mock.model} passport={mock.passport} resourceTypeLabel={mock.resourceTypeLabel} />
        </div>,
      )
      expectFiveZones(container)
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(mock.passport.sections.identity.title)
      unmount()
    }
  })

  it('shows outcome in header for terminal order mock', () => {
    const mock = ENTITY_WORKSPACE_MOCKS.order
    render(
      <div className="h-[640px]">
        <EntityWorkspaceShell model={mock.model} passport={mock.passport} resourceTypeLabel={mock.resourceTypeLabel} />
      </div>,
    )
    const header = document.querySelector('[data-entity-workspace-zone="header"]')
    expect(header).toBeTruthy()
    expect(within(header as HTMLElement).getByTitle('Заказ закрыт')).toBeTruthy()
  })

  it('navigation switches content section without layout change', async () => {
    const user = userEvent.setup()
    const mock = ENTITY_WORKSPACE_MOCKS.candidate
    render(
      <div className="h-[640px]">
        <EntityWorkspaceShell model={mock.model} passport={mock.passport} resourceTypeLabel={mock.resourceTypeLabel} />
      </div>,
    )
    const nav = screen.getByLabelText('Разделы')
    await user.click(within(nav).getByRole('button', { name: 'Контакты' }))
    expect(screen.getByText('+48 600 000 000')).toBeTruthy()
  })

  it('harness switches between mocks', async () => {
    const user = userEvent.setup()
    const { EntityWorkspaceShellHarness } = await import('./EntityWorkspaceShellHarness')
    render(<EntityWorkspaceShellHarness />)
    await user.click(screen.getByRole('button', { name: 'order' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Заказ SO-441')
  })
})
