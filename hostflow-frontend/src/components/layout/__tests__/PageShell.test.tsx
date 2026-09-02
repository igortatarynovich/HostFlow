import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PageShell, PageShellBody, PageShellHeader } from '../PageShell'

describe('PageShell', () => {
  it('allows the page body to scroll instead of clipping to the viewport', () => {
    const { container } = render(
      <PageShell>
        <PageShellHeader>chrome</PageShellHeader>
        <PageShellBody>content</PageShellBody>
      </PageShell>,
    )
    const shell = container.querySelector('[data-hf-page-shell]')
    const body = container.querySelector('[data-hf-page-shell-body]')
    expect(shell?.className).toContain('min-w-0')
    expect(shell?.className).toContain('overflow-y-auto')
    expect(shell?.className).not.toContain('overflow-hidden')
    expect(body?.className).toContain('overflow-y-auto')
    expect(body?.className).toContain('min-w-0')
  })
})
