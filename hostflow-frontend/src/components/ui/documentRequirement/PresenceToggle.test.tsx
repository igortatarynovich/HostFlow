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

  it('offers ordered only when the requirement allows a procedure state', () => {
    const onChange = vi.fn()
    const onOrdered = vi.fn()
    const { rerender } = render(
      <PresenceToggle value={null} yesLabel="Есть" noLabel="Нет" onChange={onChange} />,
    )
    expect(screen.queryByRole('button', { name: 'Заказано' })).toBeNull()

    rerender(
      <PresenceToggle
        value="ordered"
        yesLabel="Есть"
        noLabel="Нет"
        orderedLabel="Заказано"
        onChange={onChange}
        onOrdered={onOrdered}
      />,
    )
    const ordered = screen.getByRole('button', { name: 'Заказано' })
    expect(screen.getByRole('group').getAttribute('data-presence')).toBe('ordered')
    expect(ordered.className).toMatch(/bg-slate-100/)
    fireEvent.click(ordered)
    expect(onOrdered).toHaveBeenCalledOnce()
    expect(onChange).not.toHaveBeenCalled()
  })
})
