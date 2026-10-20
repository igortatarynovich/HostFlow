import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../i18n'
import DateInput from './DateInput'

describe('DateInput calendar', () => {
  it('opens a page-level calendar and returns the chosen day', () => {
    const onValueChange = vi.fn()
    render(
      <I18nProvider initialLocale="ru">
        <DateInput value="2026-11-01" onValueChange={onValueChange} />
      </I18nProvider>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Календарь' }))
    const panel = document.body.querySelector('[data-testid="date-input-calendar"]')
    expect(panel).toBeTruthy()
    expect(panel?.parentElement).toBe(document.body)
    expect((panel as HTMLElement).className).toContain('fixed')
    fireEvent.click(screen.getByRole('button', { name: '15' }))
    expect(onValueChange).toHaveBeenCalledWith('2026-11-15')
    expect(document.body.querySelector('[data-testid="date-input-calendar"]')).toBeNull()
  })
})
