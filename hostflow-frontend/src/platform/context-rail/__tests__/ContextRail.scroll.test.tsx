import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { ObjectDecision } from '../../decision-model/types'
import { ContextRail } from '../ContextRail'

const DECISION: ObjectDecision = {
  stateId: 'sales.contact',
  currentState: 'Позвонить',
  primaryAction: { id: 'call', label: 'Позвонить', href: 'tel:+48111' },
  requiredContext: ['summary'],
}

describe('ContextRail scroll', () => {
  it('owns the only vertical scrollbar (parent rail is overflow-hidden)', () => {
    const { container } = render(
      <MemoryRouter>
        <ContextRail
          header={{ title: 'Acme' }}
          decision={DECISION}
          onClose={() => undefined}
          contextSlots={{ summary: <p>answers</p> }}
        />
      </MemoryRouter>,
    )
    const root = container.querySelector('[data-context-rail]')
    expect(root?.className).toContain('overflow-y-auto')
    expect(root?.className).toContain('h-full')
    expect(root?.className).not.toContain('overscroll-contain')
    expect(container.querySelector('[data-context-rail-zone="scroll"]')?.className ?? '').not.toContain(
      'overflow-y-auto',
    )
  })
})
