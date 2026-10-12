import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PresenceToggle } from './PresenceToggle'

describe('PresenceToggle', () => {
  it('keeps unknown distinct from an explicit no, and uses the brand accent for yes', () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <PresenceToggle value={null} yesLabel="Есть" noLabel="Нет" onChange={onChange} />,
    )
    const group = screen.getByRole('group')
    expect(group.getAttribute('data-presence')).toBe('unknown')
    expect(group.className).toMatch(/border-dashed/)
    expect(group.className).not.toMatch(/bg-slate-900/)

    rerender(<PresenceToggle value={false} yesLabel="Есть" noLabel="Нет" onChange={onChange} />)
    const no = screen.getByRole('button', { name: 'Нет' })
    expect(screen.getByRole('group').getAttribute('data-presence')).toBe('no')
    expect(no.className).toMatch(/bg-slate-100/)
    expect(no.className).not.toMatch(/bg-slate-900/)

    rerender(<PresenceToggle value={true} yesLabel="Есть" noLabel="Нет" onChange={onChange} />)
    const yes = screen.getByRole('button', { name: 'Есть' })
    expect(screen.getByRole('group').getAttribute('data-presence')).toBe('yes')
    expect(yes.className).toMatch(/bg-brand-600/)
    expect(yes.className).not.toMatch(/bg-slate-900/)

    fireEvent.click(yes)
    expect(onChange).toHaveBeenCalledWith(true)
  })
})
