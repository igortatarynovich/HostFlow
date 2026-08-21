import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { Checkbox } from '../Checkbox'

describe('Checkbox', () => {
  it('toggles through the primitive, not a page-local input', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<Checkbox checked={false} onChange={onChange} label="Covered at source" />)
    await user.click(screen.getByLabelText('Covered at source'))
    expect(onChange).toHaveBeenCalledWith(true)
  })

  it('does not toggle when disabled', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<Checkbox checked={false} onChange={onChange} label="Locked" disabled />)
    await user.click(screen.getByLabelText('Locked'))
    expect(onChange).not.toHaveBeenCalled()
  })
})
