import { type ReactElement, useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '../../../i18n'
import {
  Button,
  Checkbox,
  EmptyState,
  FormField,
  IconButton,
  Input,
  Modal,
  Pagination,
  Radio,
  SearchField,
  SemanticSurface,
  Switch,
  Tabs,
} from '../index'

function wrap(ui: ReactElement) {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">{ui}</I18nProvider>
    </MemoryRouter>,
  )
}

describe('P0 UI kit primitives', () => {
  it('renders Button with kit class', () => {
    wrap(<Button variant="primary">Save</Button>)
    expect(screen.getByRole('button', { name: 'Save' })).toHaveClass('btn-primary')
  })

  it('requires IconButton accessible name', () => {
    wrap(
      <IconButton aria-label="Close">
        <span>×</span>
      </IconButton>,
    )
    expect(screen.getByRole('button', { name: 'Close' })).toHaveClass('btn-icon')
  })

  it('wraps search in the input contract', () => {
    wrap(<SearchField aria-label="Search" placeholder="Find" />)
    const field = screen.getByRole('searchbox', { name: 'Search' })
    expect(field).toHaveAttribute('type', 'search')
    expect(field).toHaveClass('input')
  })

  it('renders Input with .input', () => {
    wrap(<Input aria-label="Name" />)
    expect(screen.getByRole('textbox', { name: 'Name' })).toHaveClass('input')
  })

  it('toggles Tabs', async () => {
    const user = userEvent.setup()
    function Harness() {
      const [value, setValue] = useState('a')
      return <Tabs aria-label="Demo" items={[{ id: 'a', label: 'One' }, { id: 'b', label: 'Two' }]} value={value} onChange={setValue} />
    }
    wrap(<Harness />)
    expect(screen.getByRole('tab', { name: 'One' })).toHaveAttribute('aria-selected', 'true')
    await user.click(screen.getByRole('tab', { name: 'Two' }))
    expect(screen.getByRole('tab', { name: 'Two' })).toHaveAttribute('aria-selected', 'true')
  })

  it('shows FormField error in rose, not a local red', () => {
    wrap(
      <FormField label="Email" htmlFor="email" error="Required">
        <Input id="email" />
      </FormField>,
    )
    expect(screen.getByText('Required')).toHaveClass('text-rose-700')
  })

  it('pages with kit Buttons', async () => {
    const user = userEvent.setup()
    const onPageChange = vi.fn()
    wrap(<Pagination page={1} pageSize={10} total={25} onPageChange={onPageChange} />)
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(onPageChange).toHaveBeenCalledWith(2)
  })

  it('applies SemanticSurface tone from the badge palette', () => {
    wrap(<SemanticSurface tone="danger">Blocked</SemanticSurface>)
    expect(screen.getByText('Blocked').closest('section')).toHaveClass('bg-rose-50')
  })

  it('renders EmptyState actions', () => {
    wrap(<EmptyState title="Nothing here" description="Add a record." primaryAction={{ label: 'Create', to: '/new' }} />)
    expect(screen.getByRole('link', { name: 'Create' })).toHaveAttribute('href', '/new')
  })

  it('sets checkbox indeterminate', () => {
    wrap(<Checkbox aria-label="Select page" indeterminate />)
    const box = screen.getByRole('checkbox', { name: 'Select page' }) as HTMLInputElement
    expect(box.indeterminate).toBe(true)
  })

  it('renders Radio and Switch', () => {
    wrap(
      <>
        <Radio name="choice" label="Option A" defaultChecked />
        <Switch label="Enabled" defaultChecked />
      </>,
    )
    expect(screen.getByRole('radio', { name: 'Option A' })).toBeChecked()
    expect(screen.getByRole('switch', { name: 'Enabled' })).toBeChecked()
  })

  it('closes Modal via IconButton', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    wrap(
      <Modal open title="Edit" onClose={onClose}>
        Body
      </Modal>,
    )
    expect(screen.getByText('Edit')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalled()
  })
})
