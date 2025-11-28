import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { UserTable } from '../UserTable'
import type { AdminUser } from '../../../api/types'

const SAMPLE_USERS: AdminUser[] = [
  {
    user_id: 'u-1',
    invite_id: null,
    email: 'admin@example.com',
    role: 'administrator',
    status: 'active',
    is_active: true,
    full_name: 'Администратор',
    short_id: 'ADM1',
    supervisor_id: null,
    companies: [],
    company_ids: [],
    recruiters: [],
  },
  {
    user_id: 'u-2',
    invite_id: null,
    email: 'recruiter@example.com',
    role: 'recruiter',
    status: 'active',
    is_active: true,
    full_name: 'Рекрутер',
    short_id: 'REC1',
    supervisor_id: 'u-1',
    companies: [],
    company_ids: [],
    recruiters: [],
  },
]

const noop = async () => {}

describe('UserTable', () => {
  it('renders role labels and handles selection', () => {
    const handleSelect = vi.fn()
    render(
      <UserTable
        users={SAMPLE_USERS}
        onChangeRole={noop}
        onToggleActive={noop}
        onRevokeRefresh={noop}
        onShowAudit={() => {}}
        onSelect={handleSelect}
        selectedUserId={null}
      />,
    )

    const adminRow = screen.getByText('admin@example.com').closest('tr')!
    expect(adminRow).toBeTruthy()
    expect(within(adminRow).getByText('Администратор', { selector: 'div' })).toBeInTheDocument()

    const recruiterRow = screen.getByText('recruiter@example.com').closest('tr')!
    expect(recruiterRow).toBeTruthy()

    fireEvent.click(recruiterRow!)
    expect(handleSelect).toHaveBeenCalled()
  })
})
